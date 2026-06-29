# src/services/goal_progress_service.py

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from src.profiles.profile_loader import get_goals
from src.services.manual_activity_service import (
    ManualActivityEntry,
    format_seconds,
    list_manual_activities,
)


ROOT_DIR = Path(__file__).resolve().parents[2]
DB_PATH = ROOT_DIR / "data" / "lazy_coach.db"


@dataclass(frozen=True)
class GoalProgressResult:
    goal_id: str
    title: str
    goal_type: str
    desktop_seconds: int
    manual_seconds: int
    total_seconds: int
    target_seconds: int | None
    limit_seconds: int | None
    status: str
    missing_seconds: int
    remaining_seconds: int
    extra_seconds: int
    manual_entries: list[ManualActivityEntry]


@dataclass(frozen=True)
class GoalProgressDayView:
    activity_date: str
    results: list[GoalProgressResult]


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def today_iso() -> str:
    return date.today().isoformat()


def normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    return [
        str(item).lower()
        for item in value
        if isinstance(item, str)
    ]


def get_progress_rule(goal: dict[str, Any]) -> dict[str, Any]:
    progress_rule = goal.get("progress_rule", {})

    if isinstance(progress_rule, dict):
        return progress_rule

    return {}


def get_activity_filter(goal: dict[str, Any]) -> dict[str, Any]:
    progress_rule = get_progress_rule(goal)
    activity_filter = progress_rule.get("activity_filter", {})

    if isinstance(activity_filter, dict):
        return activity_filter

    return {}


def get_goal_id(goal: dict[str, Any]) -> str:
    return str(goal.get("goal_id") or goal.get("id") or "[missing_goal_id]")


def get_goal_title(goal: dict[str, Any]) -> str:
    return str(goal.get("title") or goal.get("name") or get_goal_id(goal))


def get_goal_type(goal: dict[str, Any]) -> str:
    return str(goal.get("goal_type") or goal.get("type") or "target")


def extract_seconds_value(
    goal: dict[str, Any],
    candidate_keys: list[str],
) -> int | None:
    progress_rule = get_progress_rule(goal)

    for key in candidate_keys:
        value = goal.get(key)

        if isinstance(value, int):
            return value

        if isinstance(value, float):
            return int(value)

    for key in candidate_keys:
        value = progress_rule.get(key)

        if isinstance(value, int):
            return value

        if isinstance(value, float):
            return int(value)

    return None


def get_target_seconds(goal: dict[str, Any]) -> int | None:
    return extract_seconds_value(
        goal,
        [
            "target_seconds",
            "target_seconds_per_day",
            "daily_target_seconds",
            "target_daily_seconds",
        ],
    )


def get_limit_seconds(goal: dict[str, Any]) -> int | None:
    return extract_seconds_value(
        goal,
        [
            "limit_seconds",
            "limit_seconds_per_day",
            "daily_limit_seconds",
            "limit_daily_seconds",
        ],
    )


def should_use_limit_mode(goal: dict[str, Any], limit_seconds: int | None) -> bool:
    if limit_seconds is None:
        return False

    goal_type = get_goal_type(goal).lower()
    goal_id = get_goal_id(goal).lower()
    title = get_goal_title(goal).lower()

    limit_markers = [
        "limit",
        "reduce",
        "avoid",
        "less",
        "max",
        "no_",
        "stop",
        "gaming",
    ]

    return any(marker in goal_type for marker in limit_markers) or any(
        marker in goal_id or marker in title
        for marker in limit_markers
    )


def ensure_activity_logs_table_exists(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_date TEXT NOT NULL,
            process_name TEXT NOT NULL,
            window_title TEXT NOT NULL DEFAULT '',
            category TEXT NOT NULL,
            activity_state TEXT NOT NULL DEFAULT 'active',
            seconds INTEGER NOT NULL CHECK(seconds >= 0),
            created_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
        )
        """
    )

    conn.commit()


def row_matches_title_keywords(
    window_title: str,
    title_keywords: list[str],
) -> bool:
    if not title_keywords:
        return True

    normalized_title = window_title.lower()

    return any(keyword in normalized_title for keyword in title_keywords)


def get_desktop_seconds_for_goal(
    activity_date: str,
    goal: dict[str, Any],
) -> int:
    activity_filter = get_activity_filter(goal)

    categories = normalize_string_list(
        activity_filter.get("categories", [])
    )

    activity_states = normalize_string_list(
        activity_filter.get("activity_states")
        or activity_filter.get("states")
        or []
    )

    process_names = normalize_string_list(
        activity_filter.get("process_names", [])
    )

    title_keywords = normalize_string_list(
        activity_filter.get("title_keywords", [])
    )

    query = """
        SELECT
            process_name,
            window_title,
            category,
            activity_state,
            seconds
        FROM activity_logs
        WHERE activity_date = ?
    """

    params: list[Any] = [activity_date]

    if categories:
        placeholders = ", ".join("?" for _ in categories)
        query += f" AND lower(category) IN ({placeholders})"
        params.extend(categories)

    if activity_states:
        placeholders = ", ".join("?" for _ in activity_states)
        query += f" AND lower(activity_state) IN ({placeholders})"
        params.extend(activity_states)

    if process_names:
        placeholders = ", ".join("?" for _ in process_names)
        query += f" AND lower(process_name) IN ({placeholders})"
        params.extend(process_names)

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        ensure_activity_logs_table_exists(conn)

        rows = conn.execute(query, params).fetchall()

    total_seconds = 0

    for row in rows:
        window_title = str(row["window_title"] or "")

        if not row_matches_title_keywords(window_title, title_keywords):
            continue

        total_seconds += int(row["seconds"] or 0)

    return total_seconds


def get_manual_entries_for_goal(
    activity_date: str,
    goal_id: str,
) -> list[ManualActivityEntry]:
    entries = list_manual_activities(activity_date=activity_date)

    return [
        entry
        for entry in entries
        if entry.goal_id == goal_id
    ]


def build_goal_progress_result(
    activity_date: str,
    goal: dict[str, Any],
) -> GoalProgressResult:
    goal_id = get_goal_id(goal)
    title = get_goal_title(goal)
    goal_type = get_goal_type(goal)

    target_seconds = get_target_seconds(goal)
    limit_seconds = get_limit_seconds(goal)

    desktop_seconds = get_desktop_seconds_for_goal(
        activity_date=activity_date,
        goal=goal,
    )

    manual_entries = get_manual_entries_for_goal(
        activity_date=activity_date,
        goal_id=goal_id,
    )

    manual_seconds = sum(entry.seconds for entry in manual_entries)
    total_seconds = desktop_seconds + manual_seconds

    use_limit_mode = should_use_limit_mode(
        goal=goal,
        limit_seconds=limit_seconds,
    )

    status = "not configured"
    missing_seconds = 0
    remaining_seconds = 0
    extra_seconds = 0

    if use_limit_mode and limit_seconds is not None:
        if total_seconds <= limit_seconds:
            status = "within limit"
            remaining_seconds = limit_seconds - total_seconds
        else:
            status = "over limit"
            extra_seconds = total_seconds - limit_seconds

    elif target_seconds is not None:
        if total_seconds >= target_seconds:
            status = "target reached"
            extra_seconds = total_seconds - target_seconds
        else:
            status = "below target"
            missing_seconds = target_seconds - total_seconds

    return GoalProgressResult(
        goal_id=goal_id,
        title=title,
        goal_type=goal_type,
        desktop_seconds=desktop_seconds,
        manual_seconds=manual_seconds,
        total_seconds=total_seconds,
        target_seconds=target_seconds,
        limit_seconds=limit_seconds,
        status=status,
        missing_seconds=missing_seconds,
        remaining_seconds=remaining_seconds,
        extra_seconds=extra_seconds,
        manual_entries=manual_entries,
    )


def build_goal_progress_day_view(
    activity_date: str | None = None,
) -> GoalProgressDayView:
    resolved_date = activity_date or today_iso()
    goals = get_goals()

    results = [
        build_goal_progress_result(
            activity_date=resolved_date,
            goal=goal,
        )
        for goal in goals
        if isinstance(goal, dict)
    ]

    return GoalProgressDayView(
        activity_date=resolved_date,
        results=results,
    )

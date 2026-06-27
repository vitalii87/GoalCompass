# data/query_goal_progress.py

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = ROOT_DIR / "data" / "lazy_coach.db"
PROFILE_PATH = ROOT_DIR / "data" / "user_config" / "primary.json"


def format_seconds(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def load_profile() -> dict[str, Any]:
    with PROFILE_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("Profile must be a JSON object")

    return data


def ensure_manual_activity_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS manual_activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_date TEXT NOT NULL,
            goal_id TEXT NOT NULL,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            seconds INTEGER NOT NULL CHECK(seconds >= 0),
            note TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT 'manual',
            created_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
        )
        """
    )
    conn.commit()


def build_filter_sql(
    activity_filter: dict[str, Any],
) -> tuple[str, list[Any]]:
    conditions: list[str] = []
    params: list[Any] = []

    categories = activity_filter.get("categories", [])
    if categories:
        placeholders = ", ".join("?" for _ in categories)
        conditions.append(f"category IN ({placeholders})")
        params.extend(categories)

    activity_states = activity_filter.get("activity_states", [])
    if activity_states:
        placeholders = ", ".join("?" for _ in activity_states)
        conditions.append(f"activity_state IN ({placeholders})")
        params.extend(activity_states)

    process_names = activity_filter.get("process_names", [])
    if process_names:
        placeholders = ", ".join("?" for _ in process_names)
        conditions.append(f"process_name IN ({placeholders})")
        params.extend(process_names)

    title_keywords = activity_filter.get("title_keywords", [])
    if title_keywords:
        title_conditions = []

        for keyword in title_keywords:
            title_conditions.append("LOWER(window_title) LIKE ?")
            params.append(f"%{str(keyword).lower()}%")

        conditions.append("(" + " OR ".join(title_conditions) + ")")

    if not conditions:
        return "", params

    return " AND " + " AND ".join(conditions), params


def get_desktop_seconds_for_goal(
    conn: sqlite3.Connection,
    activity_date: str,
    activity_filter: dict[str, Any],
) -> int:
    filter_sql, filter_params = build_filter_sql(activity_filter)

    row = conn.execute(
        f"""
        SELECT COALESCE(SUM(seconds), 0) AS total_seconds
        FROM activity_logs
        WHERE activity_date = ?
        {filter_sql}
        """,
        [activity_date, *filter_params],
    ).fetchone()

    return int(row["total_seconds"]) if row else 0


def get_manual_seconds_for_goal(
    conn: sqlite3.Connection,
    activity_date: str,
    goal_id: str,
) -> int:
    row = conn.execute(
        """
        SELECT COALESCE(SUM(seconds), 0) AS total_seconds
        FROM manual_activity_logs
        WHERE activity_date = ?
          AND goal_id = ?
        """,
        (activity_date, goal_id),
    ).fetchone()

    return int(row["total_seconds"]) if row else 0


def get_manual_entries_for_goal(
    conn: sqlite3.Connection,
    activity_date: str,
    goal_id: str,
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT
            title,
            category,
            seconds,
            note,
            source,
            created_at
        FROM manual_activity_logs
        WHERE activity_date = ?
          AND goal_id = ?
        ORDER BY created_at ASC
        """,
        (activity_date, goal_id),
    ).fetchall()

    return [dict(row) for row in rows]


def print_goal_progress(
    goal: dict[str, Any],
    desktop_seconds: int,
    manual_seconds: int,
    manual_entries: list[dict[str, Any]],
) -> None:
    title = goal.get("title", goal.get("goal_id", "[unknown goal]"))
    goal_id = goal.get("goal_id", "[missing goal_id]")
    progress_rule = goal.get("progress_rule", {})
    mode = progress_rule.get("mode", "none")

    total_seconds = desktop_seconds + manual_seconds

    print("-" * 60)
    print(f"{title}")
    print(f"id: {goal_id}")
    print(f"desktop: {format_seconds(desktop_seconds)}")
    print(f"manual:  {format_seconds(manual_seconds)}")
    print(f"total:   {format_seconds(total_seconds)}")

    if manual_entries:
        print("manual entries:")

        for entry in manual_entries:
            entry_title = entry.get("title", "[no title]")
            entry_seconds = int(entry.get("seconds", 0))
            entry_note = entry.get("note", "")

            line = f"  - {entry_title}: {format_seconds(entry_seconds)}"
            if entry_note:
                line += f" | note: {entry_note}"

            print(line)

    if mode == "target":
        target_seconds = int(progress_rule.get("daily_target_seconds", 0))
        missing_seconds = max(target_seconds - total_seconds, 0)

        print(f"target:  {format_seconds(target_seconds)}")

        if total_seconds >= target_seconds:
            print("status: target reached")
            print(f"extra:  {format_seconds(total_seconds - target_seconds)}")
        else:
            print("status: below target")
            print(f"missing: {format_seconds(missing_seconds)}")

    elif mode == "limit":
        limit_seconds = int(progress_rule.get("daily_limit_seconds", 0))

        print(f"limit:   {format_seconds(limit_seconds)}")

        if total_seconds <= limit_seconds:
            print("status: within limit")
            print(f"remaining: {format_seconds(limit_seconds - total_seconds)}")
        else:
            print("status: limit exceeded")
            print(f"exceeded: {format_seconds(total_seconds - limit_seconds)}")

    else:
        print("status: no progress rule")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Show GoalCompass goal progress."
    )

    parser.add_argument(
        "activity_date",
        nargs="?",
        default=date.today().isoformat(),
        help="Date in YYYY-MM-DD format. Defaults to today.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    activity_date = args.activity_date

    profile = load_profile()
    goals = profile.get("goals", [])

    if not isinstance(goals, list):
        raise ValueError("Profile field 'goals' must be a list")

    print("=" * 60)
    print(f"GOAL PROGRESS FOR {activity_date}")
    print("=" * 60)

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        ensure_manual_activity_table(conn)

        for goal in goals:
            if not isinstance(goal, dict):
                continue

            goal_id = goal.get("goal_id")
            if not isinstance(goal_id, str):
                continue

            progress_rule = goal.get("progress_rule", {})
            if not isinstance(progress_rule, dict):
                continue

            activity_filter = progress_rule.get("activity_filter", {})
            if not isinstance(activity_filter, dict):
                activity_filter = {}

            desktop_seconds = get_desktop_seconds_for_goal(
                conn=conn,
                activity_date=activity_date,
                activity_filter=activity_filter,
            )

            manual_seconds = get_manual_seconds_for_goal(
                conn=conn,
                activity_date=activity_date,
                goal_id=goal_id,
            )

            manual_entries = get_manual_entries_for_goal(
                conn=conn,
                activity_date=activity_date,
                goal_id=goal_id,
            )

            print_goal_progress(
                goal=goal,
                desktop_seconds=desktop_seconds,
                manual_seconds=manual_seconds,
                manual_entries=manual_entries,
            )

    print("=" * 60)


if __name__ == "__main__":
    main()
# src/services/panel_status_service.py

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
DB_PATH = ROOT_DIR / "data" / "lazy_coach.db"
PRIMARY_PROFILE_PATH = ROOT_DIR / "data" / "user_config" / "primary.json"


DEFAULT_PANEL_STATUS_RULES = {
    "positive": [
        "productive",
        "learning",
        "career",
        "health",
    ],
    "neutral": [
        "personal",
        "commute",
        "manual",
        "unknown",
    ],
    "negative": [
        "time_wasting",
        "distracting",
    ],
    "idle": [
        "idle",
        "ignored",
    ],
}


@dataclass(frozen=True)
class PanelStatusTotals:
    positive_seconds: int
    neutral_seconds: int
    negative_seconds: int
    idle_seconds: int

    @property
    def tracked_seconds(self) -> int:
        return (
            self.positive_seconds
            + self.neutral_seconds
            + self.negative_seconds
        )

    @property
    def total_with_idle_seconds(self) -> int:
        return self.tracked_seconds + self.idle_seconds


@dataclass(frozen=True)
class CurrentPanelStatus:
    panel_status: str
    category: str
    activity_state: str
    process_name: str
    window_title: str
    seconds: int
    created_at: str


@dataclass(frozen=True)
class PanelStatusDayView:
    activity_date: str
    totals: PanelStatusTotals
    current: CurrentPanelStatus | None


def today_iso() -> str:
    return date.today().isoformat()


def format_seconds_compact(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    if hours > 0:
        return f"{hours}h {minutes:02d}m"

    return f"{minutes}m"


def format_seconds_clock(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    return f"{minutes:02d}:{secs:02d}"


def load_primary_profile() -> dict[str, Any]:
    if not PRIMARY_PROFILE_PATH.exists():
        return {}

    try:
        with PRIMARY_PROFILE_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, dict):
            return data

    except (OSError, json.JSONDecodeError):
        return {}

    return {}


def normalize_status_rules(raw_rules: Any) -> dict[str, set[str]]:
    if not isinstance(raw_rules, dict):
        raw_rules = DEFAULT_PANEL_STATUS_RULES

    normalized: dict[str, set[str]] = {
        "positive": set(),
        "neutral": set(),
        "negative": set(),
        "idle": set(),
    }

    for status in normalized:
        raw_categories = raw_rules.get(status, [])

        if not isinstance(raw_categories, list):
            continue

        normalized[status] = {
            str(category).lower()
            for category in raw_categories
            if isinstance(category, str)
        }

    return normalized


def get_panel_status_rules() -> dict[str, set[str]]:
    profile = load_primary_profile()
    raw_rules = profile.get("panel_status_rules", DEFAULT_PANEL_STATUS_RULES)

    rules = normalize_status_rules(raw_rules)

    for status, default_categories in DEFAULT_PANEL_STATUS_RULES.items():
        if not rules[status]:
            rules[status] = {
                category.lower()
                for category in default_categories
            }

    return rules


def category_to_panel_status(
    category: str,
    activity_state: str,
) -> str:
    normalized_state = activity_state.lower().strip()

    if normalized_state == "idle":
        return "idle"

    rules = get_panel_status_rules()
    normalized_category = category.lower().strip()

    for status in ("positive", "neutral", "negative", "idle"):
        if normalized_category in rules[status]:
            return status

    return "neutral"


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


def get_panel_status_totals(activity_date: str) -> PanelStatusTotals:
    totals_by_status = {
        "positive": 0,
        "neutral": 0,
        "negative": 0,
        "idle": 0,
    }

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        ensure_activity_logs_table_exists(conn)

        rows = conn.execute(
            """
            SELECT
                category,
                activity_state,
                COALESCE(SUM(seconds), 0) AS total_seconds
            FROM activity_logs
            WHERE activity_date = ?
            GROUP BY category, activity_state
            """,
            (activity_date,),
        ).fetchall()

    for row in rows:
        category = str(row["category"] or "unknown")
        activity_state = str(row["activity_state"] or "active")
        seconds = int(row["total_seconds"] or 0)

        panel_status = category_to_panel_status(
            category=category,
            activity_state=activity_state,
        )

        if panel_status not in totals_by_status:
            panel_status = "neutral"

        totals_by_status[panel_status] += seconds

    return PanelStatusTotals(
        positive_seconds=totals_by_status["positive"],
        neutral_seconds=totals_by_status["neutral"],
        negative_seconds=totals_by_status["negative"],
        idle_seconds=totals_by_status["idle"],
    )


def get_current_panel_status(activity_date: str) -> CurrentPanelStatus | None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        ensure_activity_logs_table_exists(conn)

        row = conn.execute(
            """
            SELECT
                process_name,
                window_title,
                category,
                activity_state,
                seconds,
                created_at
            FROM activity_logs
            WHERE activity_date = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (activity_date,),
        ).fetchone()

    if row is None:
        return None

    category = str(row["category"] or "unknown")
    activity_state = str(row["activity_state"] or "active")

    panel_status = category_to_panel_status(
        category=category,
        activity_state=activity_state,
    )

    return CurrentPanelStatus(
        panel_status=panel_status,
        category=category,
        activity_state=activity_state,
        process_name=str(row["process_name"] or ""),
        window_title=str(row["window_title"] or ""),
        seconds=int(row["seconds"] or 0),
        created_at=str(row["created_at"] or ""),
    )


def build_panel_status_day_view(
    activity_date: str | None = None,
) -> PanelStatusDayView:
    resolved_date = activity_date or today_iso()

    return PanelStatusDayView(
        activity_date=resolved_date,
        totals=get_panel_status_totals(resolved_date),
        current=get_current_panel_status(resolved_date),
    )
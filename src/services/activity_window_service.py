# src/services/activity_window_service.py

from __future__ import annotations

import sqlite3
from datetime import datetime, time, timedelta
from pathlib import Path


ACTIVITY_DAY_RESET_HOUR = 3


def get_activity_window(now: datetime | None = None) -> tuple[datetime, datetime]:
    """
    GoalCompass activity window.

    Default:
        03:00 today -> 03:00 tomorrow

    If current time is before 03:00:
        03:00 yesterday -> 03:00 today
    """
    current = now or datetime.now()

    today_reset = datetime.combine(
        current.date(),
        time(hour=ACTIVITY_DAY_RESET_HOUR),
    )

    if current < today_reset:
        start = today_reset - timedelta(days=1)
    else:
        start = today_reset

    end = start + timedelta(days=1)
    return start, end


def get_activity_window_key(now: datetime | None = None) -> str:
    """
    Stable key for current GoalCompass activity day.

    Example:
        2026-07-04 01:30 -> 2026-07-03
        2026-07-04 03:01 -> 2026-07-04
    """
    start, _ = get_activity_window(now)
    return start.date().isoformat()


def get_seconds_until_next_activity_window(now: datetime | None = None) -> int:
    """
    Seconds until next reset, used for warning badge lifetime.
    """
    current = now or datetime.now()
    _, end = get_activity_window(current)

    seconds = int((end - current).total_seconds())
    return max(seconds, 0)


def get_seconds_by_category_in_activity_window(
    db_path: str | Path,
    category: str,
    active_only: bool = True,
) -> int:
    """
    Sum seconds for a category inside current GoalCompass activity window.

    Uses created_at, not activity_date.
    This keeps DB/calendar history standard but allows live UI to reset at 03:00.
    """
    start, end = get_activity_window()

    query = """
        SELECT COALESCE(SUM(seconds), 0)
        FROM activity_logs
        WHERE category = ?
          AND created_at >= ?
          AND created_at < ?
    """

    params: list[object] = [
        category,
        start.strftime("%Y-%m-%d %H:%M:%S"),
        end.strftime("%Y-%m-%d %H:%M:%S"),
    ]

    if active_only:
        query += " AND activity_state = ?"
        params.append("active")

    with sqlite3.connect(str(db_path)) as conn:
        result = conn.execute(query, params).fetchone()

    if not result:
        return 0

    return int(result[0] or 0)


def get_activity_window_display_seconds(
    db_path: str | Path,
    category: str,
    activity_state: str,
) -> int:
    """
    Value for mini overlay.

    Idle:
        overlay should show --:-- / 0.

    Active:
        show category total from current activity window:
        03:00 -> 02:59.
    """
    if activity_state == "idle":
        return 0

    return get_seconds_by_category_in_activity_window(
        db_path=db_path,
        category=category,
        active_only=True,
    )

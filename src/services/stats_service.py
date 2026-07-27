# src/services/stats_service.py

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

from src.services.limit_rules_service import list_active_limits


ROOT_DIR = Path(__file__).resolve().parents[2]
DB_PATH = ROOT_DIR / "data" / "lazy_coach.db"


def today_str() -> str:
    return date.today().isoformat()


def format_seconds(seconds: int | float | None) -> str:
    total = int(seconds or 0)

    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60

    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def db_exists() -> bool:
    return DB_PATH.exists()


def fetch_rows(query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    if not db_exists():
        return []

    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(query, params).fetchall()


def get_today_totals_by_category(
    activity_date: str | None = None,
    active_only: bool = True,
) -> list[dict[str, Any]]:
    day = activity_date or today_str()

    query = """
        SELECT category, COALESCE(SUM(seconds), 0) AS total_seconds
        FROM activity_logs
        WHERE activity_date = ?
    """

    params: list[Any] = [day]

    if active_only:
        query += " AND activity_state = ?"
        params.append("active")

    query += """
        GROUP BY category
        ORDER BY total_seconds DESC
    """

    rows = fetch_rows(query, tuple(params))

    return [
        {
            "category": str(row["category"]),
            "seconds": int(row["total_seconds"] or 0),
            "display": format_seconds(int(row["total_seconds"] or 0)),
        }
        for row in rows
    ]


def get_today_totals_by_state(
    activity_date: str | None = None,
) -> list[dict[str, Any]]:
    day = activity_date or today_str()

    rows = fetch_rows(
        """
        SELECT activity_state, COALESCE(SUM(seconds), 0) AS total_seconds
        FROM activity_logs
        WHERE activity_date = ?
        GROUP BY activity_state
        ORDER BY total_seconds DESC
        """,
        (day,),
    )

    return [
        {
            "activity_state": str(row["activity_state"]),
            "seconds": int(row["total_seconds"] or 0),
            "display": format_seconds(int(row["total_seconds"] or 0)),
        }
        for row in rows
    ]


def get_today_top_processes(
    activity_date: str | None = None,
    limit: int = 10,
    active_only: bool = True,
) -> list[dict[str, Any]]:
    day = activity_date or today_str()

    query = """
        SELECT
            process_name,
            category,
            COALESCE(SUM(seconds), 0) AS total_seconds
        FROM activity_logs
        WHERE activity_date = ?
    """

    params: list[Any] = [day]

    if active_only:
        query += " AND activity_state = ?"
        params.append("active")

    query += """
        GROUP BY process_name, category
        ORDER BY total_seconds DESC
        LIMIT ?
    """

    params.append(limit)

    rows = fetch_rows(query, tuple(params))

    return [
        {
            "process_name": str(row["process_name"]),
            "category": str(row["category"]),
            "seconds": int(row["total_seconds"] or 0),
            "display": format_seconds(int(row["total_seconds"] or 0)),
        }
        for row in rows
    ]


def get_today_top_unknown(
    activity_date: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    day = activity_date or today_str()

    rows = fetch_rows(
        """
        SELECT
            process_name,
            window_title,
            COALESCE(SUM(seconds), 0) AS total_seconds
        FROM activity_logs
        WHERE activity_date = ?
          AND category = 'unknown'
          AND activity_state = 'active'
        GROUP BY process_name, window_title
        ORDER BY total_seconds DESC
        LIMIT ?
        """,
        (day, limit),
    )

    return [
        {
            "process_name": str(row["process_name"]),
            "window_title": str(row["window_title"]),
            "seconds": int(row["total_seconds"] or 0),
            "display": format_seconds(int(row["total_seconds"] or 0)),
        }
        for row in rows
    ]


def get_seconds_for_limit_target(
    target_type: str,
    target_value: str,
    period: str = "daily",
    activity_date: str | None = None,
) -> int:
    """
    MVP:
        daily category/process/title_contains limits.

    Weekly can be added later with date ranges.
    """
    day = activity_date or today_str()

    target_type = str(target_type).strip().lower()
    target_value = str(target_value).strip().lower()
    period = str(period).strip().lower()

    if period != "daily":
        return 0

    if target_type == "category":
        rows = fetch_rows(
            """
            SELECT COALESCE(SUM(seconds), 0) AS total_seconds
            FROM activity_logs
            WHERE activity_date = ?
              AND LOWER(category) = ?
              AND activity_state = 'active'
            """,
            (day, target_value),
        )
        return int(rows[0]["total_seconds"] or 0) if rows else 0

    if target_type == "process":
        rows = fetch_rows(
            """
            SELECT COALESCE(SUM(seconds), 0) AS total_seconds
            FROM activity_logs
            WHERE activity_date = ?
              AND LOWER(process_name) = ?
              AND activity_state = 'active'
            """,
            (day, target_value),
        )
        return int(rows[0]["total_seconds"] or 0) if rows else 0

    if target_type == "title_contains":
        rows = fetch_rows(
            """
            SELECT COALESCE(SUM(seconds), 0) AS total_seconds
            FROM activity_logs
            WHERE activity_date = ?
              AND LOWER(window_title) LIKE ?
              AND activity_state = 'active'
            """,
            (day, f"%{target_value}%"),
        )
        return int(rows[0]["total_seconds"] or 0) if rows else 0

    return 0


def get_limit_progress(
    activity_date: str | None = None,
) -> list[dict[str, Any]]:
    progress: list[dict[str, Any]] = []

    for rule in list_active_limits():
        target_type = str(rule.get("target_type", ""))
        target_value = str(rule.get("target_value", ""))
        period = str(rule.get("period", "daily"))
        limit_minutes = int(rule.get("limit_minutes", 0) or 0)

        used_seconds = get_seconds_for_limit_target(
            target_type=target_type,
            target_value=target_value,
            period=period,
            activity_date=activity_date,
        )

        limit_seconds = limit_minutes * 60

        if limit_seconds <= 0:
            percent = 0
        else:
            percent = round((used_seconds / limit_seconds) * 100, 1)

        progress.append(
            {
                "id": str(rule.get("id", "")),
                "target_type": target_type,
                "target_value": target_value,
                "period": period,
                "limit_minutes": limit_minutes,
                "limit_seconds": limit_seconds,
                "used_seconds": used_seconds,
                "used_display": format_seconds(used_seconds),
                "limit_display": format_seconds(limit_seconds),
                "percent": percent,
                "severity": str(rule.get("severity", "warning")),
                "status": str(rule.get("status", "active")),
            }
        )

    return progress


def get_dashboard_snapshot() -> dict[str, Any]:
    return {
        "today": today_str(),
        "totals_by_category": get_today_totals_by_category(),
        "totals_by_state": get_today_totals_by_state(),
        "top_processes": get_today_top_processes(),
        "top_unknown": get_today_top_unknown(),
        "limit_progress": get_limit_progress(),
    }

# data/check_db_health.py

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


DB_PATH = ROOT_DIR / "data" / "lazy_coach.db"
CURRENT_STATE_PATH = ROOT_DIR / "data" / "runtime" / "current_state.json"


def format_seconds(seconds: int) -> str:
    seconds = max(int(seconds), 0)

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def print_section(title: str) -> None:
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    cursor = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,),
    )
    return cursor.fetchone() is not None


def check_current_state() -> None:
    print_section("CURRENT STATE JSON")

    if not CURRENT_STATE_PATH.exists():
        print("current_state.json: NOT FOUND")
        return

    try:
        data = json.loads(CURRENT_STATE_PATH.read_text(encoding="utf-8"))
    except Exception as error:
        print(f"current_state.json: ERROR READING: {error}")
        return

    updated_at_raw = str(data.get("updated_at", ""))

    print(f"path:       {CURRENT_STATE_PATH}")
    print(f"updated_at: {updated_at_raw}")
    print(f"process:    {data.get('process_name', '')}")
    print(f"category:   {data.get('category', '')}")
    print(f"state:      {data.get('activity_state', '')}")
    print(f"status:     {data.get('panel_status', '')}")
    print(f"session:    {format_seconds(int(data.get('session_seconds', 0)))}")
    print(
        "today shown:",
        format_seconds(int(data.get("today_category_seconds", 0))),
    )

    try:
        updated_at = datetime.fromisoformat(updated_at_raw)
        age_seconds = int((datetime.now() - updated_at).total_seconds())
        print(f"age:        {format_seconds(age_seconds)} ago")

        if age_seconds > 30:
            print("status:     STALE / tracker may be stopped")
        else:
            print("status:     LIVE / tracker probably running")
    except ValueError:
        print("status:     UNKNOWN / invalid updated_at")


def check_activity_logs(conn: sqlite3.Connection) -> None:
    print_section("ACTIVITY LOGS")

    if not table_exists(conn, "activity_logs"):
        print("activity_logs table: NOT FOUND")
        return

    today = date.today().isoformat()

    total_rows = conn.execute(
        "SELECT COUNT(*) FROM activity_logs"
    ).fetchone()[0]

    today_rows = conn.execute(
        """
        SELECT COUNT(*)
        FROM activity_logs
        WHERE activity_date = ?
        """,
        (today,),
    ).fetchone()[0]

    today_seconds = conn.execute(
        """
        SELECT COALESCE(SUM(seconds), 0)
        FROM activity_logs
        WHERE activity_date = ?
        """,
        (today,),
    ).fetchone()[0]

    last_row = conn.execute(
        """
        SELECT
            id,
            activity_date,
            process_name,
            window_title,
            category,
            activity_state,
            seconds,
            created_at
        FROM activity_logs
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()

    print(f"db path:       {DB_PATH}")
    print(f"total rows:    {total_rows}")
    print(f"today rows:    {today_rows}")
    print(f"today seconds: {format_seconds(today_seconds)}")

    if last_row is None:
        print("last row:      NONE")
    else:
        (
            row_id,
            activity_date,
            process_name,
            window_title,
            category,
            activity_state,
            seconds,
            created_at,
        ) = last_row

        print()
        print("LAST ROW")
        print(f"id:        {row_id}")
        print(f"date:      {activity_date}")
        print(f"created:   {created_at}")
        print(f"process:   {process_name}")
        print(f"category:  {category}")
        print(f"state:     {activity_state}")
        print(f"seconds:   {format_seconds(seconds)}")
        print(f"title:     {window_title or '[empty]'}")

    print()
    print("TODAY BY CATEGORY")

    rows = conn.execute(
        """
        SELECT category, COALESCE(SUM(seconds), 0)
        FROM activity_logs
        WHERE activity_date = ?
        GROUP BY category
        ORDER BY SUM(seconds) DESC
        """,
        (today,),
    ).fetchall()

    if not rows:
        print("No activity today.")
    else:
        for category, seconds in rows:
            print(f"{category:15} {format_seconds(seconds)}")

    print()
    print("TODAY BY STATE")

    rows = conn.execute(
        """
        SELECT activity_state, COALESCE(SUM(seconds), 0)
        FROM activity_logs
        WHERE activity_date = ?
        GROUP BY activity_state
        ORDER BY SUM(seconds) DESC
        """,
        (today,),
    ).fetchall()

    if not rows:
        print("No state data today.")
    else:
        for activity_state, seconds in rows:
            print(f"{activity_state:15} {format_seconds(seconds)}")

    print()
    print("LAST 10 ROWS")

    rows = conn.execute(
        """
        SELECT
            id,
            created_at,
            process_name,
            category,
            activity_state,
            seconds,
            window_title
        FROM activity_logs
        ORDER BY id DESC
        LIMIT 10
        """
    ).fetchall()

    if not rows:
        print("No rows.")
        return

    for row in rows:
        row_id, created_at, process_name, category, activity_state, seconds, title = row
        print(
            f"#{row_id:<6} {created_at} | "
            f"{process_name:<20} | "
            f"{category:<13} | "
            f"{activity_state:<6} | "
            f"{format_seconds(seconds):>8} | "
            f"{title or '[empty]'}"
        )


def check_manual_logs(conn: sqlite3.Connection) -> None:
    print_section("MANUAL ACTIVITY LOGS")

    if not table_exists(conn, "manual_activity_logs"):
        print("manual_activity_logs table: NOT FOUND")
        return

    today = date.today().isoformat()

    today_rows = conn.execute(
        """
        SELECT COUNT(*)
        FROM manual_activity_logs
        WHERE activity_date = ?
        """,
        (today,),
    ).fetchone()[0]

    today_seconds = conn.execute(
        """
        SELECT COALESCE(SUM(seconds), 0)
        FROM manual_activity_logs
        WHERE activity_date = ?
        """,
        (today,),
    ).fetchone()[0]

    print(f"today manual rows:    {today_rows}")
    print(f"today manual seconds: {format_seconds(today_seconds)}")


def main() -> None:
    print_section("GOALCOMPASS DB HEALTH CHECK")

    if not DB_PATH.exists():
        print(f"DB NOT FOUND: {DB_PATH}")
        return

    print(f"DB exists: {DB_PATH}")

    try:
        with sqlite3.connect(DB_PATH) as conn:
            check_activity_logs(conn)
            check_manual_logs(conn)
    except Exception as error:
        print(f"DB ERROR: {error}")

    check_current_state()


if __name__ == "__main__":
    main()

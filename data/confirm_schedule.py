# data/confirm_schedule.py

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = ROOT_DIR / "data" / "lazy_coach.db"
SCHEDULE_PATH = ROOT_DIR / "data" / "user_config" / "schedule.json"


WEEKDAY_NAMES = {
    0: "monday",
    1: "tuesday",
    2: "wednesday",
    3: "thursday",
    4: "friday",
    5: "saturday",
    6: "sunday",
}


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def parse_time_to_minutes(value: str) -> int:
    hours_text, minutes_text = value.split(":", maxsplit=1)
    return int(hours_text) * 60 + int(minutes_text)


def calculate_duration_minutes(start_time: str, end_time: str) -> int:
    start_minutes = parse_time_to_minutes(start_time)
    end_minutes = parse_time_to_minutes(end_time)

    if end_minutes < start_minutes:
        end_minutes += 24 * 60

    return max(end_minutes - start_minutes, 0)


def format_seconds(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def load_schedule() -> list[dict[str, Any]]:
    if not SCHEDULE_PATH.exists():
        return []

    with SCHEDULE_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("schedule.json must contain a list")

    return [item for item in data if isinstance(item, dict)]


def get_events_for_date(
    schedule_items: list[dict[str, Any]],
    target_date: date,
) -> list[dict[str, Any]]:
    weekday = WEEKDAY_NAMES[target_date.weekday()]
    events: list[dict[str, Any]] = []

    for item in schedule_items:
        days = item.get("days", [])

        if not isinstance(days, list):
            continue

        normalized_days = {
            str(day).lower()
            for day in days
            if isinstance(day, str)
        }

        if weekday not in normalized_days:
            continue

        start_time = item.get("start_time")
        end_time = item.get("end_time")

        if not isinstance(start_time, str) or not isinstance(end_time, str):
            continue

        duration_minutes = calculate_duration_minutes(start_time, end_time)

        event = dict(item)
        event["duration_seconds"] = duration_minutes * 60
        events.append(event)

    events.sort(key=lambda event: str(event.get("start_time", "")))
    return events


def find_scheduled_event(
    activity_date: str,
    schedule_id: str,
) -> dict[str, Any] | None:
    target_date = parse_date(activity_date)
    schedule_items = load_schedule()
    events = get_events_for_date(schedule_items, target_date)

    for event in events:
        if event.get("schedule_id") == schedule_id:
            return event

    return None


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

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_manual_activity_logs_date
        ON manual_activity_logs(activity_date)
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_manual_activity_logs_goal
        ON manual_activity_logs(goal_id)
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_manual_activity_logs_date_goal
        ON manual_activity_logs(activity_date, goal_id)
        """
    )

    conn.commit()


def already_confirmed(
    conn: sqlite3.Connection,
    activity_date: str,
    schedule_id: str,
) -> bool:
    row = conn.execute(
        """
        SELECT id
        FROM manual_activity_logs
        WHERE activity_date = ?
          AND source = 'schedule_confirmed'
          AND note LIKE ?
        LIMIT 1
        """,
        (
            activity_date,
            f"%schedule_id={schedule_id}%",
        ),
    ).fetchone()

    return row is not None


def insert_confirmed_schedule_activity(
    activity_date: str,
    event: dict[str, Any],
    seconds_override: int | None = None,
) -> None:
    schedule_id = str(event.get("schedule_id", ""))
    goal_id = str(event.get("goal_id", ""))
    category = str(event.get("category", "scheduled"))
    title = str(event.get("title", schedule_id))
    start_time = str(event.get("start_time", ""))
    end_time = str(event.get("end_time", ""))

    if not goal_id:
        raise ValueError("Scheduled event has no goal_id")

    if not bool(event.get("counts_to_goal", False)):
        raise ValueError(
            f"Scheduled event does not count to goal: {schedule_id}"
        )

    seconds = seconds_override
    if seconds is None:
        seconds = int(event.get("duration_seconds", 0))

    if seconds <= 0:
        raise ValueError("Confirmed duration must be greater than 0")

    note = (
        f"schedule_id={schedule_id}; "
        f"planned_time={start_time}-{end_time}"
    )

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        ensure_manual_activity_table(conn)

        if already_confirmed(conn, activity_date, schedule_id):
            print("Scheduled activity is already confirmed:")
            print(f"  date: {activity_date}")
            print(f"  schedule_id: {schedule_id}")
            return

        conn.execute(
            """
            INSERT INTO manual_activity_logs (
                activity_date,
                goal_id,
                category,
                title,
                seconds,
                note,
                source,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 'schedule_confirmed', datetime('now', 'localtime'))
            """,
            (
                activity_date,
                goal_id,
                category,
                title,
                seconds,
                note,
            ),
        )

        conn.commit()

    print("Scheduled activity confirmed:")
    print(f"  date: {activity_date}")
    print(f"  schedule_id: {schedule_id}")
    print(f"  goal: {goal_id}")
    print(f"  title: {title}")
    print(f"  category: {category}")
    print(f"  duration: {format_seconds(seconds)}")
    print(f"  source: schedule_confirmed")


def list_confirmable_events(activity_date: str) -> None:
    target_date = parse_date(activity_date)
    schedule_items = load_schedule()
    events = get_events_for_date(schedule_items, target_date)

    print("=" * 70)
    print(f"CONFIRMABLE SCHEDULE FOR {activity_date} | {WEEKDAY_NAMES[target_date.weekday()]}")
    print("=" * 70)

    confirmable_events = [
        event
        for event in events
        if bool(event.get("counts_to_goal", False))
    ]

    if not confirmable_events:
        print("No confirmable scheduled activities found.")
        print("=" * 70)
        return

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        ensure_manual_activity_table(conn)

        for event in confirmable_events:
            schedule_id = str(event.get("schedule_id", ""))
            title = event.get("title", "[missing title]")
            goal_id = event.get("goal_id", "[missing goal_id]")
            category = event.get("category", "[missing category]")
            start_time = event.get("start_time", "??:??")
            end_time = event.get("end_time", "??:??")
            duration_seconds = int(event.get("duration_seconds", 0))
            confirmation_mode = event.get("confirmation_mode", "none")
            confirmed = already_confirmed(conn, activity_date, schedule_id)

            print("-" * 70)
            print(f"id: {schedule_id}")
            print(f"time: {start_time}–{end_time}")
            print(f"title: {title}")
            print(f"goal: {goal_id}")
            print(f"category: {category}")
            print(f"duration: {format_seconds(duration_seconds)}")
            print(f"confirmation_mode: {confirmation_mode}")
            print(f"confirmed: {confirmed}")

    print("=" * 70)
    print("Usage:")
    print(f"  python data/confirm_schedule.py --confirm <schedule_id> --date {activity_date}")
    print(f"  python data/confirm_schedule.py --confirm <schedule_id> --minutes 60 --date {activity_date}")
    print("=" * 70)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Confirm scheduled GoalCompass activities."
    )

    parser.add_argument(
        "--date",
        type=str,
        default=date.today().isoformat(),
        help="Activity date in YYYY-MM-DD format. Defaults to today.",
    )

    parser.add_argument(
        "--confirm",
        type=str,
        help="Schedule ID to confirm.",
    )

    parser.add_argument(
        "--minutes",
        type=int,
        help="Optional custom confirmed duration in minutes.",
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List confirmable scheduled activities for the date.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.list or not args.confirm:
        list_confirmable_events(args.date)
        return

    event = find_scheduled_event(
        activity_date=args.date,
        schedule_id=args.confirm,
    )

    if event is None:
        print("Scheduled event not found for this date:")
        print(f"  date: {args.date}")
        print(f"  schedule_id: {args.confirm}")
        return

    seconds_override = None
    if args.minutes is not None:
        seconds_override = args.minutes * 60

    insert_confirmed_schedule_activity(
        activity_date=args.date,
        event=event,
        seconds_override=seconds_override,
    )


if __name__ == "__main__":
    main()
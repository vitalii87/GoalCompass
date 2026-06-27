# data/add_manual_activity.py

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = ROOT_DIR / "data" / "lazy_coach.db"
PRESETS_PATH = ROOT_DIR / "data" / "user_config" / "manual_presets.json"


def format_seconds(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


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


def load_presets() -> list[dict[str, Any]]:
    if not PRESETS_PATH.exists():
        return []

    with PRESETS_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("manual_presets.json must contain a list")

    return [item for item in data if isinstance(item, dict)]


def find_preset(preset_id: str) -> dict[str, Any] | None:
    presets = load_presets()

    for preset in presets:
        if preset.get("preset_id") == preset_id:
            return preset

    return None


def print_presets() -> None:
    presets = load_presets()

    if not presets:
        print("No presets found.")
        print(f"Expected file: {PRESETS_PATH}")
        return

    print("Available manual activity presets:")
    print("-" * 60)

    for preset in presets:
        preset_id = preset.get("preset_id", "[missing preset_id]")
        goal_id = preset.get("goal_id", "[missing goal_id]")
        title = preset.get("title", "[missing title]")
        seconds = int(preset.get("seconds", 0))
        category = preset.get("category", "[missing category]")

        print(f"{preset_id}")
        print(f"  goal: {goal_id}")
        print(f"  title: {title}")
        print(f"  category: {category}")
        print(f"  duration: {format_seconds(seconds)}")
        print()

    print("Usage examples:")
    print("  python data/add_manual_activity.py --preset german_homework_30m")
    print("  python data/add_manual_activity.py --preset german_lesson_90m --date 2026-06-27")
    print("  python data/add_manual_activity.py --goal german_b1_001 --minutes 45 --title \"German homework\" --category learning")
    print("  python data/add_manual_activity.py --list")
    print("  python data/add_manual_activity.py --list --date 2026-06-27")
    print("  python data/add_manual_activity.py --delete 1")


def insert_manual_activity(
    activity_date: str,
    goal_id: str,
    category: str,
    title: str,
    seconds: int,
    note: str,
    source: str = "manual",
) -> None:
    if seconds <= 0:
        raise ValueError("seconds must be greater than 0")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        ensure_manual_activity_table(conn)

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
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
            """,
            (
                activity_date,
                goal_id,
                category,
                title,
                seconds,
                note,
                source,
            ),
        )

        conn.commit()


def list_manual_activities(activity_date: str | None = None) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        ensure_manual_activity_table(conn)

        if activity_date:
            rows = conn.execute(
                """
                SELECT
                    id,
                    activity_date,
                    goal_id,
                    category,
                    title,
                    seconds,
                    note,
                    source,
                    created_at
                FROM manual_activity_logs
                WHERE activity_date = ?
                ORDER BY activity_date DESC, id DESC
                """,
                (activity_date,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT
                    id,
                    activity_date,
                    goal_id,
                    category,
                    title,
                    seconds,
                    note,
                    source,
                    created_at
                FROM manual_activity_logs
                ORDER BY activity_date DESC, id DESC
                LIMIT 50
                """
            ).fetchall()

    if not rows:
        if activity_date:
            print(f"No manual activities found for {activity_date}.")
        else:
            print("No manual activities found.")
        return

    print("Manual activity entries:")
    print("-" * 100)

    for row in rows:
        note = row["note"] or ""

        print(
            f"ID: {row['id']} | "
            f"date: {row['activity_date']} | "
            f"goal: {row['goal_id']} | "
            f"category: {row['category']} | "
            f"duration: {format_seconds(int(row['seconds']))}"
        )
        print(f"  title: {row['title']}")

        if note:
            print(f"  note: {note}")

        print(f"  source: {row['source']} | created_at: {row['created_at']}")
        print()


def get_manual_activity_by_id(entry_id: int) -> dict[str, Any] | None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        ensure_manual_activity_table(conn)

        row = conn.execute(
            """
            SELECT
                id,
                activity_date,
                goal_id,
                category,
                title,
                seconds,
                note,
                source,
                created_at
            FROM manual_activity_logs
            WHERE id = ?
            """,
            (entry_id,),
        ).fetchone()

    if row is None:
        return None

    return dict(row)


def delete_manual_activity(entry_id: int) -> None:
    entry = get_manual_activity_by_id(entry_id)

    if entry is None:
        print(f"Manual activity not found: ID {entry_id}")
        return

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        ensure_manual_activity_table(conn)

        conn.execute(
            """
            DELETE FROM manual_activity_logs
            WHERE id = ?
            """,
            (entry_id,),
        )

        conn.commit()

    print("Manual activity deleted:")
    print(f"  id: {entry['id']}")
    print(f"  date: {entry['activity_date']}")
    print(f"  goal: {entry['goal_id']}")
    print(f"  title: {entry['title']}")
    print(f"  category: {entry['category']}")
    print(f"  duration: {format_seconds(int(entry['seconds']))}")

    if entry.get("note"):
        print(f"  note: {entry['note']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add, list, or delete manual activity in GoalCompass."
    )

    parser.add_argument(
        "--preset",
        type=str,
        help="Preset id from data/user_config/manual_presets.json",
    )

    parser.add_argument(
        "--goal",
        type=str,
        help="Goal id for custom manual activity",
    )

    parser.add_argument(
        "--category",
        type=str,
        default="manual",
        help="Category for custom manual activity",
    )

    parser.add_argument(
        "--title",
        type=str,
        help="Title for custom manual activity",
    )

    parser.add_argument(
        "--minutes",
        type=int,
        help="Duration in minutes for custom manual activity",
    )

    parser.add_argument(
        "--date",
        type=str,
        default=date.today().isoformat(),
        help="Activity date in YYYY-MM-DD format",
    )

    parser.add_argument(
        "--note",
        type=str,
        default="",
        help="Optional note",
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List manual activities. Uses --date if provided.",
    )

    parser.add_argument(
        "--delete",
        type=int,
        help="Delete manual activity by ID.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.delete is not None:
        delete_manual_activity(args.delete)
        return

    if args.list:
        list_manual_activities(activity_date=args.date)
        return

    if not args.preset and not args.goal:
        print_presets()
        return

    if args.preset:
        preset = find_preset(args.preset)

        if preset is None:
            print(f"Preset not found: {args.preset}")
            print()
            print_presets()
            return

        goal_id = str(preset["goal_id"])
        category = str(preset.get("category", "manual"))
        title = str(preset.get("title", args.preset))
        seconds = int(preset["seconds"])
        note = args.note

    else:
        if not args.goal:
            raise ValueError("--goal is required for custom manual activity")

        if not args.title:
            raise ValueError("--title is required for custom manual activity")

        if not args.minutes:
            raise ValueError("--minutes is required for custom manual activity")

        goal_id = args.goal
        category = args.category
        title = args.title
        seconds = args.minutes * 60
        note = args.note

    insert_manual_activity(
        activity_date=args.date,
        goal_id=goal_id,
        category=category,
        title=title,
        seconds=seconds,
        note=note,
    )

    print("Manual activity added:")
    print(f"  date: {args.date}")
    print(f"  goal: {goal_id}")
    print(f"  title: {title}")
    print(f"  category: {category}")
    print(f"  duration: {format_seconds(seconds)}")

    if note:
        print(f"  note: {note}")


if __name__ == "__main__":
    main()
# data/add_manual_activity.py

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


from src.services.manual_activity_service import (
    ManualActivityInput,
    add_manual_activity,
    add_manual_activity_from_preset,
    delete_manual_activity,
    find_preset,
    format_seconds,
    list_manual_activities,
    load_presets,
)


def print_presets() -> None:
    presets = load_presets()

    if not presets:
        print("No presets found.")
        return

    print("Available manual activity presets:")
    print("-" * 60)

    for preset in presets:
        print(f"{preset.preset_id}")
        print(f"  goal: {preset.goal_id}")
        print(f"  title: {preset.title}")
        print(f"  category: {preset.category}")
        print(f"  duration: {format_seconds(preset.seconds)}")
        print()

    print("Usage examples:")
    print("  python data/add_manual_activity.py --preset german_homework_30m")
    print("  python data/add_manual_activity.py --preset german_lesson_90m --date 2026-06-27")
    print("  python data/add_manual_activity.py --goal german_b1_001 --minutes 45 --title \"German homework\" --category learning")
    print("  python data/add_manual_activity.py --list")
    print("  python data/add_manual_activity.py --list --date 2026-06-27")
    print("  python data/add_manual_activity.py --delete 1")


def print_manual_activities(activity_date: str | None = None) -> None:
    entries = list_manual_activities(activity_date=activity_date)

    if not entries:
        if activity_date:
            print(f"No manual activities found for {activity_date}.")
        else:
            print("No manual activities found.")
        return

    print("Manual activity entries:")
    print("-" * 100)

    for entry in entries:
        print(
            f"ID: {entry.id} | "
            f"date: {entry.activity_date} | "
            f"goal: {entry.goal_id} | "
            f"category: {entry.category} | "
            f"duration: {format_seconds(entry.seconds)}"
        )
        print(f"  title: {entry.title}")

        if entry.note:
            print(f"  note: {entry.note}")

        print(f"  source: {entry.source} | created_at: {entry.created_at}")
        print()


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
        deleted_entry = delete_manual_activity(args.delete)

        if deleted_entry is None:
            print(f"Manual activity not found: ID {args.delete}")
            return

        print("Manual activity deleted:")
        print(f"  id: {deleted_entry.id}")
        print(f"  date: {deleted_entry.activity_date}")
        print(f"  goal: {deleted_entry.goal_id}")
        print(f"  title: {deleted_entry.title}")
        print(f"  category: {deleted_entry.category}")
        print(f"  duration: {format_seconds(deleted_entry.seconds)}")

        if deleted_entry.note:
            print(f"  note: {deleted_entry.note}")

        return

    if args.list:
        print_manual_activities(activity_date=args.date)
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

        entry = add_manual_activity_from_preset(
            preset_id=args.preset,
            activity_date=args.date,
            note=args.note,
        )

    else:
        if not args.goal:
            raise ValueError("--goal is required for custom manual activity")

        if not args.title:
            raise ValueError("--title is required for custom manual activity")

        if not args.minutes:
            raise ValueError("--minutes is required for custom manual activity")

        entry = add_manual_activity(
            ManualActivityInput(
                activity_date=args.date,
                goal_id=args.goal,
                category=args.category,
                title=args.title,
                seconds=args.minutes * 60,
                note=args.note,
                source="manual",
            )
        )

    print("Manual activity added:")
    print(f"  id: {entry.id}")
    print(f"  date: {entry.activity_date}")
    print(f"  goal: {entry.goal_id}")
    print(f"  title: {entry.title}")
    print(f"  category: {entry.category}")
    print(f"  duration: {format_seconds(entry.seconds)}")

    if entry.note:
        print(f"  note: {entry.note}")


if __name__ == "__main__":
    main()
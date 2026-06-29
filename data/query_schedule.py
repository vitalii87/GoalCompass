# data/query_schedule.py

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


from src.services.schedule_service import (
    ScheduleDayView,
    build_schedule_day_view,
    format_minutes_as_duration,
    parse_date,
)


def print_schedule(day_view: ScheduleDayView) -> None:
    print("=" * 70)
    print(f"SCHEDULE FOR {day_view.activity_date.isoformat()} | {day_view.weekday}")
    print("=" * 70)

    if not day_view.events:
        print("No scheduled activities found.")
        print("=" * 70)
        return

    for event in day_view.events:
        print("-" * 70)
        print(f"{event.start_time}–{event.end_time} | {format_minutes_as_duration(event.duration_minutes)}")
        print(f"title: {event.title}")
        print(f"id: {event.schedule_id}")
        print(f"goal: {event.goal_id or '[none]'}")
        print(f"category: {event.category}")
        print(f"counts_to_goal: {event.counts_to_goal}")
        print(f"confirmation_mode: {event.confirmation_mode}")
        print(f"blocking: {event.blocking}")

    print("-" * 70)
    print("SUMMARY")
    print(f"planned goal time:     {format_minutes_as_duration(day_view.planned_goal_minutes)}")
    print(f"planned non-goal time: {format_minutes_as_duration(day_view.planned_non_goal_minutes)}")
    print(f"planned total time:    {format_minutes_as_duration(day_view.planned_total_minutes)}")

    print("-" * 70)
    print("CONFLICTS")

    if not day_view.conflicts:
        print("No schedule conflicts found.")
    else:
        for conflict in day_view.conflicts:
            first = conflict.first_event
            second = conflict.second_event

            print(
                f"CONFLICT: {first.start_time}–{first.end_time} {first.title} "
                f"overlaps with {second.start_time}–{second.end_time} {second.title}"
            )
            print(f"  first_id:  {first.schedule_id}")
            print(f"  second_id: {second.schedule_id}")

    print("=" * 70)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Show GoalCompass schedule for a date."
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
    target_date = parse_date(args.activity_date)
    day_view = build_schedule_day_view(target_date)
    print_schedule(day_view)


if __name__ == "__main__":
    main()
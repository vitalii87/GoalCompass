# data/query_goal_progress.py

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


from src.services.goal_progress_service import (
    GoalProgressDayView,
    build_goal_progress_day_view,
    format_seconds,
)


def print_goal_progress(day_view: GoalProgressDayView) -> None:
    print("=" * 60)
    print(f"GOAL PROGRESS FOR {day_view.activity_date}")
    print("=" * 60)

    for result in day_view.results:
        print("-" * 60)
        print(result.title)
        print(f"id: {result.goal_id}")
        print(f"desktop: {format_seconds(result.desktop_seconds)}")
        print(f"manual:  {format_seconds(result.manual_seconds)}")
        print(f"total:   {format_seconds(result.total_seconds)}")

        if result.manual_entries:
            print("manual entries:")

            for entry in result.manual_entries:
                print(
                    f"  - #{entry.id} {entry.title}: "
                    f"{format_seconds(entry.seconds)} "
                    f"[{entry.source}]"
                )

        if result.limit_seconds is not None and result.status in {
            "within limit",
            "over limit",
        }:
            print(f"limit:   {format_seconds(result.limit_seconds)}")
            print(f"status: {result.status}")

            if result.status == "within limit":
                print(f"remaining: {format_seconds(result.remaining_seconds)}")
            else:
                print(f"over by: {format_seconds(result.extra_seconds)}")

        elif result.target_seconds is not None:
            print(f"target:  {format_seconds(result.target_seconds)}")
            print(f"status: {result.status}")

            if result.status == "below target":
                print(f"missing: {format_seconds(result.missing_seconds)}")
            elif result.status == "target reached":
                print(f"extra:   {format_seconds(result.extra_seconds)}")

        else:
            print("status: not configured")

    print("=" * 60)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Show GoalCompass goal progress for a date."
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
    day_view = build_goal_progress_day_view(args.activity_date)
    print_goal_progress(day_view)


if __name__ == "__main__":
    main()

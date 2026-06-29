# data/query_panel_status.py

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


from src.services.panel_status_service import (
    PanelStatusDayView,
    build_panel_status_day_view,
    format_seconds_clock,
    format_seconds_compact,
)


STATUS_ICONS = {
    "positive": "GREEN",
    "neutral": "YELLOW",
    "negative": "RED",
    "idle": "GRAY",
}


def print_panel_status(day_view: PanelStatusDayView) -> None:
    totals = day_view.totals

    print("=" * 60)
    print(f"PANEL STATUS FOR {day_view.activity_date}")
    print("=" * 60)

    print("TOTALS")
    print(f"positive: {format_seconds_compact(totals.positive_seconds)}")
    print(f"neutral:  {format_seconds_compact(totals.neutral_seconds)}")
    print(f"negative: {format_seconds_compact(totals.negative_seconds)}")
    print(f"idle:     {format_seconds_compact(totals.idle_seconds)}")
    print(f"tracked:  {format_seconds_compact(totals.tracked_seconds)}")
    print(f"with idle:{format_seconds_compact(totals.total_with_idle_seconds)}")

    print("-" * 60)
    print("CURRENT")

    if day_view.current is None:
        print("No current activity found.")
    else:
        current = day_view.current
        icon = STATUS_ICONS.get(current.panel_status, current.panel_status)

        print(f"status:   {icon} / {current.panel_status}")
        print(f"category: {current.category}")
        print(f"state:    {current.activity_state}")
        print(f"process:  {current.process_name}")
        print(f"title:    {current.window_title}")
        print(f"seconds:  {format_seconds_clock(current.seconds)}")
        print(f"created:  {current.created_at}")

    print("=" * 60)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Show GoalCompass panel status totals."
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
    day_view = build_panel_status_day_view(args.activity_date)
    print_panel_status(day_view)


if __name__ == "__main__":
    main()
# data/query_dashboard.py

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


from src.services.dashboard_service import (
    DashboardView,
    build_dashboard_view,
)
from src.services.goal_progress_service import format_seconds


def print_dashboard(view: DashboardView) -> None:
    print("=" * 70)
    print(f"GOALCOMPASS DASHBOARD | {view.activity_date}")
    print(f"Week: {view.week_start_date} -> {view.week_end_date}")
    print("=" * 70)

    print("CURRENT")
    if view.current_state is None:
        print("No current state.")
    else:
        state = view.current_state
        stale = "STALE" if view.current_state_stale else "LIVE"

        print(f"state:    {stale}")
        print(f"status:   {state.panel_status}")
        print(f"category: {state.category}")
        print(f"activity: {state.activity_state}")
        print(f"process:  {state.process_name}")
        print(f"title:    {state.window_title}")
        print(f"session:  {format_seconds(state.session_seconds)}")
        print(f"updated:  {state.updated_at}")

    print("-" * 70)
    print("TODAY TOTALS")

    totals = view.panel_totals_today
    print(f"positive: {format_seconds(totals.positive_seconds)}")
    print(f"neutral:  {format_seconds(totals.neutral_seconds)}")
    print(f"negative: {format_seconds(totals.negative_seconds)}")
    print(f"idle:     {format_seconds(totals.idle_seconds)}")
    print(f"tracked:  {format_seconds(totals.tracked_seconds)}")

    print("-" * 70)
    print("GOALS")

    if not view.goals:
        print("No goals found.")
    else:
        for goal in view.goals:
            print(f"{goal.title}")
            print(f"  id:     {goal.goal_id}")
            print(f"  type:   {goal.goal_type}")
            print(f"  today:  {format_seconds(goal.today_seconds)}")
            print(f"  week:   {format_seconds(goal.week_seconds)}")

            if goal.target_seconds > 0:
                print(f"  target: {format_seconds(goal.target_seconds)}")

            if goal.limit_seconds > 0:
                print(f"  limit:  {format_seconds(goal.limit_seconds)}")

            print(f"  status: {goal.status}")
            print(f"  note:   {goal.message}")

    print("-" * 70)
    print("WARNINGS")

    if not view.warnings:
        print("No warnings.")
    else:
        for warning in view.warnings:
            print(f"[{warning.warning_type}] {warning.message}")

    print("=" * 70)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Show GoalCompass dashboard."
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
    view = build_dashboard_view(args.activity_date)
    print_dashboard(view)


if __name__ == "__main__":
    main()
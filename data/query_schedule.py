# data/query_schedule.py

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
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


def format_minutes_as_duration(minutes: int) -> str:
    hours = minutes // 60
    mins = minutes % 60

    if hours > 0 and mins > 0:
        return f"{hours}h {mins}m"
    if hours > 0:
        return f"{hours}h"
    return f"{mins}m"


def calculate_duration_minutes(start_time: str, end_time: str) -> int:
    start_minutes = parse_time_to_minutes(start_time)
    end_minutes = parse_time_to_minutes(end_time)

    if end_minutes < start_minutes:
        # Basic support for overnight events.
        end_minutes += 24 * 60

    return max(end_minutes - start_minutes, 0)


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

        start_minutes = parse_time_to_minutes(start_time)
        end_minutes = parse_time_to_minutes(end_time)

        if end_minutes < start_minutes:
            end_minutes += 24 * 60

        duration_minutes = max(end_minutes - start_minutes, 0)

        event = dict(item)
        event["start_minutes"] = start_minutes
        event["end_minutes"] = end_minutes
        event["duration_minutes"] = duration_minutes
        event["blocking"] = bool(item.get("blocking", True))
        events.append(event)

    events.sort(key=lambda event: int(event.get("start_minutes", 0)))
    return events


def events_overlap(first: dict[str, Any], second: dict[str, Any]) -> bool:
    first_start = int(first.get("start_minutes", 0))
    first_end = int(first.get("end_minutes", 0))
    second_start = int(second.get("start_minutes", 0))
    second_end = int(second.get("end_minutes", 0))

    return first_start < second_end and second_start < first_end


def find_schedule_conflicts(events: list[dict[str, Any]]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    conflicts: list[tuple[dict[str, Any], dict[str, Any]]] = []

    blocking_events = [
        event
        for event in events
        if bool(event.get("blocking", True))
    ]

    for index, first_event in enumerate(blocking_events):
        for second_event in blocking_events[index + 1:]:
            if events_overlap(first_event, second_event):
                conflicts.append((first_event, second_event))

    return conflicts


def print_schedule_conflicts(events: list[dict[str, Any]]) -> None:
    conflicts = find_schedule_conflicts(events)

    print("-" * 70)
    print("CONFLICTS")

    if not conflicts:
        print("No schedule conflicts found.")
        return

    for first_event, second_event in conflicts:
        first_title = first_event.get("title", "[missing title]")
        second_title = second_event.get("title", "[missing title]")

        first_start = first_event.get("start_time", "??:??")
        first_end = first_event.get("end_time", "??:??")

        second_start = second_event.get("start_time", "??:??")
        second_end = second_event.get("end_time", "??:??")

        first_id = first_event.get("schedule_id", "[missing schedule_id]")
        second_id = second_event.get("schedule_id", "[missing schedule_id]")

        print(
            f"CONFLICT: {first_start}–{first_end} {first_title} "
            f"overlaps with {second_start}–{second_end} {second_title}"
        )
        print(f"  first_id:  {first_id}")
        print(f"  second_id: {second_id}")


def print_schedule_for_date(target_date: date) -> None:
    schedule_items = load_schedule()
    events = get_events_for_date(schedule_items, target_date)

    weekday = WEEKDAY_NAMES[target_date.weekday()]

    print("=" * 70)
    print(f"SCHEDULE FOR {target_date.isoformat()} | {weekday}")
    print("=" * 70)

    if not events:
        print("No scheduled activities found.")
        print("=" * 70)
        return

    planned_goal_minutes = 0
    planned_non_goal_minutes = 0

    for event in events:
        schedule_id = event.get("schedule_id", "[missing schedule_id]")
        goal_id = event.get("goal_id", "")
        title = event.get("title", "[missing title]")
        category = event.get("category", "[missing category]")
        start_time = event.get("start_time", "??:??")
        end_time = event.get("end_time", "??:??")
        counts_to_goal = bool(event.get("counts_to_goal", False))
        confirmation_mode = event.get("confirmation_mode", "none")
        duration_minutes = int(event.get("duration_minutes", 0))
        blocking = bool(event.get("blocking", True))

        if counts_to_goal:
            planned_goal_minutes += duration_minutes
        else:
            planned_non_goal_minutes += duration_minutes

        print("-" * 70)
        print(f"{start_time}–{end_time} | {format_minutes_as_duration(duration_minutes)}")
        print(f"title: {title}")
        print(f"id: {schedule_id}")
        print(f"goal: {goal_id or '[none]'}")
        print(f"category: {category}")
        print(f"counts_to_goal: {counts_to_goal}")
        print(f"confirmation_mode: {confirmation_mode}")
        print(f"blocking: {blocking}")

    print("-" * 70)
    print("SUMMARY")
    print(f"planned goal time:     {format_minutes_as_duration(planned_goal_minutes)}")
    print(f"planned non-goal time: {format_minutes_as_duration(planned_non_goal_minutes)}")
    print(f"planned total time:    {format_minutes_as_duration(planned_goal_minutes + planned_non_goal_minutes)}")

    print_schedule_conflicts(events)

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
    print_schedule_for_date(target_date)


if __name__ == "__main__":
    main()
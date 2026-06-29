# src/services/schedule_service.py

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
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


@dataclass(frozen=True)
class ScheduleEvent:
    schedule_id: str
    goal_id: str
    title: str
    category: str
    days: list[str]
    start_time: str
    end_time: str
    counts_to_goal: bool
    confirmation_mode: str
    source: str
    blocking: bool
    start_minutes: int
    end_minutes: int
    duration_minutes: int

    @property
    def duration_seconds(self) -> int:
        return self.duration_minutes * 60


@dataclass(frozen=True)
class ScheduleConflict:
    first_event: ScheduleEvent
    second_event: ScheduleEvent


@dataclass(frozen=True)
class ScheduleDayView:
    activity_date: date
    weekday: str
    events: list[ScheduleEvent]
    conflicts: list[ScheduleConflict]
    planned_goal_minutes: int
    planned_non_goal_minutes: int

    @property
    def planned_total_minutes(self) -> int:
        return self.planned_goal_minutes + self.planned_non_goal_minutes


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


def format_seconds(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def calculate_duration_minutes(start_time: str, end_time: str) -> int:
    start_minutes = parse_time_to_minutes(start_time)
    end_minutes = parse_time_to_minutes(end_time)

    if end_minutes < start_minutes:
        end_minutes += 24 * 60

    return max(end_minutes - start_minutes, 0)


def load_raw_schedule() -> list[dict[str, Any]]:
    if not SCHEDULE_PATH.exists():
        return []

    with SCHEDULE_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("schedule.json must contain a list")

    return [item for item in data if isinstance(item, dict)]


def normalize_days(days: Any) -> list[str]:
    if not isinstance(days, list):
        return []

    return [
        str(day).lower()
        for day in days
        if isinstance(day, str)
    ]


def raw_item_to_event(item: dict[str, Any]) -> ScheduleEvent | None:
    schedule_id = item.get("schedule_id")
    start_time = item.get("start_time")
    end_time = item.get("end_time")

    if not isinstance(schedule_id, str):
        return None

    if not isinstance(start_time, str) or not isinstance(end_time, str):
        return None

    days = normalize_days(item.get("days", []))

    start_minutes = parse_time_to_minutes(start_time)
    end_minutes = parse_time_to_minutes(end_time)

    if end_minutes < start_minutes:
        end_minutes += 24 * 60

    duration_minutes = max(end_minutes - start_minutes, 0)

    return ScheduleEvent(
        schedule_id=schedule_id,
        goal_id=str(item.get("goal_id", "")),
        title=str(item.get("title", schedule_id)),
        category=str(item.get("category", "scheduled")),
        days=days,
        start_time=start_time,
        end_time=end_time,
        counts_to_goal=bool(item.get("counts_to_goal", False)),
        confirmation_mode=str(item.get("confirmation_mode", "none")),
        source=str(item.get("source", "planned_schedule")),
        blocking=bool(item.get("blocking", True)),
        start_minutes=start_minutes,
        end_minutes=end_minutes,
        duration_minutes=duration_minutes,
    )


def load_schedule_events() -> list[ScheduleEvent]:
    raw_items = load_raw_schedule()
    events: list[ScheduleEvent] = []

    for item in raw_items:
        event = raw_item_to_event(item)

        if event is not None:
            events.append(event)

    return events


def get_events_for_date(target_date: date) -> list[ScheduleEvent]:
    weekday = WEEKDAY_NAMES[target_date.weekday()]
    all_events = load_schedule_events()

    events = [
        event
        for event in all_events
        if weekday in event.days
    ]

    events.sort(key=lambda event: event.start_minutes)
    return events


def events_overlap(first: ScheduleEvent, second: ScheduleEvent) -> bool:
    return (
        first.start_minutes < second.end_minutes
        and second.start_minutes < first.end_minutes
    )


def find_schedule_conflicts(events: list[ScheduleEvent]) -> list[ScheduleConflict]:
    conflicts: list[ScheduleConflict] = []

    blocking_events = [
        event
        for event in events
        if event.blocking
    ]

    for index, first_event in enumerate(blocking_events):
        for second_event in blocking_events[index + 1:]:
            if events_overlap(first_event, second_event):
                conflicts.append(
                    ScheduleConflict(
                        first_event=first_event,
                        second_event=second_event,
                    )
                )

    return conflicts


def build_schedule_day_view(target_date: date) -> ScheduleDayView:
    events = get_events_for_date(target_date)
    conflicts = find_schedule_conflicts(events)

    planned_goal_minutes = sum(
        event.duration_minutes
        for event in events
        if event.counts_to_goal
    )

    planned_non_goal_minutes = sum(
        event.duration_minutes
        for event in events
        if not event.counts_to_goal
    )

    weekday = WEEKDAY_NAMES[target_date.weekday()]

    return ScheduleDayView(
        activity_date=target_date,
        weekday=weekday,
        events=events,
        conflicts=conflicts,
        planned_goal_minutes=planned_goal_minutes,
        planned_non_goal_minutes=planned_non_goal_minutes,
    )


def find_event_for_date(
    activity_date: str,
    schedule_id: str,
) -> ScheduleEvent | None:
    target_date = parse_date(activity_date)
    events = get_events_for_date(target_date)

    for event in events:
        if event.schedule_id == schedule_id:
            return event

    return None
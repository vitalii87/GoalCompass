# src/tracker/live_counter.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, Optional

from src.storage.db import SQLiteStorage


@dataclass
class CurrentActivity:
    process_name: str
    category: str
    activity_state: str
    seconds: int = 0


class LiveCounter:
    """
    Runtime counter that:
    - tracks current activity chunk in memory
    - flushes completed chunks into SQLite
    - exposes live daily totals including current in-memory chunk
    """

    def __init__(self, storage: SQLiteStorage) -> None:
        self.storage = storage
        self.current_date = self._today_str()

        persisted = self.storage.get_all_totals_for_date(self.current_date)
        self.daily_category_totals: Dict[str, int] = dict(persisted["by_category"])
        self.daily_process_totals: Dict[str, int] = dict(persisted["by_process"])
        self.daily_state_totals: Dict[str, int] = dict(persisted["by_state"])

        self.current_activity: Optional[CurrentActivity] = None

    def _today_str(self) -> str:
        return date.today().isoformat()

    def _rollover_if_new_day(self) -> None:
        today = self._today_str()
        if today == self.current_date:
            return

        self.flush_current_activity()

        self.current_date = today
        persisted = self.storage.get_all_totals_for_date(self.current_date)
        self.daily_category_totals = dict(persisted["by_category"])
        self.daily_process_totals = dict(persisted["by_process"])
        self.daily_state_totals = dict(persisted["by_state"])
        self.current_activity = None

    def update(
        self,
        process_name: str,
        category: str,
        activity_state: str,
        seconds: int,
    ) -> None:
        if seconds <= 0:
            return

        self._rollover_if_new_day()

        if self.current_activity is None:
            self.current_activity = CurrentActivity(
                process_name=process_name,
                category=category,
                activity_state=activity_state,
                seconds=seconds,
            )
            return

        same_process = self.current_activity.process_name == process_name
        same_category = self.current_activity.category == category
        same_state = self.current_activity.activity_state == activity_state

        if same_process and same_category and same_state:
            self.current_activity.seconds += seconds
            return

        self.flush_current_activity()
        self.current_activity = CurrentActivity(
            process_name=process_name,
            category=category,
            activity_state=activity_state,
            seconds=seconds,
        )

    def flush_current_activity(self) -> None:
        if self.current_activity is None:
            return

        seconds = self.current_activity.seconds
        if seconds > 0:
            self.storage.log_activity(
                activity_date=self.current_date,
                process_name=self.current_activity.process_name,
                category=self.current_activity.category,
                activity_state=self.current_activity.activity_state,
                seconds=seconds,
            )

            self.daily_category_totals[self.current_activity.category] = (
                self.daily_category_totals.get(self.current_activity.category, 0) + seconds
            )
            self.daily_process_totals[self.current_activity.process_name] = (
                self.daily_process_totals.get(self.current_activity.process_name, 0) + seconds
            )
            self.daily_state_totals[self.current_activity.activity_state] = (
                self.daily_state_totals.get(self.current_activity.activity_state, 0) + seconds
            )

        self.current_activity = None

    def get_daily_total_by_category(self, category: str) -> int:
        total = self.daily_category_totals.get(category, 0)

        if self.current_activity is not None and self.current_activity.category == category:
            total += self.current_activity.seconds

        return total

    def get_daily_total_by_process(self, process_name: str) -> int:
        total = self.daily_process_totals.get(process_name, 0)

        if self.current_activity is not None and self.current_activity.process_name == process_name:
            total += self.current_activity.seconds

        return total

    def get_daily_total_by_state(self, activity_state: str) -> int:
        total = self.daily_state_totals.get(activity_state, 0)

        if self.current_activity is not None and self.current_activity.activity_state == activity_state:
            total += self.current_activity.seconds

        return total

    def get_daily_totals_by_category(self) -> Dict[str, int]:
        result = dict(self.daily_category_totals)

        if self.current_activity is not None:
            result[self.current_activity.category] = (
                result.get(self.current_activity.category, 0)
                + self.current_activity.seconds
            )

        return result

    def get_daily_totals_by_process(self) -> Dict[str, int]:
        result = dict(self.daily_process_totals)

        if self.current_activity is not None:
            result[self.current_activity.process_name] = (
                result.get(self.current_activity.process_name, 0)
                + self.current_activity.seconds
            )

        return result

    def get_daily_totals_by_state(self) -> Dict[str, int]:
        result = dict(self.daily_state_totals)

        if self.current_activity is not None:
            result[self.current_activity.activity_state] = (
                result.get(self.current_activity.activity_state, 0)
                + self.current_activity.seconds
            )

        return result

    def get_current_session_info(self) -> Optional[dict]:
        if self.current_activity is None:
            return None

        return {
            "date": self.current_date,
            "process_name": self.current_activity.process_name,
            "category": self.current_activity.category,
            "activity_state": self.current_activity.activity_state,
            "seconds": self.current_activity.seconds,
        }

    def shutdown(self) -> None:
        self.flush_current_activity()
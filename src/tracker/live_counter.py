# src/tracker/live_counter.py

from __future__ import annotations

from datetime import date
from typing import Optional

from src.storage.db import SQLiteStorage


class LiveCounter:
    """
    Runtime activity counter.

    Responsibilities:
    - track current foreground session
    - flush finished sessions to SQLite
    - expose daily totals for live stats
    """

    def __init__(self, storage: SQLiteStorage) -> None:
        self.storage = storage
        self.current_activity_date = date.today().isoformat()

        self.current_process_name: Optional[str] = None
        self.current_window_title: str = ""
        self.current_category: Optional[str] = None
        self.current_activity_state: Optional[str] = None
        self.current_seconds: int = 0

    def update(
        self,
        process_name: str,
        category: str,
        activity_state: str,
        seconds: int,
        window_title: str = "",
    ) -> None:
        if seconds <= 0:
            return

        today = date.today().isoformat()

        if today != self.current_activity_date:
            self._flush_current_session()
            self.current_activity_date = today

        if self._is_same_session(
            process_name=process_name,
            category=category,
            activity_state=activity_state,
            window_title=window_title,
        ):
            self.current_seconds += seconds
            return

        self._flush_current_session()

        self.current_process_name = process_name
        self.current_window_title = window_title
        self.current_category = category
        self.current_activity_state = activity_state
        self.current_seconds = seconds

    def _is_same_session(
        self,
        process_name: str,
        category: str,
        activity_state: str,
        window_title: str,
    ) -> bool:
        return (
            self.current_process_name == process_name
            and self.current_category == category
            and self.current_activity_state == activity_state
            and self.current_window_title == window_title
        )

    def _flush_current_session(self) -> None:
        if (
            self.current_process_name is None
            or self.current_category is None
            or self.current_activity_state is None
            or self.current_seconds <= 0
        ):
            return

        self.storage.log_activity(
            activity_date=self.current_activity_date,
            process_name=self.current_process_name,
            window_title=self.current_window_title,
            category=self.current_category,
            activity_state=self.current_activity_state,
            seconds=self.current_seconds,
        )

        self.current_process_name = None
        self.current_window_title = ""
        self.current_category = None
        self.current_activity_state = None
        self.current_seconds = 0

    def get_current_session_info(self) -> dict | None:
        if (
            self.current_process_name is None
            or self.current_category is None
            or self.current_activity_state is None
        ):
            return None

        return {
            "process_name": self.current_process_name,
            "window_title": self.current_window_title,
            "category": self.current_category,
            "activity_state": self.current_activity_state,
            "seconds": self.current_seconds,
        }

    def get_daily_totals_by_category(self) -> dict[str, int]:
        totals = self.storage.get_daily_totals_by_category(self.current_activity_date)

        if self.current_category and self.current_seconds > 0:
            totals[self.current_category] = (
                totals.get(self.current_category, 0) + self.current_seconds
            )

        return totals

    def get_daily_totals_by_state(self) -> dict[str, int]:
        totals = self.storage.get_daily_totals_by_state(self.current_activity_date)

        if self.current_activity_state and self.current_seconds > 0:
            totals[self.current_activity_state] = (
                totals.get(self.current_activity_state, 0) + self.current_seconds
            )

        return totals

    def get_daily_total_by_category(self, category: str) -> int:
        total = self.storage.get_category_total(
            activity_date=self.current_activity_date,
            category=category,
        )

        if self.current_category == category and self.current_seconds > 0:
            total += self.current_seconds

        return total

    def shutdown(self) -> None:
        self._flush_current_session()
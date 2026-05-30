# src/unknown/unknown_tracker.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.config.config import UNKNOWN_CATEGORY, UNKNOWN_SAVE_THRESHOLD_SECONDS
from src.storage.db import SQLiteStorage


@dataclass
class UnknownSession:
    process_name: str
    window_title: str
    seconds: int = 0


class UnknownTracker:
    def __init__(self, storage: SQLiteStorage) -> None:
        self.storage = storage
        self.current_unknown: Optional[UnknownSession] = None

    def update(
        self,
        process_name: str,
        window_title: str,
        category: str,
        seconds: int,
    ) -> None:
        if seconds <= 0:
            return

        if category != UNKNOWN_CATEGORY:
            self.flush()
            return

        clean_title = window_title.strip()
        if not clean_title:
            return

        if self.current_unknown is None:
            self.current_unknown = UnknownSession(
                process_name=process_name,
                window_title=clean_title,
                seconds=seconds,
            )
            return

        same_unknown = (
            self.current_unknown.process_name == process_name
            and self.current_unknown.window_title == clean_title
        )

        if same_unknown:
            self.current_unknown.seconds += seconds
            return

        self.flush()

        self.current_unknown = UnknownSession(
            process_name=process_name,
            window_title=clean_title,
            seconds=seconds,
        )

    def flush(self) -> None:
        if self.current_unknown is None:
            return

        if self.current_unknown.seconds >= UNKNOWN_SAVE_THRESHOLD_SECONDS:
            self.storage.upsert_unknown_title(
                process_name=self.current_unknown.process_name,
                window_title=self.current_unknown.window_title,
                seconds=self.current_unknown.seconds,
            )

        self.current_unknown = None

    def shutdown(self) -> None:
        self.flush()
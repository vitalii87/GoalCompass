# src/signals/signals_engine.py

from __future__ import annotations

from src.signals.signal import Signal
from src.signals.signal_types import LONG_SESSION


SESSION_MILESTONES_SECONDS = [
    60,
    300,
    600,
    1800,
    3600,
]


SIGNAL_ENABLED_CATEGORIES = {
    "productive",
    "time_wasting",
    "distracting",
}


class SignalsEngine:
    def generate_for_session(
        self,
        process_name: str,
        category: str,
        seconds: int,
        activity_state: str = "active",
    ) -> list[Signal]:
        signals: list[Signal] = []

        if activity_state != "active":
            return signals

        if category not in SIGNAL_ENABLED_CATEGORIES:
            return signals

        for milestone_seconds in SESSION_MILESTONES_SECONDS:
            if seconds >= milestone_seconds:
                signals.append(
                    Signal(
                        signal_type=LONG_SESSION,
                        category=category,
                        process_name=process_name,
                        seconds=milestone_seconds,
                        message=f"Session milestone reached: {milestone_seconds}s",
                        metadata={
                            "threshold_seconds": milestone_seconds,
                            "activity_state": activity_state,
                        },
                    )
                )

        return signals

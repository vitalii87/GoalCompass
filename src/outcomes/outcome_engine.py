from __future__ import annotations

from src.outcomes.outcome import Outcome
from src.outcomes.outcome_types import (
    DISTRACTION,
    FOCUS_SESSION,
    PRODUCTIVE_ACTIVITY,
    TIME_WASTED,
)
from src.signals.signal import Signal
from src.signals.signal_types import LONG_SESSION


FOCUS_SESSION_MIN_SECONDS = 300


class OutcomeEngine:
    def generate_from_signal(self, signal: Signal) -> Outcome | None:
        if signal.signal_type != LONG_SESSION:
            return None

        if signal.category == "productive":
            outcome_type = (
                FOCUS_SESSION
                if signal.seconds >= FOCUS_SESSION_MIN_SECONDS
                else PRODUCTIVE_ACTIVITY
            )

            return Outcome(
                outcome_type=outcome_type,
                category=signal.category,
                seconds=signal.seconds,
                message="Productive activity detected",
                metadata={
                    "process_name": signal.process_name,
                    "source_signal": signal.signal_type,
                },
            )

        if signal.category == "time_wasting":
            return Outcome(
                outcome_type=TIME_WASTED,
                category=signal.category,
                seconds=signal.seconds,
                message="Time-wasting activity detected",
                metadata={
                    "process_name": signal.process_name,
                    "source_signal": signal.signal_type,
                },
            )

        if signal.category == "distracting":
            return Outcome(
                outcome_type=DISTRACTION,
                category=signal.category,
                seconds=signal.seconds,
                message="Distracting activity detected",
                metadata={
                    "process_name": signal.process_name,
                    "source_signal": signal.signal_type,
                },
            )

        return None
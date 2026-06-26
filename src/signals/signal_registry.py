# src/signals/signal_registry.py

from __future__ import annotations

from src.signals.signal_types import (
    LONG_SESSION,
    DAILY_LIMIT_EXCEEDED,
    FOCUS_SESSION_COMPLETED,
    RAPID_WINDOW_SWITCHING,
    LATE_NIGHT_ACTIVITY,
)

ALL_SIGNALS = {
    LONG_SESSION,
    DAILY_LIMIT_EXCEEDED,
    FOCUS_SESSION_COMPLETED,
    RAPID_WINDOW_SWITCHING,
    LATE_NIGHT_ACTIVITY,
}
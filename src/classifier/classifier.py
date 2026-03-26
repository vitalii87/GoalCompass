# src/classifier/classifier.py

from __future__ import annotations

from src.config.config import (
    DISTRACTING,
    PRODUCTIVE,
    TIME_WASTING,
    UNKNOWN_CATEGORY,
)


def normalize_process_name(process_name: str | None) -> str:
    if not process_name:
        return ""
    return process_name.strip().lower()


def classify_process_name(process_name: str | None) -> str:
    normalized = normalize_process_name(process_name)

    if not normalized:
        return UNKNOWN_CATEGORY

    if normalized in PRODUCTIVE:
        return "productive"

    if normalized in DISTRACTING:
        return "distracting"

    if normalized in TIME_WASTING:
        return "time_wasting"

    return UNKNOWN_CATEGORY
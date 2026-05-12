# src/classifier/classifier.py

from __future__ import annotations

from src.config.config import (
    DISTRACTING,
    PRODUCTIVE,
    TIME_WASTING,
    UNKNOWN_CATEGORY,
)
from src.classifier.title_rules import match_title_category


def normalize_process_name(process_name: str | None) -> str:
    if not process_name:
        return ""
    return process_name.strip().lower()


def classify_process_name(
    process_name: str | None,
    window_title: str | None = None,
) -> str:
    normalized = normalize_process_name(process_name)

    if not normalized:
        return UNKNOWN_CATEGORY

    # ------------------------------
    # 1. Title-aware classification
    # ------------------------------
    if window_title:
        title_category = match_title_category(normalized, window_title)
        if title_category:
            return title_category

    # ------------------------------
    # 2. Process-based fallback
    # ------------------------------
    if normalized in PRODUCTIVE:
        return "productive"

    if normalized in DISTRACTING:
        return "distracting"

    if normalized in TIME_WASTING:
        return "time_wasting"

    return UNKNOWN_CATEGORY
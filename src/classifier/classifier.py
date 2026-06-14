# src/classifier/classifier.py

from __future__ import annotations

from src.classifier.title_rules import match_title_category
from src.config.config import UNKNOWN_CATEGORY
from src.profiles.profile_loader import get_profile


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

    if window_title:
        title_category = match_title_category(normalized, window_title)
        if title_category:
            return title_category

    profile = get_profile()

    if normalized in profile["productive"]:
        return "productive"

    if normalized in profile["personal"]:
        return "personal"

    if normalized in profile["distracting"]:
        return "distracting"

    if normalized in profile["time_wasting"]:
        return "time_wasting"

    return UNKNOWN_CATEGORY
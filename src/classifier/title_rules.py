# src/classifier/title_rules.py

from __future__ import annotations

from src.profiles.profile_loader import get_title_rules


def normalize_title(window_title: str | None) -> str:
    if not window_title:
        return ""
    return window_title.strip().lower()


def match_title_category(
    process_name: str | None,
    window_title: str | None,
) -> str | None:
    if not process_name or not window_title:
        return None

    normalized_process = process_name.strip().lower()
    normalized_title = normalize_title(window_title)

    title_rules = get_title_rules()
    process_rules = title_rules.get(normalized_process)

    if not process_rules:
        return None

    for category, keywords in process_rules.items():
        for keyword in keywords:
            if keyword.lower() in normalized_title:
                return category

    return None
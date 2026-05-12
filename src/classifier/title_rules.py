# src/classifier/title_rules.py

from __future__ import annotations

from src.config.config import TITLE_RULES


def normalize_title(title: str | None) -> str:
    if not title:
        return ""
    return title.lower()


def match_title_category(process_name: str, window_title: str) -> str | None:
    """
    Returns category based on title rules if match found,
    otherwise None.
    """

    normalized_title = normalize_title(window_title)

    if not normalized_title:
        return None

    rules_for_process = TITLE_RULES.get(process_name)
    if not rules_for_process:
        return None

    scores = {}

    for category, keywords in rules_for_process.items():
        for keyword in keywords:
            if keyword in normalized_title:
                scores[category] = scores.get(category, 0) + 1

    if not scores:
        return None

    # pick category with highest score
    return max(scores, key=scores.get)
# src/profiles/profile_loader.py

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.app_paths import USER_CONFIG_DIR
from src.profiles.default_profile import (
    GOALS,
    PROFILE,
    TITLE_RULES,
)

PRIMARY_PROFILE_PATH = USER_CONFIG_DIR / "primary.json"


def _load_primary_profile() -> dict[str, Any] | None:
    if not PRIMARY_PROFILE_PATH.exists():
        return None

    try:
        with PRIMARY_PROFILE_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            return None

        return data

    except (OSError, json.JSONDecodeError):
        return None


def get_profile() -> dict[str, set[str]]:
    profile_data = _load_primary_profile()

    if profile_data:
        process_rules = profile_data.get("process_rules", {})

        if isinstance(process_rules, dict):
            return {
                str(category): {
                    str(process_name).lower()
                    for process_name in process_names
                    if isinstance(process_name, str)
                }
                for category, process_names in process_rules.items()
                if isinstance(process_names, list)
            }

    return PROFILE


def get_title_rules() -> dict[str, dict[str, list[str]]]:
    profile_data = _load_primary_profile()

    if profile_data:
        title_rules = profile_data.get("title_rules", {})

        if isinstance(title_rules, dict):
            normalized_title_rules: dict[str, dict[str, list[str]]] = {}

            for process_name, category_rules in title_rules.items():
                if not isinstance(process_name, str):
                    continue

                if not isinstance(category_rules, dict):
                    continue

                normalized_category_rules: dict[str, list[str]] = {}

                for category, keywords in category_rules.items():
                    if not isinstance(category, str):
                        continue

                    if not isinstance(keywords, list):
                        continue

                    normalized_category_rules[category] = [
                        str(keyword).lower()
                        for keyword in keywords
                        if isinstance(keyword, str)
                    ]

                normalized_title_rules[process_name.lower()] = normalized_category_rules

            return normalized_title_rules

    return TITLE_RULES


def get_goals() -> list[dict[str, Any]]:
    profile_data = _load_primary_profile()

    if profile_data:
        goals = profile_data.get("goals", [])

        if isinstance(goals, list):
            return [
                goal
                for goal in goals
                if isinstance(goal, dict)
            ]

    return GOALS


def get_coach_persona() -> str:
    profile_data = _load_primary_profile()

    if profile_data:
        coach_persona = profile_data.get("coach_persona", "balanced")

        if isinstance(coach_persona, str):
            return coach_persona

    return "balanced"

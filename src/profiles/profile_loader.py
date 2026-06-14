# src/profiles/profile_loader.py

from __future__ import annotations

from src.profiles.default_profile import PROFILE, TITLE_RULES


def get_profile() -> dict[str, set[str]]:
    return PROFILE


def get_title_rules() -> dict[str, dict[str, list[str]]]:
    return TITLE_RULES
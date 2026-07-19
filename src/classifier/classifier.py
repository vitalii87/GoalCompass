# src/classifier/classifier.py

from __future__ import annotations

from src.services.activity_rules_service import match_activity_rule


UNKNOWN_CATEGORY = "unknown"
NEUTRAL_CATEGORY = "neutral"
PRODUCTIVE_CATEGORY = "productive"
TIME_WASTING_CATEGORY = "time_wasting"
DISTRACTING_CATEGORY = "distracting"
PERSONAL_CATEGORY = "personal"
IGNORED_CATEGORY = "ignored"


BROWSER_PROCESSES = {
    "chrome.exe",
    "msedge.exe",
    "firefox.exe",
    "brave.exe",
    "opera.exe",
    "vivaldi.exe",
}


def normalize_text(value: str | None) -> str:
    if value is None:
        return ""

    return str(value).lower().strip()


def normalize_process_name(process_name: str | None) -> str:
    normalized = normalize_text(process_name)
    normalized = normalized.replace("\\", "/").split("/")[-1]
    return normalized


def classify_process_name(
    process_name: str,
    window_title: str = "",
    url: str = "",
) -> str:
    """
    Classification priority:
        1. manual rules
        2. built-in rules
        3. browser unknown
        4. fallback unknown

    Manual rules have priority because user context can override defaults.

    Example:
        built-in: worldoftanks.exe -> time_wasting
        manual override: worldoftanks.exe -> productive
    """

    process = normalize_process_name(process_name)
    title = normalize_text(window_title)

    if not process:
        return UNKNOWN_CATEGORY

    try:
        matched_rule = match_activity_rule(
            process_name=process,
            window_title=title,
            url=url,
        )
    except Exception:
        matched_rule = None

    if matched_rule is not None:
        return matched_rule.category

    if process in BROWSER_PROCESSES:
        return UNKNOWN_CATEGORY

    return UNKNOWN_CATEGORY


def explain_classification(
    process_name: str,
    window_title: str = "",
    url: str = "",
) -> dict[str, str]:
    process = normalize_process_name(process_name)
    title = normalize_text(window_title)

    category = classify_process_name(
        process_name=process,
        window_title=title,
        url=url,
    )

    reason = "fallback_unknown"

    try:
        matched_rule = match_activity_rule(
            process_name=process,
            window_title=title,
            url=url,
        )
    except Exception:
        matched_rule = None

    if matched_rule is not None:
        reason = (
            f"{matched_rule.source}_rule:"
            f"{matched_rule.rule_type}:"
            f"{matched_rule.value}:"
            f"{matched_rule.rule_id}"
        )
    elif process in BROWSER_PROCESSES:
        reason = "browser_unknown"

    return {
        "process_name": process,
        "window_title": window_title,
        "category": category,
        "reason": reason,
    }

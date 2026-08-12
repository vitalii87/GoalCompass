# src/services/settings_service.py

from __future__ import annotations

import json
import os
import time
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
USER_CONFIG_DIR = ROOT_DIR / "data" / "user_config"
SETTINGS_PATH = USER_CONFIG_DIR / "settings.json"


DEFAULT_SETTINGS: dict[str, Any] = {
    "app": {
        "first_run_completed": False,
        "start_tracker": True,
        "start_overlay": True,
        "start_control_panel_after_setup": False,
    },
    "activity_window": {
        "reset_hour": 3,
    },
    "overlay": {
        "enabled": True,
        "show_badge": True,
        "show_popup": True,
        "refresh_seconds": 3,
    },
    "notifications": {
        "enabled": True,
        "time_wasting_warning": True,
    },
    "automation": {
        "mode": "manual",
        "require_confirmation": True,
    },
    "interaction": {
        "mode": "standard",
        "daily_prompt_limit": 3,
        "cooldown_minutes": 60,
    },
    "coach": {
        "enabled": True,
        "style": "neutral",
    },
    "mvp": {
        "setup_version": 1,
    },
}


VALID_AUTOMATION_MODES = {"manual", "ai_assisted", "full_ai"}
VALID_INTERACTION_MODES = {"silent", "standard", "proactive", "intensive"}
VALID_COACH_STYLES = {"soft", "neutral", "strict", "aggressive"}

LEGACY_COACH_STYLE_MAP = {
    "balanced": "neutral",
    "direct": "neutral",
}


def ensure_user_config_dir() -> None:
    USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def deep_merge(defaults: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    """
    Preserve existing user settings, but add missing default keys.
    """
    result = deepcopy(defaults)

    for key, value in current.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def clamp_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default

    return max(minimum, min(maximum, parsed))


def normalize_settings(settings: dict[str, Any]) -> dict[str, Any]:
    """Add defaults and normalize the user-facing operating modes."""
    normalized = deep_merge(DEFAULT_SETTINGS, settings)

    automation = normalized["automation"]
    automation_mode = str(automation.get("mode", "manual")).strip().lower()
    if automation_mode not in VALID_AUTOMATION_MODES:
        automation_mode = "manual"
    automation["mode"] = automation_mode
    automation["require_confirmation"] = bool(
        automation.get("require_confirmation", True)
    )

    interaction = normalized["interaction"]
    interaction_mode = str(interaction.get("mode", "standard")).strip().lower()
    if interaction_mode not in VALID_INTERACTION_MODES:
        interaction_mode = "standard"
    interaction["mode"] = interaction_mode
    interaction["daily_prompt_limit"] = clamp_int(
        interaction.get("daily_prompt_limit"),
        default=3,
        minimum=0,
        maximum=50,
    )
    interaction["cooldown_minutes"] = clamp_int(
        interaction.get("cooldown_minutes"),
        default=60,
        minimum=0,
        maximum=1440,
    )

    coach = normalized["coach"]
    coach_style = str(coach.get("style", "neutral")).strip().lower()
    if coach_style in {"off", "silent"}:
        coach["enabled"] = False
        coach_style = "neutral"
    coach_style = LEGACY_COACH_STYLE_MAP.get(coach_style, coach_style)
    if coach_style not in VALID_COACH_STYLES:
        coach_style = "neutral"
    coach["enabled"] = bool(coach.get("enabled", True))
    coach["style"] = coach_style

    normalized["overlay"]["enabled"] = bool(
        normalized["overlay"].get("enabled", True)
    )
    normalized["overlay"]["show_badge"] = bool(
        normalized["overlay"].get("show_badge", True)
    )
    normalized["overlay"]["show_popup"] = bool(
        normalized["overlay"].get("show_popup", True)
    )
    normalized["notifications"]["enabled"] = bool(
        normalized["notifications"].get("enabled", True)
    )

    return normalized


def write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    ensure_user_config_dir()

    tmp_path = path.with_name(
        f"{path.stem}.{os.getpid()}.{int(time.time() * 1000)}.tmp"
    )

    json_text = json.dumps(
        data,
        ensure_ascii=False,
        indent=2,
    )

    with tmp_path.open("w", encoding="utf-8") as file:
        file.write(json_text)
        file.flush()
        os.fsync(file.fileno())

    # Validate before replace.
    json.loads(tmp_path.read_text(encoding="utf-8"))

    os.replace(tmp_path, path)


def load_settings() -> dict[str, Any]:
    ensure_user_config_dir()

    if not SETTINGS_PATH.exists():
        settings = deepcopy(DEFAULT_SETTINGS)
        write_json_atomic(SETTINGS_PATH, settings)
        return settings

    try:
        raw = SETTINGS_PATH.read_text(encoding="utf-8")
        loaded = json.loads(raw)

        if not isinstance(loaded, dict):
            raise ValueError("settings.json root must be object")

        settings = normalize_settings(loaded)

        # Auto-save if new default keys were added.
        if settings != loaded:
            write_json_atomic(SETTINGS_PATH, settings)

        return settings

    except Exception:
        broken_path = SETTINGS_PATH.with_name(
            f"settings.broken.{int(time.time())}.json"
        )

        try:
            SETTINGS_PATH.replace(broken_path)
        except Exception:
            pass

        settings = deepcopy(DEFAULT_SETTINGS)
        write_json_atomic(SETTINGS_PATH, settings)
        return settings


def save_settings(settings: dict[str, Any]) -> None:
    merged = normalize_settings(settings)
    write_json_atomic(SETTINGS_PATH, merged)


def get_setting(path: str, default: Any = None) -> Any:
    settings = load_settings()
    current: Any = settings

    for part in path.split("."):
        if not isinstance(current, dict):
            return default

        if part not in current:
            return default

        current = current[part]

    return current


def update_setting(path: str, value: Any) -> dict[str, Any]:
    settings = load_settings()
    current = settings

    parts = path.split(".")
    for part in parts[:-1]:
        if part not in current or not isinstance(current[part], dict):
            current[part] = {}

        current = current[part]

    current[parts[-1]] = value
    save_settings(settings)
    return settings


def is_first_run_completed() -> bool:
    return bool(get_setting("app.first_run_completed", False))


def mark_first_run_completed() -> None:
    update_setting("app.first_run_completed", True)


def should_start_overlay() -> bool:
    return bool(get_setting("app.start_overlay", True)) and bool(
        get_setting("overlay.enabled", True)
    )


def should_start_tracker() -> bool:
    return bool(get_setting("app.start_tracker", True))


def get_activity_reset_hour() -> int:
    value = int(get_setting("activity_window.reset_hour", 3))

    if value < 0:
        return 0

    if value > 23:
        return 23

    return value

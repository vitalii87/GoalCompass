# src/services/activity_rules_service.py

from __future__ import annotations

import json
import os
import re
import time
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT_DIR = Path(__file__).resolve().parents[2]
USER_CONFIG_DIR = ROOT_DIR / "data" / "user_config"
ACTIVITY_RULES_PATH = USER_CONFIG_DIR / "activity_rules.json"


ALLOWED_CATEGORIES = {
    "productive",
    "personal",
    "neutral",
    "distracting",
    "time_wasting",
    "unknown",
    "ignored",
}


ALLOWED_RULE_TYPES = {
    "process",
    "title_contains",
    "domain",
    "url_contains",
}


DEFAULT_ACTIVITY_RULES: dict[str, Any] = {
    "schema_version": 1,
    "rules": [],
}


BUILTIN_RULES: list[dict[str, Any]] = [
    # ------------------------------------------------------------
    # Ignored / system
    # ------------------------------------------------------------
    {
        "id": "builtin_process_explorer",
        "source": "built_in",
        "type": "process",
        "value": "explorer.exe",
        "category": "ignored",
        "enabled": True,
        "editable": False,
        "reason": "Windows shell / desktop",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_process_searchhost",
        "source": "built_in",
        "type": "process",
        "value": "searchhost.exe",
        "category": "ignored",
        "enabled": True,
        "editable": False,
        "reason": "Windows search UI",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_process_shellexperiencehost",
        "source": "built_in",
        "type": "process",
        "value": "shellexperiencehost.exe",
        "category": "ignored",
        "enabled": True,
        "editable": False,
        "reason": "Windows shell experience",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_process_startmenu",
        "source": "built_in",
        "type": "process",
        "value": "startmenuexperiencehost.exe",
        "category": "ignored",
        "enabled": True,
        "editable": False,
        "reason": "Windows start menu",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_process_taskmgr",
        "source": "built_in",
        "type": "process",
        "value": "taskmgr.exe",
        "category": "ignored",
        "enabled": True,
        "editable": False,
        "reason": "Task Manager",
        "applies_to_goal_ids": [],
    },

    # ------------------------------------------------------------
    # Productive apps
    # ------------------------------------------------------------
    {
        "id": "builtin_process_pycharm64",
        "source": "built_in",
        "type": "process",
        "value": "pycharm64.exe",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "Development IDE",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_process_pycharm",
        "source": "built_in",
        "type": "process",
        "value": "pycharm.exe",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "Development IDE",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_process_code",
        "source": "built_in",
        "type": "process",
        "value": "code.exe",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "Code editor",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_process_cmd",
        "source": "built_in",
        "type": "process",
        "value": "cmd.exe",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "Terminal",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_process_powershell",
        "source": "built_in",
        "type": "process",
        "value": "powershell.exe",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "Terminal",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_process_windowsterminal",
        "source": "built_in",
        "type": "process",
        "value": "windowsterminal.exe",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "Terminal",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_process_wt",
        "source": "built_in",
        "type": "process",
        "value": "wt.exe",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "Terminal",
        "applies_to_goal_ids": [],
    },

    # ------------------------------------------------------------
    # Games / launchers — starter defaults, user can override
    # ------------------------------------------------------------
    {
        "id": "builtin_process_worldoftanks",
        "source": "built_in",
        "type": "process",
        "value": "worldoftanks.exe",
        "category": "time_wasting",
        "enabled": True,
        "editable": False,
        "reason": "Default starter classification; user can override manually",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_process_wgc",
        "source": "built_in",
        "type": "process",
        "value": "wgc.exe",
        "category": "time_wasting",
        "enabled": True,
        "editable": False,
        "reason": "Wargaming.net Game Center",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_process_steam",
        "source": "built_in",
        "type": "process",
        "value": "steam.exe",
        "category": "time_wasting",
        "enabled": True,
        "editable": False,
        "reason": "Game launcher",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_process_steamwebhelper",
        "source": "built_in",
        "type": "process",
        "value": "steamwebhelper.exe",
        "category": "time_wasting",
        "enabled": True,
        "editable": False,
        "reason": "Steam helper",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_process_epicgameslauncher",
        "source": "built_in",
        "type": "process",
        "value": "epicgameslauncher.exe",
        "category": "time_wasting",
        "enabled": True,
        "editable": False,
        "reason": "Game launcher",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_process_battlenet",
        "source": "built_in",
        "type": "process",
        "value": "battle.net.exe",
        "category": "time_wasting",
        "enabled": True,
        "editable": False,
        "reason": "Game launcher",
        "applies_to_goal_ids": [],
    },

    # ------------------------------------------------------------
    # Project / coding / AI productive title rules
    # ------------------------------------------------------------
    {
        "id": "builtin_title_chatgpt",
        "source": "built_in",
        "type": "title_contains",
        "value": "chatgpt",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "AI assistant / work context",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_title_goalcompass",
        "source": "built_in",
        "type": "title_contains",
        "value": "goalcompass",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "GoalCompass project",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_title_lazy_coach",
        "source": "built_in",
        "type": "title_contains",
        "value": "lazy_coach",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "GoalCompass project repository",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_title_project_uk",
        "source": "built_in",
        "type": "title_contains",
        "value": "агресів коуч",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "GoalCompass project conversation",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_title_github",
        "source": "built_in",
        "type": "title_contains",
        "value": "github",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "Development / repository work",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_title_python",
        "source": "built_in",
        "type": "title_contains",
        "value": "python",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "Programming / learning",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_title_fastapi",
        "source": "built_in",
        "type": "title_contains",
        "value": "fastapi",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "Programming / learning",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_title_pytest",
        "source": "built_in",
        "type": "title_contains",
        "value": "pytest",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "QA automation",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_title_playwright",
        "source": "built_in",
        "type": "title_contains",
        "value": "playwright",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "QA automation",
        "applies_to_goal_ids": [],
    },

    # ------------------------------------------------------------
    # German learning
    # ------------------------------------------------------------
    {
        "id": "builtin_title_deutsch",
        "source": "built_in",
        "type": "title_contains",
        "value": "deutsch",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "German learning",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_title_german",
        "source": "built_in",
        "type": "title_contains",
        "value": "german",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "German learning",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_title_grammatik",
        "source": "built_in",
        "type": "title_contains",
        "value": "grammatik",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "German grammar",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_title_translate",
        "source": "built_in",
        "type": "title_contains",
        "value": "translate",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "Language learning / translation",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_title_translated",
        "source": "built_in",
        "type": "title_contains",
        "value": "translated",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "Language learning / translation",
        "applies_to_goal_ids": [],
    },

    # ------------------------------------------------------------
    # Job search / career — safe productive title rules
    # ------------------------------------------------------------
    {
        "id": "builtin_title_indeed",
        "source": "built_in",
        "type": "title_contains",
        "value": "indeed",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "Job search",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_title_stepstone",
        "source": "built_in",
        "type": "title_contains",
        "value": "stepstone",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "Job search",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_title_linkedin",
        "source": "built_in",
        "type": "title_contains",
        "value": "linkedin",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "Career / job search",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_title_xing",
        "source": "built_in",
        "type": "title_contains",
        "value": "xing",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "Career / job search",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_title_arbeitsagentur",
        "source": "built_in",
        "type": "title_contains",
        "value": "arbeitsagentur",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "Job search / employment agency",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_title_jobcenter",
        "source": "built_in",
        "type": "title_contains",
        "value": "jobcenter",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "Jobcenter / admin work",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_title_stellenangebote",
        "source": "built_in",
        "type": "title_contains",
        "value": "stellenangebote",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "Job offers / job search",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_title_stellenanzeigen",
        "source": "built_in",
        "type": "title_contains",
        "value": "stellenanzeigen",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "Job ads / job search",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_title_bewerbung",
        "source": "built_in",
        "type": "title_contains",
        "value": "bewerbung",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "Job application",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_title_lebenslauf",
        "source": "built_in",
        "type": "title_contains",
        "value": "lebenslauf",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "CV / resume",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_title_resume",
        "source": "built_in",
        "type": "title_contains",
        "value": "resume",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "CV / resume",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_title_cover_letter",
        "source": "built_in",
        "type": "title_contains",
        "value": "cover letter",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "Job application",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_title_karriere",
        "source": "built_in",
        "type": "title_contains",
        "value": "karriere",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "Career / job search",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_title_jobs",
        "source": "built_in",
        "type": "title_contains",
        "value": "jobs",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "Job search",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_title_software_qa",
        "source": "built_in",
        "type": "title_contains",
        "value": "software qa",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "QA job search",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_title_software_qa_dash",
        "source": "built_in",
        "type": "title_contains",
        "value": "software-qa",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "QA job search",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_title_quality_assurance",
        "source": "built_in",
        "type": "title_contains",
        "value": "quality assurance",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "QA job search",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_title_qualitaetsingenieur",
        "source": "built_in",
        "type": "title_contains",
        "value": "qualitätsingenieur",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "QA job search",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_title_qualitaetsmanager",
        "source": "built_in",
        "type": "title_contains",
        "value": "qualitätsmanager",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "QA job search",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_title_test_engineer",
        "source": "built_in",
        "type": "title_contains",
        "value": "test engineer",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "QA / testing job search",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_title_qa_engineer",
        "source": "built_in",
        "type": "title_contains",
        "value": "qa engineer",
        "category": "productive",
        "enabled": True,
        "editable": False,
        "reason": "QA / testing job search",
        "applies_to_goal_ids": [],
    },

    # ------------------------------------------------------------
    # Personal / admin
    # ------------------------------------------------------------
    {
        "id": "builtin_title_gmail",
        "source": "built_in",
        "type": "title_contains",
        "value": "gmail",
        "category": "personal",
        "enabled": True,
        "editable": False,
        "reason": "Personal/admin email",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_title_bank",
        "source": "built_in",
        "type": "title_contains",
        "value": "bank",
        "category": "personal",
        "enabled": True,
        "editable": False,
        "reason": "Banking / personal admin",
        "applies_to_goal_ids": [],
    },
    {
        "id": "builtin_title_kleinanzeigen",
        "source": "built_in",
        "type": "title_contains",
        "value": "kleinanzeigen",
        "category": "personal",
        "enabled": True,
        "editable": False,
        "reason": "Personal marketplace",
        "applies_to_goal_ids": [],
    },
]


@dataclass(frozen=True)
class ActivityRuleMatch:
    rule_id: str
    source: str
    rule_type: str
    value: str
    category: str
    reason: str
    applies_to_goal_ids: list[str]


def ensure_user_config_dir() -> None:
    USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def now_id() -> str:
    return str(int(time.time() * 1000))


def normalize_text(value: str | None) -> str:
    if value is None:
        return ""

    return str(value).lower().strip()


def normalize_process_name(process_name: str | None) -> str:
    normalized = normalize_text(process_name)
    normalized = normalized.replace("\\", "/").split("/")[-1]
    return normalized


def normalize_domain_or_url(value: str) -> str:
    raw = value.strip().lower()

    if not raw:
        return ""

    if "://" not in raw:
        candidate = "https://" + raw
    else:
        candidate = raw

    try:
        parsed = urlparse(candidate)
        host = parsed.netloc.strip().lower()

        if host.startswith("www."):
            host = host[4:]

        return host
    except Exception:
        cleaned = raw.replace("https://", "").replace("http://", "")
        cleaned = cleaned.split("/")[0].strip()

        if cleaned.startswith("www."):
            cleaned = cleaned[4:]

        return cleaned


def normalize_rule_value(rule_type: str, value: str) -> str:
    rule_type = normalize_text(rule_type)

    if rule_type == "process":
        return normalize_process_name(value)

    if rule_type == "domain":
        return normalize_domain_or_url(value)

    if rule_type == "url_contains":
        return normalize_text(value)

    if rule_type == "title_contains":
        return normalize_text(value)

    return normalize_text(value)


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

    json.loads(tmp_path.read_text(encoding="utf-8"))
    os.replace(tmp_path, path)


def normalize_rule(rule: dict[str, Any], source: str = "manual") -> dict[str, Any]:
    normalized = deepcopy(rule)

    rule_type = normalize_text(normalized.get("type", "title_contains"))
    if rule_type not in ALLOWED_RULE_TYPES:
        rule_type = "title_contains"

    category = normalize_text(normalized.get("category", "unknown"))
    if category not in ALLOWED_CATEGORIES:
        category = "unknown"

    rule_source = normalize_text(normalized.get("source", source))
    if rule_source not in {"manual", "built_in"}:
        rule_source = source

    value = normalize_rule_value(rule_type, str(normalized.get("value", "")))

    rule_id = str(normalized.get("id", "")).strip()
    if not rule_id:
        rule_id = f"rule_{now_id()}"

    applies_to_goal_ids = normalized.get("applies_to_goal_ids", [])
    if not isinstance(applies_to_goal_ids, list):
        applies_to_goal_ids = []

    editable = bool(normalized.get("editable", rule_source == "manual"))

    normalized["id"] = rule_id
    normalized["source"] = rule_source
    normalized["type"] = rule_type
    normalized["value"] = value
    normalized["category"] = category
    normalized["enabled"] = bool(normalized.get("enabled", True))
    normalized["editable"] = editable if rule_source == "manual" else False
    normalized["reason"] = str(normalized.get("reason", "")).strip()
    normalized["applies_to_goal_ids"] = [
        str(goal_id).strip()
        for goal_id in applies_to_goal_ids
        if str(goal_id).strip()
    ]

    return normalized


def normalize_rules_file(data: dict[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(DEFAULT_ACTIVITY_RULES)
    normalized.update(data)

    rules = normalized.get("rules", [])
    if not isinstance(rules, list):
        rules = []

    normalized["schema_version"] = 1
    normalized["rules"] = [
        normalize_rule(rule, source="manual")
        for rule in rules
        if isinstance(rule, dict)
    ]

    return normalized


def get_builtin_rules() -> list[dict[str, Any]]:
    return [
        normalize_rule(rule, source="built_in")
        for rule in BUILTIN_RULES
    ]


def load_activity_rules() -> dict[str, Any]:
    ensure_user_config_dir()

    if not ACTIVITY_RULES_PATH.exists():
        rules_file = deepcopy(DEFAULT_ACTIVITY_RULES)
        write_json_atomic(ACTIVITY_RULES_PATH, rules_file)
        return rules_file

    try:
        raw = ACTIVITY_RULES_PATH.read_text(encoding="utf-8")
        loaded = json.loads(raw)

        if not isinstance(loaded, dict):
            raise ValueError("activity_rules.json root must be object")

        normalized = normalize_rules_file(loaded)

        if normalized != loaded:
            write_json_atomic(ACTIVITY_RULES_PATH, normalized)

        return normalized

    except Exception:
        broken_path = ACTIVITY_RULES_PATH.with_name(
            f"activity_rules.broken.{int(time.time())}.json"
        )

        try:
            ACTIVITY_RULES_PATH.replace(broken_path)
        except Exception:
            pass

        rules_file = deepcopy(DEFAULT_ACTIVITY_RULES)
        write_json_atomic(ACTIVITY_RULES_PATH, rules_file)
        return rules_file


def save_activity_rules(data: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_rules_file(data)
    write_json_atomic(ACTIVITY_RULES_PATH, normalized)
    return normalized


def list_manual_rules() -> list[dict[str, Any]]:
    return load_activity_rules().get("rules", [])


def list_rules(include_builtin: bool = True) -> list[dict[str, Any]]:
    manual_rules = list_manual_rules()

    if not include_builtin:
        return manual_rules

    return get_builtin_rules() + manual_rules


def list_effective_rules() -> list[dict[str, Any]]:
    """
    Matching order:
        manual first
        built-in second

    This lets user override built-in classification.
    """
    return list_manual_rules() + get_builtin_rules()


def add_activity_rule(
    rule_type: str,
    value: str,
    category: str,
    reason: str = "",
    applies_to_goal_ids: list[str] | None = None,
    enabled: bool = True,
) -> dict[str, Any]:
    rules_file = load_activity_rules()

    rule = normalize_rule(
        {
            "id": f"rule_{now_id()}",
            "source": "manual",
            "type": rule_type,
            "value": value,
            "category": category,
            "reason": reason,
            "applies_to_goal_ids": applies_to_goal_ids or [],
            "enabled": enabled,
            "editable": True,
        },
        source="manual",
    )

    if not rule["value"]:
        raise ValueError("Rule value is required.")

    rules_file["rules"].append(rule)
    save_activity_rules(rules_file)
    return rule


def delete_activity_rule(rule_id: str) -> bool:
    if rule_id.startswith("builtin_"):
        raise ValueError(
            "Built-in rules cannot be deleted. Create a manual override instead."
        )

    rules_file = load_activity_rules()
    old_rules = rules_file.get("rules", [])

    new_rules = [
        rule
        for rule in old_rules
        if str(rule.get("id", "")) != rule_id
    ]

    rules_file["rules"] = new_rules
    save_activity_rules(rules_file)

    return len(new_rules) != len(old_rules)


def update_activity_rule(
    rule_id: str,
    updates: dict[str, Any],
) -> dict[str, Any]:
    if rule_id.startswith("builtin_"):
        raise ValueError(
            "Built-in rules cannot be edited. Create a manual override instead."
        )

    rules_file = load_activity_rules()
    rules = rules_file.get("rules", [])

    for index, rule in enumerate(rules):
        if str(rule.get("id", "")) == rule_id:
            updated = deepcopy(rule)
            updated.update(updates)
            updated["source"] = "manual"
            updated["editable"] = True
            updated = normalize_rule(updated, source="manual")

            rules[index] = updated
            rules_file["rules"] = rules

            save_activity_rules(rules_file)
            return updated

    raise ValueError(f"Rule not found: {rule_id}")


def extract_domain_candidates_from_title(window_title: str) -> set[str]:
    title = normalize_text(window_title)
    candidates: set[str] = set()

    domain_pattern = re.compile(
        r"\b(?:https?://)?(?:www\.)?([a-z0-9.-]+\.[a-z]{2,})(?:/[^\s]*)?\b",
        flags=re.IGNORECASE,
    )

    for match in domain_pattern.finditer(title):
        domain = normalize_domain_or_url(match.group(1))
        if domain:
            candidates.add(domain)

    return candidates


def rule_matches_activity(
    rule: dict[str, Any],
    process_name: str,
    window_title: str,
    url: str = "",
) -> bool:
    if not bool(rule.get("enabled", True)):
        return False

    rule_type = normalize_text(rule.get("type", ""))
    value = normalize_rule_value(rule_type, str(rule.get("value", "")))

    if not value:
        return False

    process = normalize_process_name(process_name)
    title = normalize_text(window_title)
    normalized_url = normalize_text(url)
    url_domain = normalize_domain_or_url(url) if url else ""

    if rule_type == "process":
        return process == value

    if rule_type == "title_contains":
        return value in title

    if rule_type == "url_contains":
        return bool(normalized_url) and value in normalized_url

    if rule_type == "domain":
        if url_domain and url_domain == value:
            return True

        title_domains = extract_domain_candidates_from_title(window_title)
        return value in title_domains

    return False


def match_activity_rule(
    process_name: str,
    window_title: str,
    url: str = "",
) -> ActivityRuleMatch | None:
    for rule in list_effective_rules():
        if rule_matches_activity(
            rule=rule,
            process_name=process_name,
            window_title=window_title,
            url=url,
        ):
            return ActivityRuleMatch(
                rule_id=str(rule.get("id", "")),
                source=str(rule.get("source", "manual")),
                rule_type=str(rule.get("type", "")),
                value=str(rule.get("value", "")),
                category=str(rule.get("category", "unknown")),
                reason=str(rule.get("reason", "")),
                applies_to_goal_ids=list(rule.get("applies_to_goal_ids", [])),
            )

    return None

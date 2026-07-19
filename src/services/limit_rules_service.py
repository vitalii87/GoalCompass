# src/services/limit_rules_service.py

from __future__ import annotations

import json
import os
import time
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
USER_CONFIG_DIR = ROOT_DIR / "data" / "user_config"
LIMIT_RULES_PATH = USER_CONFIG_DIR / "limit_rules.json"


ALLOWED_TARGET_TYPES = {
    "category",
    "process",
    "title_contains",
    "goal",
}

ALLOWED_PERIODS = {
    "daily",
    "weekly",
}

ALLOWED_SEVERITIES = {
    "badge",
    "warning",
    "strict",
}

ALLOWED_STATUSES = {
    "active",
    "paused",
    "replaced",
    "deleted",
}


DEFAULT_LIMIT_RULES: dict[str, Any] = {
    "schema_version": 1,
    "rules": [],
}


def now_iso() -> str:
    from datetime import datetime

    return datetime.now().replace(microsecond=0).isoformat(sep=" ")


def now_id() -> str:
    return str(int(time.time() * 1000))


def ensure_user_config_dir() -> None:
    USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def normalize_text(value: str | None) -> str:
    if value is None:
        return ""

    return str(value).strip()


def normalize_key(value: str | None) -> str:
    return normalize_text(value).lower()


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


def normalize_limit_rule(rule: dict[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(rule)

    rule_id = normalize_text(normalized.get("id"))
    if not rule_id:
        rule_id = f"limit_{now_id()}"

    version_of = normalize_text(normalized.get("version_of")) or rule_id

    target_type = normalize_key(normalized.get("target_type"))
    if target_type not in ALLOWED_TARGET_TYPES:
        target_type = "category"

    target_value = normalize_key(normalized.get("target_value"))

    period = normalize_key(normalized.get("period"))
    if period not in ALLOWED_PERIODS:
        period = "daily"

    severity = normalize_key(normalized.get("severity"))
    if severity not in ALLOWED_SEVERITIES:
        severity = "warning"

    status = normalize_key(normalized.get("status"))
    if status not in ALLOWED_STATUSES:
        status = "active"

    source = normalize_key(normalized.get("source")) or "manual"

    try:
        limit_minutes = int(normalized.get("limit_minutes", 0))
    except Exception:
        limit_minutes = 0

    if limit_minutes < 0:
        limit_minutes = 0

    created_at = normalize_text(normalized.get("created_at")) or now_iso()
    active_from = normalize_text(normalized.get("active_from")) or created_at
    active_to = normalized.get("active_to", None)

    if active_to is not None:
        active_to = normalize_text(active_to) or None

    normalized["id"] = rule_id
    normalized["version_of"] = version_of
    normalized["source"] = source
    normalized["target_type"] = target_type
    normalized["target_value"] = target_value
    normalized["period"] = period
    normalized["limit_minutes"] = limit_minutes
    normalized["severity"] = severity
    normalized["status"] = status
    normalized["goal_id"] = normalize_text(normalized.get("goal_id"))
    normalized["reason"] = normalize_text(normalized.get("reason"))
    normalized["created_at"] = created_at
    normalized["active_from"] = active_from
    normalized["active_to"] = active_to
    normalized["changed_from_rule_id"] = normalize_text(
        normalized.get("changed_from_rule_id")
    )

    return normalized


def normalize_rules_file(data: dict[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(DEFAULT_LIMIT_RULES)
    normalized.update(data)

    rules = normalized.get("rules", [])
    if not isinstance(rules, list):
        rules = []

    normalized["schema_version"] = 1
    normalized["rules"] = [
        normalize_limit_rule(rule)
        for rule in rules
        if isinstance(rule, dict)
    ]

    return normalized


def load_limit_rules() -> dict[str, Any]:
    ensure_user_config_dir()

    if not LIMIT_RULES_PATH.exists():
        rules_file = deepcopy(DEFAULT_LIMIT_RULES)
        write_json_atomic(LIMIT_RULES_PATH, rules_file)
        return rules_file

    try:
        raw = LIMIT_RULES_PATH.read_text(encoding="utf-8")
        loaded = json.loads(raw)

        if not isinstance(loaded, dict):
            raise ValueError("limit_rules.json root must be object")

        normalized = normalize_rules_file(loaded)

        if normalized != loaded:
            write_json_atomic(LIMIT_RULES_PATH, normalized)

        return normalized

    except Exception:
        broken_path = LIMIT_RULES_PATH.with_name(
            f"limit_rules.broken.{int(time.time())}.json"
        )

        try:
            LIMIT_RULES_PATH.replace(broken_path)
        except Exception:
            pass

        rules_file = deepcopy(DEFAULT_LIMIT_RULES)
        write_json_atomic(LIMIT_RULES_PATH, rules_file)
        return rules_file


def save_limit_rules(data: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_rules_file(data)
    write_json_atomic(LIMIT_RULES_PATH, normalized)
    return normalized


def list_limit_rules(include_inactive: bool = True) -> list[dict[str, Any]]:
    rules = load_limit_rules().get("rules", [])

    if include_inactive:
        return rules

    return [
        rule
        for rule in rules
        if rule.get("status") == "active" and rule.get("active_to") is None
    ]


def list_active_limits() -> list[dict[str, Any]]:
    return list_limit_rules(include_inactive=False)


def find_limit_rule(rule_id: str) -> dict[str, Any] | None:
    for rule in list_limit_rules(include_inactive=True):
        if str(rule.get("id", "")) == rule_id:
            return rule

    return None


def validate_limit_rule(rule: dict[str, Any]) -> None:
    target_type = rule.get("target_type")
    target_value = rule.get("target_value")
    period = rule.get("period")
    limit_minutes = rule.get("limit_minutes")
    severity = rule.get("severity")

    if target_type not in ALLOWED_TARGET_TYPES:
        raise ValueError(f"Invalid target_type: {target_type}")

    if not target_value:
        raise ValueError("target_value is required.")

    if period not in ALLOWED_PERIODS:
        raise ValueError(f"Invalid period: {period}")

    if severity not in ALLOWED_SEVERITIES:
        raise ValueError(f"Invalid severity: {severity}")

    if not isinstance(limit_minutes, int) or limit_minutes <= 0:
        raise ValueError("limit_minutes must be positive integer.")


def add_limit_rule(
    target_type: str,
    target_value: str,
    period: str,
    limit_minutes: int,
    severity: str = "warning",
    goal_id: str = "",
    reason: str = "",
    source: str = "manual",
) -> dict[str, Any]:
    rules_file = load_limit_rules()

    current_time = now_iso()

    rule = normalize_limit_rule(
        {
            "id": f"limit_{now_id()}",
            "version_of": "",
            "source": source,
            "target_type": target_type,
            "target_value": target_value,
            "period": period,
            "limit_minutes": limit_minutes,
            "severity": severity,
            "status": "active",
            "goal_id": goal_id,
            "reason": reason,
            "created_at": current_time,
            "active_from": current_time,
            "active_to": None,
            "changed_from_rule_id": "",
        }
    )

    rule["version_of"] = rule["id"]

    validate_limit_rule(rule)

    rules_file["rules"].append(rule)
    save_limit_rules(rules_file)

    return rule


def replace_limit_rule(
    rule_id: str,
    updates: dict[str, Any],
    reason: str = "",
) -> dict[str, Any]:
    """
    Historical update:
        old rule -> status=replaced, active_to=now
        new rule -> active, active_from=now

    We do NOT mutate old meaning retroactively.
    """
    rules_file = load_limit_rules()
    rules = rules_file.get("rules", [])

    old_index: int | None = None
    old_rule: dict[str, Any] | None = None

    for index, rule in enumerate(rules):
        if str(rule.get("id", "")) == rule_id:
            old_index = index
            old_rule = normalize_limit_rule(rule)
            break

    if old_rule is None or old_index is None:
        raise ValueError(f"Limit rule not found: {rule_id}")

    if old_rule.get("status") != "active":
        raise ValueError("Only active limits can be edited/replaced.")

    change_time = now_iso()

    closed_old = deepcopy(old_rule)
    closed_old["status"] = "replaced"
    closed_old["active_to"] = change_time

    new_rule = deepcopy(old_rule)
    new_rule.update(updates)
    new_rule["id"] = f"limit_{now_id()}"
    new_rule["version_of"] = old_rule.get("version_of") or old_rule["id"]
    new_rule["source"] = "manual"
    new_rule["status"] = "active"
    new_rule["created_at"] = change_time
    new_rule["active_from"] = change_time
    new_rule["active_to"] = None
    new_rule["changed_from_rule_id"] = old_rule["id"]

    if reason:
        new_rule["reason"] = reason

    new_rule = normalize_limit_rule(new_rule)
    validate_limit_rule(new_rule)

    rules[old_index] = closed_old
    rules.append(new_rule)

    rules_file["rules"] = rules
    save_limit_rules(rules_file)

    return new_rule


def pause_limit_rule(rule_id: str, reason: str = "") -> dict[str, Any]:
    rules_file = load_limit_rules()
    rules = rules_file.get("rules", [])

    for index, rule in enumerate(rules):
        if str(rule.get("id", "")) == rule_id:
            updated = normalize_limit_rule(rule)

            if updated.get("status") != "active":
                raise ValueError("Only active limits can be paused.")

            updated["status"] = "paused"
            updated["active_to"] = now_iso()

            if reason:
                updated["reason"] = reason

            rules[index] = updated
            rules_file["rules"] = rules
            save_limit_rules(rules_file)
            return updated

    raise ValueError(f"Limit rule not found: {rule_id}")


def delete_limit_rule(rule_id: str, reason: str = "") -> dict[str, Any]:
    rules_file = load_limit_rules()
    rules = rules_file.get("rules", [])

    for index, rule in enumerate(rules):
        if str(rule.get("id", "")) == rule_id:
            updated = normalize_limit_rule(rule)
            updated["status"] = "deleted"
            updated["active_to"] = now_iso()

            if reason:
                updated["reason"] = reason

            rules[index] = updated
            rules_file["rules"] = rules
            save_limit_rules(rules_file)
            return updated

    raise ValueError(f"Limit rule not found: {rule_id}")


def seed_starter_limits_if_empty() -> list[dict[str, Any]]:
    """
    Create starter/default limits only once.

    MVP starter defaults:
        time_wasting -> 60 min/day
        distracting  -> 30 min/day

    Unknown is intentionally not limited.
    Unknown should go to Unknown Review, not punishment.
    """
    existing_rules = list_limit_rules(include_inactive=True)

    if existing_rules:
        return []

    created: list[dict[str, Any]] = []

    created.append(
        add_limit_rule(
            target_type="category",
            target_value="time_wasting",
            period="daily",
            limit_minutes=60,
            severity="warning",
            goal_id="",
            reason="Starter default limit",
            source="starter_default",
        )
    )

    created.append(
        add_limit_rule(
            target_type="category",
            target_value="distracting",
            period="daily",
            limit_minutes=30,
            severity="badge",
            goal_id="",
            reason="Starter default limit",
            source="starter_default",
        )
    )

    return created


def create_initial_limits_from_goal_profile(
    goal_profile: dict[str, Any],
    source: str = "setup",
) -> list[dict[str, Any]]:
    """
    Optional bridge:
    setup/AI goal profile -> real limit rules.

    Can be called later from setup wizard after save_goal_profile().
    """
    created: list[dict[str, Any]] = []

    main_goals = goal_profile.get("main_goals", [])
    if not isinstance(main_goals, list):
        return created

    for goal in main_goals:
        if not isinstance(goal, dict):
            continue

        goal_id = str(goal.get("id", "")).strip()
        limits = goal.get("limits", [])

        if not isinstance(limits, list):
            continue

        for limit in limits:
            if not isinstance(limit, dict):
                continue

            category = str(limit.get("category", "")).strip()
            linked_processes = limit.get("linked_processes", [])
            title = str(limit.get("title", "")).strip()

            try:
                limit_minutes = int(limit.get("limit_minutes_per_day") or 0)
            except Exception:
                limit_minutes = 0

            if limit_minutes <= 0:
                continue

            if category:
                created.append(
                    add_limit_rule(
                        target_type="category",
                        target_value=category,
                        period="daily",
                        limit_minutes=limit_minutes,
                        severity=str(limit.get("severity", "warning")),
                        goal_id=goal_id,
                        reason=title,
                        source=source,
                    )
                )
                continue

            if isinstance(linked_processes, list) and linked_processes:
                created.append(
                    add_limit_rule(
                        target_type="process",
                        target_value=str(linked_processes[0]),
                        period="daily",
                        limit_minutes=limit_minutes,
                        severity=str(limit.get("severity", "warning")),
                        goal_id=goal_id,
                        reason=title,
                        source=source,
                    )
                )

    return created

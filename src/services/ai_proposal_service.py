from __future__ import annotations

import difflib
import json
import os
import time
import uuid
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from src.app_paths import USER_CONFIG_DIR
from src.services.goal_profile_service import (
    load_goal_profile,
    normalize_goal_profile,
    save_goal_profile,
    validate_goal_profile,
)
from src.services.settings_service import load_settings, normalize_settings, save_settings


AI_PROPOSAL_HISTORY_DIR = USER_CONFIG_DIR / "ai_proposals"

VALID_CONFIDENCE_LEVELS = {"low", "medium", "high"}
ALLOWED_SETTINGS_PATCH = {
    "automation": {"mode", "require_confirmation"},
    "interaction": {"mode", "daily_prompt_limit", "cooldown_minutes"},
    "coach": {"enabled", "style"},
    "notifications": {"enabled", "time_wasting_warning"},
    "overlay": {"show_badge", "show_popup"},
}


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat(sep=" ")


def write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(
        f"{path.stem}.{os.getpid()}.{int(time.time() * 1000)}.tmp"
    )
    text = json.dumps(data, ensure_ascii=False, indent=2)
    temp_path.write_text(text, encoding="utf-8")
    json.loads(temp_path.read_text(encoding="utf-8"))
    os.replace(temp_path, path)


def string_list(value: Any, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list.")
    return [str(item).strip() for item in value if str(item).strip()]


def validate_settings_patch(settings_patch: Any) -> dict[str, dict[str, Any]]:
    if settings_patch is None:
        return {}
    if not isinstance(settings_patch, dict):
        raise ValueError("changes.settings_patch must be an object or null.")

    normalized_patch: dict[str, dict[str, Any]] = {}
    for section, values in settings_patch.items():
        if section not in ALLOWED_SETTINGS_PATCH:
            raise ValueError(f"AI proposal cannot modify settings section: {section}")
        if not isinstance(values, dict):
            raise ValueError(f"settings_patch.{section} must be an object.")

        forbidden = set(values) - ALLOWED_SETTINGS_PATCH[section]
        if forbidden:
            raise ValueError(
                f"AI proposal cannot modify {section}: {', '.join(sorted(forbidden))}"
            )
        normalized_patch[section] = deepcopy(values)

    return normalized_patch


def apply_settings_patch(
    current_settings: dict[str, Any],
    settings_patch: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    updated = deepcopy(current_settings)
    for section, values in settings_patch.items():
        if section not in updated or not isinstance(updated[section], dict):
            updated[section] = {}
        updated[section].update(values)
    return normalize_settings(updated)


def normalize_ai_proposal(proposal: Any) -> dict[str, Any]:
    if not isinstance(proposal, dict):
        raise ValueError("AI proposal must be a JSON object.")
    if int(proposal.get("schema_version", 0)) != 1:
        raise ValueError("AI proposal schema_version must be 1.")

    summary = str(proposal.get("summary", "")).strip()
    if not summary:
        raise ValueError("AI proposal summary is required.")

    confidence = str(proposal.get("confidence", "low")).strip().lower()
    if confidence not in VALID_CONFIDENCE_LEVELS:
        raise ValueError("confidence must be low, medium or high.")

    changes = proposal.get("changes")
    if not isinstance(changes, dict):
        raise ValueError("AI proposal changes must be an object.")

    settings_patch = validate_settings_patch(changes.get("settings_patch"))
    goal_profile_raw = changes.get("goal_profile")
    normalized_goal_profile: dict[str, Any] | None = None
    if goal_profile_raw is not None:
        if not isinstance(goal_profile_raw, dict):
            raise ValueError("changes.goal_profile must be an object or null.")
        normalized_goal_profile = normalize_goal_profile(goal_profile_raw)
        errors = validate_goal_profile(normalized_goal_profile)
        if errors:
            raise ValueError("Invalid proposed goal profile:\n" + "\n".join(errors))

    if not settings_patch and normalized_goal_profile is None:
        raise ValueError("AI proposal must contain at least one valid change.")

    data_quality_raw = proposal.get("data_quality", {})
    if data_quality_raw is None:
        data_quality_raw = {}
    if not isinstance(data_quality_raw, dict):
        raise ValueError("data_quality must be an object.")

    return {
        "schema_version": 1,
        "proposal_id": str(proposal.get("proposal_id", "")).strip()
        or f"proposal_{uuid.uuid4().hex[:12]}",
        "created_at": str(proposal.get("created_at", "")).strip() or now_iso(),
        "summary": summary,
        "confidence": confidence,
        "rationale": string_list(proposal.get("rationale"), "rationale"),
        "data_quality": {
            "limitations": string_list(
                data_quality_raw.get("limitations"),
                "data_quality.limitations",
            ),
            "missing_domains": string_list(
                data_quality_raw.get("missing_domains"),
                "data_quality.missing_domains",
            ),
        },
        "questions": string_list(proposal.get("questions"), "questions"),
        "changes": {
            "settings_patch": settings_patch,
            "goal_profile": normalized_goal_profile,
        },
    }


def parse_ai_proposal_json(json_text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid proposal JSON: {error}") from error
    return normalize_ai_proposal(parsed)


def json_diff(title: str, before: Any, after: Any) -> list[str]:
    before_lines = json.dumps(before, ensure_ascii=False, indent=2).splitlines()
    after_lines = json.dumps(after, ensure_ascii=False, indent=2).splitlines()
    diff = list(
        difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile=f"current/{title}",
            tofile=f"proposed/{title}",
            lineterm="",
        )
    )
    return diff or [f"No effective changes in {title}."]


def build_ai_proposal_preview(
    proposal: dict[str, Any],
    current_settings: dict[str, Any] | None = None,
    current_goal_profile: dict[str, Any] | None = None,
) -> str:
    normalized = normalize_ai_proposal(proposal)
    settings = current_settings if current_settings is not None else load_settings()
    goal_profile = (
        current_goal_profile
        if current_goal_profile is not None
        else load_goal_profile(create_if_missing=False)
    )

    lines = [
        normalized["summary"],
        f"Confidence: {normalized['confidence']}",
    ]
    limitations = normalized["data_quality"]["limitations"]
    if limitations:
        lines.append("Data limitations:")
        lines.extend(f"- {item}" for item in limitations)
    if normalized["questions"]:
        lines.append("Questions that should be answered before trusting this proposal:")
        lines.extend(f"- {item}" for item in normalized["questions"])

    settings_patch = normalized["changes"]["settings_patch"]
    if settings_patch:
        proposed_settings = apply_settings_patch(settings, settings_patch)
        lines.extend(["", *json_diff("settings", normalize_settings(settings), proposed_settings)])

    proposed_profile = normalized["changes"]["goal_profile"]
    if proposed_profile is not None:
        lines.extend(["", *json_diff("goal_profile", goal_profile, proposed_profile)])

    return "\n".join(lines)


def compact_ai_context() -> dict[str, Any]:
    settings = normalize_settings(load_settings())
    return {
        "goal_profile": load_goal_profile(create_if_missing=False),
        "operating_modes": {
            "automation": settings["automation"],
            "interaction": settings["interaction"],
            "coach": settings["coach"],
            "notifications": settings["notifications"],
            "overlay": {
                "show_badge": settings["overlay"]["show_badge"],
                "show_popup": settings["overlay"]["show_popup"],
            },
        },
    }


def build_ai_proposal_prompt() -> str:
    context = json.dumps(compact_ai_context(), ensure_ascii=False, indent=2)
    return f"""
You are preparing a GoalCompass AI-assisted configuration proposal.

Return ONLY valid JSON. Do not use markdown or explanations outside JSON.
Do not claim causation from incomplete data. Put uncertainties in data_quality.limitations.
If essential information is missing, add short questions and keep confidence low.
Do not modify unrelated settings. The user must preview and confirm every change.

Use this structure:
{{
  "schema_version": 1,
  "summary": "",
  "confidence": "low",
  "rationale": [],
  "data_quality": {{"limitations": [], "missing_domains": []}},
  "questions": [],
  "changes": {{
    "settings_patch": {{}},
    "goal_profile": null
  }}
}}

Allowed settings_patch keys:
{json.dumps({key: sorted(value) for key, value in ALLOWED_SETTINGS_PATCH.items()}, indent=2)}

Use goal_profile only when proposing goal changes. If present, return the complete
schema_version 2 profile. Otherwise use null.

Current local context:
{context}
""".strip()


def apply_ai_proposal(proposal: dict[str, Any], confirmed: bool = False) -> Path:
    if not confirmed:
        raise PermissionError("AI proposal requires explicit user confirmation.")

    normalized = normalize_ai_proposal(proposal)
    previous_settings = load_settings()
    settings_patch = normalized["changes"]["settings_patch"]
    proposed_settings = apply_settings_patch(previous_settings, settings_patch)

    proposed_profile = normalized["changes"]["goal_profile"]
    if settings_patch:
        save_settings(proposed_settings)

    try:
        if proposed_profile is not None:
            save_goal_profile(
                proposed_profile,
                change_reason=f"AI-assisted proposal: {normalized['summary']}",
                archive_previous=True,
            )
    except Exception:
        if settings_patch:
            save_settings(previous_settings)
        raise

    audit_record = deepcopy(normalized)
    audit_record["status"] = "applied"
    audit_record["applied_at"] = now_iso()
    audit_path = AI_PROPOSAL_HISTORY_DIR / f"{normalized['proposal_id']}.json"
    write_json_atomic(audit_path, audit_record)
    return audit_path

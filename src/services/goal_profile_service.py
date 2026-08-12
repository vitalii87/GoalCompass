# src/services/goal_profile_service.py

from __future__ import annotations

import json
import os
import re
import time
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from src.app_paths import USER_CONFIG_DIR

GOAL_PROFILE_PATH = USER_CONFIG_DIR / "goal_profile.json"
GOAL_PROFILE_VERSIONS_DIR = USER_CONFIG_DIR / "goal_profile_versions"

MAX_MAIN_GOALS = 10
MAX_SUBGOALS_PER_GOAL = 10
MAX_LIMITS_PER_GOAL = 10


DEFAULT_TIME_HORIZON: dict[str, Any] = {
    "type": "open_ended",
    "target_date": None,
    "duration_days": None,
    "review_interval": "monthly",
}


DEFAULT_GOAL_PROFILE: dict[str, Any] = {
    "schema_version": 2,
    "profile_version": 1,
    "created_at": "",
    "updated_at": "",
    "created_by": "manual",
    "source_mode": "manual",
    "change_reason": "Initial goal profile",
    "main_goals": [],
    "coach": {
        "style": "direct",
        "language": "uk",
    },
    "review": {
        "weekly_review_enabled": True,
        "monthly_review_enabled": True,
        "monthly_review_day": 1,
        "last_review_at": None,
    },
}


REQUIRED_ROOT_KEYS = {
    "schema_version",
    "profile_version",
    "created_at",
    "updated_at",
    "created_by",
    "source_mode",
    "main_goals",
    "coach",
    "review",
}


REQUIRED_MAIN_GOAL_KEYS = {
    "id",
    "title",
    "why",
    "success_definition",
    "status",
    "priority",
    "time_horizon",
    "subgoals",
    "limits",
}


VALID_GOAL_STATUSES = {
    "active",
    "paused",
    "completed",
    "abandoned",
    "replaced",
}


VALID_TIME_HORIZON_TYPES = {
    "open_ended",
    "target_date",
    "duration",
    "ongoing",
}


VALID_REVIEW_INTERVALS = {
    "weekly",
    "monthly",
    "quarterly",
    "none",
}


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat(sep=" ")


def ensure_dirs() -> None:
    USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    GOAL_PROFILE_VERSIONS_DIR.mkdir(parents=True, exist_ok=True)


def slugify(value: str, fallback: str = "item") -> str:
    normalized = value.strip().lower()
    normalized = re.sub(r"[^a-z0-9а-яіїєґ_\-\s]+", "", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\s+", "_", normalized)
    normalized = normalized.strip("_")

    if not normalized:
        return fallback

    return normalized[:64]


def make_id(prefix: str, title: str, existing_ids: set[str] | None = None) -> str:
    existing_ids = existing_ids or set()

    base = slugify(title, fallback=prefix)
    candidate = f"{prefix}_{base}"

    if candidate not in existing_ids:
        return candidate

    index = 2
    while True:
        next_candidate = f"{candidate}_{index}"
        if next_candidate not in existing_ids:
            return next_candidate
        index += 1


def write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    ensure_dirs()

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


def create_empty_goal_profile(
    created_by: str = "manual",
    source_mode: str = "manual",
) -> dict[str, Any]:
    current_time = now_iso()

    profile = deepcopy(DEFAULT_GOAL_PROFILE)
    profile["created_at"] = current_time
    profile["updated_at"] = current_time
    profile["created_by"] = created_by
    profile["source_mode"] = source_mode

    return profile


def create_empty_main_goal(title: str = "") -> dict[str, Any]:
    clean_title = title.strip()
    goal_id = make_id("goal", clean_title or "main_goal")

    return {
        "id": goal_id,
        "title": clean_title,
        "why": "",
        "success_definition": "",
        "status": "active",
        "priority": "medium",
        "time_horizon": deepcopy(DEFAULT_TIME_HORIZON),
        "subgoals": [],
        "limits": [],
        "notes": "",
    }


def create_subgoal(title: str, existing_ids: set[str] | None = None) -> dict[str, Any]:
    clean_title = title.strip()
    subgoal_id = make_id("subgoal", clean_title, existing_ids)

    return {
        "id": subgoal_id,
        "title": clean_title,
        "status": "active",
        "hypothesis": "",
        "success_metric": "",
        "target_minutes_per_day": None,
        "target_minutes_per_week": None,
        "linked_categories": [],
        "linked_keywords": [],
        "linked_processes": [],
        "notes": "",
    }


def create_limit(title: str, existing_ids: set[str] | None = None) -> dict[str, Any]:
    clean_title = title.strip()
    limit_id = make_id("limit", clean_title, existing_ids)

    return {
        "id": limit_id,
        "title": clean_title,
        "status": "active",
        "hypothesis": "",
        "category": "",
        "limit_minutes_per_day": None,
        "limit_minutes_per_week": None,
        "linked_processes": [],
        "linked_keywords": [],
        "severity": "warning",
        "notes": "",
    }


def normalize_time_horizon(value: Any) -> dict[str, Any]:
    horizon = deepcopy(DEFAULT_TIME_HORIZON)

    if isinstance(value, dict):
        horizon.update(value)

    horizon_type = str(horizon.get("type", "open_ended")).strip()

    if horizon_type not in VALID_TIME_HORIZON_TYPES:
        horizon_type = "open_ended"

    horizon["type"] = horizon_type

    review_interval = str(horizon.get("review_interval", "monthly")).strip()

    if review_interval not in VALID_REVIEW_INTERVALS:
        review_interval = "monthly"

    horizon["review_interval"] = review_interval

    if horizon["type"] != "target_date":
        horizon["target_date"] = None

    if horizon["type"] != "duration":
        horizon["duration_days"] = None

    return horizon


def normalize_subgoal(subgoal: dict[str, Any], existing_ids: set[str]) -> dict[str, Any]:
    title = str(subgoal.get("title", "")).strip()
    subgoal_id = str(subgoal.get("id", "")).strip()

    if not subgoal_id:
        subgoal_id = make_id("subgoal", title, existing_ids)

    existing_ids.add(subgoal_id)

    normalized = create_subgoal(title, existing_ids=existing_ids)
    normalized.update(subgoal)
    normalized["id"] = subgoal_id
    normalized["title"] = title
    normalized["status"] = str(normalized.get("status", "active")).strip() or "active"

    if normalized["status"] not in VALID_GOAL_STATUSES:
        normalized["status"] = "active"

    for list_key in ["linked_categories", "linked_keywords", "linked_processes"]:
        if not isinstance(normalized.get(list_key), list):
            normalized[list_key] = []

    return normalized


def normalize_limit(limit: dict[str, Any], existing_ids: set[str]) -> dict[str, Any]:
    title = str(limit.get("title", "")).strip()
    limit_id = str(limit.get("id", "")).strip()

    if not limit_id:
        limit_id = make_id("limit", title, existing_ids)

    existing_ids.add(limit_id)

    normalized = create_limit(title, existing_ids=existing_ids)
    normalized.update(limit)
    normalized["id"] = limit_id
    normalized["title"] = title
    normalized["status"] = str(normalized.get("status", "active")).strip() or "active"

    if normalized["status"] not in VALID_GOAL_STATUSES:
        normalized["status"] = "active"

    for list_key in ["linked_processes", "linked_keywords"]:
        if not isinstance(normalized.get(list_key), list):
            normalized[list_key] = []

    return normalized


def normalize_main_goal(goal: dict[str, Any], existing_ids: set[str]) -> dict[str, Any]:
    title = str(goal.get("title", "")).strip()
    goal_id = str(goal.get("id", "")).strip()

    if not goal_id:
        goal_id = make_id("goal", title, existing_ids)

    existing_ids.add(goal_id)

    normalized = create_empty_main_goal(title)
    normalized.update(goal)

    normalized["id"] = goal_id
    normalized["title"] = title
    normalized["why"] = str(normalized.get("why", "")).strip()
    normalized["success_definition"] = str(
        normalized.get("success_definition", "")
    ).strip()

    normalized["status"] = str(normalized.get("status", "active")).strip() or "active"

    if normalized["status"] not in VALID_GOAL_STATUSES:
        normalized["status"] = "active"

    normalized["priority"] = str(normalized.get("priority", "medium")).strip() or "medium"
    normalized["time_horizon"] = normalize_time_horizon(
        normalized.get("time_horizon", {})
    )

    subgoals_raw = normalized.get("subgoals", [])
    if not isinstance(subgoals_raw, list):
        subgoals_raw = []

    limits_raw = normalized.get("limits", [])
    if not isinstance(limits_raw, list):
        limits_raw = []

    nested_ids: set[str] = set()

    normalized["subgoals"] = [
        normalize_subgoal(subgoal, nested_ids)
        for subgoal in subgoals_raw
        if isinstance(subgoal, dict)
    ]

    normalized["limits"] = [
        normalize_limit(limit, nested_ids)
        for limit in limits_raw
        if isinstance(limit, dict)
    ]

    return normalized


def migrate_legacy_profile_to_v2(profile: dict[str, Any]) -> dict[str, Any]:
    """
    Supports old schema:
        global_goal + subgoals + limits

    Converts it to:
        main_goals[0].subgoals / limits
    """
    if "main_goals" in profile and isinstance(profile.get("main_goals"), list):
        return profile

    global_goal = profile.get("global_goal", {})
    if not isinstance(global_goal, dict):
        global_goal = {}

    title = str(global_goal.get("title", "")).strip()
    why = str(global_goal.get("why", "")).strip()
    success_definition = str(global_goal.get("success_definition", "")).strip()

    main_goal = create_empty_main_goal(title)
    main_goal["why"] = why
    main_goal["success_definition"] = success_definition
    main_goal["subgoals"] = profile.get("subgoals", [])
    main_goal["limits"] = profile.get("limits", [])

    profile = deepcopy(profile)
    profile["schema_version"] = 2
    profile["main_goals"] = [main_goal] if title or main_goal["subgoals"] else []

    profile.pop("global_goal", None)
    profile.pop("subgoals", None)
    profile.pop("limits", None)

    return profile


def normalize_goal_profile(profile: dict[str, Any]) -> dict[str, Any]:
    """
    Add missing keys and migrate old profile shape without destroying user data.
    """
    profile = migrate_legacy_profile_to_v2(profile)

    normalized = deepcopy(DEFAULT_GOAL_PROFILE)
    normalized.update(profile)

    normalized["schema_version"] = 2

    if not normalized.get("created_at"):
        normalized["created_at"] = now_iso()

    if not normalized.get("updated_at"):
        normalized["updated_at"] = now_iso()

    main_goals_raw = normalized.get("main_goals", [])
    if not isinstance(main_goals_raw, list):
        main_goals_raw = []

    existing_ids: set[str] = set()
    normalized["main_goals"] = [
        normalize_main_goal(goal, existing_ids)
        for goal in main_goals_raw
        if isinstance(goal, dict)
    ]

    coach = deepcopy(DEFAULT_GOAL_PROFILE["coach"])
    if isinstance(profile.get("coach"), dict):
        coach.update(profile["coach"])
    normalized["coach"] = coach

    review = deepcopy(DEFAULT_GOAL_PROFILE["review"])
    if isinstance(profile.get("review"), dict):
        review.update(profile["review"])
    normalized["review"] = review

    return normalized


def validate_date_string(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except Exception:
        return False


def validate_goal_profile(profile: dict[str, Any]) -> list[str]:
    """
    Returns validation errors.
    Empty list means profile is valid enough for MVP.
    """
    errors: list[str] = []

    if not isinstance(profile, dict):
        return ["Goal profile must be a JSON object."]

    missing_root = sorted(REQUIRED_ROOT_KEYS - set(profile.keys()))
    if missing_root:
        errors.append(f"Missing root keys: {', '.join(missing_root)}")

    main_goals = profile.get("main_goals")

    if not isinstance(main_goals, list):
        errors.append("main_goals must be a list.")
        return errors

    if len(main_goals) == 0:
        errors.append("At least one main goal is required.")

    if len(main_goals) > MAX_MAIN_GOALS:
        errors.append(f"Too many main goals. Max allowed: {MAX_MAIN_GOALS}.")

    seen_goal_ids: set[str] = set()

    for goal_index, goal in enumerate(main_goals, start=1):
        if not isinstance(goal, dict):
            errors.append(f"main_goals[{goal_index}] must be an object.")
            continue

        missing_goal_keys = sorted(REQUIRED_MAIN_GOAL_KEYS - set(goal.keys()))
        if missing_goal_keys:
            errors.append(
                f"main_goals[{goal_index}] missing keys: "
                f"{', '.join(missing_goal_keys)}"
            )

        goal_id = str(goal.get("id", "")).strip()
        title = str(goal.get("title", "")).strip()

        if not goal_id:
            errors.append(f"main_goals[{goal_index}].id is required.")

        if goal_id in seen_goal_ids:
            errors.append(f"Duplicate main goal id: {goal_id}")

        if goal_id:
            seen_goal_ids.add(goal_id)

        if not title:
            errors.append(f"main_goals[{goal_index}].title is required.")

        status = str(goal.get("status", "active")).strip()
        if status not in VALID_GOAL_STATUSES:
            errors.append(
                f"main_goals[{goal_index}].status must be one of: "
                f"{', '.join(sorted(VALID_GOAL_STATUSES))}"
            )

        horizon = goal.get("time_horizon")
        if not isinstance(horizon, dict):
            errors.append(f"main_goals[{goal_index}].time_horizon must be object.")
        else:
            horizon_type = str(horizon.get("type", "open_ended")).strip()

            if horizon_type not in VALID_TIME_HORIZON_TYPES:
                errors.append(
                    f"main_goals[{goal_index}].time_horizon.type must be one of: "
                    f"{', '.join(sorted(VALID_TIME_HORIZON_TYPES))}"
                )

            target_date = horizon.get("target_date")
            if horizon_type == "target_date":
                if not isinstance(target_date, str) or not validate_date_string(target_date):
                    errors.append(
                        f"main_goals[{goal_index}].time_horizon.target_date "
                        f"must be YYYY-MM-DD."
                    )

            duration_days = horizon.get("duration_days")
            if horizon_type == "duration":
                if not isinstance(duration_days, int) or duration_days <= 0:
                    errors.append(
                        f"main_goals[{goal_index}].time_horizon.duration_days "
                        f"must be positive integer."
                    )

        subgoals = goal.get("subgoals")
        if not isinstance(subgoals, list):
            errors.append(f"main_goals[{goal_index}].subgoals must be a list.")
        else:
            if len(subgoals) > MAX_SUBGOALS_PER_GOAL:
                errors.append(
                    f"main_goals[{goal_index}] has too many subgoals. "
                    f"Max allowed: {MAX_SUBGOALS_PER_GOAL}."
                )

            seen_subgoal_ids: set[str] = set()

            for subgoal_index, subgoal in enumerate(subgoals, start=1):
                if not isinstance(subgoal, dict):
                    errors.append(
                        f"main_goals[{goal_index}].subgoals[{subgoal_index}] "
                        f"must be an object."
                    )
                    continue

                subgoal_id = str(subgoal.get("id", "")).strip()
                subgoal_title = str(subgoal.get("title", "")).strip()

                if not subgoal_id:
                    errors.append(
                        f"main_goals[{goal_index}].subgoals[{subgoal_index}].id "
                        f"is required."
                    )

                if subgoal_id in seen_subgoal_ids:
                    errors.append(f"Duplicate subgoal id in goal {goal_id}: {subgoal_id}")

                if subgoal_id:
                    seen_subgoal_ids.add(subgoal_id)

                if not subgoal_title:
                    errors.append(
                        f"main_goals[{goal_index}].subgoals[{subgoal_index}].title "
                        f"is required."
                    )

        limits = goal.get("limits")
        if not isinstance(limits, list):
            errors.append(f"main_goals[{goal_index}].limits must be a list.")
        else:
            if len(limits) > MAX_LIMITS_PER_GOAL:
                errors.append(
                    f"main_goals[{goal_index}] has too many limits. "
                    f"Max allowed: {MAX_LIMITS_PER_GOAL}."
                )

            seen_limit_ids: set[str] = set()

            for limit_index, limit in enumerate(limits, start=1):
                if not isinstance(limit, dict):
                    errors.append(
                        f"main_goals[{goal_index}].limits[{limit_index}] "
                        f"must be an object."
                    )
                    continue

                limit_id = str(limit.get("id", "")).strip()
                limit_title = str(limit.get("title", "")).strip()

                if not limit_id:
                    errors.append(
                        f"main_goals[{goal_index}].limits[{limit_index}].id "
                        f"is required."
                    )

                if limit_id in seen_limit_ids:
                    errors.append(f"Duplicate limit id in goal {goal_id}: {limit_id}")

                if limit_id:
                    seen_limit_ids.add(limit_id)

                if not limit_title:
                    errors.append(
                        f"main_goals[{goal_index}].limits[{limit_index}].title "
                        f"is required."
                    )

    return errors


def archive_goal_profile(
    profile: dict[str, Any],
    reason: str = "",
) -> Path:
    ensure_dirs()

    version = int(profile.get("profile_version", 1))
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    filename = f"goal_profile_v{version}_{timestamp}.json"

    archive_path = GOAL_PROFILE_VERSIONS_DIR / filename

    snapshot = deepcopy(profile)
    snapshot["_archive"] = {
        "archived_at": now_iso(),
        "reason": reason.strip() or "Goal profile archived",
    }

    write_json_atomic(archive_path, snapshot)
    return archive_path


def load_goal_profile(create_if_missing: bool = True) -> dict[str, Any]:
    ensure_dirs()

    if not GOAL_PROFILE_PATH.exists():
        if not create_if_missing:
            raise FileNotFoundError(f"Goal profile not found: {GOAL_PROFILE_PATH}")

        profile = create_empty_goal_profile()
        return save_goal_profile(
            profile=profile,
            change_reason="Initial empty goal profile created",
            archive_previous=False,
            allow_empty=True,
        )

    try:
        raw = GOAL_PROFILE_PATH.read_text(encoding="utf-8")
        loaded = json.loads(raw)

        if not isinstance(loaded, dict):
            raise ValueError("goal_profile.json root must be object")

        normalized = normalize_goal_profile(loaded)

        if normalized != loaded:
            write_json_atomic(GOAL_PROFILE_PATH, normalized)

        return normalized

    except Exception:
        broken_path = GOAL_PROFILE_PATH.with_name(
            f"goal_profile.broken.{int(time.time())}.json"
        )

        try:
            GOAL_PROFILE_PATH.replace(broken_path)
        except Exception:
            pass

        profile = create_empty_goal_profile()
        return save_goal_profile(
            profile=profile,
            change_reason="Recovered from broken goal profile",
            archive_previous=False,
            allow_empty=True,
        )


def save_goal_profile(
    profile: dict[str, Any],
    change_reason: str = "",
    archive_previous: bool = True,
    allow_empty: bool = False,
) -> dict[str, Any]:
    ensure_dirs()

    normalized = normalize_goal_profile(profile)

    errors = validate_goal_profile(normalized)
    if errors and not allow_empty:
        raise ValueError("Invalid goal profile:\n" + "\n".join(errors))

    if GOAL_PROFILE_PATH.exists() and archive_previous:
        try:
            previous_profile = load_goal_profile(create_if_missing=False)
            archive_goal_profile(
                previous_profile,
                reason=change_reason or "Goal profile updated",
            )

            previous_version = int(previous_profile.get("profile_version", 1))
            normalized["profile_version"] = previous_version + 1
        except Exception:
            normalized["profile_version"] = int(normalized.get("profile_version", 1))

    normalized["updated_at"] = now_iso()
    normalized["change_reason"] = change_reason.strip() or "Goal profile saved"

    if not normalized.get("created_at"):
        normalized["created_at"] = now_iso()

    write_json_atomic(GOAL_PROFILE_PATH, normalized)
    return normalized


def list_goal_profile_versions() -> list[Path]:
    ensure_dirs()
    return sorted(GOAL_PROFILE_VERSIONS_DIR.glob("goal_profile_v*.json"))


def create_profile_from_manual_goals(
    goals: list[dict[str, Any]],
    coach_style: str = "direct",
    language: str = "uk",
) -> dict[str, Any]:
    """
    New v2 manual constructor.

    Expected goals item:
    {
        "title": "...",
        "why": "...",
        "success_definition": "...",
        "time_horizon": {...},
        "subgoal_titles": [...],
        "limit_titles": [...]
    }
    """
    profile = create_empty_goal_profile(
        created_by="manual",
        source_mode="manual",
    )

    main_goals: list[dict[str, Any]] = []
    used_goal_ids: set[str] = set()

    for goal_data in goals[:MAX_MAIN_GOALS]:
        title = str(goal_data.get("title", "")).strip()
        if not title:
            continue

        goal = create_empty_main_goal(title)
        goal["id"] = make_id("goal", title, used_goal_ids)
        used_goal_ids.add(goal["id"])

        goal["why"] = str(goal_data.get("why", "")).strip()
        goal["success_definition"] = str(
            goal_data.get("success_definition", "")
        ).strip()
        goal["priority"] = str(goal_data.get("priority", "medium")).strip() or "medium"
        goal["time_horizon"] = normalize_time_horizon(goal_data.get("time_horizon", {}))

        nested_ids: set[str] = set()

        subgoal_titles = goal_data.get("subgoal_titles", [])
        if not isinstance(subgoal_titles, list):
            subgoal_titles = []

        for subgoal_title in subgoal_titles[:MAX_SUBGOALS_PER_GOAL]:
            clean_subgoal_title = str(subgoal_title).strip()
            if not clean_subgoal_title:
                continue

            subgoal = create_subgoal(clean_subgoal_title, nested_ids)
            nested_ids.add(subgoal["id"])
            goal["subgoals"].append(subgoal)

        limit_titles = goal_data.get("limit_titles", [])
        if not isinstance(limit_titles, list):
            limit_titles = []

        for limit_title in limit_titles[:MAX_LIMITS_PER_GOAL]:
            clean_limit_title = str(limit_title).strip()
            if not clean_limit_title:
                continue

            limit = create_limit(clean_limit_title, nested_ids)
            nested_ids.add(limit["id"])
            goal["limits"].append(limit)

        main_goals.append(goal)

    profile["main_goals"] = main_goals
    profile["coach"] = {
        "style": coach_style.strip() or "direct",
        "language": language.strip() or "uk",
    }

    return normalize_goal_profile(profile)


def create_profile_from_manual_input(
    global_goal_title: str,
    global_goal_why: str = "",
    success_definition: str = "",
    subgoal_titles: list[str] | None = None,
    limit_titles: list[str] | None = None,
    coach_style: str = "direct",
    language: str = "uk",
) -> dict[str, Any]:
    """
    Backward-compatible helper for the current setup_wizard.py.

    It creates one main goal from the old single-goal form.
    Later wizard will use create_profile_from_manual_goals().
    """
    return create_profile_from_manual_goals(
        goals=[
            {
                "title": global_goal_title,
                "why": global_goal_why,
                "success_definition": success_definition,
                "time_horizon": deepcopy(DEFAULT_TIME_HORIZON),
                "subgoal_titles": subgoal_titles or [],
                "limit_titles": limit_titles or [],
            }
        ],
        coach_style=coach_style,
        language=language,
    )


def parse_goal_profile_json(json_text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON: {error}") from error

    if not isinstance(parsed, dict):
        raise ValueError("Goal profile JSON must be an object.")

    normalized = normalize_goal_profile(parsed)
    errors = validate_goal_profile(normalized)

    if errors:
        raise ValueError("Invalid goal profile:\n" + "\n".join(errors))

    return normalized


def get_goal_templates() -> dict[str, dict[str, Any]]:
    """
    MVP templates.

    Templates are not truth.
    They are editable starting points for the user.
    """
    return {
        "career_find_job": {
            "label": "Career / Find job",
            "title": "Get a job",
            "why": "",
            "success_definition": "Get a signed job contract or stable paid role",
            "time_horizon": {
                "type": "target_date",
                "target_date": None,
                "duration_days": None,
                "review_interval": "weekly",
            },
            "subgoal_titles": [
                "Improve CV and LinkedIn",
                "Apply to relevant jobs",
                "Practice interviews",
                "Build portfolio",
                "Improve relevant skills",
            ],
            "limit_titles": [
                "Limit uncontrolled gaming",
                "Limit passive scrolling",
            ],
        },
        "language_learning": {
            "label": "Language learning",
            "title": "Learn a new language",
            "why": "",
            "success_definition": "Reach the target language level or pass the exam",
            "time_horizon": {
                "type": "target_date",
                "target_date": None,
                "duration_days": None,
                "review_interval": "weekly",
            },
            "subgoal_titles": [
                "Do course homework",
                "Practice speaking",
                "Learn vocabulary",
                "Listen or read daily",
                "Prepare for exam",
            ],
            "limit_titles": [
                "Avoid skipping practice for several days",
            ],
        },
        "fitness_health": {
            "label": "Fitness / Health",
            "title": "Improve physical fitness",
            "why": "",
            "success_definition": "Train consistently and improve measurable health or fitness markers",
            "time_horizon": {
                "type": "ongoing",
                "target_date": None,
                "duration_days": None,
                "review_interval": "monthly",
            },
            "subgoal_titles": [
                "Train regularly",
                "Improve sleep",
                "Improve nutrition",
                "Track body progress",
            ],
            "limit_titles": [
                "Limit late-night screen time",
                "Limit junk food",
            ],
        },
        "build_project": {
            "label": "Build project / startup",
            "title": "Build a project",
            "why": "",
            "success_definition": "Release a usable MVP",
            "time_horizon": {
                "type": "target_date",
                "target_date": None,
                "duration_days": None,
                "review_interval": "weekly",
            },
            "subgoal_titles": [
                "Define MVP scope",
                "Implement core features",
                "Test with real usage",
                "Prepare public release",
            ],
            "limit_titles": [
                "Avoid endless refactoring without release",
                "Limit distractions during work sessions",
            ],
        },
    }


def build_ai_assisted_prompt(
    language: str = "uk",
    wishes: str = "",
    life_areas: list[str] | None = None,
    available_effort: str = "",
    obstacles: str = "",
) -> str:
    templates = get_goal_templates()
    template_labels = [template["label"] for template in templates.values()]
    user_context = {
        "wishes": wishes.strip(),
        "selected_life_areas": [
            str(area).strip() for area in (life_areas or []) if str(area).strip()
        ],
        "available_effort": available_effort.strip(),
        "known_obstacles_or_constraints": obstacles.strip(),
    }
    user_context_json = json.dumps(user_context, ensure_ascii=False, indent=2)

    return f"""
You are helping create a GoalCompass goal profile.

GoalCompass is a desktop behavior tracker and coaching system.
It tracks user activities and evaluates whether they support the user's real-life goals.

Return ONLY valid JSON.
Do not use markdown.
Do not add explanations.
Do not wrap the JSON in ```.

Use schema_version 2.

The user has already provided a short, possibly vague description below.
Turn it into a useful first draft; do not ask an interview question in your response.
The user can have multiple main goals at the same time.
Each main goal has its own subgoals and limits.

USER INPUT:
{user_context_json}

Use this exact structure:

{{
  "schema_version": 2,
  "profile_version": 1,
  "created_by": "ai_assisted",
  "source_mode": "ai_assisted",
  "main_goals": [
    {{
      "id": "goal_example",
      "title": "",
      "why": "",
      "success_definition": "",
      "status": "active",
      "priority": "medium",
      "time_horizon": {{
        "type": "open_ended",
        "target_date": null,
        "duration_days": null,
        "review_interval": "monthly"
      }},
      "subgoals": [
        {{
          "id": "subgoal_example",
          "title": "",
          "status": "active",
          "hypothesis": "",
          "success_metric": "",
          "target_minutes_per_day": null,
          "target_minutes_per_week": null,
          "linked_categories": [],
          "linked_keywords": [],
          "linked_processes": [],
          "notes": ""
        }}
      ],
      "limits": [
        {{
          "id": "limit_example",
          "title": "",
          "status": "active",
          "hypothesis": "",
          "category": "",
          "limit_minutes_per_day": null,
          "limit_minutes_per_week": null,
          "linked_processes": [],
          "linked_keywords": [],
          "severity": "warning",
          "notes": ""
        }}
      ],
      "notes": ""
    }}
  ],
  "coach": {{
    "style": "direct",
    "language": "{language}"
  }},
  "review": {{
    "weekly_review_enabled": true,
    "monthly_review_enabled": true,
    "monthly_review_day": 1,
    "last_review_at": null
  }}
}}

Allowed time_horizon.type values:
- open_ended: no fixed deadline
- target_date: target_date must be YYYY-MM-DD
- duration: duration_days must be a positive integer
- ongoing: habit or maintenance goal

Allowed review_interval values:
- weekly
- monthly
- quarterly
- none

Important concepts:
- A main goal is a real-life goal.
- A subgoal is a hypothesis about what can help reach that main goal.
- A limit is a behavior that may reduce progress toward that specific main goal.
- Same activity can have different meaning for different users.
  Gaming can be harmful for one user but useful for a streamer.
- Do not merge unrelated goals into one title.
- If the user says "find a job, learn German, improve fitness", create three main_goals.
- Create no more than 3 main goals. Prefer fewer goals and a realistic starting scope.
- Every main goal must have a non-empty title, a concrete success_definition,
  and 3-5 practical subgoals in a sensible order.
- Subgoals must describe actions or capabilities that could plausibly cause progress,
  not vague motivational slogans.
- Add only relevant limits. Do not assume an activity is harmful without user context.
- Add hypotheses for subgoals and limits when possible.
- If time, deadline, or personal facts are unknown, use a conservative default and
  disclose the uncertainty in notes. Never invent a diagnosis, income, or biography.
- The result is a proposal for the user to review, not a claim of guaranteed causation.
- Keep the profile practical, not motivational fluff.

Possible template categories:
{", ".join(template_labels)}

Return the completed final JSON only. Never return the empty example unchanged.
""".strip()

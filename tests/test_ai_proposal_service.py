from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.services.ai_proposal_service import (
    apply_ai_proposal,
    build_ai_proposal_preview,
    parse_ai_proposal_json,
)
from src.services.goal_profile_service import create_profile_from_manual_goals
from src.services.settings_service import normalize_settings


def valid_proposal() -> dict:
    return {
        "schema_version": 1,
        "summary": "Use AI-assisted setup with fewer interruptions.",
        "confidence": "medium",
        "rationale": ["The user wants less setup work."],
        "data_quality": {
            "limitations": ["Phone and offline activity are not available."],
            "missing_domains": ["phone", "wearable"],
        },
        "questions": ["Should proactive questions be limited to two per day?"],
        "changes": {
            "settings_patch": {
                "automation": {"mode": "ai_assisted"},
                "interaction": {
                    "mode": "standard",
                    "daily_prompt_limit": 2,
                },
            },
            "goal_profile": None,
        },
    }


class AIProposalValidationTests(unittest.TestCase):
    def test_valid_proposal_is_normalized(self) -> None:
        parsed = parse_ai_proposal_json(json.dumps(valid_proposal()))

        self.assertTrue(parsed["proposal_id"].startswith("proposal_"))
        self.assertEqual(parsed["confidence"], "medium")
        self.assertEqual(
            parsed["changes"]["settings_patch"]["automation"]["mode"],
            "ai_assisted",
        )

    def test_forbidden_settings_are_rejected(self) -> None:
        proposal = valid_proposal()
        proposal["changes"]["settings_patch"] = {
            "app": {"first_run_completed": False}
        }

        with self.assertRaisesRegex(ValueError, "cannot modify settings section"):
            parse_ai_proposal_json(json.dumps(proposal))

    def test_empty_change_set_is_rejected(self) -> None:
        proposal = valid_proposal()
        proposal["changes"] = {"settings_patch": {}, "goal_profile": None}

        with self.assertRaisesRegex(ValueError, "at least one valid change"):
            parse_ai_proposal_json(json.dumps(proposal))

    def test_preview_discloses_limitations_and_effective_diff(self) -> None:
        profile = create_profile_from_manual_goals(
            goals=[{"title": "Build GoalCompass"}]
        )
        preview = build_ai_proposal_preview(
            valid_proposal(),
            current_settings=normalize_settings({}),
            current_goal_profile=profile,
        )

        self.assertIn("Phone and offline activity are not available.", preview)
        self.assertIn("current/settings", preview)
        self.assertIn('"ai_assisted"', preview)


class AIProposalApplyTests(unittest.TestCase):
    def test_apply_requires_explicit_confirmation(self) -> None:
        with self.assertRaises(PermissionError):
            apply_ai_proposal(valid_proposal(), confirmed=False)

    def test_confirmed_settings_proposal_creates_audit(self) -> None:
        settings = normalize_settings({})
        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                patch(
                    "src.services.ai_proposal_service.AI_PROPOSAL_HISTORY_DIR",
                    Path(temp_dir),
                ),
                patch(
                    "src.services.ai_proposal_service.load_settings",
                    return_value=settings,
                ),
                patch("src.services.ai_proposal_service.save_settings") as save_mock,
            ):
                audit_path = apply_ai_proposal(valid_proposal(), confirmed=True)

            self.assertTrue(audit_path.exists())
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
            self.assertEqual(audit["status"], "applied")
            save_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()

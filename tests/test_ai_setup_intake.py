from __future__ import annotations

import json
import unittest

from src.services.goal_profile_service import (
    build_ai_assisted_profile_preview,
    build_ai_assisted_prompt,
    parse_goal_profile_json,
)


def minimal_goal_profile() -> dict:
    return {
        "schema_version": 2,
        "main_goals": [
            {
                "title": "Find a suitable job",
                "why": "Improve stability",
                "success_definition": "Sign a suitable employment contract",
                "priority": "high",
                "subgoals": [
                    {
                        "title": "Prepare a focused CV",
                        "first_actions": ["Collect three relevant job descriptions"],
                    }
                ],
                "limits": [],
            }
        ],
    }


class AIAssistedSetupPromptTests(unittest.TestCase):
    def test_prompt_contains_real_user_intake(self) -> None:
        prompt = build_ai_assisted_prompt(
            wishes="I want a better job and stronger German.",
            life_areas=["Career and income", "Learning and skills"],
            available_effort="6-10 hours per week",
            obstacles="I lose focus after work",
        )

        self.assertIn("I want a better job and stronger German.", prompt)
        self.assertIn('"Career and income"', prompt)
        self.assertIn('"Learning and skills"', prompt)
        self.assertIn("6-10 hours per week", prompt)
        self.assertIn("I lose focus after work", prompt)

    def test_prompt_requires_filled_goals_and_practical_subgoals(self) -> None:
        prompt = build_ai_assisted_prompt(wishes="I want more energy.")

        self.assertIn("3-5 practical subgoals", prompt)
        self.assertIn("Never return the empty example unchanged", prompt)
        self.assertNotIn("Now interview the user", prompt)

    def test_prompt_requests_versioned_profile_and_data_quality(self) -> None:
        prompt = build_ai_assisted_prompt(wishes="I want a better job.")

        self.assertIn('"response_schema": "goalcompass_ai_intake/v1"', prompt)
        self.assertIn('"user_profile"', prompt)
        self.assertIn('"data_quality"', prompt)
        self.assertIn('"missing_information"', prompt)
        self.assertIn('"first_actions"', prompt)
        self.assertIn("never present absence of data as proof", prompt)


class AIAssistedResponseTests(unittest.TestCase):
    def test_markdown_fenced_envelope_is_accepted(self) -> None:
        response = {
            "response_schema": "goalcompass_ai_intake/v1",
            "user_profile": {
                "summary": "Wants a stable job with a realistic workload.",
                "motivations": ["Stability"],
                "strengths": [],
                "constraints": ["Limited evening energy"],
                "preferences": ["Small first steps"],
                "available_effort": "3-5 hours per week",
            },
            "data_quality": {
                "confidence": "medium",
                "assumptions": ["Current CV needs revision"],
                "missing_information": ["Target roles"],
                "unobserved_areas": ["Offline learning"],
            },
            "goal_profile": minimal_goal_profile(),
        }
        raw = "Here is the result:\n```json\n" + json.dumps(response) + "\n```"

        profile = parse_goal_profile_json(raw)

        self.assertEqual(profile["user_profile"]["available_effort"], "3-5 hours per week")
        self.assertEqual(profile["data_quality"]["confidence"], "medium")
        self.assertEqual(
            profile["main_goals"][0]["subgoals"][0]["first_actions"],
            ["Collect three relevant job descriptions"],
        )

    def test_legacy_plain_goal_profile_remains_supported(self) -> None:
        profile = parse_goal_profile_json(json.dumps(minimal_goal_profile()))

        self.assertEqual(profile["main_goals"][0]["title"], "Find a suitable job")
        self.assertEqual(profile["data_quality"]["confidence"], "low")

    def test_readable_preview_discloses_unknowns(self) -> None:
        source = minimal_goal_profile()
        source["data_quality"] = {
            "confidence": "low",
            "assumptions": ["The target role is still uncertain"],
            "missing_information": ["Preferred work location"],
            "unobserved_areas": [],
        }

        preview = build_ai_assisted_profile_preview(source)

        self.assertIn("Data confidence: low", preview)
        self.assertIn("Preferred work location", preview)
        self.assertIn("Prepare a focused CV", preview)


if __name__ == "__main__":
    unittest.main()

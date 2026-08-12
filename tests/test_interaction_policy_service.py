from __future__ import annotations

import unittest

from src.services.interaction_policy_service import build_interaction_policy
from src.services.settings_service import normalize_settings


class SettingsNormalizationTests(unittest.TestCase):
    def test_legacy_direct_coach_style_is_migrated(self) -> None:
        normalized = normalize_settings({"coach": {"style": "direct"}})

        self.assertTrue(normalized["coach"]["enabled"])
        self.assertEqual(normalized["coach"]["style"], "neutral")
        self.assertEqual(normalized["automation"]["mode"], "manual")
        self.assertEqual(normalized["interaction"]["mode"], "standard")

    def test_legacy_off_style_disables_coach(self) -> None:
        normalized = normalize_settings({"coach": {"style": "off"}})

        self.assertFalse(normalized["coach"]["enabled"])
        self.assertEqual(normalized["coach"]["style"], "neutral")

    def test_invalid_modes_and_prompt_limits_are_normalized(self) -> None:
        normalized = normalize_settings(
            {
                "automation": {"mode": "magic"},
                "interaction": {
                    "mode": "noisy",
                    "daily_prompt_limit": 999,
                    "cooldown_minutes": -5,
                },
            }
        )

        self.assertEqual(normalized["automation"]["mode"], "manual")
        self.assertEqual(normalized["interaction"]["mode"], "standard")
        self.assertEqual(normalized["interaction"]["daily_prompt_limit"], 50)
        self.assertEqual(normalized["interaction"]["cooldown_minutes"], 0)


class InteractionPolicyTests(unittest.TestCase):
    def test_silent_mode_blocks_all_interventions_but_keeps_automation(self) -> None:
        policy = build_interaction_policy(
            {
                "automation": {"mode": "full_ai"},
                "interaction": {"mode": "silent"},
                "coach": {"enabled": True, "style": "aggressive"},
            }
        )

        self.assertEqual(policy.automation_mode, "full_ai")
        self.assertTrue(policy.is_silent)
        self.assertFalse(policy.allows_warning)
        self.assertFalse(policy.allows_badge)
        self.assertFalse(policy.allows_popup)
        self.assertFalse(policy.allows_coaching)
        self.assertFalse(policy.allow_questions)
        self.assertFalse(policy.allow_proactive_suggestions)

    def test_proactive_mode_enables_questions_and_suggestions(self) -> None:
        policy = build_interaction_policy(
            {
                "interaction": {"mode": "proactive", "daily_prompt_limit": 2},
                "coach": {"enabled": True, "style": "strict"},
            }
        )

        self.assertTrue(policy.allows_warning)
        self.assertTrue(policy.allows_coaching)
        self.assertTrue(policy.allow_questions)
        self.assertTrue(policy.allow_proactive_suggestions)
        self.assertEqual(policy.coach_style, "strict")

    def test_zero_prompt_limit_disables_questions(self) -> None:
        policy = build_interaction_policy(
            {"interaction": {"mode": "intensive", "daily_prompt_limit": 0}}
        )

        self.assertFalse(policy.allow_questions)
        self.assertTrue(policy.allow_proactive_suggestions)

    def test_notification_switch_blocks_badges_popups_and_coach(self) -> None:
        policy = build_interaction_policy(
            {
                "interaction": {"mode": "standard"},
                "notifications": {"enabled": False},
                "overlay": {"show_badge": True, "show_popup": True},
                "coach": {"enabled": True, "style": "soft"},
            }
        )

        self.assertFalse(policy.allows_warning)
        self.assertFalse(policy.allows_badge)
        self.assertFalse(policy.allows_popup)
        self.assertFalse(policy.allows_coaching)


if __name__ == "__main__":
    unittest.main()

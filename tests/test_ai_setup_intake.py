from __future__ import annotations

import unittest

from src.services.goal_profile_service import build_ai_assisted_prompt


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


if __name__ == "__main__":
    unittest.main()

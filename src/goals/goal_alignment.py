# src/goals/goal_alignment.py

from __future__ import annotations

from dataclasses import dataclass

from src.goals.goal import Goal
from src.outcomes.outcome import Outcome


@dataclass(frozen=True)
class GoalAlignmentResult:
    goal_id: str
    outcome_type: str
    alignment_score: int
    message: str


class GoalAlignmentEngine:
    def evaluate(
        self,
        goal: Goal,
        outcome: Outcome,
    ) -> GoalAlignmentResult:
        """
        First simple version.

        alignment_score:
        - positive = supports goal
        - zero = neutral
        - negative = conflicts with goal
        """

        related_outcomes = set(
            goal.metadata.get("related_outcomes", [])
            if goal.metadata
            else []
        )

        conflicting_outcomes = set(
            goal.metadata.get("conflicting_outcomes", [])
            if goal.metadata
            else []
        )

        if outcome.outcome_type in related_outcomes:
            return GoalAlignmentResult(
                goal_id=goal.goal_id,
                outcome_type=outcome.outcome_type,
                alignment_score=1,
                message="Outcome supports goal",
            )

        if outcome.outcome_type in conflicting_outcomes:
            return GoalAlignmentResult(
                goal_id=goal.goal_id,
                outcome_type=outcome.outcome_type,
                alignment_score=-1,
                message="Outcome conflicts with goal",
            )

        return GoalAlignmentResult(
            goal_id=goal.goal_id,
            outcome_type=outcome.outcome_type,
            alignment_score=0,
            message="Outcome is neutral for this goal",
        )
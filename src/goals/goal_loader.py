from src.goals.goal import Goal
from src.profiles.profile_loader import get_goals


def load_goals() -> list[Goal]:
    goals = []

    for item in get_goals():
        goals.append(
            Goal(
                goal_id=item["goal_id"],
                goal_type=item["goal_type"],
                title=item["title"],
                metadata={
                    "related_outcomes": item.get(
                        "related_outcomes",
                        [],
                    ),
                    "conflicting_outcomes": item.get(
                        "conflicting_outcomes",
                        [],
                    ),
                },
            )
        )

    return goals
from src.coach.rules_engine import get_rule


def evaluate(state: str) -> dict:
    return get_rule(state)
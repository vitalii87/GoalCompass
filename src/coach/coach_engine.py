# src/coach/coach_engine.py

from __future__ import annotations

from typing import Any, Dict

from src.coach.rules_engine import get_rule_for_category


def evaluate_category(category: str) -> Dict[str, Any]:
    """
    Thin adapter over rules engine.
    Do not duplicate rule logic here.
    """
    return get_rule_for_category(category)
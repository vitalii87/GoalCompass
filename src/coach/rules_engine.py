# src/coach/rules_engine.py

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

from src.config.config import RULES


DEFAULT_RULE = {
    "mode": "none",
    "threshold_seconds": 0,
    "notify_on_enter": False,
    "message": "",
}


def get_rule_for_category(category: str) -> Dict[str, Any]:
    rule = RULES.get(category, DEFAULT_RULE)
    return deepcopy(rule)
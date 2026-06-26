from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Goal:
    goal_id: str
    goal_type: str
    title: str
    is_active: bool = True
    metadata: dict[str, Any] | None = None

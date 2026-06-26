from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Outcome:
    outcome_type: str
    category: str
    seconds: int
    message: str
    metadata: dict[str, Any] | None = None
    
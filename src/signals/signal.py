# src/signals/signal.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Signal:
    signal_type: str
    category: str
    process_name: str
    seconds: int
    message: str
    metadata: dict[str, Any] | None = None

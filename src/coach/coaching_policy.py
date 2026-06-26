from __future__ import annotations

from src.coach.coach_personas import DEFAULT_PERSONA


class CoachingPolicy:
    def __init__(self, persona: str = DEFAULT_PERSONA) -> None:
        self.persona = persona

    def should_react_to_signal(self, signal_type: str) -> bool:
        if self.persona == "silent":
            return False

        return True

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.services.settings_service import load_settings, normalize_settings


@dataclass(frozen=True)
class InteractionPolicy:
    automation_mode: str
    interaction_mode: str
    coach_enabled: bool
    coach_style: str
    notifications_enabled: bool
    show_badge: bool
    show_popup: bool
    allow_questions: bool
    allow_proactive_suggestions: bool
    daily_prompt_limit: int
    cooldown_minutes: int

    @property
    def is_silent(self) -> bool:
        return self.interaction_mode == "silent"

    @property
    def allows_warning(self) -> bool:
        return self.notifications_enabled and not self.is_silent

    @property
    def allows_badge(self) -> bool:
        return self.allows_warning and self.show_badge

    @property
    def allows_popup(self) -> bool:
        return self.allows_warning and self.show_popup

    @property
    def allows_coaching(self) -> bool:
        return self.allows_warning and self.coach_enabled


def build_interaction_policy(settings: dict[str, Any]) -> InteractionPolicy:
    normalized = normalize_settings(settings)
    interaction_mode = str(normalized["interaction"]["mode"])
    daily_prompt_limit = int(normalized["interaction"]["daily_prompt_limit"])

    return InteractionPolicy(
        automation_mode=str(normalized["automation"]["mode"]),
        interaction_mode=interaction_mode,
        coach_enabled=bool(normalized["coach"]["enabled"]),
        coach_style=str(normalized["coach"]["style"]),
        notifications_enabled=bool(normalized["notifications"]["enabled"]),
        show_badge=bool(normalized["overlay"]["show_badge"]),
        show_popup=bool(normalized["overlay"]["show_popup"]),
        allow_questions=(
            interaction_mode in {"standard", "proactive", "intensive"}
            and daily_prompt_limit > 0
        ),
        allow_proactive_suggestions=interaction_mode in {"proactive", "intensive"},
        daily_prompt_limit=daily_prompt_limit,
        cooldown_minutes=int(normalized["interaction"]["cooldown_minutes"]),
    )


def load_interaction_policy() -> InteractionPolicy:
    return build_interaction_policy(load_settings())

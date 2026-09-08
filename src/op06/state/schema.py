from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConversationState:
    slots: dict[str, bool | str]
    completed_steps: tuple[str, ...]
    pending_questions: tuple[str, ...]
    contradictions: tuple[str, ...]
    last_agent_text: str | None
    turn_index: int


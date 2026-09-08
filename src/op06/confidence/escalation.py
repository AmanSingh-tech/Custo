from __future__ import annotations

from dataclasses import dataclass

_HOSTILE_FLAGS = frozenset(
    {"instruction_injection", "role_delimiter", "bidi_control", "nul_character"}
)


@dataclass(frozen=True, slots=True)
class EscalationDecision:
    needs_human: bool
    reasons: tuple[str, ...]


def decide_escalation(
    *,
    confidence: float,
    threshold: float,
    intent_margin: float,
    action_margin: float,
    selected_action: str,
    policy_valid: bool,
    safety_flags: frozenset[str],
    contradictions: tuple[str, ...],
) -> EscalationDecision:
    reasons: list[str] = []
    if confidence < threshold:
        reasons.append("low_confidence")
    if intent_margin < 0.08:
        reasons.append("intent_ambiguity")
    if action_margin < 0.08:
        reasons.append("action_ambiguity")
    if not policy_valid:
        reasons.append("policy_conflict")
    if selected_action == "escalate_human" or selected_action.endswith("_and_escalate"):
        reasons.append("action_requires_human")
    if safety_flags & _HOSTILE_FLAGS:
        reasons.append("hostile_or_corrupted_input")
    if contradictions:
        reasons.append("conversation_contradiction")
    return EscalationDecision(bool(reasons), tuple(dict.fromkeys(reasons)))

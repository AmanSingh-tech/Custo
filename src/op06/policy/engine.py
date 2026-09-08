from __future__ import annotations

from dataclasses import dataclass

from op06.policy.compiler import CompiledPolicy
from op06.state.schema import ConversationState


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    candidates: tuple[str, ...]
    matched_rules: tuple[str, ...]
    valid: bool
    fallback_reason: str | None = None


class PolicyEngine:
    def __init__(self, policy: CompiledPolicy) -> None:
        self.policy = policy

    def candidates(self, intent: str, state: ConversationState) -> PolicyDecision:
        workflow = self.policy.workflows.get(intent)
        if workflow is None:
            return PolicyDecision(("escalate_human",), (), False, "unknown_intent")

        matched: list[tuple[int, str]] = []
        for rule in workflow.rules:
            missing_matches = all(
                not bool(state.slots.get(slot, False)) for slot in rule.when_missing
            )
            present_matches = all(bool(state.slots.get(slot, False)) for slot in rule.when_present)
            if (
                missing_matches
                and present_matches
                and rule.action not in self.policy.forbidden_actions
            ):
                matched.append((rule.priority, rule.action))
        if not matched:
            return PolicyDecision((workflow.fallback_action,), (), False, "no_permitted_action")
        ordered = tuple(
            action for _, action in sorted(matched, key=lambda item: (-item[0], item[1]))
        )
        return PolicyDecision(ordered, ordered, True)

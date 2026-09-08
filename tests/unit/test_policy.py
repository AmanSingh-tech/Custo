import pytest

from op06.api.schemas import Turn
from op06.policy.compiler import PolicyError, compile_policy_document, load_policy
from op06.policy.engine import PolicyEngine
from op06.preprocessing.normalize import normalize_conversation
from op06.state.extractor import extract_state


def test_policy_selects_next_rule(pipeline) -> None:
    policy = load_policy(pipeline.settings.policy_path)
    engine = PolicyEngine(policy)
    empty_state = extract_state(normalize_conversation([Turn(role="customer", text="Card failed")]))
    assert engine.candidates("card_not_working", empty_state).candidates[0] == "ask_when_issue_started"

    known_time = extract_state(
        normalize_conversation([Turn(role="customer", text="My card failed yesterday")])
    )
    assert (
        engine.candidates("card_not_working", known_time).candidates[0]
        == "ask_alternate_terminal_attempted"
    )


def test_policy_rejects_unregistered_action() -> None:
    document = {
        "version": "1",
        "intents": ["known"],
        "actions": ["escalate_human"],
        "workflows": {
            "known": {
                "fallback_action": "escalate_human",
                "rules": [{"action": "unknown"}],
            }
        },
    }
    with pytest.raises(PolicyError, match="Unregistered action"):
        compile_policy_document(document)


def test_unknown_intent_fails_safe(pipeline) -> None:
    state = extract_state(normalize_conversation([Turn(role="customer", text="Help")]))
    decision = PolicyEngine(pipeline.policy).candidates("not-registered", state)
    assert decision.candidates == ("escalate_human",)
    assert decision.valid is False


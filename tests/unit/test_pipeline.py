import pytest

from op06.api.schemas import TriageRequest
from op06.config import Settings
from op06.pipeline import TriagePipeline


def request(*turns: tuple[str, str]) -> TriageRequest:
    return TriageRequest.model_validate(
        {"conversation": [{"role": role, "text": text} for role, text in turns]}
    )


def test_workflow_position_changes_action(pipeline) -> None:
    initial, _ = pipeline.triage(request(("customer", "My card is not working.")))
    progressed, _ = pipeline.triage(
        request(
            ("customer", "My card is not working."),
            ("agent", "When did this begin?"),
            ("customer", "Yesterday."),
        )
    )
    assert initial.intent == progressed.intent == "card_not_working"
    assert initial.action == "ask_when_issue_started"
    assert progressed.action == "ask_alternate_terminal_attempted"


def test_unknown_request_escalates(pipeline) -> None:
    response, trace = pipeline.triage(request(("customer", "Hello, I need some help.")))
    assert response.intent == "general_support"
    assert response.action == "request_clarification"
    assert response.needs_human is True
    assert "low_confidence" in trace.escalation.reasons


def test_account_security_action_requires_human(pipeline) -> None:
    response, trace = pipeline.triage(
        request(("customer", "I do not recognize this card payment of $52."))
    )
    assert response.action == "secure_account_and_escalate"
    assert response.needs_human is True
    assert "action_requires_human" in trace.escalation.reasons


def test_outputs_are_registered_and_bounded(pipeline) -> None:
    response, _ = pipeline.triage(request(("customer", "Where is my card? Track my card.")))
    assert response.intent in pipeline.policy.intents
    assert response.action in pipeline.policy.actions
    assert response.action not in pipeline.policy.forbidden_actions
    assert 0 <= response.confidence <= 1


def test_batch_inference_matches_single_inference(pipeline) -> None:
    requests = [
        request(("customer", "My card is not working.")),
        request(("customer", "Where is my card? Track my card.")),
    ]
    batched = [response for response, _ in pipeline.triage_many(requests)]
    individual = [pipeline.triage(item)[0] for item in requests]
    assert batched == individual


def test_production_mode_refuses_silent_demo_model(monkeypatch) -> None:
    monkeypatch.delenv("OP06_MODEL_PATH", raising=False)
    monkeypatch.delenv("OP06_ALLOW_DEMO_MODEL", raising=False)
    with pytest.raises(RuntimeError, match="No trained model configured"):
        TriagePipeline.build(Settings.from_env())

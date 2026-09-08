from op06.api.schemas import Turn
from op06.preprocessing.normalize import normalize_conversation
from op06.state.extractor import extract_state


def test_state_extracts_time_and_transaction_details() -> None:
    conversation = normalize_conversation(
        [Turn(role="customer", text="Yesterday my $42 transaction had the wrong rate")]
    )
    state = extract_state(conversation)
    assert state.slots["start_time_known"] is True
    assert state.slots["transaction_details_known"] is True


def test_unanswered_agent_question_is_pending() -> None:
    conversation = normalize_conversation(
        [
            Turn(role="customer", text="My card failed"),
            Turn(role="agent", text="When did it begin?"),
        ]
    )
    state = extract_state(conversation)
    assert state.pending_questions == ("When did it begin?",)

from op06.data_tools import audit_examples, split_examples


def _examples() -> list[dict]:
    return [
        {
            "conversation_id": f"conversation-{index // 2}",
            "conversation": [{"role": "customer", "text": f"message {index}"}],
            "intent": "general_support",
            "action": "request_clarification",
        }
        for index in range(30)
    ]


def test_audit_counts_conversations_and_prefixes() -> None:
    audit = audit_examples(_examples())
    assert audit["rows"] == 30
    assert audit["conversations"] == 15
    assert audit["prefix_rows"] == 15


def test_grouped_split_has_no_conversation_overlap() -> None:
    splits = split_examples(_examples(), seed=42)
    id_sets = [{example["conversation_id"] for example in examples} for examples in splits.values()]
    assert not id_sets[0] & id_sets[1]
    assert not id_sets[0] & id_sets[2]
    assert not id_sets[1] & id_sets[2]
    assert split_examples(_examples(), seed=42) == splits

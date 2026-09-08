from __future__ import annotations

import json

from op06.abcd import (
    build_benchmark_cases,
    build_policy_from_examples,
    extract_abcd_examples,
    prepare_abcd,
)


def _dataset() -> dict:
    return {
        "train": [
            {
                "convo_id": "train-1",
                "scenario": {"flow": "product_defect", "subflow": "return_size"},
                "delexed": [
                    {"speaker": "customer", "text": "I need a return", "targets": ["return_size", None, None]},
                    {"speaker": "agent", "text": "Can I see your order?", "targets": ["return_size", "retrieve_utterance", None]},
                    {"speaker": "action", "text": "validated", "targets": ["return_size", "take_action", "validate-purchase"]},
                ],
            },
            {
                "convo_id": "train-2",
                "scenario": {"flow": "shipping_issue", "subflow": "status"},
                "delexed": [
                    {"speaker": "customer", "text": "Track my order", "targets": ["status", None, None]},
                    {"speaker": "action", "text": "status found", "targets": ["status", "take_action", "shipping-status"]},
                ],
            },
        ]
    }


def test_extracts_only_action_prediction_points() -> None:
    rows = extract_abcd_examples(_dataset())["train"]
    assert len(rows) == 2
    assert rows[0]["conversation_id"] == "train-1"
    assert rows[0]["intent"] == "return_size"
    assert rows[0]["action"] == "validate-purchase"
    assert [turn["role"] for turn in rows[0]["conversation"]] == ["customer", "agent"]

    # The second action prefix can see the first completed action but never its
    # own future action.
    second_dataset = _dataset()
    second_dataset["train"][0]["delexed"].extend(
        [
            {"speaker": "customer", "text": "Thanks", "targets": ["return_size", None, None]},
            {"speaker": "action", "text": "notified", "targets": ["return_size", "take_action", "notify-team"]},
        ]
    )
    second_row = extract_abcd_examples(second_dataset)["train"][1]
    assert {turn["text"] for turn in second_row["conversation"]} >= {
        "[workflow action completed: validate-purchase]"
    }


def test_prepare_accepts_public_sample_list_shape(tmp_path) -> None:
    sample = _dataset()["train"]
    path = tmp_path / "abcd_sample.json"
    path.write_text(json.dumps(sample), encoding="utf-8")
    prepared = prepare_abcd(path)
    assert prepared.manifest["rows"] == {"train": 2}
    assert "return_size" in prepared.policy["intents"]
    assert "validate-purchase" in prepared.policy["actions"]


def test_generated_policy_limits_actions_by_intent() -> None:
    splits = extract_abcd_examples(_dataset())
    policy = build_policy_from_examples(splits, "a" * 64)
    rules = policy["workflows"]["return_size"]["rules"]
    assert rules == [{"action": "validate-purchase", "priority": 1}]


def test_generated_benchmark_cases_are_paired() -> None:
    examples = extract_abcd_examples(_dataset())["train"]
    cases = build_benchmark_cases(examples[:1])
    assert [case["type"] for case in cases] == ["clean", "noisy", "hostile"]
    assert cases[1]["pair_id"] == cases[0]["case_id"]
    assert cases[2]["needs_human"] is True

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from op06.api.schemas import TriageRequest
from op06.data_tools import iter_jsonl_files, load_jsonl
from op06.evaluation.metrics import (
    brier_score,
    classification_metrics,
    confidence_error_ratio,
    expected_calibration_error,
)
from op06.pipeline import TriagePipeline


@dataclass(frozen=True, slots=True)
class CaseResult:
    case_id: str
    intent_correct: bool
    action_correct: bool
    human_correct: bool
    schema_valid: bool
    confidence: float
    actual_intent: str
    actual_action: str
    actual_needs_human: bool

    @property
    def passed(self) -> bool:
        return (
            self.intent_correct and self.action_correct and self.human_correct and self.schema_valid
        )


def _request_from_case(case: dict[str, Any]) -> TriageRequest:
    payload: dict[str, Any] = {"conversation": case["conversation"]}
    if "context" in case:
        payload["context"] = case["context"]
    return TriageRequest.model_validate(payload)


def run_benchmark(path: Path, pipeline: TriagePipeline | None = None) -> dict[str, Any]:
    runtime = pipeline or TriagePipeline.build()
    cases: list[dict[str, Any]] = []
    for jsonl_path in iter_jsonl_files(path):
        cases.extend(load_jsonl(jsonl_path))
    requests = [_request_from_case(case) for case in cases]
    predictions = runtime.triage_many(requests)
    results: list[CaseResult] = []
    for index, (case, (response, _)) in enumerate(zip(cases, predictions, strict=True)):
        expected_human = case.get("needs_human")
        results.append(
            CaseResult(
                case_id=str(case.get("case_id", index)),
                intent_correct=response.intent == case["intent"],
                action_correct=response.action == case["action"],
                human_correct=expected_human is None or response.needs_human is expected_human,
                schema_valid=True,
                confidence=response.confidence,
                actual_intent=response.intent,
                actual_action=response.action,
                actual_needs_human=response.needs_human,
            )
        )
    expected_intents = [str(case["intent"]) for case in cases]
    expected_actions = [str(case["action"]) for case in cases]
    actual_intents = [result.actual_intent for result in results]
    actual_actions = [result.actual_action for result in results]
    intent_metrics = classification_metrics(expected_intents, actual_intents)
    action_metrics = classification_metrics(expected_actions, actual_actions)
    action_correct = [result.action_correct for result in results]
    confidences = [result.confidence for result in results]
    by_case_id = {result.case_id: result for result in results}
    paired = []
    for case, result in zip(cases, results, strict=True):
        pair_id = case.get("pair_id")
        clean = by_case_id.get(str(pair_id)) if pair_id is not None else None
        if clean is not None:
            paired.append(
                {
                    "case_id": result.case_id,
                    "pair_id": clean.case_id,
                    "intent_invariant": result.actual_intent == clean.actual_intent,
                    "action_invariant": result.actual_action == clean.actual_action,
                    "confidence_delta": result.confidence - clean.confidence,
                }
            )
    clean_indexes = [index for index, case in enumerate(cases) if case.get("type") == "clean"]
    noisy_indexes = [index for index, case in enumerate(cases) if case.get("type") == "noisy"]
    clean_action_accuracy = (
        sum(results[index].action_correct for index in clean_indexes) / len(clean_indexes)
        if clean_indexes
        else None
    )
    noisy_action_accuracy = (
        sum(results[index].action_correct for index in noisy_indexes) / len(noisy_indexes)
        if noisy_indexes
        else None
    )
    clean_to_noisy_gap = (
        max(0.0, clean_action_accuracy - noisy_action_accuracy)
        if clean_action_accuracy is not None and noisy_action_accuracy is not None
        else None
    )
    routed_indexes = [index for index, case in enumerate(cases) if "needs_human" in case]
    human_routing_accuracy = (
        sum(results[index].human_correct for index in routed_indexes) / len(routed_indexes)
        if routed_indexes
        else None
    )
    invalid_actions = sum(
        result.actual_action not in runtime.policy.actions
        or result.actual_action in runtime.policy.forbidden_actions
        for result in results
    )
    failed = [asdict(result) for result in results if not result.passed]
    failure_limit = 50
    pair_limit = 50
    return {
        "summary": {
            "cases": len(results),
            "passed": len(results) - len(failed),
            "failed": len(failed),
            "intent_accuracy": intent_metrics.accuracy,
            "intent_macro_f1": intent_metrics.macro_f1,
            "action_accuracy": action_metrics.accuracy,
            "action_macro_f1": action_metrics.macro_f1,
            "clean_action_accuracy": clean_action_accuracy,
            "noisy_action_accuracy": noisy_action_accuracy,
            "clean_to_noisy_action_gap": clean_to_noisy_gap,
            "paired_action_invariance": (
                sum(item["action_invariant"] for item in paired) / len(paired) if paired else None
            ),
            "human_routing_accuracy": human_routing_accuracy,
            "invalid_policy_action_rate": invalid_actions / len(results) if results else 0.0,
            "expected_calibration_error": expected_calibration_error(action_correct, confidences),
            "brier_score": brier_score(action_correct, confidences),
            "confidence_error_ratio": confidence_error_ratio(action_correct, confidences),
        },
        "failure_count_total": len(failed),
        "failures": failed[:failure_limit],
        "pair_count_total": len(paired),
        "pairs": paired[:pair_limit],
        "versions": {
            "model": runtime.intent_model.version,
            "action_model": runtime.action_ranker.version,
            "policy": runtime.policy.version,
        },
    }


def render_report(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True)

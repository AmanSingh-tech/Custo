from __future__ import annotations

from typing import Any


MVP_GATES = {
    "intent_accuracy": 0.55,
    "intent_macro_f1": 0.50,
    "action_accuracy": 0.55,
    "invalid_policy_action_rate": 0.01,
}


def evaluate_release_gates(summary: dict[str, Any]) -> dict[str, Any]:
    """Return machine-readable release-gate results for CI and promotion."""
    checks: dict[str, dict[str, Any]] = {}
    for metric, threshold in MVP_GATES.items():
        value = summary.get(metric)
        if value is None:
            checks[metric] = {"passed": False, "value": None, "threshold": threshold}
            continue
        passed = value <= threshold if metric.endswith("_rate") else value >= threshold
        checks[metric] = {"passed": passed, "value": value, "threshold": threshold}

    noisy_gap = summary.get("clean_to_noisy_action_gap")
    checks["clean_to_noisy_action_gap"] = {
        "passed": noisy_gap is not None and noisy_gap <= 0.10,
        "value": noisy_gap,
        "threshold": 0.10,
    }
    return {
        "passed": all(check["passed"] for check in checks.values()),
        "checks": checks,
        "note": "Confidence error ratio is intentionally not gated until the official scorer definition is supplied.",
    }

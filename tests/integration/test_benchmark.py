from pathlib import Path

from op06.benchmark import run_benchmark


def test_smoke_benchmark_passes() -> None:
    report = run_benchmark(Path("benchmark/cases/smoke.jsonl"))
    assert report["summary"]["cases"] == 8
    assert report["summary"]["failed"] == 0
    assert report["summary"]["intent_accuracy"] == 1.0
    assert report["summary"]["action_accuracy"] == 1.0
    assert report["summary"]["clean_to_noisy_action_gap"] == 0.0
    assert report["summary"]["paired_action_invariance"] == 1.0
    assert report["summary"]["invalid_policy_action_rate"] == 0.0

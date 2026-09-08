import pytest

from op06.evaluation.metrics import (
    brier_score,
    classification_metrics,
    expected_calibration_error,
)


def test_classification_metrics_perfect() -> None:
    result = classification_metrics(["a", "b", "a"], ["a", "b", "a"])
    assert result.accuracy == 1.0
    assert result.macro_f1 == 1.0


def test_calibration_metrics() -> None:
    assert brier_score([True, False], [1.0, 0.0]) == 0.0
    assert expected_calibration_error([True, False], [1.0, 0.0]) == 0.0


def test_metrics_reject_mismatched_lengths() -> None:
    with pytest.raises(ValueError):
        classification_metrics(["a"], [])

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ClassificationMetrics:
    accuracy: float
    macro_f1: float
    support: int


def classification_metrics(expected: Sequence[str], predicted: Sequence[str]) -> ClassificationMetrics:
    if len(expected) != len(predicted):
        raise ValueError("expected and predicted must have equal lengths")
    if not expected:
        return ClassificationMetrics(0.0, 0.0, 0)
    labels = sorted(set(expected) | set(predicted))
    f1_scores: list[float] = []
    for label in labels:
        true_positive = sum(e == label and p == label for e, p in zip(expected, predicted, strict=True))
        false_positive = sum(e != label and p == label for e, p in zip(expected, predicted, strict=True))
        false_negative = sum(e == label and p != label for e, p in zip(expected, predicted, strict=True))
        precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
        recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        f1_scores.append(f1)
    correct = sum(e == p for e, p in zip(expected, predicted, strict=True))
    return ClassificationMetrics(correct / len(expected), sum(f1_scores) / len(f1_scores), len(expected))


def expected_calibration_error(
    correct: Sequence[bool], confidences: Sequence[float], bins: int = 10
) -> float:
    if len(correct) != len(confidences):
        raise ValueError("correct and confidences must have equal lengths")
    if bins <= 0:
        raise ValueError("bins must be positive")
    if not correct:
        return 0.0
    total = len(correct)
    error = 0.0
    for index in range(bins):
        lower = index / bins
        upper = (index + 1) / bins
        members = [
            item
            for item, confidence in enumerate(confidences)
            if lower <= confidence < upper or (index == bins - 1 and confidence == 1.0)
        ]
        if not members:
            continue
        accuracy = sum(correct[item] for item in members) / len(members)
        mean_confidence = sum(confidences[item] for item in members) / len(members)
        error += len(members) / total * abs(accuracy - mean_confidence)
    return error


def brier_score(correct: Sequence[bool], confidences: Sequence[float]) -> float:
    if len(correct) != len(confidences):
        raise ValueError("correct and confidences must have equal lengths")
    if not correct:
        return 0.0
    return sum((confidence - float(outcome)) ** 2 for outcome, confidence in zip(correct, confidences, strict=True)) / len(correct)


def confusion_counts(expected: Sequence[str], predicted: Sequence[str]) -> dict[str, int]:
    return dict(Counter(f"{actual} -> {guess}" for actual, guess in zip(expected, predicted, strict=True)))


def finite_unit_interval(value: float) -> bool:
    return math.isfinite(value) and 0.0 <= value <= 1.0


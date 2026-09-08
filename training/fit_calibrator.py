"""Fit a serializable temperature calibration artifact on a held-out split."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import joblib


def _load_rows(path: Path) -> list[dict[str, Any]]:
    rows = [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    if not rows:
        raise ValueError("Calibration input is empty")
    return rows


def _serialize(turns: list[dict[str, Any]]) -> str:
    selected = turns if len(turns) <= 8 else [turns[0], *turns[-7:]]
    return "\n".join(
        json.dumps(
            {"role": str(turn["role"]), "text": str(turn["text"])},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        for turn in selected
    )


def _calibrate(probability: float, temperature: float) -> float:
    bounded = min(1.0 - 1e-7, max(1e-7, probability))
    logit = math.log(bounded / (1.0 - bounded))
    return 1.0 / (1.0 + math.exp(-logit / temperature))


def _brier(probabilities: list[float], correct: list[bool], temperature: float) -> float:
    return sum(
        (_calibrate(probability, temperature) - float(outcome)) ** 2
        for probability, outcome in zip(probabilities, correct, strict=True)
    ) / len(probabilities)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fit OP-06 temperature calibration")
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()

    artifact = joblib.load(args.model)
    pipeline = artifact.get("action_pipeline")
    if pipeline is None:
        raise ValueError("Model bundle has no action_pipeline")
    rows = _load_rows(args.input)
    texts = [_serialize(row["conversation"]) for row in rows]
    expected = [str(row.get("action", row.get("next_action"))) for row in rows]
    probabilities = pipeline.predict_proba(texts)
    predicted = [str(pipeline.classes_[row.argmax()]) for row in probabilities]
    max_probabilities = [float(row.max()) for row in probabilities]
    correct = [actual == guess for actual, guess in zip(expected, predicted, strict=True)]
    candidates = [round(value / 20, 2) for value in range(5, 81)]
    temperature = min(candidates, key=lambda value: _brier(max_probabilities, correct, value))
    artifact["calibration"] = {
        "method": "temperature_brier_grid",
        "temperature": temperature,
        "rows": len(rows),
        "uncalibrated_brier": _brier(max_probabilities, correct, 1.0),
        "calibrated_brier": _brier(max_probabilities, correct, temperature),
    }
    joblib.dump(artifact, args.model)
    print(json.dumps(artifact["calibration"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

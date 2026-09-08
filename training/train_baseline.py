from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.pipeline import FeatureUnion, Pipeline


def _load(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if line.strip():
                row = json.loads(line)
                for field in ("conversation", "intent"):
                    if field not in row:
                        raise ValueError(f"{path}:{line_number}: missing {field}")
                if "action" not in row and "next_action" not in row:
                    raise ValueError(f"{path}:{line_number}: missing action or next_action")
                rows.append(row)
    if len(rows) < 4:
        raise ValueError("At least four training examples are required")
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


def _classifier(seed: int) -> Pipeline:
    features = FeatureUnion(
        [
            (
                "word",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    min_df=2,
                    max_features=80_000,
                    sublinear_tf=True,
                ),
            ),
            (
                "character",
                TfidfVectorizer(
                    analyzer="char_wb",
                    ngram_range=(3, 5),
                    min_df=3,
                    max_features=80_000,
                    sublinear_tf=True,
                ),
            ),
        ]
    )
    return Pipeline(
        [
            ("features", features),
            (
                "classifier",
                SGDClassifier(
                    loss="log_loss",
                    alpha=1e-5,
                    max_iter=1_000,
                    tol=1e-3,
                    early_stopping=True,
                    validation_fraction=0.1,
                    n_iter_no_change=5,
                    class_weight="balanced",
                    n_jobs=-1,
                    random_state=seed,
                ),
            ),
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Train reproducible TF-IDF OP-06 baselines")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rows = _load(args.input)
    texts = [_serialize(row["conversation"]) for row in rows]
    intents = [str(row["intent"]) for row in rows]
    actions = [str(row.get("action", row.get("next_action"))) for row in rows]
    if len(set(intents)) < 2 or len(set(actions)) < 2:
        raise ValueError("Training requires at least two intent and two action classes")
    intent_pipeline = _classifier(args.seed).fit(texts, intents)
    action_pipeline = _classifier(args.seed).fit(texts, actions)
    artifact = {
        "schema_version": "1",
        "model_version": "tfidf-sgd-0.2.0",
        "seed": args.seed,
        "training_rows": len(rows),
        "training_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
        "intent_pipeline": intent_pipeline,
        "action_pipeline": action_pipeline,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, args.output)
    print(
        json.dumps(
            {key: value for key, value in artifact.items() if "pipeline" not in key}, indent=2
        )
    )


if __name__ == "__main__":
    main()

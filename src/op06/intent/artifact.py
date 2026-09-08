from __future__ import annotations

from pathlib import Path
from typing import Any

from op06.intent.interface import IntentPrediction
from op06.preprocessing.normalize import NormalizedConversation
from op06.preprocessing.serialize import serialize_conversation


class SklearnIntentClassifier:
    version = "tfidf-artifact-1"

    def __init__(self, artifact: dict[str, Any], path: Path) -> None:
        if artifact.get("schema_version") != "1":
            raise ValueError(f"Unsupported model artifact schema in {path}")
        self._pipeline = artifact["intent_pipeline"]
        self.version = str(artifact.get("model_version", self.version))

    def predict(self, conversation: NormalizedConversation) -> IntentPrediction:
        return self.predict_many([conversation])[0]

    def predict_many(self, conversations: list[NormalizedConversation]) -> list[IntentPrediction]:
        texts = [serialize_conversation(conversation) for conversation in conversations]
        probabilities_by_row = self._pipeline.predict_proba(texts)
        classes = [str(value) for value in self._pipeline.classes_]
        predictions: list[IntentPrediction] = []
        for probabilities in probabilities_by_row:
            scores = dict(zip(classes, (float(value) for value in probabilities), strict=True))
            ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
            label, confidence = ordered[0]
            second = ordered[1][1] if len(ordered) > 1 else 0.0
            predictions.append(IntentPrediction(label, confidence, scores, max(0.0, confidence - second)))
        return predictions


def load_artifact(path: Path) -> dict[str, Any]:
    import joblib

    artifact = joblib.load(path)
    if not isinstance(artifact, dict):
        raise ValueError("Model artifact must be a dictionary bundle")
    return artifact

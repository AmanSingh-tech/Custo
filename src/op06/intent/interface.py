from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from op06.preprocessing.normalize import NormalizedConversation


@dataclass(frozen=True, slots=True)
class IntentPrediction:
    label: str
    confidence: float
    scores: dict[str, float]
    margin: float


class IntentClassifier(Protocol):
    version: str

    def predict(self, conversation: NormalizedConversation) -> IntentPrediction: ...


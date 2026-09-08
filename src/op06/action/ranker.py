from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from op06.preprocessing.normalize import NormalizedConversation
from op06.preprocessing.serialize import serialize_conversation
from op06.state.schema import ConversationState


@dataclass(frozen=True, slots=True)
class ActionPrediction:
    label: str
    confidence: float
    scores: dict[str, float]
    margin: float


class RuleActionRanker:
    version = "policy-priority-0.1.0"

    def rank(
        self,
        candidates: tuple[str, ...],
        conversation: NormalizedConversation,
        intent: str,
        state: ConversationState,
    ) -> ActionPrediction:
        if not candidates:
            return ActionPrediction("escalate_human", 0.25, {"escalate_human": 1.0}, 0.0)
        del conversation, intent, state
        scores = {action: 1.0 / (index + 1) for index, action in enumerate(candidates)}
        total = sum(scores.values())
        probabilities = {label: value / total for label, value in scores.items()}
        label = candidates[0]
        ordered = sorted(probabilities.values(), reverse=True)
        margin = ordered[0] - ordered[1] if len(ordered) > 1 else ordered[0]
        confidence = 0.88 if len(candidates) == 1 else min(0.82, 0.58 + margin / 2)
        return ActionPrediction(label, confidence, probabilities, margin)


class SklearnActionRanker:
    version = "tfidf-action-artifact-1"

    def __init__(self, artifact: dict[str, Any]) -> None:
        self._pipeline = artifact["action_pipeline"]
        self.version = str(artifact.get("model_version", self.version))

    def rank(
        self,
        candidates: tuple[str, ...],
        conversation: NormalizedConversation,
        intent: str,
        state: ConversationState,
    ) -> ActionPrediction:
        return self.rank_many([candidates], [conversation], [intent], [state])[0]

    def rank_many(
        self,
        candidate_sets: list[tuple[str, ...]],
        conversations: list[NormalizedConversation],
        intents: list[str],
        states: list[ConversationState],
    ) -> list[ActionPrediction]:
        if not (
            len(candidate_sets) == len(conversations) == len(intents) == len(states)
        ):
            raise ValueError("Batch action-ranking inputs must have equal lengths")
        texts = [serialize_conversation(conversation) for conversation in conversations]
        probabilities_by_row = self._pipeline.predict_proba(texts)
        classes = [str(value) for value in self._pipeline.classes_]
        predictions: list[ActionPrediction] = []
        fallback = RuleActionRanker()
        for candidates, conversation, state, probabilities in zip(
            candidate_sets, conversations, states, probabilities_by_row, strict=True
        ):
            if not candidates:
                predictions.append(ActionPrediction("escalate_human", 0.25, {"escalate_human": 1.0}, 0.0))
                continue
            all_scores = dict(zip(classes, (float(value) for value in probabilities), strict=True))
            allowed = {label: all_scores.get(label, 0.0) for label in candidates}
            if not any(allowed.values()):
                predictions.append(fallback.rank(candidates, conversation, "", state))
                continue
            total = sum(allowed.values())
            scores = {label: value / total for label, value in allowed.items()}
            ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
            label, confidence = ordered[0]
            second = ordered[1][1] if len(ordered) > 1 else 0.0
            predictions.append(ActionPrediction(label, confidence, scores, max(0.0, confidence - second)))
        return predictions

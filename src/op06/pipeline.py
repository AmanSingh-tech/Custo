from __future__ import annotations

from dataclasses import dataclass

from op06.action.ranker import RuleActionRanker, SklearnActionRanker
from op06.api.schemas import TriageRequest, TriageResponse
from op06.confidence.calibrator import TemperatureCalibrator
from op06.confidence.escalation import EscalationDecision, decide_escalation
from op06.config import Settings
from op06.intent.artifact import SklearnIntentClassifier, load_artifact
from op06.intent.interface import IntentClassifier, IntentPrediction
from op06.intent.keyword import KeywordIntentClassifier
from op06.policy.compiler import CompiledPolicy, load_policy
from op06.policy.engine import PolicyDecision, PolicyEngine
from op06.preprocessing.normalize import NormalizedConversation, normalize_conversation
from op06.state.extractor import extract_state
from op06.state.schema import ConversationState


@dataclass(frozen=True, slots=True)
class TriageTrace:
    normalized: NormalizedConversation
    intent: IntentPrediction
    state: ConversationState
    policy: PolicyDecision
    escalation: EscalationDecision
    model_version: str
    action_model_version: str
    policy_version: str


class TriagePipeline:
    def __init__(
        self,
        settings: Settings,
        policy: CompiledPolicy,
        intent_model: IntentClassifier,
        action_ranker: RuleActionRanker | SklearnActionRanker,
        calibrator: TemperatureCalibrator | None = None,
    ) -> None:
        self.settings = settings
        self.policy = policy
        self.intent_model = intent_model
        self.action_ranker = action_ranker
        self.policy_engine = PolicyEngine(policy)
        self.calibrator = calibrator or TemperatureCalibrator()

    @classmethod
    def build(cls, settings: Settings | None = None) -> TriagePipeline:
        actual = settings or Settings.from_env()
        policy = load_policy(actual.policy_path)
        intent_model: IntentClassifier = KeywordIntentClassifier()
        action_ranker: RuleActionRanker | SklearnActionRanker = RuleActionRanker()
        calibrator = TemperatureCalibrator()
        if actual.model_path is not None:
            artifact = load_artifact(actual.model_path)
            intent_model = SklearnIntentClassifier(artifact, actual.model_path)
            if "action_pipeline" in artifact:
                action_ranker = SklearnActionRanker(artifact)
            calibration = artifact.get("calibration", {})
            if isinstance(calibration, dict) and isinstance(calibration.get("temperature"), (int, float)):
                calibrator = TemperatureCalibrator(float(calibration["temperature"]))
        elif not actual.allow_demo_model:
            raise RuntimeError(
                "No trained model configured. Set OP06_MODEL_PATH and OP06_POLICY_PATH for production, "
                "or explicitly set OP06_ALLOW_DEMO_MODEL=1 for the local demo."
            )
        return cls(actual, policy, intent_model, action_ranker, calibrator)

    def triage(self, request: TriageRequest) -> tuple[TriageResponse, TriageTrace]:
        normalized = normalize_conversation(request.conversation)
        state = extract_state(normalized)
        intent = self.intent_model.predict(normalized)
        selected_intent = intent.label if intent.label in self.policy.intents else "general_support"
        policy_decision = self.policy_engine.candidates(selected_intent, state)
        action = self.action_ranker.rank(
            policy_decision.candidates,
            normalized,
            selected_intent,
            state,
        )
        joint_probability = max(1e-7, min(1.0 - 1e-7, intent.confidence * action.confidence))
        confidence = self.calibrator.calibrate(joint_probability)
        escalation = decide_escalation(
            confidence=confidence,
            threshold=self.settings.confidence_threshold,
            intent_margin=intent.margin,
            action_margin=action.margin,
            selected_action=action.label,
            policy_valid=policy_decision.valid,
            safety_flags=normalized.safety_flags,
            contradictions=state.contradictions,
        )
        response = TriageResponse(
            intent=selected_intent,
            action=action.label,
            confidence=confidence,
            needs_human=escalation.needs_human,
        )
        trace = TriageTrace(
            normalized=normalized,
            intent=intent,
            state=state,
            policy=policy_decision,
            escalation=escalation,
            model_version=self.intent_model.version,
            action_model_version=self.action_ranker.version,
            policy_version=self.policy.version,
        )
        return response, trace

    def triage_many(self, requests: list[TriageRequest]) -> list[tuple[TriageResponse, TriageTrace]]:
        """Vectorized inference path used by corpus benchmark evaluation."""
        if not requests:
            return []
        normalized = [normalize_conversation(request.conversation) for request in requests]
        states = [extract_state(conversation) for conversation in normalized]
        if isinstance(self.intent_model, SklearnIntentClassifier):
            intents = self.intent_model.predict_many(normalized)
        else:
            intents = [self.intent_model.predict(conversation) for conversation in normalized]
        selected_intents = [
            prediction.label if prediction.label in self.policy.intents else "general_support"
            for prediction in intents
        ]
        policy_decisions = [
            self.policy_engine.candidates(intent, state)
            for intent, state in zip(selected_intents, states, strict=True)
        ]
        candidate_sets = [decision.candidates for decision in policy_decisions]
        if isinstance(self.action_ranker, SklearnActionRanker):
            actions = self.action_ranker.rank_many(candidate_sets, normalized, selected_intents, states)
        else:
            actions = [
                self.action_ranker.rank(candidates, conversation, intent, state)
                for candidates, conversation, intent, state in zip(
                    candidate_sets, normalized, selected_intents, states, strict=True
                )
            ]

        output: list[tuple[TriageResponse, TriageTrace]] = []
        for conversation, state, intent, selected_intent, policy_decision, action in zip(
            normalized, states, intents, selected_intents, policy_decisions, actions, strict=True
        ):
            joint_probability = max(1e-7, min(1.0 - 1e-7, intent.confidence * action.confidence))
            confidence = self.calibrator.calibrate(joint_probability)
            escalation = decide_escalation(
                confidence=confidence,
                threshold=self.settings.confidence_threshold,
                intent_margin=intent.margin,
                action_margin=action.margin,
                selected_action=action.label,
                policy_valid=policy_decision.valid,
                safety_flags=conversation.safety_flags,
                contradictions=state.contradictions,
            )
            response = TriageResponse(
                intent=selected_intent,
                action=action.label,
                confidence=confidence,
                needs_human=escalation.needs_human,
            )
            trace = TriageTrace(
                normalized=conversation,
                intent=intent,
                state=state,
                policy=policy_decision,
                escalation=escalation,
                model_version=self.intent_model.version,
                action_model_version=self.action_ranker.version,
                policy_version=self.policy.version,
            )
            output.append((response, trace))
        return output

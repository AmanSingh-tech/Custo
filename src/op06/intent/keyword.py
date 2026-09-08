from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from difflib import SequenceMatcher

from op06.intent.interface import IntentPrediction
from op06.preprocessing.normalize import NormalizedConversation


DEFAULT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "card_not_working": (
        "card not working",
        "card declined",
        "card rejected",
        "cannot use my card",
        "can't use my card",
        "card stopped",
    ),
    "card_payment_wrong_exchange_rate": (
        "wrong exchange rate",
        "exchange rate card",
        "card conversion",
        "foreign card payment",
        "currency conversion card",
    ),
    "cash_withdrawal_wrong_exchange_rate": (
        "atm exchange rate",
        "cash withdrawal exchange",
        "wrong cash conversion",
        "withdrawal conversion",
    ),
    "card_payment_not_recognised": (
        "card payment not mine",
        "do not recognize payment",
        "don't recognise payment",
        "unknown card payment",
        "unauthorized card payment",
    ),
    "cash_withdrawal_not_recognised": (
        "cash withdrawal not mine",
        "do not recognize withdrawal",
        "unknown atm withdrawal",
        "unauthorized withdrawal",
    ),
    "cash_withdrawal_issue": (
        "cash not received",
        "atm did not dispense",
        "cash withdrawal failed",
        "cash machine issue",
        "atm problem",
    ),
    "card_payment_reverted": (
        "card payment reversed",
        "card payment reverted",
        "reversed card transaction",
        "payment disappeared",
    ),
    "card_payment_fee_charged": (
        "card payment fee",
        "extra card charge",
        "charged a fee",
        "card surcharge",
    ),
    "card_delivery_tracking": (
        "where is my card",
        "track my card",
        "card delivery",
        "card has not arrived",
        "card hasn't arrived",
    ),
    "cash_withdrawal_fee_charged": (
        "atm fee",
        "cash withdrawal fee",
        "withdrawal charge",
        "charged for withdrawing",
    ),
    "cash_withdrawal_reverted": (
        "cash withdrawal reversed",
        "withdrawal reverted",
        "atm reversal",
    ),
    "cash_withdrawal_missing": (
        "cash withdrawal missing",
        "cash not showing",
        "withdrawal pending",
    ),
}
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "for",
        "has",
        "have",
        "i",
        "in",
        "is",
        "it",
        "my",
        "of",
        "on",
        "the",
        "this",
        "to",
        "was",
        "with",
    }
)


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[\w']+", value.casefold())) - _STOPWORDS


def _overlap_count(input_tokens: set[str], phrase_tokens: set[str]) -> int:
    matched = 0
    remaining = set(input_tokens)
    for expected in sorted(phrase_tokens, key=len, reverse=True):
        candidate = next(
            (
                actual
                for actual in remaining
                if actual == expected
                or (
                    len(actual) >= 5
                    and len(expected) >= 5
                    and SequenceMatcher(None, actual, expected).ratio() >= 0.8
                )
            ),
            None,
        )
        if candidate is not None:
            matched += 1
            remaining.remove(candidate)
    return matched


class KeywordIntentClassifier:
    """Safe cold-start model used until a trained artifact is supplied."""

    version = "keyword-0.1.0"

    def __init__(self, keywords: Mapping[str, Sequence[str]] | None = None) -> None:
        source = keywords or DEFAULT_KEYWORDS
        self._keywords = {label: tuple(values) for label, values in source.items()}

    def predict(self, conversation: NormalizedConversation) -> IntentPrediction:
        text = conversation.customer_text.casefold()
        input_tokens = _tokens(text)
        raw: dict[str, float] = {}
        for label, phrases in self._keywords.items():
            score = 0.0
            for phrase in phrases:
                phrase_lower = phrase.casefold()
                phrase_tokens = _tokens(phrase_lower)
                overlap_count = _overlap_count(input_tokens, phrase_tokens)
                overlap = overlap_count / max(1, len(phrase_tokens))
                if overlap_count >= min(2, len(phrase_tokens)):
                    score = max(score, overlap * 2.0)
                if phrase_lower in text:
                    score += 3.0 + min(1.0, len(phrase_tokens) / 4.0)
            raw[label] = score

        ordered = sorted(raw.items(), key=lambda item: (-item[1], item[0]))
        best_label, best_raw = ordered[0]
        second_raw = ordered[1][1] if len(ordered) > 1 else 0.0
        if best_raw < 0.8:
            return IntentPrediction("general_support", 0.34, {"general_support": 1.0}, 0.0)

        positive = {label: score for label, score in raw.items() if score > 0}
        exp_scores = {label: math.exp(min(score, 8.0) / 1.5) for label, score in positive.items()}
        denominator = sum(exp_scores.values()) or 1.0
        scores = {label: score / denominator for label, score in exp_scores.items()}
        confidence = min(0.96, 0.48 + best_raw / 10.0 + max(0.0, best_raw - second_raw) / 12.0)
        margin = min(1.0, max(0.0, (best_raw - second_raw) / max(1.0, best_raw)))
        return IntentPrediction(best_label, confidence, scores, margin)

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from op06.api.schemas import Turn

_BIDI_CONTROLS = frozenset(
    {
        "\u061c",
        "\u200e",
        "\u200f",
        "\u202a",
        "\u202b",
        "\u202c",
        "\u202d",
        "\u202e",
        "\u2066",
        "\u2067",
        "\u2068",
        "\u2069",
    }
)
_ZERO_WIDTH = frozenset({"\u200b", "\u200c", "\u200d", "\u2060", "\ufeff"})
_INJECTION_PATTERNS = (
    re.compile(r"\bignore\s+(all\s+)?(previous|prior|system)\s+instructions?\b", re.I),
    re.compile(r"\b(system|developer)\s+prompt\b", re.I),
    re.compile(r"\b(output|return|emit)\s+(the\s+)?(label|json|action|intent)\b", re.I),
    re.compile(r"<\s*/?\s*(system|assistant|developer)\s*>", re.I),
)
_FAKE_ROLE = re.compile(r"(?im)^\s*(system|developer|assistant|customer|agent)\s*:")
_WHITESPACE = re.compile(r"[\t\v\f \u00a0]+")


@dataclass(frozen=True, slots=True)
class NormalizedTurn:
    role: str
    text: str


@dataclass(frozen=True, slots=True)
class NormalizedConversation:
    turns: tuple[NormalizedTurn, ...]
    safety_flags: frozenset[str]

    @property
    def customer_text(self) -> str:
        return " ".join(turn.text for turn in self.turns if turn.role == "customer")

    @property
    def all_text(self) -> str:
        return " ".join(turn.text for turn in self.turns)


def _clean_text(text: str, flags: set[str]) -> str:
    text = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    if any(char in _BIDI_CONTROLS for char in text):
        flags.add("bidi_control")
    if any(char in _ZERO_WIDTH for char in text):
        flags.add("zero_width")
    if "\x00" in text:
        flags.add("nul_character")

    cleaned: list[str] = []
    for char in text:
        category = unicodedata.category(char)
        if char in _BIDI_CONTROLS or char in _ZERO_WIDTH:
            continue
        if char == "\n":
            cleaned.append(char)
        elif category == "Cc":
            cleaned.append(" ")
        else:
            cleaned.append(char)
    value = "\n".join(_WHITESPACE.sub(" ", line).strip() for line in "".join(cleaned).split("\n"))
    return value.strip()


def normalize_conversation(turns: list[Turn]) -> NormalizedConversation:
    flags: set[str] = set()
    normalized: list[NormalizedTurn] = []
    for turn in turns:
        text = _clean_text(turn.text, flags)
        if _FAKE_ROLE.search(text):
            flags.add("role_delimiter")
        if any(pattern.search(text) for pattern in _INJECTION_PATTERNS):
            flags.add("instruction_injection")
        normalized.append(NormalizedTurn(role=turn.role.value, text=text))
    return NormalizedConversation(tuple(normalized), frozenset(flags))

from __future__ import annotations

import re

from op06.preprocessing.normalize import NormalizedConversation
from op06.state.schema import ConversationState

_TIME = re.compile(
    r"\b(today|yesterday|tonight|morning|afternoon|evening|last\s+(night|week|month)|"
    r"since|ago|on\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)|\d{1,2}[:/]\d{1,2})\b",
    re.I,
)
_ALTERNATE_TERMINAL = re.compile(
    r"\b(another|different|alternate|second)\s+(terminal|merchant|shop|store|machine|atm)\b|"
    r"\btried\s+(elsewhere|again)\b",
    re.I,
)
_TRANSACTION_DETAIL = re.compile(
    r"(?:[$£€₹]\s?\d)|(?:\b\d+(?:\.\d{1,2})?\s?(?:usd|eur|gbp|inr|dollars?|rupees?)\b)|"
    r"\b(merchant|transaction|payment)\s+(id|reference|date|amount|name)\b",
    re.I,
)
_ATM_DETAIL = re.compile(r"\b(atm|cash machine)\b.*\b(location|id|number|street|branch)\b", re.I)
_VERIFIED = re.compile(
    r"\b(verified|verification complete|identity confirmed|last four digits)\b", re.I
)
_RESOLVED = re.compile(r"\b(it works|working now|resolved|fixed|sorted)\b", re.I)
_NEGATION = re.compile(r"\b(no|not|never|didn['’]?t|have not|haven['’]?t)\b", re.I)


def extract_state(conversation: NormalizedConversation) -> ConversationState:
    text = conversation.all_text
    customer_text = conversation.customer_text
    last_agent = next(
        (turn.text for turn in reversed(conversation.turns) if turn.role == "agent"),
        None,
    )
    slots: dict[str, bool | str] = {
        "start_time_known": bool(_TIME.search(customer_text)),
        "alternate_terminal_attempted": bool(_ALTERNATE_TERMINAL.search(customer_text)),
        "transaction_details_known": bool(_TRANSACTION_DETAIL.search(customer_text)),
        "atm_details_known": bool(_ATM_DETAIL.search(customer_text)),
        "identity_verified": bool(_VERIFIED.search(text)),
        "issue_resolved": bool(_RESOLVED.search(customer_text)),
    }
    completed = tuple(key for key, value in slots.items() if value is True)
    pending = tuple(
        turn.text
        for index, turn in enumerate(conversation.turns)
        if turn.role == "agent"
        and turn.text.rstrip().endswith("?")
        and not any(later.role == "customer" for later in conversation.turns[index + 1 :])
    )
    contradictions: tuple[str, ...] = ()
    if _RESOLVED.search(customer_text) and _NEGATION.search(customer_text):
        contradictions = ("possible_resolution_contradiction",)
    return ConversationState(
        slots=slots,
        completed_steps=completed,
        pending_questions=pending,
        contradictions=contradictions,
        last_agent_text=last_agent,
        turn_index=len(conversation.turns) - 1,
    )

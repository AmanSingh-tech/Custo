from __future__ import annotations

import json

from op06.preprocessing.normalize import NormalizedConversation


def serialize_conversation(conversation: NormalizedConversation) -> str:
    """Serialize untrusted turns without allowing text to create role boundaries."""
    return "\n".join(
        json.dumps(
            {"role": turn.role, "text": turn.text},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        for turn in conversation.turns
    )

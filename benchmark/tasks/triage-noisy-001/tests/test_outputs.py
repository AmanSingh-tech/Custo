from __future__ import annotations

import json
import sys
from pathlib import Path


path = Path(sys.argv[1] if len(sys.argv) > 1 else "/workspace/result.json")
result = json.loads(path.read_text(encoding="utf-8"))
assert set(result) == {"intent", "action", "confidence", "needs_human"}
assert result["intent"] == "card_not_working"
assert result["action"] == "ask_when_issue_started"
assert isinstance(result["confidence"], (int, float)) and 0 <= result["confidence"] <= 1


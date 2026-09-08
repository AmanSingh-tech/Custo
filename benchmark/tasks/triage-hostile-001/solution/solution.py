from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

payload = Path("/task/conversation.json").read_bytes()
request = urllib.request.Request(
    os.getenv("TRIAGE_URL", "http://127.0.0.1:8000/triage"),
    data=payload,
    headers={"content-type": "application/json"},
)
with urllib.request.urlopen(request, timeout=10) as response:
    result = json.loads(response.read())
Path("/workspace/result.json").write_text(json.dumps(result), encoding="utf-8")

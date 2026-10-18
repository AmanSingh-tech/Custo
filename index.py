"""Vercel entrypoint for the hosted demo.

Vercel discovers a FastAPI instance named ``app`` in a root ``index.py``. This file
exists only for that deployment: it puts ``src/`` on the import path and enables the
demo model and pipeline trace unless the project's environment variables say otherwise.
Docker, Render, and local runs use ``op06.api.app:app`` directly and are unaffected.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
os.environ.setdefault("OP06_ALLOW_DEMO_MODEL", "1")
os.environ.setdefault("OP06_EXPOSE_TRACE", "1")

from op06.api.app import app  # noqa: E402

__all__ = ["app"]

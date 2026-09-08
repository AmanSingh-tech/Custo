from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = float(raw)
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between 0 and 1")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    service_name: str = "op06-triage"
    api_version: str = "1.0.0"
    schema_version: str = "1.0.0"
    max_request_bytes: int = 65_536
    confidence_threshold: float = 0.58
    policy_path: Path = PACKAGE_ROOT / "resources" / "policy.json"
    model_path: Path | None = None
    allow_demo_model: bool = False

    @classmethod
    def from_env(cls) -> Settings:
        model_value = os.getenv("OP06_MODEL_PATH")
        policy_value = os.getenv("OP06_POLICY_PATH")
        return cls(
            max_request_bytes=int(os.getenv("OP06_MAX_REQUEST_BYTES", "65536")),
            confidence_threshold=_float_env("OP06_CONFIDENCE_THRESHOLD", 0.58),
            policy_path=(
                Path(policy_value) if policy_value else PACKAGE_ROOT / "resources" / "policy.json"
            ),
            model_path=Path(model_value) if model_value else None,
            allow_demo_model=os.getenv("OP06_ALLOW_DEMO_MODEL", "").casefold()
            in {"1", "true", "yes"},
        )

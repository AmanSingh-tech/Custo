from __future__ import annotations

import math
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator


class Role(str, Enum):
    customer = "customer"
    agent = "agent"


class Turn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)

    role: Role
    text: Annotated[StrictStr, Field(min_length=1, max_length=8_000)]

    @field_validator("text")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must contain at least one non-whitespace character")
        return value


class RequestContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    locale: Annotated[StrictStr, Field(min_length=2, max_length=35)] | None = None
    channel: Annotated[StrictStr, Field(min_length=1, max_length=32)] | None = None


class TriageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation: Annotated[list[Turn], Field(min_length=1, max_length=8)]
    context: RequestContext | None = None


class TriageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: str
    action: str
    confidence: float
    needs_human: bool

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError("confidence must be a finite number between 0 and 1")
        return round(value, 4)


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


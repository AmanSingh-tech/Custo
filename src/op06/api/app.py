from __future__ import annotations

import logging
import time
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from op06 import __version__
from op06.api.schemas import (
    ErrorDetail,
    ErrorResponse,
    OfficialTriageRequest,
    TriageRequest,
    TriageResponse,
)
from op06.config import Settings
from op06.pipeline import TriagePipeline, TriageTrace

logger = logging.getLogger("op06.api")
settings = Settings.from_env()


@lru_cache(maxsize=1)
def get_pipeline() -> TriagePipeline:
    return TriagePipeline.build(settings)


app = FastAPI(
    title="OP-06 Triage Service",
    version=__version__,
    docs_url="/docs",
    redoc_url=None,
)
WEB_ROOT = Path(__file__).resolve().parents[1] / "web"
WEB_INDEX = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
_MEDIA_TYPES = {
    ".js": "application/javascript",
    ".css": "text/css",
    ".svg": "image/svg+xml",
}
# Assets are read once at import; the allowlist doubles as path-traversal protection.
WEB_ASSETS = {
    path.name: (path.read_text(encoding="utf-8"), _MEDIA_TYPES[path.suffix])
    for path in WEB_ROOT.iterdir()
    if path.suffix in _MEDIA_TYPES
}


@app.middleware("http")
async def request_boundary(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = request_id
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            too_large = int(content_length) > settings.max_request_bytes
        except ValueError:
            too_large = True
        if too_large:
            error = ErrorResponse(
                error=ErrorDetail(
                    code="payload_too_large",
                    message=f"Request body must be at most {settings.max_request_bytes} bytes",
                    request_id=request_id,
                )
            )
            return JSONResponse(status_code=413, content=error.model_dump())
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    response.headers["x-api-version"] = settings.api_version
    response.headers["x-schema-version"] = settings.schema_version
    response.headers["x-response-time-ms"] = f"{(time.perf_counter() - started) * 1000:.2f}"
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    del exc
    error = ErrorResponse(
        error=ErrorDetail(
            code="invalid_request",
            message="Request does not match the triage schema",
            request_id=getattr(request.state, "request_id", None),
        )
    )
    return JSONResponse(status_code=422, content=error.model_dump())


def _apply_version_headers(response: Response, pipeline: TriagePipeline) -> None:
    response.headers["x-model-version"] = pipeline.intent_model.version
    response.headers["x-action-model-version"] = pipeline.action_ranker.version
    response.headers["x-policy-version"] = pipeline.policy.version


@app.post(
    "/triage",
    responses={413: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def triage(payload: dict[str, Any], response: Response, request: Request) -> Any:
    pipeline = get_pipeline()
    official = False
    if isinstance(payload, dict):
        official = "id" in payload or isinstance(payload.get("context"), list)
        try:
            if official:
                parsed = OfficialTriageRequest.model_validate(payload)
                payload = parsed.to_internal()
            else:
                payload = TriageRequest.model_validate(payload)
        except Exception:
            error = ErrorResponse(
                error=ErrorDetail(
                    code="invalid_request",
                    message="Request does not match the triage schema",
                    request_id=getattr(request.state, "request_id", None),
                )
            )
            return JSONResponse(status_code=422, content=error.model_dump())
    if official and not any(turn.text.strip() for turn in payload.conversation):
        result = {
            "id": parsed.id,
            "intent": "unknown",
            "action": "none",
            "confidence": 0.0,
            "needs_human": True,
        }
        _apply_version_headers(response, pipeline)
        return result
    result, trace = pipeline.triage(payload)
    if official and trace.normalized.safety_flags:
        result = TriageResponse(intent="unknown", action="none", confidence=0.0, needs_human=True)
    _apply_version_headers(response, pipeline)
    logger.info(
        "triage request_id=%s intent=%s action=%s confidence=%.4f needs_human=%s flags=%s",
        getattr(request.state, "request_id", "unknown"),
        result.intent,
        result.action,
        result.confidence,
        result.needs_human,
        ",".join(sorted(trace.normalized.safety_flags)) or "none",
    )
    if official:
        return {"id": parsed.id, **result.model_dump()}
    return result


@app.post("/v1/triage", include_in_schema=False)
async def triage_v1(payload: dict[str, Any], response: Response, request: Request) -> Any:
    return await triage(payload, response, request)


def _trace_payload(
    trace: TriageTrace, threshold: float, forbidden: frozenset[str]
) -> dict[str, Any]:
    scores = sorted(trace.intent.scores.items(), key=lambda item: item[1], reverse=True)
    return {
        "normalized_turns": [
            {"role": turn.role, "text": turn.text} for turn in trace.normalized.turns
        ],
        "safety_flags": sorted(trace.normalized.safety_flags),
        "intent": {
            "label": trace.intent.label,
            "confidence": round(trace.intent.confidence, 4),
            "margin": round(trace.intent.margin, 4),
            "top_scores": [
                {"intent": label, "score": round(score, 4)} for label, score in scores[:5]
            ],
        },
        "state": {
            "slots": trace.state.slots,
            "pending_questions": list(trace.state.pending_questions),
            "contradictions": list(trace.state.contradictions),
            "turn_index": trace.state.turn_index,
        },
        "policy": {
            "candidates": list(trace.policy.candidates),
            "matched_rules": list(trace.policy.matched_rules),
            "valid": trace.policy.valid,
            "fallback_reason": trace.policy.fallback_reason,
            "forbidden_actions": sorted(forbidden),
        },
        "escalation": {
            "needs_human": trace.escalation.needs_human,
            "reasons": list(trace.escalation.reasons),
            "threshold": threshold,
        },
        "versions": {
            "model": trace.model_version,
            "action_model": trace.action_model_version,
            "policy": trace.policy_version,
        },
    }


@app.post("/demo/explain", include_in_schema=False)
async def demo_explain(payload: dict[str, Any], response: Response, request: Request) -> Any:
    """Demo-only view of the pipeline trace; disabled unless OP06_EXPOSE_TRACE is set."""
    if not settings.expose_trace:
        error = ErrorResponse(
            error=ErrorDetail(
                code="not_found",
                message="Trace endpoint is disabled",
                request_id=getattr(request.state, "request_id", None),
            )
        )
        return JSONResponse(status_code=404, content=error.model_dump())
    try:
        parsed = TriageRequest.model_validate(payload)
    except Exception:
        error = ErrorResponse(
            error=ErrorDetail(
                code="invalid_request",
                message="Request does not match the triage schema",
                request_id=getattr(request.state, "request_id", None),
            )
        )
        return JSONResponse(status_code=422, content=error.model_dump())
    pipeline = get_pipeline()
    result, trace = pipeline.triage(parsed)
    _apply_version_headers(response, pipeline)
    return {
        "result": result.model_dump(),
        "trace": _trace_payload(
            trace, settings.confidence_threshold, pipeline.policy.forbidden_actions
        ),
    }


@app.get("/health/live")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    get_pipeline()
    return {"status": "ok"}


@app.get("/health/ready")
async def readiness() -> dict[str, str]:
    pipeline = get_pipeline()
    return {"status": "ready", "policy_version": pipeline.policy.version}


@app.get("/version")
async def version() -> dict[str, str]:
    pipeline = get_pipeline()
    return {
        "service_version": __version__,
        "api_version": settings.api_version,
        "schema_version": settings.schema_version,
        "model_version": pipeline.intent_model.version,
        "action_model_version": pipeline.action_ranker.version,
        "policy_version": pipeline.policy.version,
    }


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse("/app/")


@app.get("/app", include_in_schema=False)
async def app_no_slash() -> RedirectResponse:
    return RedirectResponse("/app/")


@app.get("/app/", include_in_schema=False)
async def test_console() -> HTMLResponse:
    return HTMLResponse(WEB_INDEX)


@app.get("/app/{asset}", include_in_schema=False)
async def test_console_asset(asset: str) -> Response:
    if asset not in WEB_ASSETS:
        return JSONResponse(status_code=404, content={"error": {"code": "not_found"}})
    body, media_type = WEB_ASSETS[asset]
    return Response(body, media_type=media_type, headers={"cache-control": "no-cache"})

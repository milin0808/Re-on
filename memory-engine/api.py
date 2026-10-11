"""RE:ON internal stateless Memory Engine HTTP service (FastAPI).

Start locally with: python -m uvicorn api:app --host 127.0.0.1 --port 8000
"""
import os
from collections import Counter
from secrets import compare_digest

from fastapi import Depends, FastAPI, Header, HTTPException

from api_models import AnalysisRequest, AnalysisResponse
from core_adapter import CoreAnalysisRequest, adapt_core_request
from context_analyzer import month_key
from memory_generator import generate_memories
from models import ALGORITHM, ANALYSIS_TIMEZONE_NAME, ENGINE_VERSION, parse_moments
from sync import annotate_changes, missing_memory_ids

app = FastAPI(
    title="RE:ON Memory Engine API",
    description="Internal, stateless rule-based analysis API for Core Backend integration. No DB or LLM.",
    version=ENGINE_VERSION,
)


def verify_service_token(x_service_token: str | None = Header(default=None)) -> None:
    """For non-local deployment set REON_ENGINE_TOKEN; only localhost is safe without it."""
    expected = os.getenv("REON_ENGINE_TOKEN")
    if expected is None:
        return
    if not expected.isascii() or not expected.strip():
        raise HTTPException(status_code=503, detail="REON_ENGINE_TOKEN must be a non-empty ASCII token")
    if x_service_token is None or not x_service_token.isascii() or not compare_digest(x_service_token, expected):
        raise HTTPException(status_code=401, detail="Invalid internal service token")


@app.get("/health", tags=["operations"])
def health() -> dict[str, str]:
    return {"status": "ok", "engine_version": ENGINE_VERSION}


@app.post("/api/v1/memories/analyze", response_model=AnalysisResponse,
          dependencies=[Depends(verify_service_token)], tags=["analysis"])
def analyze(request: AnalysisRequest) -> dict:
    """Analyze **one user's** full applicable Moment history, no writes performed.

    Same memory_id + same content_hash -> UNCHANGED; changed content -> UPDATE.
    New pattern -> CREATE. Core Backend should upsert by memory_id, never plain insert.
    """
    try:
        moments = sorted(
            parse_moments({"moments": [m.model_dump() for m in request.moments]}),
            key=lambda m: (m.user_id, m.recorded_at, m.moment_id),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if len({m.user_id for m in moments}) > 1:
        raise HTTPException(status_code=422, detail="한 요청에는 한 사용자의 Moment만 포함할 수 있습니다.")

    owner = moments[0].user_id if moments else None
    if request.scope:
        owner = str(request.scope.user_id)
        if any(m.user_id != owner for m in moments):
            raise HTTPException(status_code=422, detail="scope.user_id와 Moment 사용자가 서로 다릅니다.")
        if any(month_key(m) not in request.scope.months for m in moments):
            raise HTTPException(status_code=422, detail="scope.months 밖의 Moment가 있습니다 (Asia/Seoul 기준).")

    existing = {}
    for entry in request.existing_memories:
        if entry.memory_id in existing:
            raise HTTPException(status_code=422, detail="existing_memories에 중복된 memory_id가 있습니다.")
        if owner is not None and entry.user_id is not None and str(entry.user_id) != owner:
            raise HTTPException(status_code=422, detail="다른 사용자의 existing_memories가 포함되어 있습니다.")
        if request.scope and (entry.user_id is None or entry.period_month is None):
            raise HTTPException(status_code=422, detail="scope 사용 시 기존 Memory의 user_id와 period_month가 필요합니다.")
        existing[entry.memory_id] = entry.content_hash if entry.is_active else None

    generated = generate_memories(moments)
    annotated = annotate_changes(generated, existing)
    # Omitted/partial scopes never authorize invalidating stored Memories.
    scoped_ids = [entry.memory_id for entry in request.existing_memories
                  if request.scope and entry.period_month in request.scope.months and entry.is_active]
    deactivated = missing_memory_ids(generated, scoped_ids)
    counts = Counter(m["sync_action"] for m in annotated)
    return {
        "meta": {
            "input_moments": len(moments),
            "generated_memories": len(annotated),
            "create_count": counts["CREATE"],
            "update_count": counts["UPDATE"],
            "unchanged_count": counts["UNCHANGED"],
            "deactivate_count": len(deactivated),
            "unknown_artist_moments": sum(m.artist is None for m in moments),
            "unresolved_track_moments": sum(m.track_id is None for m in moments),
            "analysis_timezone": ANALYSIS_TIMEZONE_NAME,
            "engine_version": ENGINE_VERSION,
            "algorithm": ALGORITHM,
        },
        "memories": annotated,
        "scope": request.scope.model_dump() if request.scope else None,
        "deactivated_memory_ids": deactivated,
    }


@app.post("/api/v1/memories/analyze/core", response_model=AnalysisResponse,
          dependencies=[Depends(verify_service_token)], tags=["analysis"])
def analyze_from_core(request: CoreAnalysisRequest) -> dict:
    """Accept proposed Core Moment envelopes with the real MusicResolveResponse fields.

    NOTE: Spring Boot does not yet expose a Moment CRUD endpoint; this is an
    integration-ready adapter, not a live database connection.
    """
    try:
        normalized = adapt_core_request(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return analyze(normalized)

"""RE:ON internal stateless Memory Engine HTTP service (FastAPI).

Start locally with: python -m uvicorn api:app --host 127.0.0.1 --port 8000
"""
import os
from collections import Counter
from secrets import compare_digest

from fastapi import Depends, FastAPI, Header, HTTPException

from api_models import AnalysisRequest, AnalysisResponse
from memory_generator import generate_memories
from models import parse_moments
from sync import annotate_changes

app = FastAPI(
    title="RE:ON Memory Engine API",
    description="Internal, stateless rule-based analysis API for Core Backend integration. No DB or LLM.",
    version="0.2.0",
)


def verify_service_token(x_service_token: str | None = Header(default=None)) -> None:
    """For non-local deployment set REON_ENGINE_TOKEN; only localhost is safe without it."""
    expected = os.getenv("REON_ENGINE_TOKEN")
    if expected and (x_service_token is None or not compare_digest(x_service_token, expected)):
        raise HTTPException(status_code=401, detail="Invalid internal service token")


@app.get("/health", tags=["operations"])
def health() -> dict[str, str]:
    return {"status": "ok", "engine_version": "0.2.0"}


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
            key=lambda m: (m.user_id, m.recorded_at.isoformat(), m.moment_id),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if len({m.user_id for m in moments}) > 1:
        raise HTTPException(status_code=422, detail="한 요청에는 한 사용자의 Moment만 포함할 수 있습니다.")

    existing = {}
    for entry in request.existing_memories:
        if entry.memory_id in existing:
            raise HTTPException(status_code=422, detail="existing_memories에 중복된 memory_id가 있습니다.")
        existing[entry.memory_id] = entry.content_hash

    generated = generate_memories(moments)
    annotated = annotate_changes(generated, existing)
    counts = Counter(m["sync_action"] for m in annotated)
    return {
        "meta": {
            "input_moments": len(moments),
            "generated_memories": len(annotated),
            "create_count": counts["CREATE"],
            "update_count": counts["UPDATE"],
            "unchanged_count": counts["UNCHANGED"],
            "engine_version": "0.2.0",
            "algorithm": "rules-v1",
        },
        "memories": annotated,
    }

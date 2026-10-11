"""HTTP request/response contracts for the internal RE:ON Memory Engine API.

The rule engine in models.py is the source of truth for Moment semantics.
"""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]


class MomentInput(BaseModel):
    """Core Backend supplies these records after reading its own Moment database."""

    model_config = ConfigDict(extra="forbid")
    moment_id: str | int
    user_id: str | int
    artist: NonBlank
    song_title: NonBlank
    recorded_at: str = Field(..., description="ISO 8601 including UTC offset, e.g. 2026-07-03T19:30:00+09:00")
    location: str | None = Field(default=None, max_length=255)
    memo: str | None = Field(default=None, max_length=2000)
    track_id: str | None = Field(default=None, max_length=255)


class ExistingMemory(BaseModel):
    """Snapshot of a Memory already persisted by the Spring Boot Core Backend."""

    model_config = ConfigDict(extra="forbid")
    memory_id: NonBlank
    content_hash: str | None = Field(
        default=None,
        pattern=r"^[a-f0-9]{64}$",
        description="SHA-256 content_hash returned by a previous analyze response; omit to force an UPDATE",
    )


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    moments: list[MomentInput] = Field(..., max_length=1000)
    existing_memories: list[ExistingMemory] = Field(default_factory=list, max_length=1000)


class ResponseMeta(BaseModel):
    input_moments: int
    generated_memories: int
    create_count: int
    update_count: int
    unchanged_count: int
    engine_version: str
    algorithm: str


class MemoryResult(BaseModel):
    memory_id: str
    user_id: str
    type: Literal["ARTIST", "LOCATION", "TIME"]
    title: str
    description: str
    period: dict
    moment_ids: list[str]
    tracks: list[dict]
    context: dict
    content_hash: str = Field(..., description="Deterministic SHA-256 of the underlying generated Memory")
    sync_action: Literal["CREATE", "UPDATE", "UNCHANGED"]


class AnalysisResponse(BaseModel):
    meta: ResponseMeta
    memories: list[MemoryResult]

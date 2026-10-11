"""HTTP request/response contracts for the internal RE:ON Memory Engine API.

The rule engine in models.py is the source of truth for Moment semantics.
"""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StringConstraints, field_validator, model_validator


NonBlank = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=255)]
Identifier = NonBlank | StrictInt
Month = Annotated[str, StringConstraints(strict=True, pattern=r"^[0-9]{4}-(0[1-9]|1[0-2])$")]
VideoId = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, pattern=r"^[A-Za-z0-9_-]{11}$")]


class AnalysisScope(BaseModel):
    """Authoritative full history for these user/months, including empty months.

    Core must reject a response when its history_revision is no longer current.
    """

    model_config = ConfigDict(extra="forbid")
    user_id: Identifier
    months: list[Month] = Field(..., min_length=1, max_length=120)
    complete_month_history: Literal[True]
    history_revision: StrictInt = Field(..., ge=0)

    @field_validator("complete_month_history", mode="before")
    @classmethod
    def explicit_completion(cls, value):
        if value is not True:
            raise ValueError("완전한 월별 기록일 때만 complete_month_history: true를 보낼 수 있습니다.")
        return value

    @model_validator(mode="after")
    def distinct_months(self):
        if len(self.months) != len(set(self.months)):
            raise ValueError("scope.months에 중복된 월이 있습니다.")
        self.months = sorted(self.months)
        return self


class MomentInput(BaseModel):
    """Core Backend supplies these records after reading its own Moment database."""

    model_config = ConfigDict(extra="forbid")
    moment_id: Identifier
    user_id: Identifier
    artist: NonBlank | None = None
    song_title: NonBlank
    recorded_at: str = Field(..., description="ISO 8601 including UTC offset, e.g. 2026-07-03T19:30:00+09:00")
    location: str | None = Field(default=None, max_length=255)
    memo: str | None = Field(default=None, max_length=2000)
    track_id: VideoId | None = None


class ExistingMemory(BaseModel):
    """Snapshot of a Memory already persisted by the Spring Boot Core Backend."""

    model_config = ConfigDict(extra="forbid")
    memory_id: NonBlank
    user_id: Identifier | None = None
    period_month: Month | None = None
    is_active: StrictBool = True
    content_hash: str | None = Field(
        default=None,
        pattern=r"^[a-f0-9]{64}$",
        description="SHA-256 content_hash returned by a previous analyze response; omit to force an UPDATE",
    )


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    moments: list[MomentInput] = Field(..., max_length=1000)
    existing_memories: list[ExistingMemory] = Field(default_factory=list, max_length=1000)
    scope: AnalysisScope | None = None


class ResponseMeta(BaseModel):
    input_moments: int
    generated_memories: int
    create_count: int
    update_count: int
    unchanged_count: int
    deactivate_count: int
    unknown_artist_moments: int
    unresolved_track_moments: int
    analysis_timezone: str
    engine_version: str
    algorithm: str


class TrackResult(BaseModel):
    track_id: VideoId
    artist: str | None
    song_title: str


class MemoryPeriod(BaseModel):
    month: Month
    start: str
    end: str


class MemoryResult(BaseModel):
    memory_id: str
    user_id: str
    type: Literal["ARTIST", "LOCATION", "TIME"]
    title: str
    description: str
    period: MemoryPeriod
    moment_ids: list[str]
    tracks: list[TrackResult]
    replay_available: bool
    context: dict
    content_hash: str = Field(..., description="Deterministic SHA-256 of the underlying generated Memory")
    sync_action: Literal["CREATE", "UPDATE", "UNCHANGED"]


class AnalysisResponse(BaseModel):
    meta: ResponseMeta
    memories: list[MemoryResult]
    scope: AnalysisScope | None
    deactivated_memory_ids: list[str]

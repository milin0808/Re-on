"""Adapter from Core Backend music metadata to the existing Memory Engine contract.

Only MusicResolveResponse(videoId, title, channelTitle, thumbnailUrl) is
implemented by Spring Boot as of this adapter's creation. The surrounding
Moment fields below are a PROPOSED integration envelope, not an existing Core
Backend endpoint.
"""
from __future__ import annotations

import re
import unicodedata

from pydantic import BaseModel, ConfigDict, Field

from api_models import AnalysisRequest, ExistingMemory, MomentInput, NonBlank


# Only explicit, verified display aliases should be added here. Do NOT equate
# YouTube channelTitle with artist, nor guess artist from a video's title.
ARTIST_ALIASES: dict[str, str] = {
    "아이유": "IU",
    "iu": "IU",
    "nct127": "NCT 127",
    "nct 127": "NCT 127",
}


def normalize_artist(artist: str | None, channel_title: str) -> str:
    """Prefer an explicit artist; otherwise accept only an '- Topic' channel.

    Generic channels such as SMTOWN/1theK are *not* reliable artist labels.
    Fail with a useful message rather than generating false artist memories.
    """
    source = artist
    if source is None:
        topic = re.fullmatch(r"(.+?)\s+-\s+Topic\s*", channel_title, flags=re.IGNORECASE)
        if not topic:
            raise ValueError(
                f"아티스트를 확인할 수 없습니다 (channelTitle={channel_title!r}). "
                "Moment에 정확한 artist를 추가해 주세요. channelTitle은 artist와 다를 수 있습니다."
            )
        source = topic.group(1)
    cleaned = " ".join(unicodedata.normalize("NFKC", source).split())
    if not cleaned:
        raise ValueError("artist는 비어 있을 수 없습니다.")
    return ARTIST_ALIASES.get(cleaned.casefold(), cleaned)


class CoreMusicMetadata(BaseModel):
    """Matches Spring Boot MusicResolveResponse exactly."""

    model_config = ConfigDict(extra="forbid")
    videoId: NonBlank
    title: NonBlank
    channelTitle: NonBlank
    thumbnailUrl: str | None = None


class CoreMomentInput(BaseModel):
    """Proposed Moment wrapper around Spring Boot's existing music response."""

    model_config = ConfigDict(extra="forbid")
    momentId: str | int
    userId: str | int
    recordedAt: str
    music: CoreMusicMetadata
    artist: NonBlank | None = None
    songTitle: NonBlank | None = None
    location: str | None = Field(default=None, max_length=255)
    memo: str | None = Field(default=None, max_length=2000)


class CoreAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    moments: list[CoreMomentInput] = Field(..., max_length=1000)
    existing_memories: list[ExistingMemory] = Field(default_factory=list, max_length=1000)


def adapt_core_request(payload: CoreAnalysisRequest) -> AnalysisRequest:
    """Convert proposed Core Moment JSON to current Memory Engine JSON."""
    normalized = []
    for m in payload.moments:
        normalized.append(MomentInput(
            moment_id=m.momentId,
            user_id=m.userId,
            artist=normalize_artist(m.artist, m.music.channelTitle),
            song_title=m.songTitle or m.music.title,
            recorded_at=m.recordedAt,
            track_id=m.music.videoId,
            location=m.location,
            memo=m.memo,
        ))
    return AnalysisRequest(moments=normalized,
                           existing_memories=payload.existing_memories)

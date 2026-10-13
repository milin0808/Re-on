"""Accept current Core music metadata and frontend Moment fields.

MusicResolveResponse is implemented; Core Moment CRUD is not yet implemented.
Upstream artist display names are preserved, without a private alias dictionary.
"""
from __future__ import annotations

import re

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator

from api_models import (
    AnalysisRequest, AnalysisScope, ExistingMemory, Identifier, MomentInput,
    NonBlank, VideoId,
)


def normalize_artist(artist: str | None, channel_title: str | None = None) -> str | None:
    """Use the supplied name; only an explicit '- Topic' channel is a fallback.

    Case/Unicode/space comparisons occur in the shared canonical() function.
    Generic YouTube channel names never become artists.
    """
    if artist is not None:
        return artist.strip() or None
    if channel_title:
        topic = re.fullmatch(r"(.+?)\s+-\s+Topic\s*", channel_title.strip(), re.IGNORECASE)
        if topic:
            return topic.group(1).strip() or None
    return None


class CoreMusicMetadata(BaseModel):
    """API v0.4 music fields and the existing MusicResolveResponse fields."""

    model_config = ConfigDict(extra="forbid")
    videoId: VideoId | None = None
    title: NonBlank
    artist: NonBlank | None = None
    channelTitle: NonBlank | None = None
    thumbnailUrl: str | None = None
    originalUrl: str | None = None


class CoreLocation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    latitude: float = Field(strict=True, ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(strict=True, ge=-180, le=180, allow_inf_nan=False)

    def label(self) -> str:
        # Approximate coordinate cells, not a reverse-geocoded venue or a distance radius.
        lat, lon = round(self.latitude, 3), round(self.longitude, 3)
        if lat == 0: lat = 0.0
        if lon == 0: lon = 0.0
        return f"위도 {lat:.3f}, 경도 {lon:.3f}"


class FrontTrack(BaseModel):
    """Current frontend Track plus optional Core-resolved videoId."""

    model_config = ConfigDict(extra="forbid")
    title: NonBlank
    artist: NonBlank | None = None
    albumCoverUrl: str | None = None
    videoId: VideoId | None = None


class CoreMomentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    momentId: Identifier = Field(validation_alias=AliasChoices("momentId", "id"))
    userId: Identifier | None = None
    recordedAt: str = Field(validation_alias=AliasChoices("recordedAt", "createdAt"))
    music: CoreMusicMetadata | None = None
    track: FrontTrack | None = None
    artist: NonBlank | None = None
    songTitle: NonBlank | None = None
    location: str | CoreLocation | None = None
    memo: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def music_or_track(self):
        if self.music is None and self.track is None:
            raise ValueError("Moment에는 music 또는 track이 필요합니다.")
        if isinstance(self.location, str) and len(self.location) > 255:
            raise ValueError("위치 문자열은 최대 255자입니다.")
        if self.music and self.music.videoId and self.track and self.track.videoId:
            if self.music.videoId != self.track.videoId:
                raise ValueError("music.videoId와 track.videoId가 서로 다릅니다.")
        return self


class CoreAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    userId: Identifier | None = None
    moments: list[CoreMomentInput] = Field(..., max_length=1000)
    existing_memories: list[ExistingMemory] = Field(default_factory=list, max_length=1000)
    scope: AnalysisScope | None = None


def adapt_core_request(payload: CoreAnalysisRequest) -> AnalysisRequest:
    normalized = []
    request_user = str(payload.userId) if payload.userId is not None else None
    scope_user = str(payload.scope.user_id) if payload.scope else None
    if request_user is not None and scope_user is not None and request_user != scope_user:
        raise ValueError("userId와 scope.user_id가 서로 다릅니다.")
    owner = request_user or scope_user
    for m in payload.moments:
        user_id = str(m.userId) if m.userId is not None else owner
        if user_id is None:
            raise ValueError("Core가 인증된 userId를 요청 또는 Moment에 채워야 합니다.")
        if owner is not None and user_id != owner:
            raise ValueError("Moment.userId와 요청 사용자 ID가 서로 다릅니다.")
        explicit_artist = m.artist or (m.track.artist if m.track else None) or (m.music.artist if m.music else None)
        artist = normalize_artist(explicit_artist, m.music.channelTitle if m.music else None)
        song_title = m.songTitle or (m.track.title if m.track else m.music.title)
        track_id = (m.music.videoId if m.music else None) or (m.track.videoId if m.track else None)
        location = m.location.label() if isinstance(m.location, CoreLocation) else m.location
        normalized.append(MomentInput(
            moment_id=m.momentId, user_id=user_id, artist=artist,
            song_title=song_title, recorded_at=m.recordedAt,
            track_id=track_id, location=location, memo=m.memo,
        ))
    return AnalysisRequest(moments=normalized, existing_memories=payload.existing_memories,
                           scope=payload.scope)

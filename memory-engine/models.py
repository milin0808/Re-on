"""RE:ON Moment input schema and validation (Python 3.10+)."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import re
from typing import Any

ENGINE_VERSION = "0.4.0"
ALGORITHM = "rules-v2"
ANALYSIS_TIMEZONE_NAME = "Asia/Seoul"
# Korean MVP: fixed UTC+09:00, also works on Windows without a tzdata install.
ANALYSIS_TIMEZONE = timezone(timedelta(hours=9), name=ANALYSIS_TIMEZONE_NAME)
YOUTUBE_VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}")


def analysis_datetime(moment: "Moment") -> datetime:
    return moment.recorded_at.astimezone(ANALYSIS_TIMEZONE)


@dataclass(frozen=True)
class Moment:
    moment_id: str
    user_id: str
    artist: str | None
    song_title: str
    recorded_at: datetime
    location: str | None = None
    memo: str | None = None
    track_id: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Moment":
        if not isinstance(data, dict):
            raise ValueError("Moment는 JSON 객체여야 합니다.")

        def required(key: str) -> str:
            value = data.get(key)
            if not isinstance(value, (str, int)) or isinstance(value, bool):
                raise ValueError(f"'{key}' 필드는 문자열 또는 정수여야 합니다.")
            result = str(value).strip()
            if not result:
                raise ValueError(f"'{key}' 필드가 비어 있습니다.")
            return result

        def optional(key: str) -> str | None:
            value = data.get(key)
            if value is None:
                return None
            if not isinstance(value, str):
                raise ValueError(f"'{key}' 필드는 문자열 또는 null이어야 합니다.")
            return value.strip() or None

        raw_date = required("recorded_at")
        try:
            dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"recorded_at은 ISO 8601 날짜/시간이어야 합니다: {raw_date}") from exc
        if dt.tzinfo is None or dt.utcoffset() is None:
            raise ValueError("recorded_at에는 시간대 정보가 필요합니다 (예: +09:00 또는 Z).")
        track_id = optional("track_id")
        if track_id is not None and not YOUTUBE_VIDEO_ID.fullmatch(track_id):
            raise ValueError("track_id는 11자리 YouTube videoId 또는 null이어야 합니다.")
        return cls(
            moment_id=required("moment_id"),
            user_id=required("user_id"),
            artist=optional("artist"),
            song_title=required("song_title"),
            recorded_at=dt,
            location=optional("location"),
            memo=optional("memo"),
            track_id=track_id,
        )


def parse_moments(payload: Any) -> list[Moment]:
    if not isinstance(payload, dict) or not isinstance(payload.get("moments"), list):
        raise ValueError('입력은 {"moments": [...]} 형식이어야 합니다.')
    moments = [Moment.from_dict(entry) for entry in payload["moments"]]
    seen: set[tuple[str, str]] = set()
    for moment in moments:
        key = (moment.user_id, moment.moment_id)
        if key in seen:
            raise ValueError(f"중복 Moment ID입니다: user={key[0]}, id={key[1]}")
        seen.add(key)
    return moments

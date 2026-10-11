"""Convert scored pattern candidates to RE:ON Memory JSON objects."""
from hashlib import sha256
from context_analyzer import TIME_LABELS, canonical, extract_context
from models import Moment
from pattern_detector import Candidate, DetectionConfig, detect_patterns


def _tracks(moments: tuple[Moment, ...]) -> list[dict]:
    result: list[dict] = []
    seen: set[tuple[str, ...]] = set()
    for m in moments:
        key = ("id", m.track_id) if m.track_id else ("title", canonical(m.artist), canonical(m.song_title))
        if key in seen:
            continue
        seen.add(key)
        result.append({"track_id": m.track_id, "artist": m.artist, "song_title": m.song_title})
    return result


def _with_particle(label: str) -> str:
    """Best-effort Korean 과/와 particle for display-only titles."""
    last = label.strip()[-1]
    if "가" <= last <= "힣":
        has_final_consonant = (ord(last) - 0xAC00) % 28 != 0
    elif last.isdigit():
        has_final_consonant = last in "013678"
    else:
        # Romanized names are ambiguous; prefer neutral '와' except often closed sounds.
        has_final_consonant = last.lower() in "kmnpt"
    return "과" if has_final_consonant else "와"


def create_memory(candidate: Candidate) -> dict:
    year, month = candidate.month.split("-")
    month_display = f"{int(month)}월"
    group = candidate.matched
    count = len(group)
    percent = round(candidate.share * 100)
    ctx = extract_context(list(group))

    if candidate.pattern_type == "ARTIST":
        title = f"{candidate.label}{_with_particle(candidate.label)} 함께한 {month_display}"
        desc = f"{month_display}에는 {candidate.label}의 음악을 {count}번 기록했어요. 해당 월 기록의 {percent}%예요."
    elif candidate.pattern_type == "LOCATION":
        title = f"{candidate.label}에서 들었던 {month_display}의 음악"
        desc = f"{month_display}에는 {candidate.label}에서 음악을 {count}번 기록했어요. 해당 월 기록의 {percent}%예요."
    else:
        label = TIME_LABELS[candidate.pattern_key]
        title = f"{month_display}의 {label} 플레이리스트"
        desc = f"{month_display}에는 {label} 시간대에 음악을 {count}번 기록했어요. 해당 월 기록의 {percent}%예요."

    if candidate.pattern_type != "TIME" and ctx["dominant_time_ratio"] >= 0.6:
        band = TIME_LABELS[ctx["dominant_time_band"]]
        desc += f" 이 중 {round(ctx['dominant_time_ratio'] * 100)}%가 {band} 시간대 기록이에요."
    if ctx["repeated_memo_keywords"]:
        keywords = ", ".join(f"'{k}'" for k in ctx["repeated_memo_keywords"])
        desc += f" 메모에는 {keywords} 표현이 반복됐어요."

    key = f"{candidate.user_id}|{candidate.month}|{candidate.pattern_type}|{candidate.pattern_key}"
    mid = "mem_" + sha256(key.encode("utf-8")).hexdigest()[:16]
    dates = [m.recorded_at.date().isoformat() for m in group]
    return {
        "memory_id": mid,
        "user_id": candidate.user_id,
        "type": candidate.pattern_type,
        "title": title,
        "description": desc,
        "period": {"month": candidate.month, "start": min(dates), "end": max(dates)},
        "moment_ids": [m.moment_id for m in group],
        "tracks": _tracks(group),
        "context": {
            "pattern_key": candidate.pattern_key,
            "count": count,
            "total_in_month": candidate.total_in_month,
            "share": candidate.share,
            "score": candidate.score,
            **ctx,
        },
    }


def generate_memories(moments: list[Moment], config: DetectionConfig | None = None) -> list[dict]:
    return [create_memory(c) for c in detect_patterns(moments, config)]

"""Context extraction. No AI API or external packages required."""
from collections import Counter
import re
import unicodedata
from models import Moment, analysis_datetime

MEMO_KEYWORDS = (
    "공연", "콘서트", "집 가는 길", "출근", "퇴근", "산책",
    "운동", "여행", "카페", "공부", "드라이브", "친구", "학교",
)
TIME_LABELS = {"DAWN": "새벽", "MORNING": "아침", "AFTERNOON": "오후", "EVENING": "저녁", "NIGHT": "밤"}


def canonical(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text).strip()).casefold()


def month_key(moment: Moment) -> str:
    return analysis_datetime(moment).strftime("%Y-%m")


def time_band(moment: Moment) -> str:
    hour = analysis_datetime(moment).hour
    if 5 <= hour < 12:
        return "MORNING"
    if 12 <= hour < 18:
        return "AFTERNOON"
    if 18 <= hour < 22:
        return "EVENING"
    if 22 <= hour < 24:
        return "NIGHT"
    return "DAWN"


def display_label(values: list[str]) -> str:
    counts = Counter(values)
    return min(counts, key=lambda label: (-counts[label], canonical(label), label))


def extract_context(moments: list[Moment]) -> dict:
    if not moments:
        return {"dominant_time_band": None, "dominant_time_ratio": 0.0,
                "top_location": None, "repeated_memo_keywords": []}
    bands = Counter(time_band(m) for m in moments)
    top_band, top_band_count = bands.most_common(1)[0]
    locations = [m.location for m in moments if m.location]
    groups: dict[str, list[str]] = {}
    for loc in locations:
        groups.setdefault(canonical(loc), []).append(loc)
    top_location = None
    if groups:
        most_common_loc = max(groups.values(), key=len)
        if len(most_common_loc) >= 2:
            top_location = display_label(most_common_loc)
    keyword_counts = Counter(
        keyword for m in moments for keyword in MEMO_KEYWORDS
        if m.memo and canonical(keyword) in canonical(m.memo)
    )
    repeated = [k for k, cnt in keyword_counts.most_common() if cnt >= 2]
    return {
        "dominant_time_band": top_band,
        "dominant_time_ratio": round(top_band_count / len(moments), 3),
        "top_location": top_location,
        "repeated_memo_keywords": repeated[:3],
    }

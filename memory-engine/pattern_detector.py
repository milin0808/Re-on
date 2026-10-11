"""Deterministic rule-based candidate detection with explainable scores."""
from collections import defaultdict
from dataclasses import dataclass
from context_analyzer import canonical, display_label, month_key, time_band
from models import Moment


@dataclass(frozen=True)
class DetectionConfig:
    artist_min_count: int = 3
    artist_min_share: float = 0.4
    location_min_count: int = 3
    location_min_share: float = 0.5
    time_min_count: int = 4
    time_min_share: float = 0.65
    max_memories_per_month: int = 3
    overlap_limit: float = 0.8


@dataclass(frozen=True)
class Candidate:
    user_id: str
    month: str
    pattern_type: str
    pattern_key: str
    label: str
    matched: tuple[Moment, ...]
    total_in_month: int
    share: float
    score: float


def _candidate(user_id: str, month: str, pattern_type: str,
               pattern_key: str, label: str, matched: list[Moment], total: int) -> Candidate:
    ordered = tuple(sorted(matched, key=lambda m: (m.recorded_at, m.moment_id)))
    share = len(ordered) / total
    # transparent ranking: relative frequency 65% + absolute count 35% (10 saturates)
    score = round(0.65 * share + 0.35 * min(len(ordered) / 10, 1), 4)
    return Candidate(user_id, month, pattern_type, pattern_key, label,
                     ordered, total, round(share, 4), score)


def detect_patterns(moments: list[Moment], config: DetectionConfig | None = None) -> list[Candidate]:
    cfg = config or DetectionConfig()
    if cfg.max_memories_per_month < 1:
        raise ValueError("max_memories_per_month는 1 이상이어야 합니다.")
    by_scope: dict[tuple[str, str], list[Moment]] = defaultdict(list)
    for m in moments:
        by_scope[(m.user_id, month_key(m))].append(m)

    output: list[Candidate] = []
    for (user_id, month), month_moments in sorted(by_scope.items()):
        total = len(month_moments)
        possibles: list[Candidate] = []

        artist_groups: dict[str, list[Moment]] = defaultdict(list)
        location_groups: dict[str, list[Moment]] = defaultdict(list)
        time_groups: dict[str, list[Moment]] = defaultdict(list)
        for m in month_moments:
            # Unknown artists still count toward the month's total and other contexts.
            if m.artist:
                artist_groups[canonical(m.artist)].append(m)
            if m.location:
                location_groups[canonical(m.location)].append(m)
            time_groups[time_band(m)].append(m)

        for key, group in artist_groups.items():
            if len(group) >= cfg.artist_min_count and len(group) / total >= cfg.artist_min_share:
                label = display_label([m.artist for m in group if m.artist])
                possibles.append(_candidate(user_id, month, "ARTIST", key, label, group, total))

        for key, group in location_groups.items():
            if len(group) >= cfg.location_min_count and len(group) / total >= cfg.location_min_share:
                label = display_label([m.location for m in group if m.location])
                possibles.append(_candidate(user_id, month, "LOCATION", key, label, group, total))

        for key, group in time_groups.items():
            if len(group) >= cfg.time_min_count and len(group) / total >= cfg.time_min_share:
                possibles.append(_candidate(user_id, month, "TIME", key, key, group, total))

        priority = {"ARTIST": 0, "LOCATION": 1, "TIME": 2}
        # Specific memories are more meaningful than a generic time-of-day group.
        # Rank ARTIST/LOCATION before TIME, then use the explainable score.
        possibles.sort(key=lambda c: (priority[c.pattern_type], -c.score, -len(c.matched), c.pattern_key))
        selected: list[Candidate] = []
        for candidate in possibles:
            current = {m.moment_id for m in candidate.matched}
            too_similar = False
            for prev in selected:
                previous = {m.moment_id for m in prev.matched}
                if len(current & previous) / len(current | previous) >= cfg.overlap_limit:
                    too_similar = True
                    break
            if not too_similar:
                selected.append(candidate)
                if len(selected) >= cfg.max_memories_per_month:
                    break
        output.extend(selected)
    return output

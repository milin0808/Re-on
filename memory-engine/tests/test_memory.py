import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from context_analyzer import extract_context, time_band
from memory_generator import generate_memories
from models import Moment, parse_moments
from pattern_detector import DetectionConfig, detect_patterns


def m(n: int, artist="NCT 127", user="u1", date="2026-07-03T19:30:00+09:00", **extra):
    return Moment.from_dict({"moment_id": str(n), "user_id": user, "song_title": f"song-{n}",
                             "artist": artist, "recorded_at": date, **extra})


class SchemaTests(unittest.TestCase):
    def test_timezone_is_required(self):
        with self.assertRaisesRegex(ValueError, "시간대"):
            m(1, date="2026-07-03T19:30:00")

    def test_duplicate_moment_id_rejected_per_user(self):
        sample = {"moments": [self._asdict(m(1)), self._asdict(m(1))]}
        with self.assertRaisesRegex(ValueError, "중복"):
            parse_moments(sample)

    def test_same_id_across_users_is_allowed(self):
        a = self._asdict(m(1, user="u1"))
        b = self._asdict(m(1, user="u2"))
        self.assertEqual(len(parse_moments({"moments": [a, b]})), 2)

    @staticmethod
    def _asdict(moment):
        return {"moment_id": moment.moment_id, "user_id": moment.user_id,
                "artist": moment.artist, "song_title": moment.song_title,
                "recorded_at": moment.recorded_at.isoformat()}


class ContextTests(unittest.TestCase):
    def test_time_bands(self):
        self.assertEqual(time_band(m(1, date="2026-07-03T04:00:00+09:00")), "DAWN")
        self.assertEqual(time_band(m(1, date="2026-07-03T08:00:00+09:00")), "MORNING")
        self.assertEqual(time_band(m(1, date="2026-07-03T16:00:00+09:00")), "AFTERNOON")
        self.assertEqual(time_band(m(1, date="2026-07-03T20:00:00+09:00")), "EVENING")
        self.assertEqual(time_band(m(1, date="2026-07-03T23:00:00+09:00")), "NIGHT")

    def test_memo_mentions_are_never_invented(self):
        items = [m(1, memo="공연 생각"), m(2, memo="공연 너무 좋았다"), m(3, memo="산책")]
        ctx = extract_context(items)
        self.assertEqual(ctx["repeated_memo_keywords"], ["공연"])

    def test_missing_location_is_ok(self):
        ctx = extract_context([m(1), m(2)])
        self.assertIsNone(ctx["top_location"])


class PatternTests(unittest.TestCase):
    def test_artist_memory_generated(self):
        items = [m(1), m(2), m(3), m(4, artist="IU")]
        memories = generate_memories(items)
        artists = [x for x in memories if x["type"] == "ARTIST"]
        self.assertEqual(len(artists), 1)
        self.assertEqual(artists[0]["moment_ids"], ["1", "2", "3"])
        self.assertEqual(artists[0]["context"]["total_in_month"], 4)

    def test_sparse_data_no_memories(self):
        items = [m(1), m(2, artist="IU"), m(3, artist="BTS")]
        self.assertEqual(generate_memories(items), [])

    def test_never_mix_users(self):
        items = [m(1, user="u1"), m(2, user="u1"), m(3, user="u2"), m(4, user="u2")]
        self.assertEqual(generate_memories(items), [])

    def test_different_months_separate(self):
        items = [m(i, date="2026-07-03T19:00:00+09:00") for i in range(1, 4)]
        items += [m(i, date="2026-08-03T19:00:00+09:00") for i in range(4, 7)]
        artist = [x for x in generate_memories(items) if x["type"] == "ARTIST"]
        self.assertEqual(len(artist), 2)
        self.assertNotEqual(artist[0]["memory_id"], artist[1]["memory_id"])

    def test_artist_spelling_normalization(self):
        items = [m(1, artist="NCT 127"), m(2, artist=" nct   127 "), m(3, artist="NCT 127")]
        artist = [x for x in generate_memories(items) if x["type"] == "ARTIST"]
        self.assertEqual(len(artist), 1)
        self.assertEqual(artist[0]["context"]["count"], 3)

    def test_overlap_suppresses_duplicate_memory(self):
        # All three are evening artist X, so TIME would duplicate ARTIST.
        items = [m(i) for i in range(1, 5)]
        self.assertEqual(len(generate_memories(items)), 1)

    def test_tracks_deduplicate_by_track_id(self):
        items = [m(1, track_id="TESTTRACK01"), m(2, track_id="TESTTRACK01"), m(3, track_id="TESTTRACK02")]
        result = generate_memories(items)
        self.assertEqual(len(result[0]["tracks"]), 2)

    def test_stable_id_after_new_moment(self):
        first = [m(1), m(2), m(3)]
        after = first + [m(4)]
        self.assertEqual(generate_memories(first)[0]["memory_id"], generate_memories(after)[0]["memory_id"])

    def test_explicit_threshold(self):
        items = [m(1), m(2), m(3)]
        cfg = DetectionConfig(artist_min_count=4)
        self.assertEqual(detect_patterns(items, cfg), [])

    def test_sample_data(self):
        source = Path(__file__).resolve().parents[1] / "data" / "sample_moments.json"
        moments = parse_moments(json.loads(source.read_text(encoding="utf-8")))
        self.assertEqual(len(moments), 20)
        memories = generate_memories(moments)
        self.assertGreaterEqual(len(memories), 2)
        self.assertIn("NCT 127과 함께한 7월", [x["title"] for x in memories])
        self.assertIn("IU와 함께한 8월", [x["title"] for x in memories])
        for memory in memories:
            ids = set(memory["moment_ids"])
            owner_ids = {m.moment_id for m in moments if m.user_id == memory["user_id"]}
            self.assertTrue(ids <= owner_ids)
            self.assertLessEqual(memory["context"]["share"], 1)


if __name__ == "__main__":
    unittest.main()

import unittest
from pydantic import ValidationError
from core_adapter import CoreAnalysisRequest, adapt_core_request


class ApiV04Tests(unittest.TestCase):
    def payload(self, **changes):
        moment = {"id": 101, "recordedAt": "2026-07-03T18:20:00+09:00",
                  "music": {"videoId": "wJhWwt1OmT8", "title": "Live Forever", "artist": "Oasis",
                            "thumbnailUrl": None, "originalUrl": "https://music.youtube.com/watch?v=wJhWwt1OmT8"},
                  "memo": None, "location": {"latitude": 37.45001, "longitude": 127.12801}}
        moment.update(changes)
        return {"userId": 1, "moments": [moment]}

    def test_v04_music_and_coordinate_location(self):
        moment = adapt_core_request(CoreAnalysisRequest.model_validate(self.payload())).moments[0]
        self.assertEqual(moment.artist, "Oasis")
        self.assertEqual(moment.location, "위도 37.450, 경도 127.128")
        self.assertEqual(moment.track_id, "wJhWwt1OmT8")

    def test_unresolved_music_remains_analyzable(self):
        moment = adapt_core_request(CoreAnalysisRequest.model_validate(self.payload(
            music={"title": "곡", "artist": None}, location=None))).moments[0]
        self.assertIsNone(moment.artist)
        self.assertIsNone(moment.track_id)

    def test_existing_channel_contract_still_works(self):
        moment = adapt_core_request(CoreAnalysisRequest.model_validate(self.payload(
            music={"videoId": "wJhWwt1OmT8", "title": "곡", "channelTitle": "Oasis - Topic"},
            location="카페"))).moments[0]
        self.assertEqual(moment.artist, "Oasis")
        self.assertEqual(moment.location, "카페")

    def test_explicit_music_artist_wins_over_topic(self):
        moment = adapt_core_request(CoreAnalysisRequest.model_validate(self.payload(
            music={"videoId": "wJhWwt1OmT8", "title": "곡", "artist": "원본 이름", "channelTitle": "Other - Topic"}))).moments[0]
        self.assertEqual(moment.artist, "원본 이름")

    def test_invalid_coordinates_are_rejected(self):
        for location in ({"latitude": 91, "longitude": 127}, {"latitude": 37, "longitude": -181},
                         {"latitude": True, "longitude": 127}, {"latitude": "37", "longitude": 127},
                         {"latitude": float("nan"), "longitude": 127}, {"latitude": 37}):
            with self.subTest(location=location), self.assertRaises(ValidationError):
                CoreAnalysisRequest.model_validate(self.payload(location=location))

    def test_negative_zero_cells_are_normalized(self):
        moment = adapt_core_request(CoreAnalysisRequest.model_validate(self.payload(
            location={"latitude": -0.00001, "longitude": 0}))).moments[0]
        self.assertEqual(moment.location, "위도 0.000, 경도 0.000")

    def test_overlong_legacy_location_rejected(self):
        with self.assertRaises(ValidationError):
            CoreAnalysisRequest.model_validate(self.payload(location="가" * 256))


if __name__ == "__main__": unittest.main()

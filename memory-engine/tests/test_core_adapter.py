"""Core Backend adapter tests: python -m unittest discover -s tests -v"""
import copy
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from api import app  # noqa: E402
from core_adapter import normalize_artist  # noqa: E402


class CoreAdapterTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.body = json.loads((ROOT / "examples" / "core_request.json").read_text(encoding="utf-8"))

    def post(self, payload=None):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("REON_ENGINE_TOKEN", None)
            return self.client.post("/api/v1/memories/analyze/core", json=payload if payload is not None else self.body)

    def test_core_endpoint_is_in_swagger(self):
        self.assertIn("/api/v1/memories/analyze/core", self.client.get("/openapi.json").json()["paths"])

    def test_core_input_generates_artist_memory(self):
        response = self.post()
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data["meta"]["input_moments"], 5)
        memory = next(m for m in data["memories"] if m["type"] == "ARTIST")
        self.assertEqual(memory["title"], "NCT 127과 함께한 7월")
        self.assertEqual(len(memory["moment_ids"]), 4)
        self.assertEqual(memory["tracks"][0]["track_id"], "TESTTRACK01")

    def test_explicit_artist_wins_over_channel(self):
        self.assertEqual(normalize_artist("아이유", "SMTOWN"), "아이유")
        self.assertEqual(normalize_artist("NCT127", "SMTOWN"), "NCT127")

    def test_topic_channel_is_accepted_when_artist_missing(self):
        self.assertEqual(normalize_artist(None, " IU - Topic "), "IU")
        self.assertEqual(normalize_artist(None, " NCT 127 - topic "), "NCT 127")

    def test_generic_channel_does_not_become_artist(self):
        body = copy.deepcopy(self.body)
        del body["moments"][0]["artist"]
        body["moments"][0]["music"]["channelTitle"] = "SMTOWN"
        result = self.post(body)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()["meta"]["unknown_artist_moments"], 1)
        artist_memories = [m for m in result.json()["memories"] if m["type"] == "ARTIST"]
        self.assertTrue(all(m["context"]["pattern_key"] != "smtown" for m in artist_memories))

    def test_song_title_override_vs_youtube_title(self):
        body = copy.deepcopy(self.body)
        body["moments"][0]["songTitle"] = "Fact Check"
        body["moments"][0]["music"]["title"] = "Fact Check (Official Video)"
        result = self.post(body)
        self.assertEqual(result.status_code, 200, result.text)
        tracks = next(m for m in result.json()["memories"] if m["type"] == "ARTIST")["tracks"]
        self.assertEqual(tracks[0]["song_title"], "Fact Check")

    def test_old_endpoint_is_unchanged(self):
        original = json.loads((ROOT / "examples" / "request.json").read_text(encoding="utf-8"))
        response = self.client.post("/api/v1/memories/analyze", json=original)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["meta"]["generated_memories"], 2)

    def test_repeated_request_can_be_unchanged(self):
        first = self.post().json()
        snapshot = [{"memory_id": m["memory_id"], "content_hash": m["content_hash"]}
                    for m in first["memories"]]
        body = {**self.body, "existing_memories": snapshot}
        second = self.post(body)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(second.json()["meta"]["unchanged_count"], len(snapshot))

    def test_mixed_users_rejected(self):
        body = copy.deepcopy(self.body)
        body["moments"][1]["userId"] = "another-user"
        self.assertEqual(self.post(body).status_code, 422)

    def test_missing_timezone_rejected(self):
        body = copy.deepcopy(self.body)
        body["moments"][0]["recordedAt"] = "2026-07-03T19:30:00"
        self.assertEqual(self.post(body).status_code, 422)

    def test_service_token_protects_new_endpoint(self):
        with patch.dict(os.environ, {"REON_ENGINE_TOKEN": "secret-test-token"}):
            a = self.client.post("/api/v1/memories/analyze/core", json=self.body)
            b = self.client.post("/api/v1/memories/analyze/core", json=self.body,
                                 headers={"X-Service-Token": "secret-test-token"})
        self.assertEqual(a.status_code, 401)
        self.assertEqual(b.status_code, 200)


if __name__ == "__main__":
    unittest.main()

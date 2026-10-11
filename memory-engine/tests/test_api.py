"""Run all tests: python -m unittest discover -s tests -v"""
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


class FastAPITests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.request = json.loads((ROOT / "examples" / "request.json").read_text(encoding="utf-8"))

    def analyze(self, payload=None):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("REON_ENGINE_TOKEN", None)
            return self.client.post("/api/v1/memories/analyze", json=payload or self.request)

    def test_health(self):
        self.assertEqual(self.client.get("/health").json()["status"], "ok")

    def test_openapi_documents_analyze_endpoint(self):
        data = self.client.get("/openapi.json").json()
        self.assertIn("/api/v1/memories/analyze", data["paths"])

    def test_demo_generates_two_artist_memories(self):
        response = self.analyze()
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(result["meta"]["input_moments"], 20)
        self.assertEqual(result["meta"]["generated_memories"], 2)
        self.assertEqual(result["meta"]["create_count"], 2)
        self.assertEqual({m["type"] for m in result["memories"]}, {"ARTIST"})
        self.assertTrue(all(len(m["content_hash"]) == 64 for m in result["memories"]))

    def test_second_call_with_snapshot_is_unchanged(self):
        first = self.analyze().json()
        snapshot = [{"memory_id": m["memory_id"], "content_hash": m["content_hash"]}
                    for m in first["memories"]]
        second = self.analyze({**self.request, "existing_memories": snapshot})
        self.assertEqual(second.status_code, 200)
        result = second.json()
        self.assertEqual(result["meta"]["create_count"], 0)
        self.assertEqual(result["meta"]["update_count"], 0)
        self.assertEqual(result["meta"]["unchanged_count"], 2)
        self.assertEqual({m["sync_action"] for m in result["memories"]}, {"UNCHANGED"})

    def test_changed_content_marks_update_with_stable_memory_id(self):
        first = self.analyze().json()
        snapshot = [{"memory_id": m["memory_id"], "content_hash": m["content_hash"]}
                    for m in first["memories"]]
        altered = json.loads(json.dumps(self.request))
        altered["existing_memories"] = snapshot
        altered["moments"].append({"moment_id": "new-song", "user_id": "demo_user_1",
                                  "artist": "NCT 127", "song_title": "New Single",
                                  "recorded_at": "2026-07-18T18:00:00+09:00"})
        result = self.analyze(altered).json()
        older = {m["memory_id"]: m for m in first["memories"]}
        updated = [m for m in result["memories"] if m["sync_action"] == "UPDATE"]
        self.assertGreaterEqual(len(updated), 1)
        self.assertTrue(all(m["memory_id"] in older for m in updated))
        self.assertTrue(any("new-song" in m["moment_ids"] for m in updated))

    def test_snapshot_id_without_hash_forces_update(self):
        first = self.analyze().json()
        snapshot = [{"memory_id": m["memory_id"]} for m in first["memories"]]
        response = self.analyze({**self.request, "existing_memories": snapshot})
        self.assertEqual(response.json()["meta"]["update_count"], 2)

    def test_request_order_does_not_change_hash(self):
        orig = self.analyze().json()
        reversed_request = {**self.request, "moments": list(reversed(self.request["moments"]))}
        other = self.analyze(reversed_request).json()
        digest_map = lambda obj: {m["memory_id"]: m["content_hash"] for m in obj["memories"]}
        self.assertEqual(digest_map(orig), digest_map(other))

    def test_empty_moments_ok(self):
        res = self.analyze({"moments": []})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["memories"], [])

    def test_reject_mixed_users(self):
        payload = {"moments": [self.request["moments"][0],
                               {**self.request["moments"][1], "user_id": "some-other-user"}]}
        response = self.analyze(payload)
        self.assertEqual(response.status_code, 422)
        self.assertIn("한 사용자", response.json()["detail"])

    def test_duplicate_input_ids_rejected(self):
        m = self.request["moments"][0]
        response = self.analyze({"moments": [m, m]})
        self.assertEqual(response.status_code, 422)

    def test_duplicate_existing_ids_rejected(self):
        existing = {"memory_id": "mem_foo"}
        response = self.analyze({"moments": [], "existing_memories": [existing, existing]})
        self.assertEqual(response.status_code, 422)

    def test_timestamp_without_timezone_rejected(self):
        m = {**self.request["moments"][0], "recorded_at": "2026-07-03T19:30:00"}
        response = self.analyze({"moments": [m]})
        self.assertEqual(response.status_code, 422)

    def test_invalid_schema_returns_422(self):
        self.assertEqual(self.analyze({"moments": "not-a-list"}).status_code, 422)
        self.assertEqual(self.analyze({"moments": [{}]}).status_code, 422)
        self.assertEqual(self.analyze({"moments": [], "unexpected": 1}).status_code, 422)

    def test_excessive_moment_count_rejected(self):
        self.assertEqual(self.analyze({"moments": [self.request["moments"][0]] * 1001}).status_code, 422)

    def test_optional_service_token_blocks_bad_requests(self):
        with patch.dict(os.environ, {"REON_ENGINE_TOKEN": "local-test-secret"}):
            no_token = self.client.post("/api/v1/memories/analyze", json={"moments": []})
            bad_token = self.client.post("/api/v1/memories/analyze", json={"moments": []},
                                         headers={"X-Service-Token": "bad"})
            accepted = self.client.post("/api/v1/memories/analyze", json={"moments": []},
                                        headers={"X-Service-Token": "local-test-secret"})
        self.assertEqual(no_token.status_code, 401)
        self.assertEqual(bad_token.status_code, 401)
        self.assertEqual(accepted.status_code, 200)


if __name__ == "__main__":
    unittest.main()

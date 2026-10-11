"""Regression coverage for service/adapter failures and scoped synchronization."""
import copy
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api import app, verify_service_token
from memory_generator import generate_memories
from models import Moment
from sync import memory_content_hash

VIDEO = 'wJhWwt1OmT8'


def row(i, **changes):
    return dict(moment_id=str(i), user_id='u1', artist='아이유', song_title='밤편지',
                recorded_at='2026-07-03T19:30:00+09:00', track_id=VIDEO) | changes


def scope(months=None, **changes):
    return dict(user_id='u1', months=months or ['2026-07'],
                complete_month_history=True, history_revision=7) | changes


class RegressionTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {}, clear=False)
        self.env.start()
        os.environ.pop('REON_ENGINE_TOKEN', None)
        self.addCleanup(self.env.stop)
        self.client = TestClient(app)
        self.body = {'moments': [row(i) for i in range(1, 4)]}

    def post(self, body, core=False):
        return self.client.post('/api/v1/memories/analyze' + ('/core' if core else ''), json=body)

    def snapshot(self, output, **changes):
        return [{'memory_id': m['memory_id'], 'content_hash': m['content_hash'],
                 'user_id': m['user_id'], 'period_month': m['period']['month'], **changes}
                for m in output['memories']]

    def test_equivalent_utc_and_seoul_dates_have_identical_outputs(self):
        a = {'moments': [row(i, recorded_at='2026-08-01T00:30:00+09:00') for i in range(1, 4)]}
        b = {'moments': [row(i, recorded_at='2026-07-31T15:30:00Z') for i in range(1, 4)]}
        first, second = self.post(a).json(), self.post(b).json()
        self.assertEqual(first, second)
        m = first['memories'][0]
        self.assertEqual(m['period']['month'], '2026-08')
        self.assertEqual(m['period']['start'], '2026-08-01')
        self.assertEqual(m['context']['dominant_time_band'], 'DAWN')

    def test_non_ascii_config_fails_closed_without_500(self):
        os.environ['REON_ENGINE_TOKEN'] = '한글-token'
        response = self.post({'moments': []})
        self.assertEqual(response.status_code, 503)

    def test_non_ascii_request_token_returns_401(self):
        os.environ['REON_ENGINE_TOKEN'] = 'ascii-secret'
        with self.assertRaises(HTTPException) as error:
            verify_service_token('é')
        self.assertEqual(error.exception.status_code, 401)

    def test_blank_config_fails_closed(self):
        os.environ['REON_ENGINE_TOKEN'] = ''
        self.assertEqual(self.post({'moments': []}).status_code, 503)

    def test_boolean_and_float_ids_are_rejected_in_both_routes(self):
        for value in (True, False, 1.0):
            for key in ('user_id', 'moment_id'):
                with self.subTest(value=value, key=key):
                    self.assertEqual(self.post({'moments': [row(1, **{key: value})]}).status_code, 422)
            front = {'userId': value, 'moments': [{'id': '1', 'createdAt': row(1)['recorded_at'],
                     'track': {'title': 's', 'artist': 'a', 'albumCoverUrl': None}}]}
            self.assertEqual(self.post(front, core=True).status_code, 422)

    def test_unknown_artists_keep_time_and_location_analysis_and_denominator(self):
        items = [row(1), row(2), row(3), row(4, artist=None)]
        for item in items:
            item['location'] = '서울'
        result = self.post({'moments': items}).json()
        artist = next(m for m in result['memories'] if m['type'] == 'ARTIST')
        self.assertEqual(artist['context']['total_in_month'], 4)
        self.assertEqual(artist['context']['share'], .75)
        self.assertEqual(result['meta']['unknown_artist_moments'], 1)
        unknown_only = self.post({'moments': [row(i, artist=None, location='서울') for i in range(1, 5)]}).json()
        self.assertTrue(unknown_only['memories'])
        self.assertNotIn('ARTIST', {m['type'] for m in unknown_only['memories']})

    def test_frontend_fields_and_core_music_are_supported_without_alias_translation(self):
        frontend = {'userId': 'u1', 'moments': [{'id': str(i), 'createdAt': row(i)['recorded_at'],
                    'track': {'title': '밤편지', 'artist': '아이유', 'albumCoverUrl': None},
                    'music': {'videoId': VIDEO, 'title': '영상 제목', 'channelTitle': '1theK',
                              'thumbnailUrl': None}} for i in range(1, 4)]}
        a = self.post(self.body).json()
        b = self.post(frontend, core=True).json()
        self.assertEqual(a, b)
        self.assertEqual(a['memories'][0]['context']['pattern_key'], '아이유')

    def test_frontend_moments_without_video_id_can_be_analyzed(self):
        frontend = {'userId': 'u1', 'moments': [{'id': str(i), 'createdAt': row(i)['recorded_at'],
                    'track': {'title': '밤편지', 'artist': '아이유', 'albumCoverUrl': None}}
                    for i in range(1, 4)]}
        response = self.post(frontend, core=True)
        self.assertEqual(response.status_code, 200)
        memory = response.json()['memories'][0]
        self.assertFalse(memory['replay_available'])
        self.assertEqual(memory['tracks'], [])

    def test_core_conflicting_owner_and_video_ids_are_rejected(self):
        body = {'userId': 'u1', 'moments': [{'id': '1', 'userId': 'u2',
                 'createdAt': row(1)['recorded_at'], 'track': {'title': 's', 'artist': 'a'}}]}
        self.assertEqual(self.post(body, core=True).status_code, 422)
        body['moments'][0]['userId'] = 'u1'
        body['moments'][0]['track']['videoId'] = 'TESTTRACK01'
        body['moments'][0]['music'] = {'videoId': VIDEO, 'title': 's', 'channelTitle': 'c'}
        self.assertEqual(self.post(body, core=True).status_code, 422)

    def test_unresolved_track_does_not_duplicate_resolved_track(self):
        response = self.post({'moments': [row(1, track_id=None), row(2), row(3)]}).json()
        memory = response['memories'][0]
        self.assertEqual(len(memory['tracks']), 1)
        self.assertEqual(memory['tracks'][0]['track_id'], VIDEO)
        self.assertEqual(memory['context']['unresolved_track_moment_count'], 1)
        self.assertEqual(memory['moment_ids'], ['1', '2', '3'])

    def test_invalid_video_id_is_rejected(self):
        self.assertEqual(self.post({'moments': [row(1, track_id='not-video')]}).status_code, 422)

    def test_deleted_moment_invalidates_memory_only_with_complete_scope(self):
        first = self.post(self.body).json()
        old = self.snapshot(first)
        body = {'moments': self.body['moments'][:2], 'existing_memories': old}
        self.assertEqual(self.post(body).json()['deactivated_memory_ids'], [])
        body['scope'] = scope()
        response = self.post(body)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['deactivated_memory_ids'], [old[0]['memory_id']])
        self.assertEqual(response.json()['meta']['deactivate_count'], 1)
        self.assertEqual(response.json()['scope']['history_revision'], 7)

    def test_empty_scoped_month_invalidates_its_existing_memories(self):
        old = self.snapshot(self.post(self.body).json())
        response = self.post({'moments': [], 'existing_memories': old, 'scope': scope()})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['deactivated_memory_ids'], [old[0]['memory_id']])

    def test_other_months_and_inactive_memories_are_not_invalidated(self):
        first = self.post(self.body).json()
        old = self.snapshot(first)
        old += [{'memory_id': 'other-month', 'user_id': 'u1', 'period_month': '2026-08'}]
        response = self.post({'moments': [], 'existing_memories': old, 'scope': scope()}).json()
        self.assertEqual(response['deactivated_memory_ids'], [old[0]['memory_id']])
        old[0]['is_active'] = False
        self.assertEqual(self.post({'moments': [], 'existing_memories': old, 'scope': scope()})
                         .json()['deactivated_memory_ids'], [])

    def test_inactive_memory_can_be_reactivated_even_with_same_hash(self):
        old = self.snapshot(self.post(self.body).json(), is_active=False)
        result = self.post({**self.body, 'existing_memories': old, 'scope': scope()}).json()
        self.assertEqual(result['memories'][0]['sync_action'], 'UPDATE')
        self.assertEqual(result['deactivated_memory_ids'], [])

    def test_scope_requires_authoritative_snapshot_and_explicit_completion(self):
        old = self.snapshot(self.post(self.body).json())
        for key in ('user_id', 'period_month'):
            incomplete = copy.deepcopy(old)
            del incomplete[0][key]
            self.assertEqual(self.post({'moments': [], 'existing_memories': incomplete, 'scope': scope()})
                             .status_code, 422)
        for change in ({'complete_month_history': False}, {'complete_month_history': 1}, {'history_revision': True},
                       {'history_revision': -1}, {'months': ['2026-07', '2026-07']}):
            self.assertEqual(self.post({**self.body, 'scope': scope(**change)}).status_code, 422)

    def test_foreign_owner_and_outside_scope_are_rejected(self):
        self.assertEqual(self.post({**self.body, 'scope': scope(user_id='other')}).status_code, 422)
        self.assertEqual(self.post({**self.body, 'scope': scope(months=['2026-08'])}).status_code, 422)
        old = self.snapshot(self.post(self.body).json(), user_id='other')
        self.assertEqual(self.post({**self.body, 'existing_memories': old, 'scope': scope()}).status_code, 422)

    def test_direct_engine_order_has_stable_label_and_hash(self):
        items = [Moment.from_dict(row(i, artist=a)) for i,a in enumerate(['IU','IU','iu','iu'],1)]
        a, b = generate_memories(items)[0], generate_memories(items[::-1])[0]
        self.assertEqual(a, b)
        self.assertEqual(memory_content_hash(a), memory_content_hash(b))


if __name__ == '__main__':
    unittest.main()

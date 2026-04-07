import json
import unittest
from unittest.mock import MagicMock, patch

from app.scene_store_postgres import PostgresSceneStore, _row_to_scene, _scene_to_row

_JSONB_KEYS = {'items', 'verbs', 'meta_json'}


def _simulate_pg_row(row):
    """Simulate what psycopg returns: jsonb columns parsed to Python objects."""
    return {k: json.loads(v) if k in _JSONB_KEYS and isinstance(v, str) else v for k, v in row.items()}


SAMPLE_PUBLIC_SCENE = {
    'sceneId': 'scene_breakfast',
    'title': '营养早餐',
    'category': 'food',
    'visibility': 'member',
    'sceneType': 'public',
    'coverPath': '/assets/images/breakfast.jpg',
    'backgroundPath': '/assets/images/breakfast.jpg',
    'items': [
        {
            'id': 'porridge',
            'word': 'porridge',
            'ipa': '/ˈpɒrɪdʒ/',
            'meaning': '粥',
            'sentence': 'I eat porridge for breakfast.',
            'sentenceTranslation': '我早餐吃粥。',
            'rect': {'l': 13.5, 't': 24.5, 'w': 50.2, 'h': 15.0},
            'audioPath': '/assets/audio/breakfast/porridge.mp3',
        },
    ],
    'verbs': [],
    'meta': {
        'sceneType': 'public',
        'visibility': 'member',
        'version': 1,
        'category': 'food',
        'tags': ['breakfast', 'food'],
    },
}

SAMPLE_GENERATED_SCENE = {
    'sceneId': 'scene_user_001',
    'title': 'My Room',
    'category': 'existing',
    'visibility': 'private',
    'sceneType': 'private',
    'coverPath': '/assets/generated/scene_user_001/background.jpg',
    'backgroundPath': '/assets/generated/scene_user_001/background.jpg',
    'items': [
        {'id': 'chair', 'word': 'chair', 'ipa': '/tʃer/', 'meaning': '椅子',
         'sentence': 'The chair is brown.', 'sentenceTranslation': '椅子是棕色的。',
         'rect': {'l': 10.0, 't': 20.0, 'w': 15.0, 'h': 10.0}},
    ],
    'verbs': [
        {'id': 'sit', 'word': 'sit', 'ipa': '/sɪt/', 'meaning': '坐',
         'sentence': 'Sit down please.', 'sentenceTranslation': '请坐下。'},
    ],
    'meta': {
        'sceneType': 'private',
        'visibility': 'private',
        'sourceType': 'upload',
        'ownerId': 'user_abc123',
        'uploadId': 'upload_001',
        'version': 1,
    },
}


class TestSceneToRow(unittest.TestCase):
    def test_public_scene_serialization(self):
        row = _scene_to_row(SAMPLE_PUBLIC_SCENE)
        self.assertEqual(row['scene_id'], 'scene_breakfast')
        self.assertEqual(row['title'], '营养早餐')
        self.assertEqual(row['category'], 'food')
        self.assertEqual(row['visibility'], 'member')
        self.assertEqual(row['scene_type'], 'public')
        self.assertIsNone(row['owner_id'])
        self.assertIsInstance(row['items'], str)
        self.assertIsInstance(row['verbs'], str)
        self.assertIsInstance(row['meta_json'], str)

    def test_generated_scene_serialization(self):
        row = _scene_to_row(SAMPLE_GENERATED_SCENE)
        self.assertEqual(row['scene_id'], 'scene_user_001')
        self.assertEqual(row['owner_id'], 'user_abc123')
        self.assertEqual(row['scene_type'], 'private')

    def test_missing_fields_get_defaults(self):
        row = _scene_to_row({'sceneId': 'empty_scene'})
        self.assertEqual(row['scene_id'], 'empty_scene')
        self.assertEqual(row['title'], '')
        self.assertEqual(row['category'], '')
        self.assertEqual(row['visibility'], 'public')
        self.assertEqual(row['scene_type'], 'public')
        self.assertEqual(row['items'], '[]')
        self.assertEqual(row['verbs'], '[]')
        self.assertEqual(row['meta_json'], '{}')
        self.assertIsNone(row['owner_id'])


class TestRowToScene(unittest.TestCase):
    def test_none_input(self):
        self.assertIsNone(_row_to_scene(None))

    def test_round_trip_public(self):
        row = _scene_to_row(SAMPLE_PUBLIC_SCENE)
        result = _row_to_scene(_simulate_pg_row(row))
        self.assertEqual(result['sceneId'], SAMPLE_PUBLIC_SCENE['sceneId'])
        self.assertEqual(result['title'], SAMPLE_PUBLIC_SCENE['title'])
        self.assertEqual(len(result['items']), len(SAMPLE_PUBLIC_SCENE['items']))
        self.assertEqual(result['meta']['tags'], ['breakfast', 'food'])

    def test_round_trip_generated(self):
        row = _scene_to_row(SAMPLE_GENERATED_SCENE)
        result = _row_to_scene(_simulate_pg_row(row))
        self.assertEqual(json.dumps(result, sort_keys=True),
                         json.dumps(SAMPLE_GENERATED_SCENE, sort_keys=True))


class TestPostgresSceneStoreListScenesFilter(unittest.TestCase):
    """Test the filter_param dispatch logic in list_scenes."""

    def setUp(self):
        self.mock_connect = patch.object(PostgresSceneStore, '_connect').start()
        self.mock_ensure = patch.object(PostgresSceneStore, '_ensure_ready').start()
        self.store = PostgresSceneStore.__new__(PostgresSceneStore)
        self.store.database_url = 'test'
        self.store.schema_name = 'public'
        self.addCleanup(patch.stopall)

    def _mock_cursor(self, rows=None):
        rows = rows or []
        cursor = MagicMock()
        cursor.fetchall.return_value = rows
        cursor.fetchone.return_value = rows[0] if rows else None
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        self.mock_connect.return_value.__enter__ = MagicMock(return_value=conn)
        self.mock_connect.return_value.__exit__ = MagicMock(return_value=False)
        return cursor

    def test_list_all_scenes(self):
        cursor = self._mock_cursor([])
        self.store.list_scenes()
        sql = cursor.execute.call_args[0][0]
        self.assertIn('order by created_at desc', sql)
        self.assertNotIn('where', sql)

    def test_list_by_scene_type_public(self):
        cursor = self._mock_cursor([])
        self.store.list_scenes('public')
        cursor.execute.assert_called_once()
        sql, params = cursor.execute.call_args[0]
        self.assertIn('scene_type', sql)
        self.assertEqual(params, ('public',))

    def test_list_by_scene_type_private(self):
        cursor = self._mock_cursor([])
        self.store.list_scenes('private')
        sql, params = cursor.execute.call_args[0]
        self.assertIn('scene_type', sql)
        self.assertEqual(params, ('private',))

    def test_list_by_owner_id(self):
        cursor = self._mock_cursor([])
        self.store.list_scenes('user_abc123')
        sql, params = cursor.execute.call_args[0]
        self.assertIn('owner_id', sql)
        self.assertEqual(params, ('user_abc123',))

    def test_list_by_scene_id_prefix(self):
        """scene_ prefixed values that look like scene types, not owner IDs."""
        cursor = self._mock_cursor([])
        self.store.list_scenes('scene_public')
        sql, params = cursor.execute.call_args[0]
        self.assertIn('scene_type', sql)


class TestPostgresSceneStoreGetScene(unittest.TestCase):
    def setUp(self):
        self.mock_connect = patch.object(PostgresSceneStore, '_connect').start()
        self.mock_ensure = patch.object(PostgresSceneStore, '_ensure_ready').start()
        self.store = PostgresSceneStore.__new__(PostgresSceneStore)
        self.store.database_url = 'test'
        self.store.schema_name = 'public'
        self.addCleanup(patch.stopall)

    def test_get_existing_scene(self):
        row = _scene_to_row(SAMPLE_PUBLIC_SCENE)
        cursor = MagicMock()
        cursor.fetchone.return_value = _simulate_pg_row(row)
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        self.mock_connect.return_value.__enter__ = MagicMock(return_value=conn)
        self.mock_connect.return_value.__exit__ = MagicMock(return_value=False)

        result = self.store.get_scene('scene_breakfast')
        self.assertIsNotNone(result)
        self.assertEqual(result['sceneId'], 'scene_breakfast')

    def test_get_missing_scene(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        self.mock_connect.return_value.__enter__ = MagicMock(return_value=conn)
        self.mock_connect.return_value.__exit__ = MagicMock(return_value=False)

        result = self.store.get_scene('nonexistent')
        self.assertIsNone(result)


class TestPostgresSceneStoreUpsert(unittest.TestCase):
    def setUp(self):
        self.mock_connect = patch.object(PostgresSceneStore, '_connect').start()
        self.mock_ensure = patch.object(PostgresSceneStore, '_ensure_ready').start()
        self.store = PostgresSceneStore.__new__(PostgresSceneStore)
        self.store.database_url = 'test'
        self.store.schema_name = 'public'
        self.addCleanup(patch.stopall)

    def test_upsert_returns_scene(self):
        row = _scene_to_row(SAMPLE_PUBLIC_SCENE)
        cursor = MagicMock()
        cursor.fetchone.return_value = _simulate_pg_row(row)
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        self.mock_connect.return_value.__enter__ = MagicMock(return_value=conn)
        self.mock_connect.return_value.__exit__ = MagicMock(return_value=False)

        result = self.store.upsert_scene(SAMPLE_PUBLIC_SCENE)
        self.assertEqual(result['sceneId'], 'scene_breakfast')
        self.assertEqual(result['title'], '营养早餐')


if __name__ == '__main__':
    unittest.main()

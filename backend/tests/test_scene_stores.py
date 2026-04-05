import json
import tempfile
import unittest
from pathlib import Path

from backend.app.generated_scene_store import GeneratedSceneStore
from backend.app.scene_store import SceneStore


class SceneStoreHotspotUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def write_json(self, name, payload):
        path = self.base_path / name
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        return path

    def test_public_scene_hotspot_update_clamps_and_updates_meta(self):
        store = SceneStore(self.write_json('scenes.json', {
            'scenes': [
                {
                    'sceneId': 'scene_breakfast',
                    'title': '早餐',
                    'items': [
                        {
                            'id': 'corn',
                            'rect': {
                                'l': 70,
                                't': 40,
                                'w': 20,
                                'h': 20,
                            }
                        }
                    ],
                    'meta': {
                        'version': 1
                    }
                }
            ]
        }))

        updated = store.update_hotspots(
            'scene_breakfast',
            [
                {
                    'id': 'corn',
                    'rect': {
                        'l': 95,
                        't': -5,
                        'w': 30,
                        'h': 3,
                    }
                }
            ],
            operator_id='debug_editor',
        )

        self.assertEqual(updated['items'][0]['rect'], {
            'l': 70.0,
            't': 0.0,
            'w': 30.0,
            'h': 4.0,
        })
        self.assertEqual(updated['meta']['version'], 2)
        self.assertEqual(updated['meta']['hotspotUpdatedBy'], 'debug_editor')
        self.assertTrue(updated['meta']['hotspotUpdatedAt'])

    def test_generated_scene_hotspot_update_persists_to_file(self):
        store = GeneratedSceneStore(self.write_json('generated_scenes.json', {
            'scenes': [
                {
                    'sceneId': 'scene_user_001',
                    'items': [
                        {
                            'id': 'television',
                            'rect': {
                                'l': 10,
                                't': 10,
                                'w': 20,
                                'h': 20,
                            }
                        }
                    ],
                    'meta': {
                        'ownerId': 'debug_user_001',
                        'version': 1
                    }
                }
            ]
        }))

        updated = store.update_hotspots(
            'scene_user_001',
            [
                {
                    'id': 'television',
                    'rect': {
                        'l': 12.5,
                        't': 18.25,
                        'w': 22.5,
                        'h': 26,
                    }
                }
            ],
            operator_id='debug_user_001',
        )

        self.assertEqual(updated['items'][0]['rect'], {
            'l': 12.5,
            't': 18.25,
            'w': 22.5,
            'h': 26.0,
        })

        reloaded = json.loads((self.base_path / 'generated_scenes.json').read_text(encoding='utf-8'))
        self.assertEqual(reloaded['scenes'][0]['items'][0]['rect']['l'], 12.5)
        self.assertEqual(reloaded['scenes'][0]['meta']['hotspotUpdatedBy'], 'debug_user_001')


if __name__ == '__main__':
    unittest.main()

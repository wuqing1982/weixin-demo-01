import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from backend.app.commerce_store import CommerceStore
from backend.app.generated_scene_store import GeneratedSceneStore
from backend.app.postgres import connect_postgres
from backend.app.scene_store import SceneStore
from backend.app.task_store import TaskStore
from backend.app.upload_store import UploadStore
from backend.app.worker_runner import InlineSceneWorker


DATABASE_URL = 'postgresql://weixin_saas:hq425771@localhost:5432/weixin_saas'


class WorkerAdminPublishTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.schema_name = f'worker_publish_{uuid4().hex[:12]}'
        root = Path(self.temp_dir.name)
        self.generated_root = root / 'generated'
        self.generated_root.mkdir(parents=True, exist_ok=True)
        self.upload_store = UploadStore(root / 'uploads.json', root / 'uploads')
        self.task_store = TaskStore(root / 'tasks.json')
        self.generated_store = GeneratedSceneStore(root / 'generated_scenes.json')
        self.public_store = SceneStore(root / 'public_scenes.json')
        self.commerce_store = CommerceStore(DATABASE_URL, self.schema_name)
        self.worker = InlineSceneWorker(
            task_store=self.task_store,
            upload_store=self.upload_store,
            generated_scene_store=self.generated_store,
            generated_root=self.generated_root,
            core100_root=root,
            tts_url='http://127.0.0.1:5003',
            model='glm-4v-flash',
            public_scene_store=self.public_store,
            commerce_store=self.commerce_store,
        )

    def tearDown(self):
        with connect_postgres(DATABASE_URL, 'public') as connection:
            with connection.cursor() as cursor:
                cursor.execute(f'drop schema if exists {self.schema_name} cascade')
        self.temp_dir.cleanup()

    def test_worker_can_auto_publish_generated_scene(self):
        self.commerce_store.upsert_scene_category({
            'id': 'scene_category_family_daily',
            'categoryCode': 'family_daily',
            'name': '家庭日常',
            'description': '',
            'status': 'active',
            'sortOrder': 1,
        })
        self.commerce_store.upsert_scene_collection({
            'id': 'scene_collection_breakfast',
            'collectionCode': 'breakfast',
            'name': '早餐合集',
            'description': '',
            'status': 'active',
            'coverUrl': '',
            'sortOrder': 1,
        })
        upload = self.upload_store.create_upload(
            owner_id='admin_console:admin_test',
            filename='kitchen.jpg',
            content_type='image/jpeg',
            content=b'fake-image-content',
        )
        task = self.task_store.create_task(
            owner_id='admin_console:admin_test',
            payload={
                'uploadId': upload['uploadId'],
                'title': '厨房早餐',
                'includeVerbs': True,
                'requestSource': 'admin_web_generator',
                'autoPublish': True,
                'categoryId': 'scene_category_family_daily',
                'collectionIds': ['scene_collection_breakfast'],
                'publishVisibility': 'public',
            },
        )

        self.worker._copy_source_image = lambda scene_id, upload_record: f'/assets/generated/{scene_id}/background.jpg'
        self.worker._analyze_scene = lambda **kwargs: {
            'scene_id': kwargs['scene_id'],
            'scene_title': kwargs['preferred_title'] or '厨房早餐',
            'recommended_category': 'generated',
            'hotspots': [{
                'id': 'kitchen_table',
                'word': 'table',
                'meaning': '桌子',
                'sentence': 'This is a table.',
                'sentenceTranslation': '这是一张桌子。',
                'rect': {'l': 10, 't': 10, 'w': 20, 'h': 20},
            }],
            'verbs': [],
        }
        self.worker._generate_audio = lambda *args, **kwargs: None
        self.worker._attach_audio_paths = lambda *args, **kwargs: None

        self.worker._process_task(task)

        finished = self.task_store.get_task(task['taskId'])
        self.assertEqual(finished['status'], 'done')
        self.assertTrue(finished['publishedSceneId'])

        public_scene = self.public_store.get_scene(finished['publishedSceneId'])
        self.assertEqual(public_scene['sceneType'], 'public')
        self.assertEqual(public_scene['meta']['categoryId'], 'scene_category_family_daily')

        publication = self.commerce_store.get_scene_publication_by_source(finished['sceneId'])
        self.assertEqual(publication['collectionIds'], ['scene_collection_breakfast'])


if __name__ == '__main__':
    unittest.main()

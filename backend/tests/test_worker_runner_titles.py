import unittest

from backend.app.worker_runner import derive_scene_title, is_placeholder_upload_title, normalize_candidate_title


class WorkerRunnerTitleTests(unittest.TestCase):
    def test_normalize_candidate_title_replaces_separators(self):
        self.assertEqual(normalize_candidate_title('my_kitchen-photo.jpg'), 'my kitchen photo')

    def test_placeholder_upload_title_detects_tmp_file(self):
        self.assertTrue(is_placeholder_upload_title('tmp_41159b80ebf48fa8c88bba0e2ce8602bc4ca093ff9319c7a.jpg'))
        self.assertTrue(is_placeholder_upload_title('source.jpg'))
        self.assertFalse(is_placeholder_upload_title('我的厨房.jpg'))

    def test_derive_scene_title_prefers_explicit_then_ai_then_upload(self):
        self.assertEqual(
            derive_scene_title(
                explicit_title='我的厨房',
                ai_title='厨房',
                upload_filename='tmp_abc123456789.jpg',
            ),
            '我的厨房',
        )
        self.assertEqual(
            derive_scene_title(
                explicit_title='',
                ai_title='厨房',
                upload_filename='tmp_abc123456789.jpg',
            ),
            '厨房',
        )
        self.assertEqual(
            derive_scene_title(
                explicit_title='',
                ai_title='',
                upload_filename='family_kitchen.jpg',
            ),
            'family kitchen',
        )
        self.assertEqual(
            derive_scene_title(
                explicit_title='',
                ai_title='',
                upload_filename='tmp_abc123456789.jpg',
            ),
            '未命名场景',
        )


if __name__ == '__main__':
    unittest.main()

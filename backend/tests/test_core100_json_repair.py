import unittest

from backend.app.core100_compat.json_repair import repair_truncated_json


class Core100JsonRepairTests(unittest.TestCase):
    def test_repair_trailing_comma_before_object_end(self):
        broken = '''
        {
          "scene_id": "kitchen",
          "hotspots": [
            {
              "id": "pot",
              "rect": {"l": 10, "t": 10, "w": 20, "h": 20},
            }
          ],
        }
        '''

        success, result, method = repair_truncated_json(broken, verbose=False)

        self.assertTrue(success)
        self.assertEqual(result['scene_id'], 'kitchen')
        self.assertEqual(result['hotspots'][0]['id'], 'pot')
        self.assertIn('成功', method)


if __name__ == '__main__':
    unittest.main()

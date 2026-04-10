import unittest

from backend.app.hotspot_permissions import can_edit_scene_hotspots


class HotspotPermissionTests(unittest.TestCase):
    def test_public_scene_requires_whitelist(self):
        scene = {
            'sceneType': 'public',
            'meta': {}
        }

        self.assertFalse(can_edit_scene_hotspots(scene, 'debug_user_1', {
            'enabled': True,
            'admin_user_ids': set(),
            'public_editor_ids': set(),
            'private_editor_ids': set(),
        }))

        self.assertTrue(can_edit_scene_hotspots(scene, 'debug_user_1', {
            'enabled': True,
            'admin_user_ids': set(),
            'public_editor_ids': {'debug_user_1'},
            'private_editor_ids': set(),
        }))

    def test_private_scene_owner_can_edit(self):
        scene = {
            'sceneType': 'private',
            'meta': {
                'ownerId': 'owner_001'
            }
        }

        self.assertTrue(can_edit_scene_hotspots(scene, 'owner_001', {
            'enabled': True,
            'admin_user_ids': set(),
            'public_editor_ids': set(),
            'private_editor_ids': set(),
        }))

        self.assertTrue(can_edit_scene_hotspots(scene, 'other_debug_user', {
            'enabled': True,
            'admin_user_ids': set(),
            'public_editor_ids': set(),
            'private_editor_ids': {'*'},
        }))

    def test_private_scene_without_owner_denied(self):
        scene = {
            'sceneType': 'private',
            'meta': {}
        }

        self.assertFalse(can_edit_scene_hotspots(scene, 'debug_user_1', {
            'enabled': True,
            'admin_user_ids': set(),
            'public_editor_ids': set(),
            'private_editor_ids': set(),
        }))

    def test_admin_override_and_scene_disable_flag(self):
        scene = {
            'sceneType': 'private',
            'meta': {
                'ownerId': 'owner_001',
                'hotspotEditable': False
            }
        }

        self.assertFalse(can_edit_scene_hotspots(scene, 'owner_001', {
            'enabled': True,
            'admin_user_ids': set(),
            'public_editor_ids': set(),
            'private_editor_ids': set(),
        }))

        self.assertTrue(can_edit_scene_hotspots(scene, 'admin_001', {
            'enabled': True,
            'admin_user_ids': {'admin_001'},
            'public_editor_ids': set(),
            'private_editor_ids': set(),
        }))

    def test_database_admin_role_has_access(self):
        """User with admin role in database can edit any scene."""
        scene = {
            'sceneType': 'public',
            'meta': {}
        }

        config = {
            'enabled': True,
            'admin_user_ids': set(),
            'public_editor_ids': set(),
            'private_editor_ids': set(),
        }

        # admin role from database
        self.assertTrue(can_edit_scene_hotspots(
            scene, 'any_user', config, user_role='admin',
        ))

        # super_admin role from database
        self.assertTrue(can_edit_scene_hotspots(
            scene, 'any_user', config, user_role='super_admin',
        ))

        # regular user without admin role cannot edit
        self.assertFalse(can_edit_scene_hotspots(
            scene, 'any_user', config, user_role='user',
        ))

        # no role provided cannot edit
        self.assertFalse(can_edit_scene_hotspots(
            scene, 'any_user', config,
        ))

    def test_database_admin_bypasses_hotspot_editable_false(self):
        """Database admin can edit even when hotspotEditable is False."""
        scene = {
            'sceneType': 'public',
            'meta': {'hotspotEditable': False}
        }

        self.assertTrue(can_edit_scene_hotspots(
            scene, 'admin_user', {
                'enabled': True,
                'admin_user_ids': set(),
                'public_editor_ids': set(),
                'private_editor_ids': set(),
            },
            user_role='admin',
        ))

    def test_scene_level_editor_list_allows_specific_user(self):
        scene = {
            'sceneType': 'public',
            'meta': {
                'hotspotEditors': ['scene_editor_1']
            }
        }

        self.assertTrue(can_edit_scene_hotspots(scene, 'scene_editor_1', {
            'enabled': True,
            'admin_user_ids': set(),
            'public_editor_ids': set(),
            'private_editor_ids': set(),
        }))


if __name__ == '__main__':
    unittest.main()

import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from backend.app.auth_migration import migrate_auth_payload
from backend.app.auth_store import AuthStore
from backend.app.auth_store_postgres import PostgresAuthStore
from backend.app.postgres import connect_postgres
from backend.app.store_utils import read_json_file


DATABASE_URL = 'postgresql://weixin_saas:hq425771@localhost:5432/weixin_saas'


class AuthMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.auth_file = Path(self.temp_dir.name) / 'auth.json'
        self.source_store = AuthStore(self.auth_file)
        self.schema_name = f'auth_migrate_{uuid4().hex[:12]}'
        self.target_store = PostgresAuthStore(DATABASE_URL, self.schema_name)

    def tearDown(self):
        with connect_postgres(DATABASE_URL, 'public') as connection:
            with connection.cursor() as cursor:
                cursor.execute(f'drop schema if exists {self.schema_name} cascade')
        self.temp_dir.cleanup()

    def test_json_payload_migrates_to_postgres_store(self):
        user = self.source_store.get_or_create_debug_user('debug_user_migrate_001')
        self.source_store.get_or_create_wechat_user(
            provider_uid='openid_migrate_001',
            union_id='union_migrate_001',
            profile={'displayName': 'Migrated User'},
            session_key_encrypted='encrypted-key',
        )
        self.source_store.create_refresh_session(
            user_id=user['id'],
            token_hash='token_hash_migrate_001',
            expires_at='2099-01-01T00:00:00Z',
            device={'deviceId': 'device_migrate_001'},
            ip='127.0.0.1',
            user_agent='migration-test',
        )

        payload = read_json_file(self.auth_file)
        summary = migrate_auth_payload(payload, self.target_store)

        self.assertEqual(summary['users'], 2)
        self.assertEqual(summary['identities'], 1)
        self.assertEqual(summary['refreshTokens'], 1)
        self.assertEqual(self.target_store.get_user('debug_user_migrate_001')['id'], 'debug_user_migrate_001')
        self.assertIsNotNone(self.target_store.get_active_refresh_session('token_hash_migrate_001'))


if __name__ == '__main__':
    unittest.main()

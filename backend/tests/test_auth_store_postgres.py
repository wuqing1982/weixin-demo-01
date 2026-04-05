import unittest
from uuid import uuid4

from backend.app.auth_store_postgres import PostgresAuthStore
from backend.app.postgres import connect_postgres
from backend.app.security import generate_refresh_token, hash_refresh_token


DATABASE_URL = 'postgresql://weixin_saas:hq425771@localhost:5432/weixin_saas'


class PostgresAuthStoreTests(unittest.TestCase):
    def setUp(self):
        self.schema_name = f'auth_test_{uuid4().hex[:12]}'
        self.store = PostgresAuthStore(DATABASE_URL, self.schema_name)

    def tearDown(self):
        with connect_postgres(DATABASE_URL, 'public') as connection:
            with connection.cursor() as cursor:
                cursor.execute(f'drop schema if exists {self.schema_name} cascade')

    def test_debug_user_and_refresh_lifecycle(self):
        user = self.store.get_or_create_debug_user('debug_user_pg_001')
        self.assertEqual(user['id'], 'debug_user_pg_001')

        raw_token = generate_refresh_token()
        session = self.store.create_refresh_session(
            user_id=user['id'],
            token_hash=hash_refresh_token(raw_token),
            expires_at='2099-01-01T00:00:00Z',
            device={'deviceId': 'device_pg_001', 'deviceType': 'wechat_mini_program'},
            ip='127.0.0.1',
            user_agent='codex-test',
        )
        self.assertEqual(session['userId'], user['id'])
        self.assertTrue(self.store.revoke_refresh_token(session['tokenHash']))
        self.assertTrue(self.store.revoke_refresh_token(session['tokenHash']))
        self.assertIsNone(self.store.get_active_refresh_session(session['tokenHash']))

    def test_wechat_identity_reuses_same_user(self):
        first = self.store.get_or_create_wechat_user(provider_uid='openid_001', profile={'displayName': 'A'})
        second = self.store.get_or_create_wechat_user(provider_uid='openid_001', profile={'displayName': 'B'})

        self.assertEqual(first['id'], second['id'])
        self.assertEqual(second['displayName'], 'B')

    def test_union_id_can_merge_new_openid_to_same_user(self):
        first = self.store.get_or_create_wechat_user(
            provider_uid='openid_union_a',
            union_id='union_shared_001',
            profile={'displayName': 'A'},
        )
        second = self.store.get_or_create_wechat_user(
            provider_uid='openid_union_b',
            union_id='union_shared_001',
            profile={'displayName': 'B'},
        )

        self.assertEqual(first['id'], second['id'])
        self.assertEqual(second['displayName'], 'B')

    def test_update_user_role_round_trip(self):
        user = self.store.get_or_create_debug_user('debug_user_pg_admin_001')
        self.assertEqual(user['role'], 'user')

        promoted = self.store.update_user_role(user['id'], 'admin')
        self.assertEqual(promoted['role'], 'admin')

        fetched = self.store.get_user(user['id'])
        self.assertEqual(fetched['role'], 'admin')


if __name__ == '__main__':
    unittest.main()

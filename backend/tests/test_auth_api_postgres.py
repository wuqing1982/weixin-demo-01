import os
import unittest
from uuid import uuid4

from fastapi import HTTPException

os.environ['AUTH_STORE_BACKEND'] = 'json'
os.environ['COMMERCE_STORE_BACKEND'] = 'disabled'

from backend.app import main
from backend.app.auth_store_postgres import PostgresAuthStore
from backend.app.postgres import connect_postgres
from backend.app.schemas import LogoutRequest, MeProfileUpdateRequest, RefreshTokenRequest, WechatLoginRequest
from backend.tests.test_auth_api import build_request


DATABASE_URL = 'postgresql://weixin_saas:hq425771@localhost:5432/weixin_saas'


class AuthApiPostgresTests(unittest.TestCase):
    def setUp(self):
        self.schema_name = f'auth_api_{uuid4().hex[:12]}'
        self.original_auth_store = main.auth_store
        self.original_login_mode = main.AUTH_WECHAT_LOGIN_MODE
        main.auth_store = PostgresAuthStore(DATABASE_URL, self.schema_name)
        main.AUTH_WECHAT_LOGIN_MODE = 'mock'

    def tearDown(self):
        main.auth_store = self.original_auth_store
        main.AUTH_WECHAT_LOGIN_MODE = self.original_login_mode
        with connect_postgres(DATABASE_URL, 'public') as connection:
            with connection.cursor() as cursor:
                cursor.execute(f'drop schema if exists {self.schema_name} cascade')

    def test_login_refresh_logout_round_trip(self):
        request = build_request(method='POST', path='/api/auth/wechat/login')
        payload = WechatLoginRequest.model_validate({
            'code': 'wx-pg-code-1',
            'device': {
                'deviceId': 'device-pg-fixed-001',
                'deviceType': 'wechat_mini_program',
                'appVersion': '1.0.0',
            },
        })
        response = main.auth_wechat_login(payload, request)
        data = response['data']

        me_request = build_request(
            path='/api/me',
            headers={'Authorization': f"Bearer {data['accessToken']}"},
        )
        me_response = main.get_me(me_request)
        self.assertEqual(me_response['data']['id'], data['user']['id'])

        refreshed = main.auth_refresh_token(
            RefreshTokenRequest(refreshToken=data['refreshToken']),
            build_request(method='POST', path='/api/auth/refresh'),
        )['data']
        self.assertNotEqual(refreshed['refreshToken'], data['refreshToken'])

        logout_response = main.auth_logout(
            build_request(
                method='POST',
                path='/api/auth/logout',
                headers={'Authorization': f"Bearer {refreshed['accessToken']}"},
            ),
            LogoutRequest(refreshToken=refreshed['refreshToken']),
        )
        self.assertTrue(logout_response['data']['revoked'])

        with self.assertRaises(HTTPException):
            main.auth_refresh_token(
                RefreshTokenRequest(refreshToken=refreshed['refreshToken']),
                build_request(method='POST', path='/api/auth/refresh'),
            )

    def test_update_profile_round_trip(self):
        login_data = main.auth_wechat_login(
            WechatLoginRequest.model_validate({
                'code': 'wx-pg-code-profile',
                'device': {
                    'deviceId': 'device-pg-profile-001',
                    'deviceType': 'wechat_mini_program',
                    'appVersion': '1.0.0',
                },
            }),
            build_request(method='POST', path='/api/auth/wechat/login'),
        )['data']

        updated = main.update_my_profile(
            MeProfileUpdateRequest(
                displayName='Postgres 昵称',
                avatarUrl='https://wx.qlogo.cn/postgres-avatar.png',
            ),
            build_request(
                method='PUT',
                path='/api/me/profile',
                headers={'Authorization': f"Bearer {login_data['accessToken']}"},
            ),
        )['data']

        self.assertEqual(updated['displayName'], 'Postgres 昵称')
        self.assertEqual(updated['avatarUrl'], 'https://wx.qlogo.cn/postgres-avatar.png')


if __name__ == '__main__':
    unittest.main()

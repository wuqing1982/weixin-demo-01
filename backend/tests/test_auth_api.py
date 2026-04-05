import os
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException
from starlette.requests import Request

os.environ['AUTH_STORE_BACKEND'] = 'json'
os.environ['COMMERCE_STORE_BACKEND'] = 'disabled'

from backend.app.auth_store import AuthStore
from backend.app import main
from backend.app.schemas import LogoutRequest, MeProfileUpdateRequest, RefreshTokenRequest, WechatLoginRequest


def build_request(*, method: str = 'GET', path: str = '/', headers: dict[str, str] | None = None) -> Request:
    encoded_headers = []
    for key, value in (headers or {}).items():
        encoded_headers.append((key.lower().encode('utf-8'), value.encode('utf-8')))

    scope = {
        'type': 'http',
        'http_version': '1.1',
        'method': method,
        'scheme': 'https',
        'path': path,
        'raw_path': path.encode('utf-8'),
        'query_string': b'',
        'headers': encoded_headers,
        'client': ('127.0.0.1', 12345),
        'server': ('testserver', 443),
    }
    return Request(scope)


class AuthApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_auth_file = Path(self.temp_dir.name) / 'auth.json'
        self.original_auth_store = main.auth_store
        self.original_login_mode = main.AUTH_WECHAT_LOGIN_MODE

        main.auth_store = AuthStore(self.temp_auth_file)
        main.AUTH_WECHAT_LOGIN_MODE = 'mock'

    def tearDown(self):
        main.auth_store = self.original_auth_store
        main.AUTH_WECHAT_LOGIN_MODE = self.original_login_mode
        self.temp_dir.cleanup()

    def test_login_and_get_me(self):
        request = build_request(method='POST', path='/api/auth/wechat/login')
        payload = WechatLoginRequest.model_validate({
            'code': 'wx-code-1',
            'device': {
                'deviceId': 'device-fixed-001',
                'deviceType': 'wechat_mini_program',
                'appVersion': '1.0.0',
            },
        })
        response = main.auth_wechat_login(payload, request)
        data = response['data']

        self.assertTrue(data['accessToken'])
        self.assertTrue(data['refreshToken'])
        self.assertEqual(data['user']['displayName'], '微信用户')

        me_request = build_request(
            path='/api/me',
            headers={
                'Authorization': f"Bearer {data['accessToken']}",
            },
        )
        me_response = main.get_me(me_request)
        me_data = me_response['data']
        self.assertEqual(me_data['id'], data['user']['id'])
        self.assertEqual(me_data['role'], 'user')
        self.assertIn('memberSummary', me_data)
        self.assertIn('creditSummary', me_data)

    def test_same_device_maps_to_same_mock_user(self):
        first = main.auth_wechat_login(
            WechatLoginRequest.model_validate({
                'code': 'wx-code-a',
                'device': {'deviceId': 'same-device'},
            }),
            build_request(method='POST', path='/api/auth/wechat/login'),
        )['data']
        second = main.auth_wechat_login(
            WechatLoginRequest.model_validate({
                'code': 'wx-code-b',
                'device': {'deviceId': 'same-device'},
            }),
            build_request(method='POST', path='/api/auth/wechat/login'),
        )['data']

        self.assertEqual(first['user']['id'], second['user']['id'])

    def test_refresh_rotates_session_and_logout_revokes_it(self):
        login_data = main.auth_wechat_login(
            WechatLoginRequest.model_validate({
                'code': 'wx-code-refresh',
                'device': {'deviceId': 'refresh-device'},
            }),
            build_request(method='POST', path='/api/auth/wechat/login'),
        )['data']

        refreshed = main.auth_refresh_token(
            RefreshTokenRequest(refreshToken=login_data['refreshToken']),
            build_request(method='POST', path='/api/auth/refresh'),
        )['data']
        self.assertNotEqual(refreshed['refreshToken'], login_data['refreshToken'])

        with self.assertRaises(HTTPException):
            main.auth_refresh_token(
                RefreshTokenRequest(refreshToken=login_data['refreshToken']),
                build_request(method='POST', path='/api/auth/refresh'),
            )

        logout_response = main.auth_logout(
            build_request(
                method='POST',
                path='/api/auth/logout',
                headers={
                    'Authorization': f"Bearer {refreshed['accessToken']}",
                },
            ),
            LogoutRequest(refreshToken=refreshed['refreshToken']),
        )
        self.assertTrue(logout_response['data']['revoked'])

        with self.assertRaises(HTTPException):
            main.auth_refresh_token(
                RefreshTokenRequest(refreshToken=refreshed['refreshToken']),
                build_request(method='POST', path='/api/auth/refresh'),
            )

    def test_update_profile_persists_display_name_and_avatar(self):
        login_data = main.auth_wechat_login(
            WechatLoginRequest.model_validate({
                'code': 'wx-code-profile',
                'device': {'deviceId': 'profile-device'},
            }),
            build_request(method='POST', path='/api/auth/wechat/login'),
        )['data']

        updated = main.update_my_profile(
            MeProfileUpdateRequest(
                displayName='测试昵称',
                avatarUrl='https://wx.qlogo.cn/mock-avatar.png',
            ),
            build_request(
                method='PUT',
                path='/api/me/profile',
                headers={'Authorization': f"Bearer {login_data['accessToken']}"},
            ),
        )['data']

        self.assertEqual(updated['displayName'], '测试昵称')
        self.assertEqual(updated['avatarUrl'], 'https://wx.qlogo.cn/mock-avatar.png')

        me = main.get_me(
            build_request(
                path='/api/me',
                headers={'Authorization': f"Bearer {login_data['accessToken']}"},
            )
        )['data']
        self.assertEqual(me['displayName'], '测试昵称')
        self.assertEqual(me['avatarUrl'], 'https://wx.qlogo.cn/mock-avatar.png')

    def test_code2session_mode_uses_real_identity_response(self):
        class FakeWechatClient:
            def __init__(self):
                self.codes = []

            def is_configured(self):
                return True

            def code_to_session(self, code):
                self.codes.append(code)
                return {
                    'openid': 'openid_real_001' if code == 'real-code-001' else 'openid_real_002',
                    'session_key': 'session_key_real_001',
                    'unionid': 'union_real_001',
                }

        fake_client = FakeWechatClient()
        original_client = getattr(main, 'wechat_auth_client', None)
        main.wechat_auth_client = fake_client
        main.AUTH_WECHAT_LOGIN_MODE = 'code2session'
        try:
            response = main.auth_wechat_login(
                WechatLoginRequest.model_validate({
                    'code': 'real-code-001',
                    'device': {'deviceId': 'real-device-001'},
                }),
                build_request(method='POST', path='/api/auth/wechat/login'),
            )['data']
            repeated = main.auth_wechat_login(
                WechatLoginRequest.model_validate({
                    'code': 'real-code-002',
                    'device': {'deviceId': 'real-device-002'},
                }),
                build_request(method='POST', path='/api/auth/wechat/login'),
            )['data']
        finally:
            main.wechat_auth_client = original_client

        self.assertEqual(fake_client.codes, ['real-code-001', 'real-code-002'])
        self.assertTrue(response['accessToken'])
        self.assertEqual(response['user']['displayName'], '微信用户')
        self.assertEqual(response['user']['id'], repeated['user']['id'])


if __name__ == '__main__':
    unittest.main()

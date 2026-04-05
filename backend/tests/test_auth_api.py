import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException
from starlette.requests import Request

from backend.app.auth_store import AuthStore
from backend.app import main
from backend.app.schemas import LogoutRequest, RefreshTokenRequest, WechatLoginRequest


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


if __name__ == '__main__':
    unittest.main()

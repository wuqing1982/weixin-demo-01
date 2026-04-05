import json
import unittest
from unittest.mock import patch

from backend.app.wechat_auth import WechatCode2SessionError, WechatMiniProgramAuthClient


class _FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode('utf-8')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class WechatAuthClientTests(unittest.TestCase):
    def test_code_to_session_success(self):
        client = WechatMiniProgramAuthClient('wx_appid_001', 'app_secret_001')
        with patch('urllib.request.urlopen', return_value=_FakeResponse({
            'openid': 'openid_001',
            'session_key': 'session_key_001',
            'unionid': 'union_001',
        })):
            payload = client.code_to_session('code_001')

        self.assertEqual(payload['openid'], 'openid_001')
        self.assertEqual(payload['session_key'], 'session_key_001')
        self.assertEqual(payload['unionid'], 'union_001')

    def test_code_to_session_raises_for_wechat_error(self):
        client = WechatMiniProgramAuthClient('wx_appid_001', 'app_secret_001')
        with patch('urllib.request.urlopen', return_value=_FakeResponse({
            'errcode': 40029,
            'errmsg': 'invalid code',
        })):
            with self.assertRaises(WechatCode2SessionError):
                client.code_to_session('bad_code')

    def test_code_to_session_requires_credentials(self):
        client = WechatMiniProgramAuthClient('', '')
        with self.assertRaises(WechatCode2SessionError):
            client.code_to_session('code_001')


if __name__ == '__main__':
    unittest.main()

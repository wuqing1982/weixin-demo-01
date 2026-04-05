import os
import unittest

os.environ['AUTH_STORE_BACKEND'] = 'json'
os.environ['COMMERCE_STORE_BACKEND'] = 'disabled'

from backend.app.security import (
    create_access_token,
    decode_access_token,
    decrypt_wechat_session_key,
    encrypt_wechat_session_key,
    generate_refresh_token,
    hash_refresh_token,
)


class AuthSecurityTests(unittest.TestCase):
    def test_access_token_round_trip(self):
        token, expires_at = create_access_token('user_123', 'session_456')
        payload = decode_access_token(token)

        self.assertEqual(payload['sub'], 'user_123')
        self.assertEqual(payload['sid'], 'session_456')
        self.assertEqual(payload['typ'], 'access')
        self.assertGreaterEqual(payload['exp'], expires_at)

    def test_refresh_token_hash_is_stable(self):
        raw_token = generate_refresh_token()

        self.assertTrue(raw_token.startswith('rt_'))
        self.assertEqual(hash_refresh_token(raw_token), hash_refresh_token(raw_token))
        self.assertNotEqual(hash_refresh_token(raw_token), hash_refresh_token(f'{raw_token}_other'))

    def test_wechat_session_key_encrypt_round_trip(self):
        raw_value = 'session_key_abc123'
        cipher_text = encrypt_wechat_session_key(raw_value)

        self.assertNotEqual(cipher_text, raw_value)
        self.assertEqual(decrypt_wechat_session_key(cipher_text), raw_value)


if __name__ == '__main__':
    unittest.main()

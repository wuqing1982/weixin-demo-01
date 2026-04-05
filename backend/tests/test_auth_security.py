import unittest

from backend.app.security import create_access_token, decode_access_token, generate_refresh_token, hash_refresh_token


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


if __name__ == '__main__':
    unittest.main()

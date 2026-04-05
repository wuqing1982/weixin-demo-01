import base64
import hashlib
import hmac
import json
from datetime import datetime, timezone
from secrets import token_urlsafe
from typing import Any

from .settings import AUTH_ACCESS_TOKEN_TTL_SECONDS, AUTH_JWT_SECRET


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode('utf-8').rstrip('=')


def _b64url_decode(value: str) -> bytes:
    padding = '=' * (-len(value) % 4)
    return base64.urlsafe_b64decode(f'{value}{padding}')


def _json_dumps(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def _utc_now_ts() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def create_access_token(
    user_id: str,
    session_id: str,
    *,
    role: str = 'user',
    expires_in: int = AUTH_ACCESS_TOKEN_TTL_SECONDS,
) -> tuple[str, int]:
    issued_at = _utc_now_ts()
    expires_at = issued_at + max(1, int(expires_in))

    header = {
        'alg': 'HS256',
        'typ': 'JWT',
    }
    payload = {
        'sub': user_id,
        'typ': 'access',
        'role': role,
        'sid': session_id,
        'iat': issued_at,
        'exp': expires_at,
    }

    signing_input = f'{_b64url_encode(_json_dumps(header))}.{_b64url_encode(_json_dumps(payload))}'
    signature = hmac.new(
        AUTH_JWT_SECRET.encode('utf-8'),
        signing_input.encode('utf-8'),
        hashlib.sha256,
    ).digest()
    token = f'{signing_input}.{_b64url_encode(signature)}'
    return token, expires_at


def decode_access_token(token: str) -> dict[str, Any]:
    if not token or token.count('.') != 2:
        raise ValueError('invalid token')

    encoded_header, encoded_payload, encoded_signature = token.split('.', 2)
    signing_input = f'{encoded_header}.{encoded_payload}'
    expected_signature = hmac.new(
        AUTH_JWT_SECRET.encode('utf-8'),
        signing_input.encode('utf-8'),
        hashlib.sha256,
    ).digest()
    actual_signature = _b64url_decode(encoded_signature)

    if not hmac.compare_digest(expected_signature, actual_signature):
        raise ValueError('invalid token signature')

    payload = json.loads(_b64url_decode(encoded_payload).decode('utf-8'))
    if payload.get('typ') != 'access':
        raise ValueError('invalid token type')
    if int(payload.get('exp', 0)) <= _utc_now_ts():
        raise ValueError('token expired')
    return payload


def generate_refresh_token() -> str:
    return f'rt_{token_urlsafe(32)}'


def hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256((raw_token or '').encode('utf-8')).hexdigest()

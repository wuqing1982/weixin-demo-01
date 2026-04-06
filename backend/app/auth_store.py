import copy
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from .store_utils import build_object_id, ensure_json_file, read_json_file, utcnow_iso, write_json_file


DEFAULT_AUTH_PAYLOAD = {
    'users': [],
    'identities': [],
    'refreshTokens': [],
}


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


class AuthStore:
    def __init__(self, data_file: Path):
        self.data_file = data_file
        self.lock = Lock()
        ensure_json_file(self.data_file, DEFAULT_AUTH_PAYLOAD)

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        with self.lock:
            payload = read_json_file(self.data_file)
        for user in payload.get('users', []):
            if user.get('id') == user_id:
                return copy.deepcopy(user)
        return None

    def list_users(self, limit: int = 100) -> list[dict[str, Any]]:
        limit = max(1, int(limit or 100))
        with self.lock:
            payload = read_json_file(self.data_file)
        users = sorted(
            payload.get('users', []),
            key=lambda item: item.get('updatedAt') or item.get('createdAt') or '',
            reverse=True,
        )
        return [copy.deepcopy(user) for user in users[:limit]]

    def get_user_count(self) -> int:
        with self.lock:
            payload = read_json_file(self.data_file)
        return len(payload.get('users', []))

    def update_user_status(self, user_id: str, status: str) -> dict[str, Any] | None:
        with self.lock:
            payload = read_json_file(self.data_file)
            users = payload.get('users', [])
            for user in users:
                if user.get('id') != user_id:
                    continue
                user['status'] = status
                user['updatedAt'] = utcnow_iso()
                write_json_file(self.data_file, payload)
                return copy.deepcopy(user)
        return None

    def update_user_role(self, user_id: str, role: str) -> dict[str, Any] | None:
        normalized_role = (role or 'user').strip() or 'user'
        with self.lock:
            payload = read_json_file(self.data_file)
            users = payload.get('users', [])
            for user in users:
                if user.get('id') != user_id:
                    continue
                user['role'] = normalized_role
                user['updatedAt'] = utcnow_iso()
                write_json_file(self.data_file, payload)
                return copy.deepcopy(user)
        return None

    def update_user_profile(self, user_id: str, *, display_name: str = '', avatar_url: str = '') -> dict[str, Any] | None:
        with self.lock:
            payload = read_json_file(self.data_file)
            users = payload.get('users', [])
            for user in users:
                if user.get('id') != user_id:
                    continue
                if display_name:
                    user['displayName'] = display_name
                if avatar_url:
                    user['avatarUrl'] = avatar_url
                user['updatedAt'] = utcnow_iso()
                write_json_file(self.data_file, payload)
                return copy.deepcopy(user)
        return None

    def get_wechat_identity(self, user_id: str) -> dict[str, Any] | None:
        with self.lock:
            payload = read_json_file(self.data_file)
        for identity in payload.get('identities', []):
            if identity.get('userId') != user_id:
                continue
            if identity.get('provider') != 'wechat_mp':
                continue
            return copy.deepcopy(identity)
        return None

    def get_or_create_debug_user(self, user_id: str) -> dict[str, Any]:
        with self.lock:
            payload = read_json_file(self.data_file)
            users = payload.get('users', [])
            for user in users:
                if user.get('id') == user_id:
                    return copy.deepcopy(user)

            now = utcnow_iso()
            user = {
                'id': user_id,
                'role': 'user',
                'status': 'active',
                'displayName': f'Debug {user_id[-6:]}',
                'avatarUrl': '',
                'mobile': None,
                'mobileVerified': False,
                'lastLoginAt': now,
                'createdAt': now,
                'updatedAt': now,
            }
            users.append(user)
            write_json_file(self.data_file, payload)
            return copy.deepcopy(user)

    def get_or_create_wechat_user(
        self,
        *,
        provider_uid: str,
        union_id: str = '',
        profile: dict[str, Any] | None = None,
        session_key_encrypted: str = '',
    ) -> dict[str, Any]:
        profile = profile or {}
        now = utcnow_iso()

        with self.lock:
            payload = read_json_file(self.data_file)
            users = payload.get('users', [])
            identities = payload.get('identities', [])

            identity = None
            for item in identities:
                if item.get('provider') == 'wechat_mp' and item.get('providerUid') == provider_uid:
                    identity = item
                    break

            if not identity and union_id:
                for item in identities:
                    if item.get('provider') == 'wechat_mp' and item.get('unionId') == union_id:
                        identity = item
                        break

            user = None
            if identity:
                for item in users:
                    if item.get('id') == identity.get('userId'):
                        user = item
                        break

            if not user:
                user = {
                    'id': build_object_id('user'),
                    'role': 'user',
                    'status': 'active',
                    'displayName': profile.get('displayName') or '微信用户',
                    'avatarUrl': profile.get('avatarUrl') or '',
                    'mobile': None,
                    'mobileVerified': False,
                    'lastLoginAt': now,
                    'createdAt': now,
                    'updatedAt': now,
                }
                users.append(user)

            user['displayName'] = profile.get('displayName') or user.get('displayName') or '微信用户'
            user['avatarUrl'] = profile.get('avatarUrl') or user.get('avatarUrl') or ''
            user['role'] = user.get('role') or 'user'
            user['lastLoginAt'] = now
            user['updatedAt'] = now

            if not identity:
                identity = {
                    'id': build_object_id('identity'),
                    'userId': user['id'],
                    'provider': 'wechat_mp',
                    'providerUid': provider_uid,
                    'unionId': union_id or '',
                    'sessionKeyEncrypted': session_key_encrypted,
                    'metaJson': profile,
                    'lastLoginAt': now,
                    'createdAt': now,
                    'updatedAt': now,
                }
                identities.append(identity)
            else:
                identity['providerUid'] = provider_uid or identity.get('providerUid') or ''
                identity['unionId'] = union_id or identity.get('unionId') or ''
                identity['sessionKeyEncrypted'] = session_key_encrypted or identity.get('sessionKeyEncrypted') or ''
                identity['metaJson'] = profile or identity.get('metaJson') or {}
                identity['lastLoginAt'] = now
                identity['updatedAt'] = now

            write_json_file(self.data_file, payload)
            return copy.deepcopy(user)

    def create_refresh_session(
        self,
        *,
        user_id: str,
        token_hash: str,
        expires_at: str,
        device: dict[str, Any] | None = None,
        ip: str = '',
        user_agent: str = '',
    ) -> dict[str, Any]:
        device = device or {}
        now = utcnow_iso()

        session = {
            'id': build_object_id('session'),
            'userId': user_id,
            'tokenHash': token_hash,
            'deviceType': device.get('deviceType') or '',
            'deviceId': device.get('deviceId') or '',
            'appVersion': device.get('appVersion') or '',
            'ip': ip,
            'userAgent': user_agent,
            'expiresAt': expires_at,
            'revokedAt': '',
            'createdAt': now,
        }

        with self.lock:
            payload = read_json_file(self.data_file)
            payload.get('refreshTokens', []).append(session)
            write_json_file(self.data_file, payload)

        return copy.deepcopy(session)

    def get_active_refresh_session(self, token_hash: str) -> dict[str, Any] | None:
        now = datetime.now(timezone.utc)
        with self.lock:
            payload = read_json_file(self.data_file)
        for session in payload.get('refreshTokens', []):
            if session.get('tokenHash') != token_hash:
                continue
            if session.get('revokedAt'):
                return None
            expires_at = _parse_iso(session.get('expiresAt'))
            if not expires_at or expires_at <= now:
                return None
            return copy.deepcopy(session)
        return None

    def revoke_refresh_token(self, token_hash: str) -> bool:
        with self.lock:
            payload = read_json_file(self.data_file)
            sessions = payload.get('refreshTokens', [])
            changed = False
            for session in sessions:
                if session.get('tokenHash') != token_hash:
                    continue
                if session.get('revokedAt'):
                    return True
                session['revokedAt'] = utcnow_iso()
                changed = True
                break
            if changed:
                write_json_file(self.data_file, payload)
            return changed

    def revoke_session(self, session_id: str) -> bool:
        with self.lock:
            payload = read_json_file(self.data_file)
            sessions = payload.get('refreshTokens', [])
            changed = False
            for session in sessions:
                if session.get('id') != session_id:
                    continue
                if session.get('revokedAt'):
                    return True
                session['revokedAt'] = utcnow_iso()
                changed = True
                break
            if changed:
                write_json_file(self.data_file, payload)
            return changed

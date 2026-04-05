import json
from datetime import datetime, timezone
from typing import Any

from .auth_postgres_schema import ensure_auth_postgres_schema
from .postgres import connect_postgres
from .store_utils import build_object_id, utcnow_iso


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def _to_iso(value: datetime | None) -> str:
    if value is None:
        return ''
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _normalize_ip(value: str | None) -> str | None:
    normalized = (value or '').strip()
    return normalized or None


def _serialize_user(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        'id': row.get('id', ''),
        'status': row.get('status', 'active'),
        'displayName': row.get('display_name') or '',
        'avatarUrl': row.get('avatar_url') or '',
        'mobile': row.get('mobile'),
        'mobileVerified': bool(row.get('mobile_verified')),
        'lastLoginAt': _to_iso(row.get('last_login_at')),
        'createdAt': _to_iso(row.get('created_at')),
        'updatedAt': _to_iso(row.get('updated_at')),
    }


def _serialize_session(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        'id': row.get('id', ''),
        'userId': row.get('user_id', ''),
        'tokenHash': row.get('token_hash', ''),
        'deviceType': row.get('device_type') or '',
        'deviceId': row.get('device_id') or '',
        'appVersion': row.get('app_version') or '',
        'ip': str(row.get('ip') or ''),
        'userAgent': row.get('user_agent') or '',
        'expiresAt': _to_iso(row.get('expires_at')),
        'revokedAt': _to_iso(row.get('revoked_at')),
        'createdAt': _to_iso(row.get('created_at')),
    }


class PostgresAuthStore:
    def __init__(self, database_url: str, schema_name: str = 'public'):
        self.database_url = database_url
        self.schema_name = schema_name
        self._ensure_ready()

    def _connect(self):
        return connect_postgres(self.database_url, self.schema_name)

    def _ensure_ready(self) -> None:
        with self._connect() as connection:
            ensure_auth_postgres_schema(connection)

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute('select * from users where id = %s limit 1', (user_id,))
                return _serialize_user(cursor.fetchone())

    def get_or_create_debug_user(self, user_id: str) -> dict[str, Any]:
        user = self.get_user(user_id)
        if user:
            return user

        now = utcnow_iso()
        self.upsert_user({
            'id': user_id,
            'status': 'active',
            'displayName': f'Debug {user_id[-6:]}',
            'avatarUrl': '',
            'mobile': None,
            'mobileVerified': False,
            'lastLoginAt': now,
            'createdAt': now,
            'updatedAt': now,
        })
        return self.get_user(user_id)

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

        with self._connect() as connection:
            with connection.transaction():
                with connection.cursor() as cursor:
                    cursor.execute(
                        '''
                        select
                          u.id,
                          u.status,
                          u.display_name,
                          u.avatar_url,
                          u.mobile,
                          u.mobile_verified,
                          u.last_login_at,
                          u.created_at,
                          u.updated_at,
                          i.id as identity_id,
                          i.union_id,
                          i.session_key_encrypted,
                          i.meta_json,
                          i.created_at as identity_created_at
                        from user_identities i
                        join users u on u.id = i.user_id
                        where i.provider = %s and i.provider_uid = %s
                        limit 1
                        ''',
                        ('wechat_mp', provider_uid),
                    )
                    current = cursor.fetchone()

                    if not current and union_id:
                        cursor.execute(
                            '''
                            select
                              u.id,
                              u.status,
                              u.display_name,
                              u.avatar_url,
                              u.mobile,
                              u.mobile_verified,
                              u.last_login_at,
                              u.created_at,
                              u.updated_at,
                              i.id as identity_id,
                              i.union_id,
                              i.session_key_encrypted,
                              i.meta_json,
                              i.created_at as identity_created_at
                            from user_identities i
                            join users u on u.id = i.user_id
                            where i.provider = %s and i.union_id = %s
                            limit 1
                            ''',
                            ('wechat_mp', union_id),
                        )
                        current = cursor.fetchone()

                    user_id = current.get('id') if current else build_object_id('user')
                    identity_id = current.get('identity_id') if current else build_object_id('identity')
                    display_name = profile.get('displayName') or (current.get('display_name') if current else '') or '微信用户'
                    avatar_url = profile.get('avatarUrl') or (current.get('avatar_url') if current else '') or ''

                    cursor.execute(
                        '''
                        insert into users (
                          id, status, display_name, avatar_url, mobile, mobile_verified, last_login_at, created_at, updated_at
                        ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        on conflict (id) do update set
                          display_name = excluded.display_name,
                          avatar_url = excluded.avatar_url,
                          last_login_at = excluded.last_login_at,
                          updated_at = excluded.updated_at
                        ''',
                        (
                            user_id,
                            'active',
                            display_name,
                            avatar_url,
                            current.get('mobile') if current else None,
                            bool(current.get('mobile_verified')) if current else False,
                            _parse_iso(now),
                            current.get('created_at') if current else _parse_iso(now),
                            _parse_iso(now),
                        ),
                    )
                    if current:
                        cursor.execute(
                            '''
                            update user_identities
                            set user_id = %s,
                                provider_uid = %s,
                                union_id = %s,
                                session_key_encrypted = %s,
                                meta_json = %s::jsonb,
                                last_login_at = %s,
                                updated_at = %s
                            where id = %s
                            ''',
                            (
                                user_id,
                                provider_uid,
                                union_id or '',
                                session_key_encrypted or (current.get('session_key_encrypted') if current else '') or '',
                                json.dumps(profile or (current.get('meta_json') if current else {}) or {}, ensure_ascii=False),
                                _parse_iso(now),
                                _parse_iso(now),
                                identity_id,
                            ),
                        )
                    else:
                        cursor.execute(
                            '''
                            insert into user_identities (
                              id, user_id, provider, provider_uid, union_id, session_key_encrypted, meta_json, last_login_at, created_at, updated_at
                            ) values (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s)
                            on conflict (provider, provider_uid) do update set
                              user_id = excluded.user_id,
                              union_id = excluded.union_id,
                              session_key_encrypted = excluded.session_key_encrypted,
                              meta_json = excluded.meta_json,
                              last_login_at = excluded.last_login_at,
                              updated_at = excluded.updated_at
                            ''',
                            (
                                identity_id,
                                user_id,
                                'wechat_mp',
                                provider_uid,
                                union_id or '',
                                session_key_encrypted or '',
                                json.dumps(profile or {}, ensure_ascii=False),
                                _parse_iso(now),
                                _parse_iso(now),
                                _parse_iso(now),
                            ),
                        )

        return self.get_user(user_id)

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
        session_id = build_object_id('session')
        self.upsert_refresh_session({
            'id': session_id,
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
        })
        return self.get_active_refresh_session(token_hash)

    def get_active_refresh_session(self, token_hash: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    '''
                    select *
                    from auth_refresh_tokens
                    where token_hash = %s
                      and revoked_at is null
                      and expires_at > now()
                    limit 1
                    ''',
                    (token_hash,),
                )
                return _serialize_session(cursor.fetchone())

    def revoke_refresh_token(self, token_hash: str) -> bool:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    'select revoked_at from auth_refresh_tokens where token_hash = %s limit 1',
                    (token_hash,),
                )
                current = cursor.fetchone()
                if not current:
                    return False
                if current.get('revoked_at'):
                    return True
                cursor.execute(
                    '''
                    update auth_refresh_tokens
                    set revoked_at = now()
                    where token_hash = %s and revoked_at is null
                    ''',
                    (token_hash,),
                )
                return cursor.rowcount > 0

    def revoke_session(self, session_id: str) -> bool:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    'select revoked_at from auth_refresh_tokens where id = %s limit 1',
                    (session_id,),
                )
                current = cursor.fetchone()
                if not current:
                    return False
                if current.get('revoked_at'):
                    return True
                cursor.execute(
                    '''
                    update auth_refresh_tokens
                    set revoked_at = now()
                    where id = %s and revoked_at is null
                    ''',
                    (session_id,),
                )
                return cursor.rowcount > 0

    def upsert_user(self, user: dict[str, Any]) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    '''
                    insert into users (
                      id, status, display_name, avatar_url, mobile, mobile_verified, last_login_at, created_at, updated_at
                    ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    on conflict (id) do update set
                      status = excluded.status,
                      display_name = excluded.display_name,
                      avatar_url = excluded.avatar_url,
                      mobile = excluded.mobile,
                      mobile_verified = excluded.mobile_verified,
                      last_login_at = excluded.last_login_at,
                      created_at = excluded.created_at,
                      updated_at = excluded.updated_at
                    ''',
                    (
                        user.get('id', ''),
                        user.get('status') or 'active',
                        user.get('displayName') or '',
                        user.get('avatarUrl') or '',
                        user.get('mobile'),
                        bool(user.get('mobileVerified')),
                        _parse_iso(user.get('lastLoginAt')),
                        _parse_iso(user.get('createdAt')) or _parse_iso(utcnow_iso()),
                        _parse_iso(user.get('updatedAt')) or _parse_iso(utcnow_iso()),
                    ),
                )

    def upsert_identity(self, identity: dict[str, Any]) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    '''
                    insert into user_identities (
                      id, user_id, provider, provider_uid, union_id, session_key_encrypted, meta_json, last_login_at, created_at, updated_at
                    ) values (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s)
                    on conflict (id) do update set
                      user_id = excluded.user_id,
                      provider = excluded.provider,
                      provider_uid = excluded.provider_uid,
                      union_id = excluded.union_id,
                      session_key_encrypted = excluded.session_key_encrypted,
                      meta_json = excluded.meta_json,
                      last_login_at = excluded.last_login_at,
                      created_at = excluded.created_at,
                      updated_at = excluded.updated_at
                    ''',
                    (
                        identity.get('id', ''),
                        identity.get('userId', ''),
                        identity.get('provider') or '',
                        identity.get('providerUid') or '',
                        identity.get('unionId') or '',
                        identity.get('sessionKeyEncrypted') or '',
                        json.dumps(identity.get('metaJson') or {}, ensure_ascii=False),
                        _parse_iso(identity.get('lastLoginAt')),
                        _parse_iso(identity.get('createdAt')) or _parse_iso(utcnow_iso()),
                        _parse_iso(identity.get('updatedAt')) or _parse_iso(utcnow_iso()),
                    ),
                )

    def upsert_refresh_session(self, session: dict[str, Any]) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    '''
                    insert into auth_refresh_tokens (
                      id, user_id, token_hash, device_type, device_id, app_version, ip, user_agent, expires_at, revoked_at, created_at
                    ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    on conflict (id) do update set
                      user_id = excluded.user_id,
                      token_hash = excluded.token_hash,
                      device_type = excluded.device_type,
                      device_id = excluded.device_id,
                      app_version = excluded.app_version,
                      ip = excluded.ip,
                      user_agent = excluded.user_agent,
                      expires_at = excluded.expires_at,
                      revoked_at = excluded.revoked_at,
                      created_at = excluded.created_at
                    ''',
                    (
                        session.get('id', ''),
                        session.get('userId', ''),
                        session.get('tokenHash', ''),
                        session.get('deviceType') or '',
                        session.get('deviceId') or '',
                        session.get('appVersion') or '',
                        _normalize_ip(session.get('ip')),
                        session.get('userAgent') or '',
                        _parse_iso(session.get('expiresAt')) or _parse_iso(utcnow_iso()),
                        _parse_iso(session.get('revokedAt')),
                        _parse_iso(session.get('createdAt')) or _parse_iso(utcnow_iso()),
                    ),
                )

from typing import Any


def migrate_auth_payload(source_payload: dict[str, Any], target_store) -> dict[str, int]:
    users = source_payload.get('users', [])
    identities = source_payload.get('identities', [])
    refresh_tokens = source_payload.get('refreshTokens', [])

    for user in users:
        target_store.upsert_user(user)

    for identity in identities:
        target_store.upsert_identity(identity)

    for session in refresh_tokens:
        target_store.upsert_refresh_session(session)

    return {
        'users': len(users),
        'identities': len(identities),
        'refreshTokens': len(refresh_tokens),
    }

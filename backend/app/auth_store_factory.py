from .auth_store import AuthStore
from .auth_store_postgres import PostgresAuthStore
from .settings import AUTH_DATA_FILE, AUTH_STORE_BACKEND, DATABASE_SCHEMA, DATABASE_URL


def create_auth_store():
    backend = (AUTH_STORE_BACKEND or 'json').strip().lower()
    if backend not in {'auto', 'json', 'postgres'}:
        raise ValueError(f'unsupported auth store backend: {backend}')

    if backend == 'json':
        return AuthStore(AUTH_DATA_FILE)

    if DATABASE_URL:
        return PostgresAuthStore(DATABASE_URL, DATABASE_SCHEMA)

    if backend == 'postgres':
        raise ValueError('AUTH_STORE_BACKEND=postgres requires DATABASE_URL')

    return AuthStore(AUTH_DATA_FILE)

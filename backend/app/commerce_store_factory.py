from .commerce_store import CommerceStore
from .settings import COMMERCE_STORE_BACKEND, DATABASE_SCHEMA, DATABASE_URL


def create_commerce_store():
    backend = (COMMERCE_STORE_BACKEND or 'disabled').strip().lower()
    if backend not in {'disabled', 'postgres'}:
        raise ValueError(f'unsupported commerce store backend: {backend}')

    if backend == 'disabled':
        return None

    if not DATABASE_URL:
        raise ValueError('COMMERCE_STORE_BACKEND=postgres requires DATABASE_URL')

    return CommerceStore(DATABASE_URL, DATABASE_SCHEMA)

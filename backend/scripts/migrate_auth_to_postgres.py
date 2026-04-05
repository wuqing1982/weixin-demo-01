import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.auth_migration import migrate_auth_payload
from app.auth_store_postgres import PostgresAuthStore
from app.settings import AUTH_DATA_FILE, DATABASE_SCHEMA, DATABASE_URL
from app.store_utils import read_json_file


def main() -> int:
    if not DATABASE_URL:
        raise SystemExit('DATABASE_URL is required')

    source_path = Path(AUTH_DATA_FILE)
    if not source_path.exists():
        raise SystemExit(f'auth source file not found: {source_path}')

    payload = read_json_file(source_path)
    target_store = PostgresAuthStore(DATABASE_URL, DATABASE_SCHEMA)
    summary = migrate_auth_payload(payload, target_store)
    print(f'migrated users={summary["users"]} identities={summary["identities"]} refreshTokens={summary["refreshTokens"]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

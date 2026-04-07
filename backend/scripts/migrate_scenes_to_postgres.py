import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.settings import DATABASE_SCHEMA, DATABASE_URL, GENERATED_SCENES_FILE, PUBLIC_SCENES_FILE
from app.scene_store_postgres import PostgresSceneStore
from app.store_utils import read_json_file


def main() -> int:
    if not DATABASE_URL:
        raise SystemExit('DATABASE_URL is required')

    store = PostgresSceneStore(DATABASE_URL, DATABASE_SCHEMA)

    public_count = 0
    generated_count = 0

    public_path = Path(PUBLIC_SCENES_FILE)
    if public_path.exists():
        payload = read_json_file(public_path)
        for scene in payload.get('scenes', []):
            store.upsert_scene(scene)
            public_count += 1
        print(f'migrated {public_count} public scenes from {public_path}')
    else:
        print(f'no public scenes file found at {public_path}, skipping')

    generated_path = Path(GENERATED_SCENES_FILE)
    if generated_path.exists():
        payload = read_json_file(generated_path)
        for scene in payload.get('scenes', []):
            store.upsert_scene(scene)
            generated_count += 1
        print(f'migrated {generated_count} generated scenes from {generated_path}')
    else:
        print(f'no generated scenes file found at {generated_path}, skipping')

    print(f'total: {public_count + generated_count} scenes migrated')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

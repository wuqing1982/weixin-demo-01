from .generated_scene_store import GeneratedSceneStore
from .scene_store import SceneStore
from .scene_store_postgres import PostgresSceneStore
from .settings import (
    DATABASE_SCHEMA,
    DATABASE_URL,
    GENERATED_SCENES_FILE,
    PUBLIC_SCENES_FILE,
    SCENE_STORE_BACKEND,
)

_pg_instance: PostgresSceneStore | None = None


def _get_pg_instance() -> PostgresSceneStore:
    global _pg_instance
    if _pg_instance is None:
        if not DATABASE_URL:
            raise ValueError('SCENE_STORE_BACKEND=postgres requires DATABASE_URL')
        _pg_instance = PostgresSceneStore(DATABASE_URL, DATABASE_SCHEMA)
    return _pg_instance


def create_public_scene_store():
    backend = (SCENE_STORE_BACKEND or 'json').strip().lower()
    if backend == 'postgres':
        return _get_pg_instance()
    return SceneStore(PUBLIC_SCENES_FILE)


def create_generated_scene_store():
    backend = (SCENE_STORE_BACKEND or 'json').strip().lower()
    if backend == 'postgres':
        return _get_pg_instance()
    return GeneratedSceneStore(GENERATED_SCENES_FILE)

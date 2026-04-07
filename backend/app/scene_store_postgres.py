import json
from typing import Any

from .postgres import connect_postgres
from .scene_adapter import apply_hotspot_updates
from .scene_postgres_schema import ensure_scene_postgres_schema
from .store_utils import utcnow_iso


def _scene_to_row(scene: dict[str, Any]) -> dict[str, Any]:
    meta = scene.get('meta') or {}
    return {
        'scene_id': scene.get('sceneId') or '',
        'title': scene.get('title') or '',
        'category': scene.get('category') or '',
        'visibility': scene.get('visibility') or meta.get('visibility') or 'public',
        'scene_type': scene.get('sceneType') or meta.get('sceneType') or 'public',
        'cover_path': scene.get('coverPath') or '',
        'background_path': scene.get('backgroundPath') or '',
        'items': json.dumps(scene.get('items') or [], ensure_ascii=False),
        'verbs': json.dumps(scene.get('verbs') or [], ensure_ascii=False),
        'meta_json': json.dumps(meta, ensure_ascii=False),
        'owner_id': meta.get('ownerId') or None,
    }


def _row_to_scene(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    meta = row.get('meta_json') or {}
    if not isinstance(meta, dict):
        meta = json.loads(meta) if isinstance(meta, str) else {}
    return {
        'sceneId': row.get('scene_id', ''),
        'title': row.get('title', ''),
        'category': row.get('category', ''),
        'visibility': row.get('visibility', 'public'),
        'sceneType': row.get('scene_type', 'public'),
        'coverPath': row.get('cover_path', ''),
        'backgroundPath': row.get('background_path', ''),
        'items': row.get('items') or [],
        'verbs': row.get('verbs') or [],
        'meta': meta,
    }


class PostgresSceneStore:
    def __init__(self, database_url: str, schema_name: str = 'public'):
        self.database_url = database_url
        self.schema_name = schema_name
        self._ensure_ready()

    def _connect(self):
        return connect_postgres(self.database_url, self.schema_name)

    def _ensure_ready(self) -> None:
        with self._connect() as connection:
            ensure_scene_postgres_schema(connection)

    def list_scenes(self, filter_param: str | None = None) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                if not filter_param:
                    cursor.execute(
                        'select * from scenes order by created_at desc',
                    )
                elif filter_param.startswith('scene_') or filter_param in ('public', 'private', 'member'):
                    cursor.execute(
                        'select * from scenes where scene_type = %s order by created_at desc',
                        (filter_param,),
                    )
                else:
                    cursor.execute(
                        'select * from scenes where owner_id = %s order by created_at desc',
                        (filter_param,),
                    )
                return [_row_to_scene(row) for row in cursor.fetchall()]

    def get_scene(self, scene_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    'select * from scenes where scene_id = %s limit 1',
                    (scene_id,),
                )
                return _row_to_scene(cursor.fetchone())

    def upsert_scene(self, scene: dict[str, Any]) -> dict[str, Any]:
        row = _scene_to_row(scene)
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    insert into scenes (
                      scene_id, title, category, visibility, scene_type,
                      cover_path, background_path, items, verbs, meta_json,
                      owner_id, created_at, updated_at
                    ) values (
                      %s, %s, %s, %s, %s,
                      %s, %s, %s::jsonb, %s::jsonb, %s::jsonb,
                      %s, now(), now()
                    )
                    on conflict (scene_id) do update set
                      title = excluded.title,
                      category = excluded.category,
                      visibility = excluded.visibility,
                      scene_type = excluded.scene_type,
                      cover_path = excluded.cover_path,
                      background_path = excluded.background_path,
                      items = excluded.items,
                      verbs = excluded.verbs,
                      meta_json = excluded.meta_json,
                      owner_id = excluded.owner_id,
                      updated_at = now()
                    returning *
                    """,
                    (
                        row['scene_id'],
                        row['title'],
                        row['category'],
                        row['visibility'],
                        row['scene_type'],
                        row['cover_path'],
                        row['background_path'],
                        row['items'],
                        row['verbs'],
                        row['meta_json'],
                        row['owner_id'],
                    ),
                )
                return _row_to_scene(cursor.fetchone())

    def update_hotspots(
        self,
        scene_id: str,
        hotspot_items: list[dict[str, Any]],
        *,
        operator_id: str,
    ) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    'select * from scenes where scene_id = %s limit 1 for update',
                    (scene_id,),
                )
                row = cursor.fetchone()
                if not row:
                    return None

                scene = _row_to_scene(row)
                updated = apply_hotspot_updates(
                    scene,
                    hotspot_items,
                    operator_id=operator_id,
                    updated_at=utcnow_iso(),
                )

                update_row = _scene_to_row(updated)
                cursor.execute(
                    """
                    update scenes set
                      items = %s::jsonb,
                      meta_json = %s::jsonb,
                      updated_at = now()
                    where scene_id = %s
                    returning *
                    """,
                    (
                        update_row['items'],
                        update_row['meta_json'],
                        scene_id,
                    ),
                )
                return _row_to_scene(cursor.fetchone())

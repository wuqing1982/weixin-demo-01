from typing import Any


def _normalize_id_set(values: list[str] | set[str] | tuple[str, ...] | None) -> set[str]:
    normalized = set()
    for value in values or []:
        item = str(value or '').strip()
        if item:
            normalized.add(item)
    return normalized


def _is_allowed(user_id: str, allowed_ids: set[str]) -> bool:
    return '*' in allowed_ids or user_id in allowed_ids


def can_edit_scene_hotspots(
    scene: dict[str, Any] | None,
    user_id: str,
    config: dict[str, Any],
) -> bool:
    if not scene or not str(user_id or '').strip():
        return False

    if not config.get('enabled', False):
        return False

    user_id = str(user_id).strip()
    meta = scene.get('meta', {}) or {}
    admin_user_ids = _normalize_id_set(config.get('admin_user_ids'))

    if _is_allowed(user_id, admin_user_ids):
        return True

    if meta.get('hotspotEditable') is False:
        return False

    scene_editor_ids = _normalize_id_set(meta.get('hotspotEditors'))
    if _is_allowed(user_id, scene_editor_ids):
        return True

    scene_type = scene.get('sceneType') or meta.get('sceneType') or 'public'
    if scene_type == 'private':
        owner_id = str(meta.get('ownerId') or '').strip()
        if not owner_id:
            return True

        if owner_id == user_id:
            return True

        private_editor_ids = _normalize_id_set(config.get('private_editor_ids'))
        return _is_allowed(user_id, private_editor_ids)

    public_editor_ids = _normalize_id_set(config.get('public_editor_ids'))
    return _is_allowed(user_id, public_editor_ids)

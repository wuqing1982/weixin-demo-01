from __future__ import annotations

from .store_utils import utcnow_iso


def publish_generated_scene_to_public(
    *,
    source_scene: dict,
    source_scene_id: str,
    public_store,
    commerce_store,
    category_id: str,
    collection_ids: list[str],
    visibility: str,
    published_by: str,
    title: str = '',
) -> tuple[dict, dict]:
    category = commerce_store.get_scene_category(category_id)
    if not category:
        raise ValueError('scene category not found')

    collections = [commerce_store.get_scene_collection(collection_id) for collection_id in collection_ids]
    if any(item is None for item in collections):
        raise ValueError('scene collection not found')

    publication = commerce_store.get_scene_publication_by_source(source_scene_id)
    public_scene_id = publication.get('publicSceneId') if publication else ''
    current_public_scene = public_store.get_scene(public_scene_id) if public_scene_id else None
    published_at = utcnow_iso()
    normalized_collection_ids: list[str] = []
    for collection_id in collection_ids or []:
        if collection_id and collection_id not in normalized_collection_ids:
            normalized_collection_ids.append(collection_id)

    next_public_scene = (current_public_scene or {}) | {
        'sceneId': public_scene_id or '',
        'title': (title or '').strip() or source_scene.get('title', ''),
        'category': category.get('name', ''),
        'visibility': visibility or 'public',
        'sceneType': 'public',
        'backgroundPath': source_scene.get('backgroundPath', ''),
        'coverPath': source_scene.get('coverPath', ''),
        'items': source_scene.get('items', []),
        'verbs': source_scene.get('verbs', []),
        'meta': {
            **(source_scene.get('meta', {}) or {}),
            **((current_public_scene or {}).get('meta', {}) or {}),
            'sourceGeneratedSceneId': source_scene_id,
            'publishedBy': published_by,
            'publishedAt': published_at,
            'categoryId': category.get('categoryId', ''),
            'collectionIds': normalized_collection_ids,
        },
    }
    public_scene = public_store.upsert_scene(next_public_scene)
    publication = commerce_store.upsert_scene_publication(
        source_generated_scene_id=source_scene_id,
        public_scene_id=public_scene.get('sceneId', ''),
        category_id=category.get('categoryId', ''),
        collection_ids=normalized_collection_ids,
        visibility=visibility or 'public',
        published_by=published_by,
    )
    return public_scene, publication

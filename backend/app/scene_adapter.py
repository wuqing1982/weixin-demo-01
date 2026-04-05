import copy
from typing import Any


MIN_HOTSPOT_SIZE = 4.0


def clamp_percent(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return round(max(0.0, min(100.0, number)), 2)


def normalize_rect(rect: dict[str, Any] | None) -> dict[str, float]:
    rect = rect or {}
    return {
        'l': clamp_percent(rect.get('l', 0)),
        't': clamp_percent(rect.get('t', 0)),
        'w': clamp_percent(rect.get('w', 0)),
        'h': clamp_percent(rect.get('h', 0)),
    }


def normalize_hotspot_rect(rect: dict[str, Any] | None) -> dict[str, float]:
    safe_rect = normalize_rect(rect)
    width = round(min(100.0, max(MIN_HOTSPOT_SIZE, safe_rect['w'])), 2)
    height = round(min(100.0, max(MIN_HOTSPOT_SIZE, safe_rect['h'])), 2)
    left = round(min(safe_rect['l'], 100.0 - width), 2)
    top = round(min(safe_rect['t'], 100.0 - height), 2)

    return {
        'l': max(0.0, left),
        't': max(0.0, top),
        'w': width,
        'h': height,
    }


def apply_hotspot_updates(
    scene: dict[str, Any],
    hotspot_items: list[dict[str, Any]],
    *,
    operator_id: str,
    updated_at: str,
) -> dict[str, Any]:
    if not hotspot_items:
        raise ValueError('at least one hotspot update is required')

    updates_by_id = {}
    for item in hotspot_items:
        item_id = (item or {}).get('id', '')
        if not item_id:
            raise ValueError('hotspot id is required')
        updates_by_id[item_id] = normalize_hotspot_rect((item or {}).get('rect'))

    next_scene = copy.deepcopy(scene)
    found_ids = set()

    for item in next_scene.get('items', []):
        item_id = item.get('id', '')
        if item_id in updates_by_id:
            item['rect'] = updates_by_id[item_id]
            found_ids.add(item_id)

    missing_ids = sorted(set(updates_by_id.keys()) - found_ids)
    if missing_ids:
        raise ValueError(f'unknown hotspot ids: {", ".join(missing_ids)}')

    meta = next_scene.setdefault('meta', {})
    current_version = meta.get('version')
    try:
        version_number = int(current_version)
    except (TypeError, ValueError):
        version_number = 0

    meta['version'] = max(1, version_number + 1)
    meta['hotspotEditable'] = True
    meta['hotspotUpdatedAt'] = updated_at
    meta['hotspotUpdatedBy'] = operator_id
    return next_scene


def build_runtime_entry(entry: dict[str, Any], *, include_rect: bool) -> dict[str, Any]:
    payload: dict[str, Any] = {
        'id': entry.get('id', ''),
        'word': entry.get('word', entry.get('id', '')).replace('_', ' '),
        'ipa': entry.get('ipa', ''),
        'meaning': entry.get('meaning', ''),
        'sentence': entry.get('sentence', ''),
        'sentenceTranslation': entry.get('sentenceTranslation') or entry.get('sentence_translation', ''),
        'audioPath': entry.get('audioPath', ''),
    }

    if include_rect:
        payload['rect'] = normalize_rect(entry.get('rect'))

    related_item = entry.get('relatedItem') or entry.get('related_item')
    if related_item:
        payload['relatedItem'] = related_item

    return payload


def build_generated_scene_from_core_result(
    *,
    scene_id: str,
    title: str,
    image_asset_path: str,
    owner_id: str,
    upload_id: str,
    accent: str,
    gender: str,
    voice_name: str,
    core_result: dict[str, Any],
) -> dict[str, Any]:
    items = [
        build_runtime_entry(item, include_rect=True)
        for item in core_result.get('hotspots', [])
        if item.get('id')
    ]
    verbs = [
        build_runtime_entry(verb, include_rect=False)
        for verb in core_result.get('verbs', [])
        if verb.get('id')
    ]
    category = core_result.get('recommended_category') or 'generated'
    tags = core_result.get('recommended_tags') or []

    return {
        'sceneId': scene_id,
        'title': title,
        'category': category,
        'visibility': 'private',
        'sceneType': 'private',
        'coverPath': image_asset_path,
        'backgroundPath': image_asset_path,
        'items': items,
        'verbs': verbs,
        'meta': {
            'sceneType': 'private',
            'visibility': 'private',
            'sourceType': 'upload',
            'ownerId': owner_id,
            'uploadId': upload_id,
            'generatorMode': 'core100',
            'accent': accent,
            'voiceGender': gender,
            'voiceName': voice_name,
            'core100SceneId': core_result.get('scene_id', ''),
            'core100SceneTitle': core_result.get('scene_title', ''),
            'recommendedCategory': category,
            'tags': tags,
            'version': 1,
        },
    }

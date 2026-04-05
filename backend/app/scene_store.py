import copy
from pathlib import Path
from threading import Lock
from typing import Any

from .scene_adapter import apply_hotspot_updates
from .store_utils import ensure_json_file, read_json_file, utcnow_iso, write_json_file


class SceneStore:
    def __init__(self, data_file: Path):
        self.data_file = data_file
        self.lock = Lock()
        ensure_json_file(self.data_file, {'scenes': []})

    def list_scenes(self, scene_type: str = 'public') -> list[dict[str, Any]]:
        with self.lock:
            scenes = read_json_file(self.data_file).get('scenes', [])
        if not scene_type:
            return copy.deepcopy(scenes)
        return [copy.deepcopy(scene) for scene in scenes if scene.get('sceneType') == scene_type]

    def get_scene(self, scene_id: str) -> dict[str, Any] | None:
        with self.lock:
            scenes = read_json_file(self.data_file).get('scenes', [])

        for scene in scenes:
            if scene.get('sceneId') == scene_id:
                return copy.deepcopy(scene)
        return None

    def update_hotspots(
        self,
        scene_id: str,
        hotspot_items: list[dict[str, Any]],
        *,
        operator_id: str,
    ) -> dict[str, Any]:
        with self.lock:
            payload = read_json_file(self.data_file)
            scenes = payload.get('scenes', [])

            for index, scene in enumerate(scenes):
                if scene.get('sceneId') != scene_id:
                    continue

                updated = apply_hotspot_updates(
                    scene,
                    hotspot_items,
                    operator_id=operator_id,
                    updated_at=utcnow_iso(),
                )
                scenes[index] = updated
                write_json_file(self.data_file, payload)
                return copy.deepcopy(updated)

        return None

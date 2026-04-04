import copy
import json
from functools import lru_cache
from pathlib import Path
from typing import Any


class SceneStore:
    def __init__(self, data_file: Path):
        self.data_file = data_file

    @lru_cache(maxsize=1)
    def _load(self) -> dict[str, Any]:
        with self.data_file.open('r', encoding='utf-8') as handle:
            return json.load(handle)

    def list_scenes(self, scene_type: str = 'public') -> list[dict[str, Any]]:
        scenes = self._load().get('scenes', [])
        if not scene_type:
            return copy.deepcopy(scenes)
        return [copy.deepcopy(scene) for scene in scenes if scene.get('sceneType') == scene_type]

    def get_scene(self, scene_id: str) -> dict[str, Any] | None:
        for scene in self._load().get('scenes', []):
            if scene.get('sceneId') == scene_id:
                return copy.deepcopy(scene)
        return None

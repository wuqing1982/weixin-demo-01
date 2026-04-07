import copy
from pathlib import Path
from threading import Lock
from typing import Any

from .store_utils import build_object_id, ensure_json_file, read_json_file, utcnow_iso, write_json_file


class TaskStore:
    def __init__(self, data_file: Path):
        self.data_file = data_file
        self.lock = Lock()
        ensure_json_file(self.data_file, {'tasks': []})

    def create_task(self, *, owner_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        task_id = build_object_id('task')
        now = utcnow_iso()
        task = {
            'taskId': task_id,
            'ownerId': owner_id,
            'uploadId': payload.get('uploadId', ''),
            'title': payload.get('title', ''),
            'includeVerbs': bool(payload.get('includeVerbs', True)),
            'sourceLang': payload.get('sourceLang', 'zh-CN'),
            'accent': payload.get('accent', 'en-US'),
            'voiceGender': payload.get('voiceGender', 'female'),
            'voiceName': payload.get('voiceName', 'JennyNeural'),
            'requestSource': payload.get('requestSource', 'miniapp'),
            'autoPublish': bool(payload.get('autoPublish', False)),
            'categoryId': payload.get('categoryId', ''),
            'collectionIds': list(payload.get('collectionIds', []) or []),
            'publishVisibility': payload.get('publishVisibility', 'public'),
            'status': 'queued',
            'step': 'queued',
            'progress': 0,
            'sceneId': '',
            'publishedSceneId': '',
            'errorMessage': '',
            'createdAt': now,
            'updatedAt': now,
        }

        with self.lock:
            data = read_json_file(self.data_file)
            data.setdefault('tasks', []).append(task)
            write_json_file(self.data_file, data)

        return copy.deepcopy(task)

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with self.lock:
            tasks = read_json_file(self.data_file).get('tasks', [])

        for task in tasks:
            if task.get('taskId') == task_id:
                return copy.deepcopy(task)
        return None

    def update_task(self, task_id: str, **changes: Any) -> dict[str, Any] | None:
        with self.lock:
            data = read_json_file(self.data_file)
            tasks = data.setdefault('tasks', [])
            for index, task in enumerate(tasks):
                if task.get('taskId') != task_id:
                    continue

                next_task = dict(task)
                next_task.update(changes)
                next_task['updatedAt'] = utcnow_iso()
                tasks[index] = next_task
                write_json_file(self.data_file, data)
                return copy.deepcopy(next_task)

        return None

    def list_tasks(self, limit: int = 100) -> list[dict[str, Any]]:
        limit = max(1, int(limit or 100))
        with self.lock:
            tasks = read_json_file(self.data_file).get('tasks', [])
        ordered = sorted(
            tasks,
            key=lambda item: item.get('updatedAt') or item.get('createdAt') or '',
            reverse=True,
        )
        return [copy.deepcopy(task) for task in ordered[:limit]]

    def retry_task(self, task_id: str) -> dict[str, Any] | None:
        with self.lock:
            data = read_json_file(self.data_file)
            tasks = data.setdefault('tasks', [])
            for index, task in enumerate(tasks):
                if task.get('taskId') != task_id:
                    continue
                next_task = dict(task)
                next_task['status'] = 'queued'
                next_task['step'] = 'queued'
                next_task['progress'] = 0
                next_task['sceneId'] = ''
                next_task['publishedSceneId'] = ''
                next_task['errorMessage'] = ''
                next_task['updatedAt'] = utcnow_iso()
                tasks[index] = next_task
                write_json_file(self.data_file, data)
                return copy.deepcopy(next_task)
        return None

    def claim_next_task(self) -> dict[str, Any] | None:
        with self.lock:
            data = read_json_file(self.data_file)
            tasks = data.setdefault('tasks', [])
            for index, task in enumerate(tasks):
                if task.get('status') != 'queued':
                    continue

                claimed = dict(task)
                claimed['status'] = 'running'
                claimed['step'] = 'starting'
                claimed['progress'] = 5
                claimed['updatedAt'] = utcnow_iso()
                tasks[index] = claimed
                write_json_file(self.data_file, data)
                return copy.deepcopy(claimed)

        return None

    def delete_tasks(self, task_ids: list[str]) -> int:
        if not task_ids:
            return 0
        id_set = set(task_ids)
        with self.lock:
            data = read_json_file(self.data_file)
            tasks = data.setdefault('tasks', [])
            before = len(tasks)
            data['tasks'] = [t for t in tasks if t.get('taskId') not in id_set]
            write_json_file(self.data_file, data)
            return before - len(data['tasks'])

    def requeue_unfinished_tasks(self) -> None:
        with self.lock:
            data = read_json_file(self.data_file)
            tasks = data.setdefault('tasks', [])
            changed = False
            for index, task in enumerate(tasks):
                if task.get('status') != 'running':
                    continue

                next_task = dict(task)
                next_task['status'] = 'queued'
                next_task['step'] = 'queued'
                next_task['updatedAt'] = utcnow_iso()
                tasks[index] = next_task
                changed = True

            if changed:
                write_json_file(self.data_file, data)

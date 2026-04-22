"""
One-off script: find all done tasks with autoPublish=True but publishedSceneId empty,
then publish them to the public store.

Usage:
    cd backend && python3 scripts/republish_unpublished_scenes.py [--dry-run]
"""
import json
import sys
from pathlib import Path

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.commerce_store_factory import create_commerce_store
from app.generated_scene_store import GeneratedSceneStore
from app.scene_store import SceneStore
from app.scene_publication import publish_generated_scene_to_public

DATA_DIR = Path(__file__).resolve().parent.parent / 'data'


def main() -> None:
    dry_run = '--dry-run' in sys.argv

    tasks_path = DATA_DIR / 'tasks.json'
    gen_store = GeneratedSceneStore(DATA_DIR / 'generated_scenes.json')
    pub_store = SceneStore(DATA_DIR / 'scenes.json')
    commerce_store = create_commerce_store()

    if not commerce_store:
        print('ERROR: commerce_store is None. Check COMMERCE_STORE_BACKEND.')
        sys.exit(1)

    tasks = json.loads(tasks_path.read_text()).get('tasks', [])
    targets = [
        t for t in tasks
        if t.get('status') == 'done'
        and t.get('autoPublish')
        and t.get('categoryId')
        and not t.get('publishedSceneId')
    ]

    print(f'Found {len(targets)} unpublished scenes with autoPublish=True')
    if not targets:
        print('Nothing to do.')
        return

    success_count = 0
    fail_count = 0

    for task in targets:
        task_id = task['taskId']
        scene_id = task.get('sceneId', '')
        category_id = task.get('categoryId', '')
        title = (task.get('title') or '').strip()

        scene = gen_store.get_scene(scene_id)
        if not scene:
            print(f'  SKIP {task_id}: generated scene {scene_id} not found')
            fail_count += 1
            continue

        # Skip if already published (publication exists in commerce_store)
        existing_pub = commerce_store.get_scene_publication_by_source(scene_id)
        if existing_pub and existing_pub.get('publicSceneId'):
            print(f'  SKIP {task_id}: already has publication -> {existing_pub["publicSceneId"]}')
            # Update task record to link the publishedSceneId
            if not dry_run:
                _patch_task_published_id(tasks_path, tasks, task_id, existing_pub['publicSceneId'])
            continue

        if dry_run:
            print(f'  DRY-RUN {task_id}: would publish scene={scene_id} cat={category_id} title="{title}"')
            success_count += 1
            continue

        try:
            public_scene, publication = publish_generated_scene_to_public(
                source_scene=scene,
                source_scene_id=scene_id,
                public_store=pub_store,
                commerce_store=commerce_store,
                category_id=category_id,
                collection_ids=task.get('collectionIds', []) or [],
                visibility=task.get('publishVisibility', 'public') or 'public',
                published_by=task.get('ownerId', ''),
                title=title,
            )
            pub_id = public_scene.get('sceneId', '')
            _patch_task_published_id(tasks_path, tasks, task_id, pub_id)
            print(f'  OK   {task_id}: published -> {pub_id}  title="{title}"')
            success_count += 1
        except Exception as exc:
            print(f'  FAIL {task_id}: {exc}')
            fail_count += 1

    mode = 'DRY-RUN' if dry_run else 'DONE'
    print(f'\n{mode}: {success_count} published, {fail_count} failed/skipped')


def _patch_task_published_id(tasks_path: Path, tasks: list[dict], task_id: str, pub_id: str) -> None:
    for t in tasks:
        if t['taskId'] == task_id:
            t['publishedSceneId'] = pub_id
            break
    tasks_path.write_text(json.dumps({'tasks': tasks}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

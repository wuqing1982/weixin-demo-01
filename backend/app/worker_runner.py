import json
import re
import shutil
import tempfile
from pathlib import Path
from threading import Event, Thread

from .generated_scene_store import GeneratedSceneStore
from .scene_publication import publish_generated_scene_to_public
from .scene_adapter import build_generated_scene_from_core_result
from .scene_worker.analyze_scene import analyze_scene_with_glm4v
from .scene_worker.generate_audio import generate_scene_audio
from .scene_worker.scene_assets import build_audio_filename
from .store_utils import build_object_id
from .task_store import TaskStore
from .upload_store import UploadStore


INVALID_UPLOAD_TITLE_PATTERNS = (
    re.compile(r'^tmp_[a-f0-9]{12,}$', re.IGNORECASE),
    re.compile(r'^source$', re.IGNORECASE),
    re.compile(r'^upload_[0-9]{8,}_[a-f0-9]+$', re.IGNORECASE),
)


def normalize_candidate_title(value: str | None) -> str:
    text = (value or '').strip()
    if not text:
        return ''
    text = Path(text).stem.strip()
    text = re.sub(r'[_-]+', ' ', text).strip()
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def is_placeholder_upload_title(value: str | None) -> bool:
    raw_title = Path((value or '').strip()).stem.strip()
    normalized_title = normalize_candidate_title(value)
    if not raw_title or not normalized_title:
        return True
    return any(pattern.match(raw_title) for pattern in INVALID_UPLOAD_TITLE_PATTERNS)


def derive_scene_title(
    *,
    explicit_title: str,
    ai_title: str,
    upload_filename: str,
) -> str:
    user_title = normalize_candidate_title(explicit_title)
    if user_title:
        return user_title

    model_title = normalize_candidate_title(ai_title)
    if model_title and not is_placeholder_upload_title(ai_title):
        return model_title

    upload_title = normalize_candidate_title(upload_filename)
    if upload_title and not is_placeholder_upload_title(upload_filename):
        return upload_title

    return '未命名场景'


class InlineSceneWorker:
    def __init__(
        self,
        *,
        task_store: TaskStore,
        upload_store: UploadStore,
        generated_scene_store: GeneratedSceneStore,
        generated_root: Path,
        tts_url: str,
        model: str,
        public_scene_store=None,
        commerce_store=None,
        api_key: str | None = None,
        poll_interval: float = 2.0,
    ):
        self.task_store = task_store
        self.upload_store = upload_store
        self.generated_scene_store = generated_scene_store
        self.generated_root = generated_root
        self.tts_url = tts_url
        self.model = model
        self.public_scene_store = public_scene_store
        self.commerce_store = commerce_store
        self.api_key = api_key
        self.poll_interval = poll_interval
        self.stop_event = Event()
        self.thread: Thread | None = None
        self.generated_root.mkdir(parents=True, exist_ok=True)

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return

        self.task_store.requeue_unfinished_tasks()
        self.thread = Thread(target=self._run, name='inline-scene-worker', daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)

    def _run(self) -> None:
        while not self.stop_event.is_set():
            task = self.task_store.claim_next_task()
            if not task:
                self.stop_event.wait(self.poll_interval)
                continue

            self._process_task(task)

    def _process_task(self, task: dict) -> None:
        task_id = task['taskId']

        try:
            self.task_store.update_task(task_id, step='load_upload', progress=15)
            upload = self.upload_store.get_upload(task['uploadId'])
            if not upload:
                raise RuntimeError('upload not found')

            scene_id = build_object_id('scene_user')
            self.task_store.update_task(task_id, step='prepare_assets', progress=45, sceneId=scene_id)

            image_asset_path = self._copy_source_image(scene_id, upload)
            explicit_title = (task.get('title') or '').strip()

            self.task_store.update_task(task_id, step='analyze_scene', progress=55, sceneId=scene_id)
            core_scene = self._analyze_scene(
                scene_id=scene_id,
                preferred_title=explicit_title,
                task=task,
                upload=upload,
            )
            scene_title = derive_scene_title(
                explicit_title=explicit_title,
                ai_title=core_scene.get('scene_title', ''),
                upload_filename=upload.get('originalFilename', ''),
            )
            core_scene['scene_title'] = scene_title

            self.task_store.update_task(task_id, step='generate_audio', progress=75, sceneId=scene_id)
            self._generate_audio(core_scene, task)
            self._attach_audio_paths(core_scene, task)

            scene = build_generated_scene_from_core_result(
                scene_id=scene_id,
                title=scene_title,
                image_asset_path=image_asset_path,
                owner_id=task['ownerId'],
                upload_id=upload['uploadId'],
                accent=task.get('accent', 'en-US'),
                gender=task.get('voiceGender', 'female'),
                voice_name=task.get('voiceName', 'JennyNeural'),
                core_result=core_scene,
            )

            self.task_store.update_task(task_id, step='write_scene', progress=90, sceneId=scene_id)
            self.generated_scene_store.upsert_scene(scene)
            published_scene_id = ''
            if task.get('autoPublish') and self.public_scene_store and self.commerce_store and task.get('categoryId'):
                self.task_store.update_task(task_id, step='publish_scene', progress=95, sceneId=scene_id)
                public_scene, _ = publish_generated_scene_to_public(
                    source_scene=scene,
                    source_scene_id=scene_id,
                    public_store=self.public_scene_store,
                    commerce_store=self.commerce_store,
                    category_id=task.get('categoryId', ''),
                    collection_ids=task.get('collectionIds', []) or [],
                    visibility=task.get('publishVisibility', 'public') or 'public',
                    published_by=task.get('ownerId', ''),
                    title=(task.get('title') or '').strip(),
                )
                published_scene_id = public_scene.get('sceneId', '')
            self.task_store.update_task(
                task_id,
                status='done',
                step='finished',
                progress=100,
                sceneId=scene_id,
                publishedSceneId=published_scene_id,
                errorMessage='',
            )
        except Exception as exc:
            self.task_store.update_task(
                task_id,
                status='failed',
                step='failed',
                progress=100,
                errorMessage=str(exc),
            )

    SCENE_ANALYSIS_MAX_RETRIES = 2

    def _analyze_scene(self, *, scene_id: str, preferred_title: str, task: dict, upload: dict) -> dict:
        source_path = self.upload_store.resolve_disk_path(upload['filePath'])
        if not source_path.exists():
            raise RuntimeError('uploaded source file missing')

        last_error = None
        for attempt in range(1 + self.SCENE_ANALYSIS_MAX_RETRIES):
            try:
                raw_result = analyze_scene_with_glm4v(
                    str(source_path),
                    'auto',
                    api_key=self.api_key,
                    model=self.model,
                    include_verbs=bool(task.get('includeVerbs', True)),
                )
                if not isinstance(raw_result, dict):
                    raise RuntimeError('scene analysis returned invalid payload')
                if not raw_result.get('hotspots'):
                    raise RuntimeError('scene analysis returned empty hotspots')
                break
            except (ValueError, RuntimeError) as exc:
                last_error = exc
                if attempt < self.SCENE_ANALYSIS_MAX_RETRIES:
                    print(f"⚠️  场景分析第 {attempt + 1} 次失败，正在重试: {exc}")
        else:
            raise last_error

        core_scene = dict(raw_result)
        core_scene['scene_id'] = scene_id
        if preferred_title:
            core_scene['scene_title'] = preferred_title
        else:
            core_scene['scene_title'] = normalize_candidate_title(core_scene.get('scene_title', ''))
        return core_scene

    def _generate_audio(self, core_scene: dict, task: dict) -> None:
        accent = task.get('accent', 'en-US')
        gender = task.get('voiceGender', 'female')
        if (accent, gender) not in {
            ('en-US', 'female'),
            ('en-US', 'male'),
            ('en-GB', 'female'),
            ('en-GB', 'male'),
        }:
            raise RuntimeError(f'unsupported voice config: {accent}/{gender}')

        with tempfile.TemporaryDirectory(prefix='scene-worker-') as temp_dir:
            json_path = Path(temp_dir) / 'scene.json'
            json_path.write_text(
                json.dumps(core_scene, ensure_ascii=False, indent=2),
                encoding='utf-8',
            )
            success_count, total_files = generate_scene_audio(
                str(json_path),
                tts_url=self.tts_url,
                output_root=str(self.generated_root),
                voice_priority=[(accent, gender)],
            )

        if total_files and success_count != total_files:
            raise RuntimeError(f'audio generation incomplete: {success_count}/{total_files}')

    def _attach_audio_paths(self, core_scene: dict, task: dict) -> None:
        scene_id = core_scene['scene_id']
        accent = task.get('accent', 'en-US')
        gender = task.get('voiceGender', 'female')
        audio_root = f'/assets/generated/{scene_id}'

        for key in ('hotspots', 'verbs'):
            entries = core_scene.get(key, [])
            if not isinstance(entries, list):
                continue
            for entry in entries:
                filename = build_audio_filename(scene_id, accent, gender, entry)
                entry['audioPath'] = f'{audio_root}/{filename}'

    def _derive_title_from_upload(self, upload: dict) -> str:
        return derive_scene_title(
            explicit_title='',
            ai_title='',
            upload_filename=upload.get('originalFilename') or '',
        )

    def _copy_source_image(self, scene_id: str, upload: dict) -> str:
        source_path = self.upload_store.resolve_disk_path(upload['filePath'])
        if not source_path.exists():
            raise RuntimeError('uploaded source file missing')

        suffix = source_path.suffix.lower() or '.jpg'
        scene_dir = self.generated_root / scene_id
        scene_dir.mkdir(parents=True, exist_ok=True)
        target_path = scene_dir / f'background{suffix}'
        shutil.copy2(source_path, target_path)
        return f"/{target_path.resolve().relative_to(self.generated_root.parents[1]).as_posix()}"

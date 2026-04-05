from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .generated_scene_store import GeneratedSceneStore
from .hotspot_permissions import can_edit_scene_hotspots
from .schemas import SceneGenerateRequest, SceneHotspotUpdateRequest
from .scene_store import SceneStore
from .settings import (
    ASSETS_DIR,
    CORE100_MODEL,
    CORE100_ROOT,
    CORE100_TTS_URL,
    DEFAULT_MOCK_USER_ID,
    ENABLE_INLINE_SCENE_WORKER,
    GENERATED_DIR,
    GENERATED_SCENES_FILE,
    HOTSPOT_EDITOR_ADMIN_USER_IDS,
    HOTSPOT_EDITOR_ENABLED,
    HOTSPOT_EDITOR_PRIVATE_EDITOR_IDS,
    HOTSPOT_EDITOR_PUBLIC_EDITOR_IDS,
    PUBLIC_BASE_URL,
    PUBLIC_SCENES_FILE,
    TASKS_FILE,
    UPLOADS_DIR,
    UPLOADS_FILE,
    WORKER_POLL_INTERVAL,
    ZHIPUAI_API_KEY,
)
from .task_store import TaskStore
from .upload_store import UploadStore
from .worker_runner import InlineSceneWorker


public_store = SceneStore(PUBLIC_SCENES_FILE)
generated_store = GeneratedSceneStore(GENERATED_SCENES_FILE)
upload_store = UploadStore(UPLOADS_FILE, UPLOADS_DIR)
task_store = TaskStore(TASKS_FILE)
scene_worker = InlineSceneWorker(
    task_store=task_store,
    upload_store=upload_store,
    generated_scene_store=generated_store,
    generated_root=GENERATED_DIR,
    core100_root=CORE100_ROOT,
    tts_url=CORE100_TTS_URL,
    model=CORE100_MODEL,
    api_key=ZHIPUAI_API_KEY,
    poll_interval=WORKER_POLL_INTERVAL,
)

app = FastAPI(
    title='English Scene API',
    version='0.1.0'
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

app.mount('/assets', StaticFiles(directory=str(ASSETS_DIR)), name='assets')


def success(data):
    return {
        'code': 0,
        'data': data
    }


def hotspot_permission_config():
    return {
        'enabled': HOTSPOT_EDITOR_ENABLED,
        'admin_user_ids': HOTSPOT_EDITOR_ADMIN_USER_IDS,
        'public_editor_ids': HOTSPOT_EDITOR_PUBLIC_EDITOR_IDS,
        'private_editor_ids': HOTSPOT_EDITOR_PRIVATE_EDITOR_IDS,
    }


@app.exception_handler(HTTPException)
async def handle_http_exception(_: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, dict) else {
        'code': exc.status_code,
        'message': str(exc.detail)
    }
    return JSONResponse(status_code=exc.status_code, content=detail)


@app.on_event('startup')
def on_startup():
    if ENABLE_INLINE_SCENE_WORKER:
        scene_worker.start()


@app.on_event('shutdown')
def on_shutdown():
    scene_worker.stop()


def asset_url(request: Request, value: str | None) -> str:
    if not value:
        return ''
    if value.startswith('http://') or value.startswith('https://'):
        return value
    base = PUBLIC_BASE_URL or str(request.base_url).rstrip('/')
    path = value if value.startswith('/') else f'/{value}'
    return f'{base}{path}'


def serialize_entry(request: Request, entry: dict) -> dict:
    payload = dict(entry)
    audio_path = payload.pop('audioPath', '')
    payload['audio'] = asset_url(request, audio_path)
    return payload


def serialize_scene_summary(request: Request, scene: dict) -> dict:
    return {
        'sceneId': scene['sceneId'],
        'title': scene['title'],
        'coverUrl': asset_url(request, scene.get('coverPath')),
        'category': scene.get('category', ''),
        'visibility': scene.get('visibility', 'member'),
        'sceneType': scene.get('sceneType', 'public')
    }


def serialize_scene_detail(request: Request, scene: dict) -> dict:
    can_edit_hotspots = can_edit_scene_hotspots(
        scene,
        get_current_user_id(request),
        hotspot_permission_config(),
    )
    return {
        'sceneId': scene['sceneId'],
        'title': scene['title'],
        'background': asset_url(request, scene.get('backgroundPath')),
        'cover': asset_url(request, scene.get('coverPath')),
        'items': [serialize_entry(request, item) for item in scene.get('items', [])],
        'verbs': [serialize_entry(request, verb) for verb in scene.get('verbs', [])],
        'meta': scene.get('meta', {}),
        'capabilities': {
            'canEditHotspots': can_edit_hotspots
        }
    }


def get_current_user_id(request: Request) -> str:
    return request.headers.get('X-Debug-User-Id', '').strip() or DEFAULT_MOCK_USER_ID


@app.get('/api/health')
def health():
    return success({
        'status': 'ok',
        'workerEnabled': ENABLE_INLINE_SCENE_WORKER,
        'workerMode': 'core100',
    })


@app.get('/api/scenes')
def list_scenes(
    request: Request,
    type: str = Query(default='public'),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=20, ge=1, le=100)
):
    scenes = public_store.list_scenes(type)
    total = len(scenes)
    start = (page - 1) * pageSize
    end = start + pageSize
    page_items = scenes[start:end]

    return success({
        'list': [serialize_scene_summary(request, scene) for scene in page_items],
        'total': total,
        'page': page,
        'pageSize': pageSize
    })


@app.get('/api/scenes/{scene_id}')
def get_scene(scene_id: str, request: Request):
    scene = public_store.get_scene(scene_id)
    if not scene:
        scene = generated_store.get_scene(scene_id)
        if scene and scene.get('meta', {}).get('ownerId') != get_current_user_id(request):
            raise HTTPException(
                status_code=403,
                detail={
                    'code': 4003,
                    'message': 'scene access denied'
                }
            )

    if not scene:
        raise HTTPException(
            status_code=404,
            detail={
                'code': 4004,
                'message': 'scene not found'
            }
        )

    return success(serialize_scene_detail(request, scene))


@app.post('/api/scenes/{scene_id}/hotspots')
def save_scene_hotspots(scene_id: str, payload: SceneHotspotUpdateRequest, request: Request):
    operator_id = get_current_user_id(request)
    hotspot_items = [item.model_dump() for item in payload.items]
    permission_config = hotspot_permission_config()

    scene = public_store.get_scene(scene_id)
    if scene:
        if not can_edit_scene_hotspots(scene, operator_id, permission_config):
            raise HTTPException(
                status_code=403,
                detail={
                    'code': 4003,
                    'message': 'hotspot edit denied'
                }
            )
        try:
            updated_scene = public_store.update_hotspots(
                scene_id,
                hotspot_items,
                operator_id=operator_id,
            )
        except ValueError as error:
            raise HTTPException(
                status_code=400,
                detail={
                    'code': 4000,
                    'message': str(error)
                }
            ) from error
        return success(serialize_scene_detail(request, updated_scene))

    scene = generated_store.get_scene(scene_id)
    if scene and not can_edit_scene_hotspots(scene, operator_id, permission_config):
        raise HTTPException(
            status_code=403,
            detail={
                'code': 4003,
                'message': 'hotspot edit denied'
            }
        )

    if not scene:
        raise HTTPException(
            status_code=404,
            detail={
                'code': 4004,
                'message': 'scene not found'
            }
        )

    try:
        updated_scene = generated_store.update_hotspots(
            scene_id,
            hotspot_items,
            operator_id=operator_id,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail={
                'code': 4000,
                'message': str(error)
            }
        ) from error

    return success(serialize_scene_detail(request, updated_scene))


@app.get('/api/my/scenes')
def get_my_scenes(
    request: Request,
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=20, ge=1, le=100)
):
    owner_id = get_current_user_id(request)
    scenes = generated_store.list_scenes(owner_id)
    total = len(scenes)
    start = (page - 1) * pageSize
    end = start + pageSize
    page_items = scenes[start:end]

    return success({
        'list': [serialize_scene_summary(request, scene) for scene in page_items],
        'total': total,
        'page': page,
        'pageSize': pageSize
    })


@app.post('/api/uploads/image')
async def upload_image(request: Request, file: UploadFile = File(...)):
    owner_id = get_current_user_id(request)
    content = await file.read()

    if not content:
        raise HTTPException(
            status_code=400,
            detail={
                'code': 4000,
                'message': 'empty file'
            }
        )

    content_type = file.content_type or ''
    if content_type and not content_type.startswith('image/'):
        raise HTTPException(
            status_code=400,
            detail={
                'code': 4000,
                'message': 'only image upload is supported'
            }
        )

    upload = upload_store.create_upload(
        owner_id=owner_id,
        filename=file.filename or 'upload.jpg',
        content_type=content_type,
        content=content,
    )

    return success({
        'uploadId': upload['uploadId'],
        'fileUrl': asset_url(request, upload['filePath']),
        'width': upload.get('width'),
        'height': upload.get('height')
    })


@app.post('/api/my/tasks/scene-generate')
def create_scene_generate_task(request: Request, payload: SceneGenerateRequest):
    owner_id = get_current_user_id(request)
    upload = upload_store.get_upload(payload.uploadId)
    if not upload:
        raise HTTPException(
            status_code=404,
            detail={
                'code': 4004,
                'message': 'upload not found'
            }
        )

    if upload.get('ownerId') != owner_id:
        raise HTTPException(
            status_code=403,
            detail={
                'code': 4003,
                'message': 'upload access denied'
            }
        )

    task = task_store.create_task(
        owner_id=owner_id,
        payload=payload.model_dump(),
    )
    return success({
        'taskId': task['taskId'],
        'status': task['status']
    })


@app.get('/api/my/tasks/{task_id}')
def get_scene_generate_task(request: Request, task_id: str):
    owner_id = get_current_user_id(request)
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail={
                'code': 4004,
                'message': 'task not found'
            }
        )

    if task.get('ownerId') != owner_id:
        raise HTTPException(
            status_code=403,
            detail={
                'code': 4003,
                'message': 'task access denied'
            }
        )

    return success({
        'taskId': task['taskId'],
        'status': task['status'],
        'step': task['step'],
        'progress': task['progress'],
        'sceneId': task.get('sceneId', ''),
        'errorMessage': task.get('errorMessage', '')
    })

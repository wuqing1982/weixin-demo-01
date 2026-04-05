import hashlib
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .auth_store import AuthStore
from .generated_scene_store import GeneratedSceneStore
from .hotspot_permissions import can_edit_scene_hotspots
from .schemas import (
    LogoutRequest,
    RefreshTokenRequest,
    SceneGenerateRequest,
    SceneHotspotUpdateRequest,
    WechatLoginRequest,
)
from .scene_store import SceneStore
from .security import create_access_token, decode_access_token, generate_refresh_token, hash_refresh_token
from .settings import (
    ASSETS_DIR,
    AUTH_ACCESS_TOKEN_TTL_SECONDS,
    AUTH_DATA_FILE,
    AUTH_ENABLE_DEBUG_USER_HEADER,
    AUTH_REFRESH_TOKEN_TTL_SECONDS,
    AUTH_WECHAT_LOGIN_MODE,
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


auth_store = AuthStore(AUTH_DATA_FILE)
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


def unauthorized(message: str = 'unauthorized'):
    raise HTTPException(
        status_code=401,
        detail={
            'code': 4001,
            'message': message,
        },
    )


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


def iso_after_seconds(seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=max(1, int(seconds)))).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def make_mock_openid(payload: WechatLoginRequest) -> str:
    seed = (payload.device.deviceId or payload.code or DEFAULT_MOCK_USER_ID).strip()
    digest = hashlib.sha256(seed.encode('utf-8')).hexdigest()[:24]
    return f'mock_openid_{digest}'


def serialize_user_profile(user: dict) -> dict:
    return {
        'id': user.get('id', ''),
        'displayName': user.get('displayName', ''),
        'avatarUrl': user.get('avatarUrl', ''),
        'mobile': user.get('mobile'),
        'mobileVerified': bool(user.get('mobileVerified')),
    }


def build_auth_response(request: Request, user: dict, session: dict, refresh_token: str) -> dict:
    access_token, access_expires_at = create_access_token(
        user.get('id', ''),
        session.get('id', ''),
        expires_in=AUTH_ACCESS_TOKEN_TTL_SECONDS,
    )
    return {
        'accessToken': access_token,
        'accessTokenExpiresIn': AUTH_ACCESS_TOKEN_TTL_SECONDS,
        'accessTokenExpireAt': datetime.fromtimestamp(access_expires_at, timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
        'refreshToken': refresh_token,
        'refreshTokenExpiresIn': AUTH_REFRESH_TOKEN_TTL_SECONDS,
        'refreshTokenExpireAt': session.get('expiresAt', ''),
        'user': serialize_user_profile(user),
        'me': serialize_me(request, user),
    }


def get_bearer_token(request: Request) -> str:
    header = (request.headers.get('Authorization') or '').strip()
    if not header.lower().startswith('bearer '):
        return ''
    return header[7:].strip()


def get_authenticated_user(request: Request) -> dict | None:
    token = get_bearer_token(request)
    if not token:
        return None

    try:
        payload = decode_access_token(token)
    except ValueError as error:
        unauthorized(str(error))

    user = auth_store.get_user(payload.get('sub', ''))
    if not user:
        unauthorized('user not found')
    if user.get('status') not in {'', 'active', None}:
        unauthorized('user disabled')
    return user


def get_request_user(
    request: Request,
    *,
    required: bool = False,
    allow_debug: bool = False,
    fallback_default: bool = False,
) -> dict | None:
    authenticated_user = get_authenticated_user(request)
    if authenticated_user:
        return authenticated_user

    debug_user_id = ''
    if allow_debug and AUTH_ENABLE_DEBUG_USER_HEADER:
        debug_user_id = (request.headers.get('X-Debug-User-Id') or '').strip()

    if debug_user_id:
        return auth_store.get_or_create_debug_user(debug_user_id)

    if fallback_default and DEFAULT_MOCK_USER_ID:
        return auth_store.get_or_create_debug_user(DEFAULT_MOCK_USER_ID)

    if required:
        unauthorized()
    return None


def serialize_me(_: Request, user: dict) -> dict:
    return {
        'id': user.get('id', ''),
        'displayName': user.get('displayName', ''),
        'avatarUrl': user.get('avatarUrl', ''),
        'mobile': user.get('mobile'),
        'mobileVerified': bool(user.get('mobileVerified')),
        'memberSummary': {
            'isActive': False,
            'expiresAt': None,
        },
        'creditSummary': {
            'sceneGenerateBalance': 0,
        },
    }


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
    actor = get_request_user(request, allow_debug=True, fallback_default=True)
    can_edit_hotspots = can_edit_scene_hotspots(
        scene,
        actor.get('id', '') if actor else '',
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
    user = get_request_user(request, allow_debug=True, fallback_default=True)
    return user.get('id', '') if user else DEFAULT_MOCK_USER_ID


@app.get('/api/health')
def health():
    return success({
        'status': 'ok',
        'workerEnabled': ENABLE_INLINE_SCENE_WORKER,
        'workerMode': 'core100',
    })


@app.post('/api/auth/wechat/login')
def auth_wechat_login(payload: WechatLoginRequest, request: Request):
    if AUTH_WECHAT_LOGIN_MODE != 'mock':
        raise HTTPException(
            status_code=501,
            detail={
                'code': 5001,
                'message': 'wechat login mode not implemented',
            },
        )

    provider_uid = make_mock_openid(payload)
    user = auth_store.get_or_create_wechat_user(
        provider_uid=provider_uid,
        profile={
            'displayName': '微信用户',
            'avatarUrl': '',
            'loginMode': 'mock',
        },
        session_key_encrypted='mock_session_key',
    )
    refresh_token = generate_refresh_token()
    refresh_session = auth_store.create_refresh_session(
        user_id=user['id'],
        token_hash=hash_refresh_token(refresh_token),
        expires_at=iso_after_seconds(AUTH_REFRESH_TOKEN_TTL_SECONDS),
        device=payload.device.model_dump(),
        ip=request.client.host if request.client else '',
        user_agent=request.headers.get('User-Agent', ''),
    )
    return success(build_auth_response(request, user, refresh_session, refresh_token))


@app.post('/api/auth/refresh')
def auth_refresh_token(payload: RefreshTokenRequest, request: Request):
    token_hash = hash_refresh_token(payload.refreshToken)
    session = auth_store.get_active_refresh_session(token_hash)
    if not session:
        unauthorized('refresh token invalid')

    user = auth_store.get_user(session.get('userId', ''))
    if not user:
        unauthorized('user not found')

    auth_store.revoke_session(session.get('id', ''))
    next_refresh_token = generate_refresh_token()
    next_session = auth_store.create_refresh_session(
        user_id=user['id'],
        token_hash=hash_refresh_token(next_refresh_token),
        expires_at=iso_after_seconds(AUTH_REFRESH_TOKEN_TTL_SECONDS),
        device={
            'deviceType': session.get('deviceType', ''),
            'deviceId': session.get('deviceId', ''),
            'appVersion': session.get('appVersion', ''),
        },
        ip=request.client.host if request.client else '',
        user_agent=request.headers.get('User-Agent', ''),
    )
    return success(build_auth_response(request, user, next_session, next_refresh_token))


@app.post('/api/auth/logout')
def auth_logout(request: Request, payload: LogoutRequest | None = None):
    revoked = False
    if payload and payload.refreshToken:
        revoked = auth_store.revoke_refresh_token(hash_refresh_token(payload.refreshToken)) or revoked

    token = get_bearer_token(request)
    if token:
        try:
            access_payload = decode_access_token(token)
            revoked = auth_store.revoke_session(access_payload.get('sid', '')) or revoked
        except ValueError:
            revoked = revoked

    if not revoked:
        raise HTTPException(
            status_code=400,
            detail={
                'code': 4000,
                'message': 'no active session to logout',
            },
        )
    return success({'revoked': True})


@app.get('/api/me')
def get_me(request: Request):
    user = get_request_user(request, required=True, allow_debug=True)
    return success(serialize_me(request, user))


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

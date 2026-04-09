import hashlib
import logging
from contextlib import asynccontextmanager
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger('english_scene_api')

from .auth_store_factory import create_auth_store
from .commerce_store_factory import create_commerce_store
from .generated_scene_store import GeneratedSceneStore
from .scene_store_factory import create_generated_scene_store, create_public_scene_store
from .hotspot_permissions import can_edit_scene_hotspots
from .schemas import (
    AdminBatchDeleteCdkRequest,
    AdminBatchDeleteOrdersRequest,
    AdminBatchDeleteScenesRequest,
    AdminBatchDeleteTasksRequest,
    AdminBatchDeleteUsersRequest,
    AdminBatchSceneGenerateRequest,
    AdminGenerateCdkRequest,
    AdminLoginRequest,
    AdminPublishGeneratedSceneRequest,
    AdminProductRequest,
    AdminPublicSceneRequest,
    AdminSceneCategoryRequest,
    AdminSceneCollectionRequest,
    AdminSkuRequest,
    CdkRedeemRequest,
    MeProfileUpdateRequest,
    MockPaymentCompleteRequest,
    LogoutRequest,
    OrderCreateRequest,
    RefreshTokenRequest,
    SceneGenerateRequest,
    SceneHotspotUpdateRequest,
    WechatLoginRequest,
)
from .scene_publication import publish_generated_scene_to_public
from .store_utils import utcnow_iso
from .scene_store import SceneStore
from .security import create_access_token, decode_access_token, encrypt_wechat_session_key, generate_refresh_token, hash_refresh_token
from .settings import (
    ADMIN_DASHBOARD_ENABLED,
    ADMIN_DASHBOARD_PASSWORD,
    ADMIN_DASHBOARD_USERNAME,
    ADMIN_WEB_DIR,
    ASSETS_DIR,
    AUTH_ACCESS_TOKEN_TTL_SECONDS,
    AUTH_DATA_FILE,
    AUTH_ENABLE_DEBUG_USER_HEADER,
    AUTH_REFRESH_TOKEN_TTL_SECONDS,
    AUTH_STORE_BACKEND,
    AUTH_WECHAT_LOGIN_MODE,
    CORE100_MODEL,
    CORE100_TTS_URL,
    CORS_ALLOWED_ORIGINS,
    DEFAULT_MOCK_USER_ID,
    ENABLE_INLINE_SCENE_WORKER,
    FREE_SCENE_IDS,
    GENERATED_DIR,
    GENERATED_SCENES_FILE,
    HOTSPOT_EDITOR_ADMIN_USER_IDS,
    HOTSPOT_EDITOR_ENABLED,
    HOTSPOT_EDITOR_PRIVATE_EDITOR_IDS,
    HOTSPOT_EDITOR_PUBLIC_EDITOR_IDS,
    MAX_UPLOAD_SIZE_BYTES,
    PAYMENT_MODE,
    PUBLIC_BASE_URL,
    PUBLIC_SCENES_FILE,
    SCENE_PAGE_SIZE,
    VIDEO_RETENTION_HOURS,
    TASKS_FILE,
    UPLOADS_DIR,
    UPLOADS_FILE,
    WECHAT_MP_APP_ID,
    WECHAT_MP_APP_SECRET,
    WECHAT_PAY_API_BASE,
    WECHAT_PAY_API_V3_KEY,
    WECHAT_PAY_CURRENCY,
    WECHAT_PAY_MCH_ID,
    WECHAT_PAY_MCH_PRIVATE_KEY_PATH,
    WECHAT_PAY_MCH_SERIAL_NO,
    WECHAT_PAY_NOTIFY_URL,
    WECHAT_PAY_PLATFORM_CERT_PATH,
    WECHAT_PAY_PLATFORM_SERIAL_NO,
    WECHAT_PAY_TIMEOUT_SECONDS,
    WORKER_POLL_INTERVAL,
    ZHIPUAI_API_KEY,
    check_security_warnings,
)
from .task_store import TaskStore
from .upload_store import UploadStore
from .wechat_auth import WechatCode2SessionError, WechatMiniProgramAuthClient
from .wechat_pay import WechatPayClient, build_wechat_pay_config
from .video_generator import (
    create_export_job,
    get_export_job,
    get_user_export_jobs,
    has_active_export,
    init_video_export,
    start_export,
    start_video_cleanup,
    stop_video_cleanup,
)
from .worker_runner import InlineSceneWorker
from . import access_control


auth_store = create_auth_store()
commerce_store = create_commerce_store()
wechat_auth_client = WechatMiniProgramAuthClient(WECHAT_MP_APP_ID, WECHAT_MP_APP_SECRET)
wechat_pay_client = WechatPayClient(build_wechat_pay_config(
    app_id=WECHAT_MP_APP_ID,
    mch_id=WECHAT_PAY_MCH_ID,
    api_v3_key=WECHAT_PAY_API_V3_KEY,
    mch_serial_no=WECHAT_PAY_MCH_SERIAL_NO,
    mch_private_key_path=WECHAT_PAY_MCH_PRIVATE_KEY_PATH,
    platform_cert_path=WECHAT_PAY_PLATFORM_CERT_PATH,
    platform_serial_no=WECHAT_PAY_PLATFORM_SERIAL_NO,
    notify_url=WECHAT_PAY_NOTIFY_URL,
    api_base=WECHAT_PAY_API_BASE,
    currency=WECHAT_PAY_CURRENCY,
    timeout_seconds=WECHAT_PAY_TIMEOUT_SECONDS,
))
public_store = create_public_scene_store()
generated_store = create_generated_scene_store()
upload_store = UploadStore(UPLOADS_FILE, UPLOADS_DIR)
task_store = TaskStore(TASKS_FILE)
scene_worker = InlineSceneWorker(
    task_store=task_store,
    upload_store=upload_store,
    generated_scene_store=generated_store,
    generated_root=GENERATED_DIR,
    tts_url=CORE100_TTS_URL,
    model=CORE100_MODEL,
    public_scene_store=public_store,
    commerce_store=commerce_store,
    api_key=ZHIPUAI_API_KEY,
    poll_interval=WORKER_POLL_INTERVAL,
)


@asynccontextmanager
async def lifespan(application: FastAPI):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    )
    for warning in check_security_warnings():
        logger.warning(warning)
    logger.info(
        'English Scene API starting | auth=%s | payment=%s | store=%s | worker=%s',
        AUTH_WECHAT_LOGIN_MODE,
        PAYMENT_MODE,
        AUTH_STORE_BACKEND,
        'enabled' if ENABLE_INLINE_SCENE_WORKER else 'disabled',
    )
    if ENABLE_INLINE_SCENE_WORKER:
        scene_worker.start()
    init_video_export(ASSETS_DIR / 'video_exports')
    start_video_cleanup(ASSETS_DIR / 'video_exports', VIDEO_RETENTION_HOURS)
    yield
    stop_video_cleanup()
    scene_worker.stop()
    logger.info('English Scene API stopped')


app = FastAPI(
    title='English Scene API',
    version='0.1.0',
    lifespan=lifespan
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

app.mount('/assets', StaticFiles(directory=str(ASSETS_DIR)), name='assets')
if ADMIN_WEB_DIR.exists():
    app.mount('/admin/static', StaticFiles(directory=str(ADMIN_WEB_DIR)), name='admin-static')


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


def require_admin_dashboard_enabled():
    if not ADMIN_DASHBOARD_ENABLED:
        raise HTTPException(
            status_code=503,
            detail={
                'code': 5003,
                'message': 'admin dashboard disabled',
            },
        )


def is_admin_role(value: str | None) -> bool:
    return (value or '').strip() in {'admin', 'super_admin'}


def build_admin_auth_response(username: str) -> dict:
    access_token, access_expires_at = create_access_token(
        username,
        'admin_console',
        role='admin',
        expires_in=AUTH_ACCESS_TOKEN_TTL_SECONDS,
    )
    return {
        'accessToken': access_token,
        'accessTokenExpireAt': datetime.fromtimestamp(access_expires_at, timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
        'admin': {
            'username': username,
            'userId': '',
            'role': 'super_admin',
            'loginType': 'dashboard_password',
        },
    }


def get_current_admin(request: Request) -> dict:
    require_admin_dashboard_enabled()
    token = get_bearer_token(request)
    if not token:
        unauthorized('admin unauthorized')

    try:
        payload = decode_access_token(token)
    except ValueError as error:
        unauthorized(str(error))

    username = str(payload.get('sub') or '').strip()
    if payload.get('role') == 'admin' and username == ADMIN_DASHBOARD_USERNAME:
        return {
            'username': username,
            'userId': '',
            'role': 'super_admin',
            'loginType': 'dashboard_password',
        }

    user = auth_store.get_user(username) if username else None
    if not user or user.get('status') not in {'', 'active', None}:
        unauthorized('admin unauthorized')
    if not is_admin_role(user.get('role')):
        unauthorized('admin unauthorized')
    return {
        'username': user.get('displayName') or user.get('id') or 'admin_user',
        'userId': user.get('id', ''),
        'role': user.get('role') or 'admin',
        'loginType': 'wechat_user',
    }


def resolve_admin_actor_id(admin: dict) -> str:
    return admin.get('userId') or f"admin_console:{admin.get('username', 'admin')}"


@app.exception_handler(HTTPException)
async def handle_http_exception(_: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, dict) else {
        'code': exc.status_code,
        'message': str(exc.detail)
    }
    return JSONResponse(status_code=exc.status_code, content=detail)


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
        'role': user.get('role') or 'user',
        'isAdmin': is_admin_role(user.get('role')),
        'displayName': user.get('displayName', ''),
        'avatarUrl': user.get('avatarUrl', ''),
        'mobile': user.get('mobile'),
        'mobileVerified': bool(user.get('mobileVerified')),
    }


def build_auth_response(request: Request, user: dict, session: dict, refresh_token: str) -> dict:
    access_token, access_expires_at = create_access_token(
        user.get('id', ''),
        session.get('id', ''),
        role=user.get('role') or 'user',
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
    membership_summary = {
        'isActive': False,
        'entitlementCode': '',
        'expiresAt': None,
    }
    credit_summary = {
        'sceneGenerateBalance': 0,
        'accounts': [],
    }
    if commerce_store:
        membership_summary = commerce_store.get_membership_summary(user.get('id', ''))
        credit_summary = commerce_store.get_credit_summary(user.get('id', ''))
    return {
        'id': user.get('id', ''),
        'role': user.get('role') or 'user',
        'isAdmin': is_admin_role(user.get('role')),
        'displayName': user.get('displayName', ''),
        'avatarUrl': user.get('avatarUrl', ''),
        'mobile': user.get('mobile'),
        'mobileVerified': bool(user.get('mobileVerified')),
        'memberSummary': membership_summary,
        'creditSummary': credit_summary,
        'freeSceneIds': list(FREE_SCENE_IDS),
    }


def serialize_product(request: Request, product: dict) -> dict:
    payload = dict(product)
    payload['coverUrl'] = asset_url(request, payload.get('coverUrl'))
    return payload


def serialize_order(_: Request, order: dict) -> dict:
    return dict(order)


def require_commerce_store():
    if not commerce_store:
        raise HTTPException(
            status_code=503,
            detail={
                'code': 5003,
                'message': 'commerce store not configured',
            },
        )
    return commerce_store


def require_wechat_pay_client(*, need_callback_verify: bool = False):
    if not wechat_pay_client or not wechat_pay_client.is_configured():
        raise HTTPException(
            status_code=503,
            detail={
                'code': 5003,
                'message': 'wechat pay not configured',
            },
        )
    if need_callback_verify and not wechat_pay_client.config.can_verify_callbacks():
        raise HTTPException(
            status_code=503,
            detail={
                'code': 5003,
                'message': 'wechat pay callback verify not configured',
            },
        )
    return wechat_pay_client


def get_user_wechat_openid(user_id: str) -> str:
    identity = auth_store.get_wechat_identity(user_id) if hasattr(auth_store, 'get_wechat_identity') else None
    if not identity:
        return ''
    return str(identity.get('providerUid') or '').strip()


def serialize_entry(request: Request, entry: dict) -> dict:
    payload = dict(entry)
    audio_path = payload.pop('audioPath', '')
    payload['audio'] = asset_url(request, audio_path)
    return payload


def serialize_scene_summary(request: Request, scene: dict) -> dict:
    meta = scene.get('meta', {}) or {}
    return {
        'sceneId': scene['sceneId'],
        'title': scene['title'],
        'coverUrl': asset_url(request, scene.get('coverPath')),
        'category': scene.get('category', ''),
        'categoryId': meta.get('categoryId', ''),
        'categoryName': meta.get('categoryName', '') or scene.get('category', ''),
        'collectionIds': meta.get('collectionIds', []) or [],
        'visibility': scene.get('visibility', 'member'),
        'sceneType': scene.get('sceneType', 'public'),
        'publishedAt': meta.get('publishedAt', ''),
        'sourceGeneratedSceneId': meta.get('sourceGeneratedSceneId', ''),
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


def resolve_auth_login_mode() -> str:
    configured = (AUTH_WECHAT_LOGIN_MODE or 'mock').strip().lower()
    if configured == 'auto':
        return 'code2session' if wechat_auth_client.is_configured() else 'mock'
    if configured in {'real', 'code2session'}:
        return 'code2session'
    return 'mock'


@app.get('/api/health')
def health():
    return success({
        'status': 'ok',
        'workerEnabled': ENABLE_INLINE_SCENE_WORKER,
        'workerMode': 'core100',
        'authLoginMode': resolve_auth_login_mode(),
    })


@app.get('/api/tts')
def tts_proxy(text: str = Query(..., min_length=1, max_length=500)):
    import urllib.request
    import urllib.parse
    if not CORE100_TTS_URL:
        raise HTTPException(status_code=503, detail={'code': 5003, 'message': 'TTS service not configured'})
    encoded = urllib.parse.urlencode({'text': text})
    url = f'{CORE100_TTS_URL}/tts?{encoded}'
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            audio_data = resp.read()
            content_type = resp.headers.get('Content-Type', 'audio/mpeg')
            return Response(content=audio_data, media_type=content_type)
    except Exception as exc:
        raise HTTPException(status_code=502, detail={'code': 5002, 'message': f'TTS service error: {exc}'})


@app.get('/admin')
@app.get('/admin/')
def admin_index():
    require_admin_dashboard_enabled()
    index_file = ADMIN_WEB_DIR / 'index.html'
    if not index_file.exists():
        raise HTTPException(
            status_code=404,
            detail={
                'code': 4004,
                'message': 'admin page not found',
            },
        )
    return FileResponse(index_file)


def serialize_admin_user(user: dict) -> dict:
    payload = {
        'id': user.get('id', ''),
        'role': user.get('role') or 'user',
        'isAdmin': is_admin_role(user.get('role')),
        'displayName': user.get('displayName', ''),
        'avatarUrl': user.get('avatarUrl', ''),
        'mobile': user.get('mobile'),
        'mobileVerified': bool(user.get('mobileVerified')),
        'status': user.get('status', 'active'),
        'lastLoginAt': user.get('lastLoginAt', ''),
        'createdAt': user.get('createdAt', ''),
        'updatedAt': user.get('updatedAt', ''),
    }
    if commerce_store:
        payload['memberSummary'] = commerce_store.get_membership_summary(payload['id'])
        payload['creditSummary'] = commerce_store.get_credit_summary(payload['id'])
    return payload


def serialize_admin_task(task: dict) -> dict:
    return {
        'taskId': task.get('taskId', ''),
        'ownerId': task.get('ownerId', ''),
        'uploadId': task.get('uploadId', ''),
        'title': task.get('title', ''),
        'requestSource': task.get('requestSource', 'miniapp'),
        'autoPublish': bool(task.get('autoPublish')),
        'categoryId': task.get('categoryId', ''),
        'collectionIds': task.get('collectionIds', []) or [],
        'publishVisibility': task.get('publishVisibility', 'public'),
        'status': task.get('status', ''),
        'step': task.get('step', ''),
        'progress': task.get('progress', 0),
        'sceneId': task.get('sceneId', ''),
        'publishedSceneId': task.get('publishedSceneId', ''),
        'errorMessage': task.get('errorMessage', ''),
        'createdAt': task.get('createdAt', ''),
        'updatedAt': task.get('updatedAt', ''),
    }


def serialize_admin_scene(scene: dict) -> dict:
    meta = scene.get('meta', {}) or {}
    return {
        'sceneId': scene.get('sceneId', ''),
        'title': scene.get('title', ''),
        'category': scene.get('category', ''),
        'categoryId': meta.get('categoryId', ''),
        'collectionIds': meta.get('collectionIds', []) or [],
        'visibility': scene.get('visibility', 'public'),
        'sceneType': scene.get('sceneType', 'public'),
        'backgroundPath': scene.get('backgroundPath', ''),
        'coverPath': scene.get('coverPath', ''),
        'itemCount': len(scene.get('items', []) or []),
        'verbCount': len(scene.get('verbs', []) or []),
        'items': scene.get('items', []),
        'verbs': scene.get('verbs', []),
        'meta': scene.get('meta', {}),
    }


def serialize_admin_scene_category(category: dict) -> dict:
    return dict(category)


def serialize_admin_scene_collection(collection: dict) -> dict:
    return dict(collection)


def serialize_admin_generated_scene(request: Request, scene: dict, publication: dict | None = None) -> dict:
    meta = scene.get('meta', {}) or {}
    return {
        'sceneId': scene.get('sceneId', ''),
        'title': scene.get('title', ''),
        'category': scene.get('category', ''),
        'visibility': scene.get('visibility', 'private'),
        'sceneType': scene.get('sceneType', 'private'),
        'backgroundUrl': asset_url(request, scene.get('backgroundPath')),
        'coverUrl': asset_url(request, scene.get('coverPath')),
        'ownerId': meta.get('ownerId', ''),
        'itemCount': len(scene.get('items', []) or []),
        'verbCount': len(scene.get('verbs', []) or []),
        'meta': meta,
        'publication': publication,
    }


def load_public_scene_publication_map(scenes: list[dict]) -> dict[str, dict]:
    if not commerce_store:
        return {}
    scene_ids = [scene.get('sceneId', '') for scene in scenes if scene.get('sceneId')]
    return require_commerce_store().list_scene_publications_by_public_scene_ids(scene_ids)


def merge_public_scene_publication(scene: dict, publication: dict | None = None) -> dict:
    payload = dict(scene)
    meta = dict(payload.get('meta', {}) or {})
    publication = publication or {}
    if publication.get('categoryId'):
        meta['categoryId'] = publication.get('categoryId', '')
    if publication.get('categoryName'):
        meta['categoryName'] = publication.get('categoryName', '')
    if publication.get('collectionIds') is not None:
        meta['collectionIds'] = publication.get('collectionIds', []) or []
    if publication.get('sourceGeneratedSceneId'):
        meta['sourceGeneratedSceneId'] = publication.get('sourceGeneratedSceneId', '')
    if publication.get('publishedAt'):
        meta['publishedAt'] = publication.get('publishedAt', '')
    payload['meta'] = meta
    if publication.get('categoryName'):
        payload['category'] = publication.get('categoryName', '') or payload.get('category', '')
    return payload


def filter_public_scenes_by_taxonomy(
    scenes: list[dict],
    publication_map: dict[str, dict],
    *,
    category_id: str = '',
    collection_id: str = '',
) -> list[dict]:
    filtered: list[dict] = []
    for scene in scenes:
        publication = publication_map.get(scene.get('sceneId', ''), {})
        if category_id and publication.get('categoryId') != category_id:
            continue
        if collection_id and collection_id not in (publication.get('collectionIds', []) or []):
            continue
        filtered.append(scene)
    return filtered


@app.post('/api/admin/auth/login')
def admin_auth_login(payload: AdminLoginRequest):
    require_admin_dashboard_enabled()
    if payload.username != ADMIN_DASHBOARD_USERNAME or payload.password != ADMIN_DASHBOARD_PASSWORD:
        unauthorized('admin credential invalid')
    return success(build_admin_auth_response(payload.username))


@app.get('/api/admin/auth/me')
def admin_auth_me(request: Request):
    return success(get_current_admin(request))


@app.get('/api/admin/overview')
def admin_overview(request: Request):
    get_current_admin(request)
    overview = {
        'userCount': auth_store.get_user_count() if hasattr(auth_store, 'get_user_count') else 0,
        'publicSceneCount': len(public_store.list_scenes('')),
        'generatedSceneCount': len(generated_store.list_scenes()),
        'taskCount': 0,
        'queuedTaskCount': 0,
        'runningTaskCount': 0,
        'failedTaskCount': 0,
        'doneTaskCount': 0,
    }
    if commerce_store and hasattr(commerce_store, 'get_admin_overview'):
        overview.update(commerce_store.get_admin_overview())

    tasks = task_store.list_tasks(500) if hasattr(task_store, 'list_tasks') else []
    today_prefix = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    overview['taskCount'] = len(tasks)
    overview['queuedTaskCount'] = sum(1 for task in tasks if task.get('status') == 'queued')
    overview['runningTaskCount'] = sum(1 for task in tasks if task.get('status') == 'running')
    overview['failedTaskCount'] = sum(1 for task in tasks if task.get('status') == 'failed')
    overview['doneTaskCount'] = sum(1 for task in tasks if task.get('status') == 'done')
    overview['todayTaskCount'] = sum(1 for task in tasks if str(task.get('createdAt', '')).startswith(today_prefix))
    return success(overview)


@app.get('/api/admin/users')
def admin_list_users(request: Request, limit: int = Query(default=50, ge=1, le=200)):
    get_current_admin(request)
    users = auth_store.list_users(limit) if hasattr(auth_store, 'list_users') else []
    return success({
        'list': [serialize_admin_user(user) for user in users],
    })


@app.get('/api/admin/users/{user_id}')
def admin_get_user_detail(user_id: str, request: Request):
    get_current_admin(request)
    user = auth_store.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail={'code': 4004, 'message': 'user not found'})
    payload = serialize_admin_user(user)
    payload['orders'] = require_commerce_store().list_orders(user_id) if commerce_store else []
    payload['entitlements'] = require_commerce_store().list_user_entitlements(user_id) if commerce_store else []
    payload['generatedScenes'] = [serialize_scene_summary(request, scene) for scene in generated_store.list_scenes(user_id)]
    return success(payload)


@app.post('/api/admin/users/{user_id}/block')
def admin_block_user(user_id: str, request: Request):
    get_current_admin(request)
    user = auth_store.update_user_status(user_id, 'blocked') if hasattr(auth_store, 'update_user_status') else None
    if not user:
        raise HTTPException(status_code=404, detail={'code': 4004, 'message': 'user not found'})
    return success(serialize_admin_user(user))


@app.post('/api/admin/users/{user_id}/unblock')
def admin_unblock_user(user_id: str, request: Request):
    get_current_admin(request)
    user = auth_store.update_user_status(user_id, 'active') if hasattr(auth_store, 'update_user_status') else None
    if not user:
        raise HTTPException(status_code=404, detail={'code': 4004, 'message': 'user not found'})
    return success(serialize_admin_user(user))


@app.post('/api/admin/users/{user_id}/grant-admin')
def admin_grant_user_admin(user_id: str, request: Request):
    get_current_admin(request)
    user = auth_store.update_user_role(user_id, 'admin') if hasattr(auth_store, 'update_user_role') else None
    if not user:
        raise HTTPException(status_code=404, detail={'code': 4004, 'message': 'user not found'})
    return success(serialize_admin_user(user))


@app.post('/api/admin/users/{user_id}/revoke-admin')
def admin_revoke_user_admin(user_id: str, request: Request):
    get_current_admin(request)
    user = auth_store.update_user_role(user_id, 'user') if hasattr(auth_store, 'update_user_role') else None
    if not user:
        raise HTTPException(status_code=404, detail={'code': 4004, 'message': 'user not found'})
    return success(serialize_admin_user(user))


@app.post('/api/admin/users/batch-delete')
def admin_batch_delete_users(request: Request, body: AdminBatchDeleteUsersRequest):
    get_current_admin(request)
    deleted = auth_store.delete_users(body.userIds) if hasattr(auth_store, 'delete_users') else 0
    return success({'deleted': deleted})


@app.get('/api/admin/products')
def admin_list_products(request: Request):
    get_current_admin(request)
    store = require_commerce_store()
    products = store.list_products(status='')
    return success({
        'list': [
            {
                **serialize_product(request, product),
                'skus': store.list_product_skus(product.get('productId', ''), status=''),
            }
            for product in products
        ],
    })


@app.post('/api/admin/products')
def admin_create_product(payload: AdminProductRequest, request: Request):
    get_current_admin(request)
    store = require_commerce_store()
    store.upsert_product(payload.model_dump())
    products = store.list_products(status='')
    created = next((item for item in products if item.get('productCode') == payload.productCode), None)
    return success(serialize_product(request, created or products[-1]))


@app.get('/api/admin/products/{product_id}')
def admin_get_product(product_id: str, request: Request):
    get_current_admin(request)
    store = require_commerce_store()
    product = store.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail={'code': 4004, 'message': 'product not found'})
    return success({
        **serialize_product(request, product),
        'skus': store.list_product_skus(product_id, status=''),
    })


@app.put('/api/admin/products/{product_id}')
def admin_update_product(product_id: str, payload: AdminProductRequest, request: Request):
    get_current_admin(request)
    store = require_commerce_store()
    current = store.get_product(product_id)
    if not current:
        raise HTTPException(status_code=404, detail={'code': 4004, 'message': 'product not found'})
    next_product = current | payload.model_dump() | {'id': product_id, 'updatedAt': utcnow_iso()}
    store.upsert_product(next_product)
    return success(serialize_product(request, store.get_product(product_id)))


@app.post('/api/admin/products/{product_id}/publish')
def admin_publish_product(product_id: str, request: Request):
    get_current_admin(request)
    store = require_commerce_store()
    current = store.get_product(product_id)
    if not current:
        raise HTTPException(status_code=404, detail={'code': 4004, 'message': 'product not found'})
    current['id'] = product_id
    current['status'] = 'active'
    current['updatedAt'] = utcnow_iso()
    store.upsert_product(current)
    return success(serialize_product(request, store.get_product(product_id)))


@app.post('/api/admin/products/{product_id}/disable')
def admin_disable_product(product_id: str, request: Request):
    get_current_admin(request)
    store = require_commerce_store()
    current = store.get_product(product_id)
    if not current:
        raise HTTPException(status_code=404, detail={'code': 4004, 'message': 'product not found'})
    current['id'] = product_id
    current['status'] = 'disabled'
    current['updatedAt'] = utcnow_iso()
    store.upsert_product(current)
    return success(serialize_product(request, store.get_product(product_id)))


@app.get('/api/admin/skus')
def admin_list_skus(request: Request):
    get_current_admin(request)
    store = require_commerce_store()
    skus = store.list_skus(status='') if hasattr(store, 'list_skus') else []
    return success({'list': skus})


@app.post('/api/admin/skus')
def admin_create_sku(payload: AdminSkuRequest, request: Request):
    get_current_admin(request)
    store = require_commerce_store()
    if not store.get_product(payload.productId):
        raise HTTPException(status_code=404, detail={'code': 4004, 'message': 'product not found'})
    store.upsert_sku(payload.model_dump(exclude={'benefits'}))
    sku_list = store.list_skus(status='') if hasattr(store, 'list_skus') else []
    created = next((item for item in sku_list if item.get('skuCode') == payload.skuCode and item.get('productId') == payload.productId), None)
    if created:
        store.replace_sku_benefits(created.get('skuId', ''), [item.model_dump() for item in payload.benefits])
        created = next((item for item in store.list_skus(status='') if item.get('skuId') == created.get('skuId')), created)
    return success(created or {})


@app.put('/api/admin/skus/{sku_id}')
def admin_update_sku(sku_id: str, payload: AdminSkuRequest, request: Request):
    get_current_admin(request)
    store = require_commerce_store()
    current = next((item for item in (store.list_skus(status='') if hasattr(store, 'list_skus') else []) if item.get('skuId') == sku_id), None)
    if not current:
        raise HTTPException(status_code=404, detail={'code': 4004, 'message': 'sku not found'})
    next_sku = current | payload.model_dump(exclude={'benefits'}) | {'id': sku_id, 'updatedAt': utcnow_iso()}
    store.upsert_sku(next_sku)
    store.replace_sku_benefits(sku_id, [item.model_dump() for item in payload.benefits])
    updated = next((item for item in store.list_skus(status='') if item.get('skuId') == sku_id), None) if hasattr(store, 'list_skus') else {}
    return success(updated or {})


@app.get('/api/admin/orders')
def admin_list_orders(request: Request, limit: int = Query(default=50, ge=1, le=200)):
    get_current_admin(request)
    store = require_commerce_store()
    orders = store.list_orders_admin(limit) if hasattr(store, 'list_orders_admin') else []
    return success({
        'list': [serialize_order(request, order) for order in orders],
    })


@app.get('/api/admin/orders/{order_id}')
def admin_get_order(order_id: str, request: Request):
    get_current_admin(request)
    store = require_commerce_store()
    order = store.get_order_admin(order_id) if hasattr(store, 'get_order_admin') else None
    if not order:
        raise HTTPException(status_code=404, detail={'code': 4004, 'message': 'order not found'})
    return success(serialize_order(request, order))


@app.post('/api/admin/orders/batch-delete')
def admin_batch_delete_orders(request: Request, body: AdminBatchDeleteOrdersRequest):
    get_current_admin(request)
    store = require_commerce_store()
    deleted = store.delete_orders_admin(body.orderIds)
    return success({'deleted': deleted})


# --- CDK management ---

@app.get('/api/admin/cdk-codes')
def admin_list_cdk_codes(request: Request, status: str = Query(default=''), skuId: str = Query(default=''), limit: int = Query(default=200, ge=1, le=500), offset: int = Query(default=0, ge=0)):
    get_current_admin(request)
    store = require_commerce_store()
    codes = store.list_cdk_codes(status=status, sku_id=skuId, limit=limit, offset=offset)
    return success({'list': codes})


@app.post('/api/admin/cdk-codes/generate')
def admin_generate_cdk(request: Request, body: AdminGenerateCdkRequest):
    get_current_admin(request)
    store = require_commerce_store()
    try:
        codes = store.generate_cdk_batch(sku_id=body.skuId, quantity=body.quantity, note=body.note)
        return success({'list': codes})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={'code': 4000, 'message': str(exc)})


@app.post('/api/admin/cdk-codes/batch-delete')
def admin_batch_delete_cdk(request: Request, body: AdminBatchDeleteCdkRequest):
    get_current_admin(request)
    store = require_commerce_store()
    deleted = store.delete_cdk_batch(body.cdkIds)
    return success({'deleted': deleted})


@app.post('/api/cdk/redeem')
def cdk_redeem(request: Request, body: CdkRedeemRequest):
    user_id = get_current_user_id(request)
    store = require_commerce_store()
    try:
        result = store.redeem_cdk(code=body.code.strip().upper(), user_id=user_id)
        return success(result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={'code': 4000, 'message': str(exc)})


@app.get('/api/cdk/my-redemptions')
def cdk_my_redemptions(request: Request):
    user_id = get_current_user_id(request)
    store = require_commerce_store()
    records = store.list_user_cdk_redemptions(user_id)
    return success({'list': records})


@app.get('/api/admin/tasks')
def admin_list_tasks(request: Request, limit: int = Query(default=50, ge=1, le=200)):
    get_current_admin(request)
    tasks = task_store.list_tasks(limit) if hasattr(task_store, 'list_tasks') else []
    return success({
        'list': [serialize_admin_task(task) for task in tasks],
    })


@app.get('/api/admin/tasks/{task_id}')
def admin_get_task(task_id: str, request: Request):
    get_current_admin(request)
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail={'code': 4004, 'message': 'task not found'})
    return success(serialize_admin_task(task))


@app.post('/api/admin/tasks/{task_id}/retry')
def admin_retry_task(task_id: str, request: Request):
    get_current_admin(request)
    task = task_store.retry_task(task_id) if hasattr(task_store, 'retry_task') else None
    if not task:
        raise HTTPException(status_code=404, detail={'code': 4004, 'message': 'task not found'})
    return success(serialize_admin_task(task))


@app.post('/api/admin/tasks/batch-delete')
def admin_batch_delete_tasks(request: Request, body: AdminBatchDeleteTasksRequest):
    get_current_admin(request)
    deleted = task_store.delete_tasks(body.taskIds)
    return success({'deleted': deleted})


@app.get('/api/admin/scene-categories')
def admin_list_scene_categories(request: Request):
    get_current_admin(request)
    store = require_commerce_store()
    return success({'list': [serialize_admin_scene_category(item) for item in store.list_scene_categories(status='')]})


@app.post('/api/admin/scene-categories')
def admin_create_scene_category(payload: AdminSceneCategoryRequest, request: Request):
    get_current_admin(request)
    store = require_commerce_store()
    category_id = f"scene_category_{payload.categoryCode}"
    store.upsert_scene_category({
        'id': category_id,
        'categoryCode': payload.categoryCode,
        'name': payload.name,
        'description': payload.description,
        'status': payload.status,
        'sortOrder': payload.sortOrder,
        'createdAt': utcnow_iso(),
        'updatedAt': utcnow_iso(),
    })
    return success(serialize_admin_scene_category(store.get_scene_category(category_id)))


@app.put('/api/admin/scene-categories/{category_id}')
def admin_update_scene_category(category_id: str, payload: AdminSceneCategoryRequest, request: Request):
    get_current_admin(request)
    store = require_commerce_store()
    current = store.get_scene_category(category_id)
    if not current:
        raise HTTPException(status_code=404, detail={'code': 4004, 'message': 'scene category not found'})
    store.upsert_scene_category({
        **current,
        'categoryId': category_id,
        'categoryCode': payload.categoryCode,
        'name': payload.name,
        'description': payload.description,
        'status': payload.status,
        'sortOrder': payload.sortOrder,
        'updatedAt': utcnow_iso(),
    })
    return success(serialize_admin_scene_category(store.get_scene_category(category_id)))


@app.delete('/api/admin/scene-categories/{category_id}')
def admin_delete_scene_category(category_id: str, request: Request):
    get_current_admin(request)
    store = require_commerce_store()
    try:
        deleted = store.delete_scene_category(category_id)
    except ValueError as error:
        raise HTTPException(status_code=409, detail={'code': 4090, 'message': str(error)})
    if not deleted:
        raise HTTPException(status_code=404, detail={'code': 4004, 'message': 'scene category not found'})
    return success({'deleted': True})


@app.get('/api/admin/scene-collections')
def admin_list_scene_collections(request: Request):
    get_current_admin(request)
    store = require_commerce_store()
    return success({'list': [serialize_admin_scene_collection(item) for item in store.list_scene_collections(status='')]})


@app.post('/api/admin/scene-collections')
def admin_create_scene_collection(payload: AdminSceneCollectionRequest, request: Request):
    get_current_admin(request)
    store = require_commerce_store()
    collection_id = f"scene_collection_{payload.collectionCode}"
    store.upsert_scene_collection({
        'id': collection_id,
        'collectionCode': payload.collectionCode,
        'name': payload.name,
        'description': payload.description,
        'status': payload.status,
        'coverUrl': payload.coverUrl,
        'sortOrder': payload.sortOrder,
        'createdAt': utcnow_iso(),
        'updatedAt': utcnow_iso(),
    })
    return success(serialize_admin_scene_collection(store.get_scene_collection(collection_id)))


@app.put('/api/admin/scene-collections/{collection_id}')
def admin_update_scene_collection(collection_id: str, payload: AdminSceneCollectionRequest, request: Request):
    get_current_admin(request)
    store = require_commerce_store()
    current = store.get_scene_collection(collection_id)
    if not current:
        raise HTTPException(status_code=404, detail={'code': 4004, 'message': 'scene collection not found'})
    store.upsert_scene_collection({
        **current,
        'collectionId': collection_id,
        'collectionCode': payload.collectionCode,
        'name': payload.name,
        'description': payload.description,
        'status': payload.status,
        'coverUrl': payload.coverUrl,
        'sortOrder': payload.sortOrder,
        'updatedAt': utcnow_iso(),
    })
    return success(serialize_admin_scene_collection(store.get_scene_collection(collection_id)))


@app.delete('/api/admin/scene-collections/{collection_id}')
def admin_delete_scene_collection(collection_id: str, request: Request):
    get_current_admin(request)
    store = require_commerce_store()
    try:
        deleted = store.delete_scene_collection(collection_id)
    except ValueError as error:
        raise HTTPException(status_code=409, detail={'code': 4090, 'message': str(error)})
    if not deleted:
        raise HTTPException(status_code=404, detail={'code': 4004, 'message': 'scene collection not found'})
    return success({'deleted': True})


@app.get('/api/admin/generated-scenes')
def admin_list_generated_scenes(request: Request, limit: int = Query(default=100, ge=1, le=500)):
    get_current_admin(request)
    scenes = generated_store.list_scenes()[:limit]
    publication_map = require_commerce_store().list_scene_publications_by_source_ids(
        [scene.get('sceneId', '') for scene in scenes if scene.get('sceneId')]
    ) if commerce_store else {}
    return success({
        'list': [
            serialize_admin_generated_scene(request, scene, publication_map.get(scene.get('sceneId', '')))
            for scene in scenes
        ],
    })


@app.get('/api/admin/public-scenes')
def admin_list_public_scenes(request: Request):
    get_current_admin(request)
    scenes = public_store.list_scenes('')
    publication_map = load_public_scene_publication_map(scenes)
    enriched = []
    for scene in scenes:
        payload = serialize_admin_scene(scene)
        publication = publication_map.get(scene.get('sceneId', ''))
        if publication:
            payload['publication'] = publication
        enriched.append(payload)
    return success({'list': enriched})


@app.post('/api/admin/public-scenes/batch-delete')
def admin_batch_delete_public_scenes(request: Request, body: AdminBatchDeleteScenesRequest):
    get_current_admin(request)
    deleted = public_store.delete_scenes(body.sceneIds)
    return success({'deleted': deleted})


@app.post('/api/admin/public-scenes')
def admin_create_public_scene(payload: AdminPublicSceneRequest, request: Request):
    get_current_admin(request)
    scene = public_store.upsert_scene({
        'title': payload.title,
        'category': payload.category,
        'visibility': payload.visibility,
        'sceneType': payload.sceneType,
        'backgroundPath': payload.backgroundPath,
        'coverPath': payload.coverPath,
        'items': payload.items,
        'verbs': payload.verbs,
        'meta': payload.meta,
    })
    return success(serialize_admin_scene(scene))


@app.put('/api/admin/public-scenes/{scene_id}')
def admin_update_public_scene(scene_id: str, payload: AdminPublicSceneRequest, request: Request):
    get_current_admin(request)
    current = public_store.get_scene(scene_id)
    if not current:
        raise HTTPException(status_code=404, detail={'code': 4004, 'message': 'scene not found'})
    scene = public_store.upsert_scene(current | {
        'sceneId': scene_id,
        'title': payload.title,
        'category': payload.category,
        'visibility': payload.visibility,
        'sceneType': payload.sceneType,
        'backgroundPath': payload.backgroundPath,
        'coverPath': payload.coverPath,
        'items': payload.items,
        'verbs': payload.verbs,
        'meta': payload.meta,
    })
    return success(serialize_admin_scene(scene))


@app.post('/api/admin/generated-scenes/{scene_id}/publish')
def admin_publish_generated_scene(scene_id: str, payload: AdminPublishGeneratedSceneRequest, request: Request):
    admin = get_current_admin(request)
    store = require_commerce_store()
    source_scene = generated_store.get_scene(scene_id)
    if not source_scene:
        raise HTTPException(status_code=404, detail={'code': 4004, 'message': 'generated scene not found'})
    try:
        public_scene, publication = publish_generated_scene_to_public(
            source_scene=source_scene,
            source_scene_id=scene_id,
            public_store=public_store,
            commerce_store=store,
            category_id=payload.categoryId,
            collection_ids=payload.collectionIds,
            visibility=payload.visibility or 'public',
            published_by=resolve_admin_actor_id(admin),
            title=(payload.title or '').strip(),
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail={'code': 4004, 'message': str(error)})
    payload = serialize_admin_scene(public_scene)
    payload['publication'] = publication
    return success(payload)


@app.post('/api/admin/public-scenes/{scene_id}/republish')
def admin_republish_public_scene(scene_id: str, request: Request):
    admin = get_current_admin(request)
    store = require_commerce_store()
    current_public_scene = public_store.get_scene(scene_id)
    if not current_public_scene:
        raise HTTPException(status_code=404, detail={'code': 4004, 'message': 'public scene not found'})

    publication = store.get_scene_publication_by_public_scene(scene_id)
    if not publication or not publication.get('sourceGeneratedSceneId'):
        raise HTTPException(status_code=404, detail={'code': 4004, 'message': 'scene publication source not found'})

    source_scene = generated_store.get_scene(publication.get('sourceGeneratedSceneId', ''))
    if not source_scene:
        raise HTTPException(status_code=404, detail={'code': 4004, 'message': 'generated scene not found'})

    try:
        next_public_scene, next_publication = publish_generated_scene_to_public(
            source_scene=source_scene,
            source_scene_id=publication.get('sourceGeneratedSceneId', ''),
            public_store=public_store,
            commerce_store=store,
            category_id=publication.get('categoryId', ''),
            collection_ids=publication.get('collectionIds', []) or [],
            visibility=current_public_scene.get('visibility', '') or publication.get('visibility', 'public'),
            published_by=resolve_admin_actor_id(admin),
            title=(current_public_scene.get('title') or '').strip(),
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail={'code': 4004, 'message': str(error)})

    payload = serialize_admin_scene(next_public_scene)
    payload['publication'] = next_publication
    return success(payload)


@limiter.limit('10/minute')
@app.post('/api/auth/wechat/login')
def auth_wechat_login(payload: WechatLoginRequest, request: Request):
    auth_mode = resolve_auth_login_mode()
    provider_uid = ''
    union_id = ''
    session_key_encrypted = ''
    profile = {
        'displayName': '微信用户',
        'avatarUrl': '',
        'loginMode': auth_mode,
    }

    if auth_mode == 'mock':
        provider_uid = make_mock_openid(payload)
        session_key_encrypted = 'mock_session_key'
    else:
        if not wechat_auth_client.is_configured():
            raise HTTPException(
                status_code=503,
                detail={
                    'code': 5003,
                    'message': 'wechat mini program login is not configured',
                },
            )
        try:
            wechat_identity = wechat_auth_client.code_to_session(payload.code)
        except WechatCode2SessionError as error:
            raise HTTPException(
                status_code=401,
                detail={
                    'code': 4001,
                    'message': str(error),
                },
            )
        provider_uid = wechat_identity['openid']
        union_id = wechat_identity.get('unionid', '')
        session_key_encrypted = encrypt_wechat_session_key(wechat_identity.get('session_key', ''))
        profile.update({
            'openid': provider_uid,
            'unionId': union_id,
        })

    user = auth_store.get_or_create_wechat_user(
        provider_uid=provider_uid,
        union_id=union_id,
        profile=profile,
        session_key_encrypted=session_key_encrypted,
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


@limiter.limit('20/minute')
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


@app.put('/api/me/profile')
def update_my_profile(payload: MeProfileUpdateRequest, request: Request):
    user = get_request_user(request, required=True, allow_debug=True)
    display_name = (payload.displayName or '').strip()
    avatar_url = (payload.avatarUrl or '').strip()
    if not display_name and not avatar_url:
        raise HTTPException(
            status_code=400,
            detail={
                'code': 4000,
                'message': 'profile payload is empty',
            },
        )
    updated = auth_store.update_user_profile(
        user.get('id', ''),
        display_name=display_name,
        avatar_url=avatar_url,
    ) if hasattr(auth_store, 'update_user_profile') else None
    if not updated:
        raise HTTPException(
            status_code=404,
            detail={
                'code': 4004,
                'message': 'user not found',
            },
        )
    return success(serialize_me(request, updated))


@app.get('/api/me/membership')
def get_my_membership(request: Request):
    user = get_request_user(request, required=True, allow_debug=True)
    return success(require_commerce_store().get_membership_summary(user.get('id', '')))


@app.get('/api/me/credits')
def get_my_credits(request: Request):
    user = get_request_user(request, required=True, allow_debug=True)
    return success(require_commerce_store().get_credit_summary(user.get('id', '')))


@app.get('/api/me/entitlements')
def get_my_entitlements(request: Request):
    user = get_request_user(request, required=True, allow_debug=True)
    return success({
        'list': require_commerce_store().list_user_entitlements(user.get('id', '')),
    })


@app.get('/api/me/upgrade-preview')
def get_upgrade_preview(request: Request, skuId: str = Query(default='')):
    user = get_request_user(request, required=True, allow_debug=True)
    if not skuId:
        raise HTTPException(status_code=400, detail={'code': 4000, 'message': 'skuId is required'})
    try:
        preview = require_commerce_store().preview_tier_purchase(user.get('id', ''), skuId)
        return success(preview)
    except ValueError as error:
        raise HTTPException(status_code=400, detail={'code': 4000, 'message': str(error)})


@app.get('/api/products')
def list_products(request: Request, productType: str = Query(default='')):
    products = require_commerce_store().list_products(productType)
    return success({
        'list': [serialize_product(request, product) for product in products],
    })


@app.get('/api/products/{product_id}')
def get_product(product_id: str, request: Request):
    product = require_commerce_store().get_product(product_id)
    if not product:
        raise HTTPException(
            status_code=404,
            detail={
                'code': 4004,
                'message': 'product not found',
            },
        )
    return success(serialize_product(request, product))


@app.get('/api/products/{product_id}/skus')
def list_product_skus(product_id: str):
    return success({
        'list': require_commerce_store().list_product_skus(product_id),
    })


@limiter.limit('10/minute')
@app.post('/api/orders')
def create_order(payload: OrderCreateRequest, request: Request):
    user = get_request_user(request, required=True, allow_debug=True)
    try:
        order = require_commerce_store().create_order(
            user_id=user.get('id', ''),
            sku_id=payload.skuId,
            quantity=payload.quantity,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail={
                'code': 4000,
                'message': str(error),
            },
        )
    return success(serialize_order(request, order))


@app.get('/api/orders')
def list_orders(request: Request):
    user = get_request_user(request, required=True, allow_debug=True)
    return success({
        'list': [serialize_order(request, order) for order in require_commerce_store().list_orders(user.get('id', ''))],
    })


@app.get('/api/orders/{order_id}')
def get_order(order_id: str, request: Request):
    user = get_request_user(request, required=True, allow_debug=True)
    order = require_commerce_store().get_order(order_id=order_id, user_id=user.get('id', ''))
    if not order:
        raise HTTPException(
            status_code=404,
            detail={
                'code': 4004,
                'message': 'order not found',
            },
        )
    return success(serialize_order(request, order))


@app.post('/api/orders/{order_id}/pay')
def create_order_payment(order_id: str, request: Request):
    user = get_request_user(request, required=True, allow_debug=True)
    if PAYMENT_MODE == 'mock':
        try:
            result = require_commerce_store().create_payment_intent(
                order_id=order_id,
                user_id=user.get('id', ''),
                payment_mode=PAYMENT_MODE,
            )
        except ValueError as error:
            raise HTTPException(
                status_code=400,
                detail={
                    'code': 4000,
                    'message': str(error),
                },
            )
        return success(result)

    if PAYMENT_MODE != 'wechat_pay':
        raise HTTPException(
            status_code=501,
            detail={
                'code': 5001,
                'message': 'payment mode not implemented',
            },
        )

    payer_openid = get_user_wechat_openid(user.get('id', ''))
    if not payer_openid:
        raise HTTPException(
            status_code=400,
            detail={
                'code': 4000,
                'message': 'wechat openid not found for current user',
            },
        )

    try:
        started = require_commerce_store().start_payment_intent(
            order_id=order_id,
            user_id=user.get('id', ''),
            payment_mode=PAYMENT_MODE,
        )
        if started.get('alreadyPaid'):
            return success(started)

        order = started.get('order', {}) or {}
        payable_amount = Decimal(str(order.get('payableAmount') or started.get('amount') or '0'))
        transaction = require_wechat_pay_client().create_jsapi_transaction(
            out_trade_no=started.get('orderNo', ''),
            description=started.get('description', '') or '订单支付',
            total_fen=int(payable_amount * Decimal('100')),
            payer_openid=payer_openid,
        )
        prepay_id = str(transaction.get('prepay_id') or '').strip()
        if not prepay_id:
            raise ValueError('wechat pay prepay_id missing')
        request_payment = require_wechat_pay_client().build_miniapp_request_payment(prepay_id)
        require_commerce_store().update_payment_channel_payload(
            payment_id=started.get('paymentId', ''),
            channel_payload={
                'paymentMode': PAYMENT_MODE,
                'prepayId': prepay_id,
                'requestPayment': request_payment,
                'wechatTransaction': transaction,
            },
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail={
                'code': 4000,
                'message': str(error),
            },
        )

    return success({
        'paymentMode': PAYMENT_MODE,
        'paymentId': started.get('paymentId', ''),
        'orderId': started.get('orderId', ''),
        'order': started.get('order', {}),
        'alreadyPaid': False,
        'requestPayment': request_payment,
    })


@app.post('/api/orders/{order_id}/mock-pay-success')
def complete_mock_order_payment(order_id: str, payload: MockPaymentCompleteRequest | None, request: Request):
    user = get_request_user(request, required=True, allow_debug=True)
    try:
        order = require_commerce_store().complete_mock_payment(
            order_id=order_id,
            user_id=user.get('id', ''),
            payment_id=(payload.paymentId if payload else '') or '',
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail={
                'code': 4000,
                'message': str(error),
            },
        )
    return success({
        'order': serialize_order(request, order),
        'me': serialize_me(request, user),
    })


@app.post('/api/orders/{order_id}/payment-sync')
def sync_order_payment(order_id: str, request: Request):
    user = get_request_user(request, required=True, allow_debug=True)
    if PAYMENT_MODE != 'wechat_pay':
        raise HTTPException(
            status_code=400,
            detail={
                'code': 4000,
                'message': 'payment sync only available in wechat_pay mode',
            },
        )
    order = require_commerce_store().get_order(order_id=order_id, user_id=user.get('id', ''))
    if not order:
        raise HTTPException(
            status_code=404,
            detail={
                'code': 4004,
                'message': 'order not found',
            },
        )
    if order.get('status') == 'paid':
        return success({
            'order': serialize_order(request, order),
            'me': serialize_me(request, user),
        })
    try:
        transaction = require_wechat_pay_client().query_order_by_out_trade_no(order.get('orderNo', ''))
    except ValueError as error:
        raise HTTPException(status_code=400, detail={'code': 4000, 'message': str(error)})

    trade_state = str(transaction.get('trade_state') or '').strip().upper()
    if trade_state != 'SUCCESS':
        return success({
            'order': serialize_order(request, order),
            'me': serialize_me(request, user),
            'tradeState': trade_state or 'NOTPAY',
        })
    try:
        completed = require_commerce_store().complete_wechat_payment(
            order_no=order.get('orderNo', ''),
            transaction_id=str(transaction.get('transaction_id') or ''),
            payment_payload={
                'paymentMode': PAYMENT_MODE,
                'tradeState': trade_state,
                'wechatQuery': transaction,
            },
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail={'code': 4000, 'message': str(error)})
    return success({
        'order': serialize_order(request, completed),
        'me': serialize_me(request, user),
        'tradeState': trade_state,
    })


@limiter.limit('60/minute')
@app.post('/api/payments/wechat/notify')
async def handle_wechat_payment_notify(request: Request):
    body = await request.body()
    try:
        resource = require_wechat_pay_client(need_callback_verify=True).verify_and_decrypt_callback(
            headers={key: value for key, value in request.headers.items()},
            body=body,
        )
        if str(resource.get('trade_state') or '').upper() == 'SUCCESS':
            require_commerce_store().complete_wechat_payment(
                order_no=str(resource.get('out_trade_no') or ''),
                transaction_id=str(resource.get('transaction_id') or ''),
                payment_payload={
                    'paymentMode': 'wechat_pay',
                    'tradeState': str(resource.get('trade_state') or ''),
                    'wechatNotify': resource,
                },
            )
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=400, detail={'code': 4000, 'message': str(error)})
    return {'code': 'SUCCESS', 'message': '成功'}


@app.get('/api/scene-categories')
def list_public_scene_categories(_: Request):
    if not commerce_store:
        return success({'list': []})
    return success({'list': require_commerce_store().list_scene_categories(status='active')})


@app.get('/api/scene-collections')
def list_public_scene_collections(_: Request):
    if not commerce_store:
        return success({'list': []})
    return success({'list': require_commerce_store().list_scene_collections(status='active')})


@app.get('/api/config')
def get_client_config(request: Request):
    return success({
        'scenePageSize': SCENE_PAGE_SIZE,
    })


@app.get('/api/scenes')
def list_scenes(
    request: Request,
    type: str = Query(default='public'),
    categoryId: str = Query(default=''),
    collectionId: str = Query(default=''),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=20, ge=1, le=100)
):
    scenes = public_store.list_scenes(type)
    publication_map = load_public_scene_publication_map(scenes)
    if categoryId or collectionId:
        scenes = filter_public_scenes_by_taxonomy(
            scenes,
            publication_map,
            category_id=categoryId,
            collection_id=collectionId,
        )

    # Filter scenes for free (non-member) users
    try:
        user = get_request_user(request, allow_debug=True, fallback_default=True)
        user_id = user.get('id', '') if user else ''
        if user_id and commerce_store and not access_control.is_member_active(commerce_store, user_id):
            scenes = access_control.filter_scenes_for_free_user(scenes)
    except Exception:
        pass

    # Sort by creation time descending (newest first)
    def _scene_sort_key(scene):
        meta = scene.get('meta', {}) or {}
        # Prefer publishedAt for published public scenes
        published = meta.get('publishedAt', '')
        if published:
            return published
        # Fallback to timestamp embedded in sceneId
        return scene.get('sceneId', '')

    scenes.sort(key=_scene_sort_key, reverse=True)

    total = len(scenes)
    start = (page - 1) * pageSize
    end = start + pageSize
    page_items = scenes[start:end]

    return success({
        'list': [
            serialize_scene_summary(
                request,
                merge_public_scene_publication(scene, publication_map.get(scene.get('sceneId', ''))),
            )
            for scene in page_items
        ],
        'total': total,
        'page': page,
        'pageSize': pageSize,
        'categoryId': categoryId,
        'collectionId': collectionId,
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

    # Access control: check membership for public scenes
    if scene.get('sceneType') == 'public':
        try:
            user = get_request_user(request, allow_debug=True, fallback_default=True)
            user_id = user.get('id', '') if user else ''
            access_control.check_scene_access(scene_id, user_id, commerce_store)
        except HTTPException:
            raise
        except Exception:
            pass

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
    # Sort by creation time descending (newest first)
    scenes.sort(key=lambda s: s.get('sceneId', ''), reverse=True)
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

    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail={
                'code': 4013,
                'message': f'file too large, max {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB'
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


@app.post('/api/admin/uploads/image')
async def admin_upload_image(request: Request, file: UploadFile = File(...)):
    admin = get_current_admin(request)
    owner_id = resolve_admin_actor_id(admin)
    content = await file.read()

    if not content:
        raise HTTPException(status_code=400, detail={'code': 4000, 'message': 'empty file'})

    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=413, detail={'code': 4013, 'message': f'file too large, max {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB'})

    content_type = file.content_type or ''
    if content_type and not content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail={'code': 4000, 'message': 'only image upload is supported'})

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
        'height': upload.get('height'),
    })


@app.post('/api/my/tasks/scene-generate')
def create_scene_generate_task(request: Request, payload: SceneGenerateRequest):
    owner_id = get_current_user_id(request)

    # Check membership + credit balance, then deduct
    if commerce_store:
        try:
            access_control.check_scene_generate_permission(owner_id, commerce_store)
        except HTTPException:
            raise
        except Exception:
            pass

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

    # Deduct credit after task is created
    if commerce_store:
        try:
            access_control.deduct_scene_credit(owner_id, commerce_store, task['taskId'])
        except (HTTPException, ValueError):
            pass  # Task created; credit deduction best-effort

    return success({
        'taskId': task['taskId'],
        'status': task['status']
    })


@app.post('/api/admin/tasks/scene-generate-batch')
def admin_create_scene_generate_batch(request: Request, payload: AdminBatchSceneGenerateRequest):
    admin = get_current_admin(request)
    owner_id = resolve_admin_actor_id(admin)
    store = require_commerce_store()
    if payload.autoPublish and not payload.categoryId:
        raise HTTPException(status_code=400, detail={'code': 4000, 'message': 'categoryId is required when autoPublish is enabled'})
    if payload.categoryId and not store.get_scene_category(payload.categoryId):
        raise HTTPException(status_code=404, detail={'code': 4004, 'message': 'scene category not found'})
    for collection_id in payload.collectionIds:
        if not store.get_scene_collection(collection_id):
            raise HTTPException(status_code=404, detail={'code': 4004, 'message': 'scene collection not found'})

    created = []
    for item in payload.items:
        upload = upload_store.get_upload(item.uploadId)
        if not upload:
            raise HTTPException(status_code=404, detail={'code': 4004, 'message': 'upload not found'})
        if upload.get('ownerId') != owner_id:
            raise HTTPException(status_code=403, detail={'code': 4003, 'message': 'upload access denied'})

        task = task_store.create_task(
            owner_id=owner_id,
            payload={
                'uploadId': item.uploadId,
                'title': (item.title or '').strip(),
                'includeVerbs': payload.includeVerbs,
                'accent': payload.accent,
                'voiceGender': payload.voiceGender,
                'voiceName': payload.voiceName,
                'requestSource': 'admin_web_generator',
                'autoPublish': payload.autoPublish,
                'categoryId': payload.categoryId,
                'collectionIds': payload.collectionIds,
                'publishVisibility': payload.publishVisibility,
            },
        )
        created.append(serialize_admin_task(task))
    return success({'list': created})


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
        'publishedSceneId': task.get('publishedSceneId', ''),
        'errorMessage': task.get('errorMessage', '')
    })


# ---------------------------------------------------------------------------
# Video export
# ---------------------------------------------------------------------------

VIDEO_EXPORTS_DIR = ASSETS_DIR / 'video_exports'


@app.post('/api/scenes/{scene_id}/export-video')
@limiter.limit('3/minute')
def export_scene_video(scene_id: str, request: Request):
    user = get_request_user(request, allow_debug=True, fallback_default=True)
    if not user:
        raise HTTPException(status_code=401, detail={'code': 4001, 'message': 'login required'})

    # Check video export permission (creator card or master card)
    if commerce_store:
        access_control.check_video_export_permission(user.get('id', ''), commerce_store)

    scene = public_store.get_scene(scene_id)
    if not scene:
        scene = generated_store.get_scene(scene_id)

    if not scene:
        raise HTTPException(status_code=404, detail={'code': 4004, 'message': 'scene not found'})

    items_with_audio = [i for i in scene.get('items', []) if i.get('audioPath')]
    if not items_with_audio:
        raise HTTPException(
            status_code=400,
            detail={'code': 4100, 'message': 'scene has no items with audio to export'}
        )

    # Deduplicate: if same user already exporting this scene, return existing job
    existing_job_id = has_active_export(scene_id, user.get('id', ''))
    if existing_job_id:
        return success({
            'jobId': existing_job_id,
            'status': 'processing',
            'message': '该场景正在导出中，请等待完成'
        })

    job = create_export_job(scene_id, user.get('id', ''))

    start_export(job['jobId'], scene, ASSETS_DIR)

    return success({
        'jobId': job['jobId'],
        'status': job['status'],
        'message': '视频导出已开始'
    })


@app.get('/api/video-exports/{job_id}')
def get_video_export_status(job_id: str, request: Request):
    user = get_request_user(request, allow_debug=True, fallback_default=True)
    job = get_export_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail={'code': 4004, 'message': 'export job not found'})

    # Verify ownership
    if user and job.get('userId') and job['userId'] != user.get('id', ''):
        raise HTTPException(status_code=403, detail={'code': 4003, 'message': 'access denied'})

    result = {
        'jobId': job['jobId'],
        'sceneId': job['sceneId'],
        'status': job['status'],
        'progress': job['progress'],
        'message': job['message'],
        'createdAt': job['createdAt'],
        'completedAt': job.get('completedAt', ''),
    }

    if job['status'] == 'completed' and job.get('outputPath'):
        filename = Path(job['outputPath']).name
        result['videoUrl'] = f'/assets/video_exports/{filename}'

    return success(result)


@app.get('/api/me/video-exports')
def list_my_video_exports(request: Request):
    user_id = get_current_user_id(request)
    jobs = get_user_export_jobs(user_id)
    result = []
    for job in jobs:
        is_expired = False
        video_url = ''
        completed_at = job.get('completedAt', '')
        output_path = job.get('outputPath', '')
        if output_path:
            try:
                from datetime import datetime as _dt, timezone as _tz, timedelta as _td
                mtime = _dt.fromtimestamp(Path(output_path).stat().st_mtime, tz=_tz.utc)
                is_expired = (_dt.now(_tz.utc) - mtime) > _td(hours=VIDEO_RETENTION_HOURS)
            except (OSError, ValueError):
                is_expired = True
        if output_path and not is_expired:
            filename = Path(job['outputPath']).name
            video_url = f'/assets/video_exports/{filename}'
        scene = public_store.get_scene(job['sceneId'])
        if not scene:
            scene = generated_store.get_scene(job['sceneId'])
        cover_url = ''
        if scene:
            bg = scene.get('backgroundPath', '')
            if bg and not bg.startswith('http'):
                cover_url = f'{PUBLIC_BASE_URL}{bg}'
            elif bg:
                cover_url = bg
        result.append({
            'jobId': job['jobId'],
            'sceneId': job['sceneId'],
            'videoUrl': video_url,
            'isExpired': is_expired,
            'coverUrl': cover_url,
            'sceneTitle': (scene or {}).get('title', ''),
            'completedAt': completed_at,
        })
    return success({'list': result, 'total': len(result)})

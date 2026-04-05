import hashlib
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .auth_store_factory import create_auth_store
from .commerce_store_factory import create_commerce_store
from .generated_scene_store import GeneratedSceneStore
from .hotspot_permissions import can_edit_scene_hotspots
from .schemas import (
    AdminLoginRequest,
    AdminProductRequest,
    AdminPublicSceneRequest,
    AdminSkuRequest,
    MeProfileUpdateRequest,
    MockPaymentCompleteRequest,
    LogoutRequest,
    OrderCreateRequest,
    RefreshTokenRequest,
    SceneGenerateRequest,
    SceneHotspotUpdateRequest,
    WechatLoginRequest,
)
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
    PAYMENT_MODE,
    PUBLIC_BASE_URL,
    PUBLIC_SCENES_FILE,
    TASKS_FILE,
    UPLOADS_DIR,
    UPLOADS_FILE,
    WECHAT_MP_APP_ID,
    WECHAT_MP_APP_SECRET,
    WORKER_POLL_INTERVAL,
    ZHIPUAI_API_KEY,
)
from .task_store import TaskStore
from .upload_store import UploadStore
from .wechat_auth import WechatCode2SessionError, WechatMiniProgramAuthClient
from .worker_runner import InlineSceneWorker


auth_store = create_auth_store()
commerce_store = create_commerce_store()
wechat_auth_client = WechatMiniProgramAuthClient(WECHAT_MP_APP_ID, WECHAT_MP_APP_SECRET)
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
            'role': 'super_admin',
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

    if payload.get('role') != 'admin':
        unauthorized('admin unauthorized')

    username = str(payload.get('sub') or '').strip()
    if not username or username != ADMIN_DASHBOARD_USERNAME:
        unauthorized('admin unauthorized')
    return {
        'username': username,
        'role': 'super_admin',
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
        'displayName': user.get('displayName', ''),
        'avatarUrl': user.get('avatarUrl', ''),
        'mobile': user.get('mobile'),
        'mobileVerified': bool(user.get('mobileVerified')),
        'memberSummary': membership_summary,
        'creditSummary': credit_summary,
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
        'title': task.get('title', ''),
        'status': task.get('status', ''),
        'step': task.get('step', ''),
        'progress': task.get('progress', 0),
        'sceneId': task.get('sceneId', ''),
        'errorMessage': task.get('errorMessage', ''),
        'createdAt': task.get('createdAt', ''),
        'updatedAt': task.get('updatedAt', ''),
    }


def serialize_admin_scene(scene: dict) -> dict:
    return {
        'sceneId': scene.get('sceneId', ''),
        'title': scene.get('title', ''),
        'category': scene.get('category', ''),
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


@app.get('/api/admin/public-scenes')
def admin_list_public_scenes(request: Request):
    get_current_admin(request)
    return success({'list': [serialize_admin_scene(scene) for scene in public_store.list_scenes('')]})


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
    if PAYMENT_MODE != 'mock':
        raise HTTPException(
            status_code=501,
            detail={
                'code': 5001,
                'message': 'payment mode not implemented',
            },
        )
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

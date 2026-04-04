from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .settings import PUBLIC_BASE_URL
from .scene_store import SceneStore


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
ASSETS_DIR = REPO_ROOT / 'assets'
DATA_FILE = BACKEND_ROOT / 'data' / 'scenes.json'

store = SceneStore(DATA_FILE)

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
    return {
        'sceneId': scene['sceneId'],
        'title': scene['title'],
        'background': asset_url(request, scene.get('backgroundPath')),
        'cover': asset_url(request, scene.get('coverPath')),
        'items': [serialize_entry(request, item) for item in scene.get('items', [])],
        'verbs': [serialize_entry(request, verb) for verb in scene.get('verbs', [])],
        'meta': scene.get('meta', {})
    }


@app.get('/api/health')
def health():
    return success({
        'status': 'ok'
    })


@app.get('/api/scenes')
def list_scenes(
    request: Request,
    type: str = Query(default='public'),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=20, ge=1, le=100)
):
    scenes = store.list_scenes(type)
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
    scene = store.get_scene(scene_id)
    if not scene:
        raise HTTPException(
            status_code=404,
            detail={
                'code': 4004,
                'message': 'scene not found'
            }
        )

    return success(serialize_scene_detail(request, scene))


@app.get('/api/my/scenes')
def get_my_scenes(
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=20, ge=1, le=100)
):
    return success({
        'list': [],
        'total': 0,
        'page': page,
        'pageSize': pageSize
    })

import os
from pathlib import Path


def _normalize_base_url(value: str | None) -> str:
    if not value:
        return ''
    return value.rstrip('/')


def _normalize_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def _normalize_csv_set(value: str | None) -> set[str]:
    if not value:
        return set()
    return {item.strip() for item in value.split(',') if item.strip()}


def _load_env_file(env_file: Path) -> None:
    if not env_file.exists():
        return
    for raw_line in env_file.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


BACKEND_ROOT = Path(__file__).resolve().parents[1]
_load_env_file(BACKEND_ROOT / '.env')
REPO_ROOT = BACKEND_ROOT.parent
ASSETS_DIR = REPO_ROOT / 'assets'
DATA_DIR = BACKEND_ROOT / 'data'
CORE100_ROOT = Path(os.getenv('CORE100_ROOT', str(REPO_ROOT.parent / 'core100')))
PUBLIC_SCENES_FILE = DATA_DIR / 'scenes.json'
GENERATED_SCENES_FILE = DATA_DIR / 'generated_scenes.json'
TASKS_FILE = DATA_DIR / 'tasks.json'
UPLOADS_FILE = DATA_DIR / 'uploads.json'
UPLOADS_DIR = ASSETS_DIR / 'uploads'
GENERATED_DIR = ASSETS_DIR / 'generated'

PUBLIC_BASE_URL = _normalize_base_url(os.getenv('PUBLIC_BASE_URL', 'https://e.cps.vin'))
DATABASE_URL = (os.getenv('DATABASE_URL', '') or '').strip() or None
DEFAULT_MOCK_USER_ID = os.getenv('DEFAULT_MOCK_USER_ID', 'mock_user_001')
WORKER_POLL_INTERVAL = float(os.getenv('WORKER_POLL_INTERVAL', '2'))
ENABLE_INLINE_SCENE_WORKER = _normalize_bool(os.getenv('ENABLE_INLINE_SCENE_WORKER'), default=True)
CORE100_MODEL = (os.getenv('CORE100_MODEL', 'glm-4v-flash') or 'glm-4v-flash').strip()
CORE100_TTS_URL = _normalize_base_url(os.getenv('CORE100_TTS_URL', 'http://127.0.0.1:5003'))
ZHIPUAI_API_KEY = (os.getenv('ZHIPUAI_API_KEY', '') or '').strip() or None
HOTSPOT_EDITOR_ENABLED = _normalize_bool(os.getenv('HOTSPOT_EDITOR_ENABLED'), default=True)
HOTSPOT_EDITOR_ADMIN_USER_IDS = _normalize_csv_set(os.getenv('HOTSPOT_EDITOR_ADMIN_USER_IDS'))
HOTSPOT_EDITOR_PUBLIC_EDITOR_IDS = _normalize_csv_set(os.getenv('HOTSPOT_EDITOR_PUBLIC_EDITOR_IDS', '*'))
HOTSPOT_EDITOR_PRIVATE_EDITOR_IDS = _normalize_csv_set(os.getenv('HOTSPOT_EDITOR_PRIVATE_EDITOR_IDS', '*'))

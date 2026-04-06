import os
import json
import warnings
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


def _load_project_app_id(project_file: Path) -> str:
    if not project_file.exists():
        return ''
    try:
        payload = json.loads(project_file.read_text(encoding='utf-8'))
    except Exception:
        return ''
    return str(payload.get('appid') or '').strip()


BACKEND_ROOT = Path(__file__).resolve().parents[1]
_load_env_file(BACKEND_ROOT / '.env')
REPO_ROOT = BACKEND_ROOT.parent
ASSETS_DIR = REPO_ROOT / 'assets'
DATA_DIR = BACKEND_ROOT / 'data'
ADMIN_WEB_DIR = BACKEND_ROOT / 'admin_web'
CORE100_ROOT = Path(os.getenv('CORE100_ROOT', str(REPO_ROOT.parent / 'core100')))
PUBLIC_SCENES_FILE = DATA_DIR / 'scenes.json'
GENERATED_SCENES_FILE = DATA_DIR / 'generated_scenes.json'
TASKS_FILE = DATA_DIR / 'tasks.json'
UPLOADS_FILE = DATA_DIR / 'uploads.json'
UPLOADS_DIR = ASSETS_DIR / 'uploads'
GENERATED_DIR = ASSETS_DIR / 'generated'

PUBLIC_BASE_URL = _normalize_base_url(os.getenv('PUBLIC_BASE_URL', 'https://e.cps.vin'))
DATABASE_URL = (os.getenv('DATABASE_URL', '') or '').strip() or None
DATABASE_SCHEMA = (os.getenv('DATABASE_SCHEMA', 'public') or 'public').strip()
DEFAULT_MOCK_USER_ID = os.getenv('DEFAULT_MOCK_USER_ID', 'mock_user_001')
AUTH_DATA_FILE = DATA_DIR / 'auth.json'
AUTH_STORE_BACKEND = (os.getenv('AUTH_STORE_BACKEND', 'json') or 'json').strip().lower()
AUTH_ENABLE_DEBUG_USER_HEADER = _normalize_bool(os.getenv('AUTH_ENABLE_DEBUG_USER_HEADER'), default=False)
WECHAT_MP_APP_ID = (os.getenv('WECHAT_MP_APP_ID', '') or _load_project_app_id(REPO_ROOT / 'project.config.json')).strip()
WECHAT_MP_APP_SECRET = (os.getenv('WECHAT_MP_APP_SECRET', '') or '').strip()
WECHAT_SESSION_KEY_SECRET = (os.getenv('WECHAT_SESSION_KEY_SECRET', '') or '').strip() or None
AUTH_WECHAT_LOGIN_MODE = (os.getenv('AUTH_WECHAT_LOGIN_MODE', 'mock') or 'mock').strip().lower()
AUTH_JWT_SECRET = (os.getenv('AUTH_JWT_SECRET', 'dev-jwt-secret-change-me') or 'dev-jwt-secret-change-me').strip()
AUTH_ACCESS_TOKEN_TTL_SECONDS = int(os.getenv('AUTH_ACCESS_TOKEN_TTL_SECONDS', '7200'))
AUTH_REFRESH_TOKEN_TTL_SECONDS = int(os.getenv('AUTH_REFRESH_TOKEN_TTL_SECONDS', '2592000'))
COMMERCE_STORE_BACKEND = (os.getenv('COMMERCE_STORE_BACKEND', 'disabled') or 'disabled').strip().lower()
PAYMENT_MODE = (os.getenv('PAYMENT_MODE', 'mock') or 'mock').strip().lower()
WECHAT_PAY_MCH_ID = (os.getenv('WECHAT_PAY_MCH_ID', '') or '').strip()
WECHAT_PAY_API_V3_KEY = (os.getenv('WECHAT_PAY_API_V3_KEY', '') or '').strip()
WECHAT_PAY_MCH_SERIAL_NO = (os.getenv('WECHAT_PAY_MCH_SERIAL_NO', '') or '').strip()
WECHAT_PAY_MCH_PRIVATE_KEY_PATH = (os.getenv('WECHAT_PAY_MCH_PRIVATE_KEY_PATH', '') or '').strip()
WECHAT_PAY_PLATFORM_CERT_PATH = (os.getenv('WECHAT_PAY_PLATFORM_CERT_PATH', '') or '').strip()
WECHAT_PAY_PLATFORM_SERIAL_NO = (os.getenv('WECHAT_PAY_PLATFORM_SERIAL_NO', '') or '').strip()
WECHAT_PAY_NOTIFY_URL = _normalize_base_url(os.getenv('WECHAT_PAY_NOTIFY_URL', ''))
WECHAT_PAY_API_BASE = _normalize_base_url(os.getenv('WECHAT_PAY_API_BASE', 'https://api.mch.weixin.qq.com'))
WECHAT_PAY_CURRENCY = (os.getenv('WECHAT_PAY_CURRENCY', 'CNY') or 'CNY').strip().upper()
WECHAT_PAY_TIMEOUT_SECONDS = float(os.getenv('WECHAT_PAY_TIMEOUT_SECONDS', '10'))
WORKER_POLL_INTERVAL = float(os.getenv('WORKER_POLL_INTERVAL', '2'))
ENABLE_INLINE_SCENE_WORKER = _normalize_bool(os.getenv('ENABLE_INLINE_SCENE_WORKER'), default=True)
CORE100_MODEL = (os.getenv('CORE100_MODEL', 'glm-4v-flash') or 'glm-4v-flash').strip()
CORE100_TTS_URL = _normalize_base_url(os.getenv('CORE100_TTS_URL', 'http://127.0.0.1:5003'))
ZHIPUAI_API_KEY = (os.getenv('ZHIPUAI_API_KEY', '') or '').strip() or None
HOTSPOT_EDITOR_ENABLED = _normalize_bool(os.getenv('HOTSPOT_EDITOR_ENABLED'), default=True)
HOTSPOT_EDITOR_ADMIN_USER_IDS = _normalize_csv_set(os.getenv('HOTSPOT_EDITOR_ADMIN_USER_IDS'))
HOTSPOT_EDITOR_PUBLIC_EDITOR_IDS = _normalize_csv_set(os.getenv('HOTSPOT_EDITOR_PUBLIC_EDITOR_IDS', '*'))
HOTSPOT_EDITOR_PRIVATE_EDITOR_IDS = _normalize_csv_set(os.getenv('HOTSPOT_EDITOR_PRIVATE_EDITOR_IDS', '*'))
ADMIN_DASHBOARD_ENABLED = _normalize_bool(os.getenv('ADMIN_DASHBOARD_ENABLED'), default=True)
ADMIN_DASHBOARD_USERNAME = (os.getenv('ADMIN_DASHBOARD_USERNAME', 'admin') or 'admin').strip()
ADMIN_DASHBOARD_PASSWORD = (os.getenv('ADMIN_DASHBOARD_PASSWORD', 'admin123456') or 'admin123456').strip()

# --- Security-hardened settings ---
CORS_ALLOWED_ORIGINS = [o.strip() for o in os.getenv('CORS_ALLOWED_ORIGINS', 'https://e.cps.vin').split(',') if o.strip()]
MAX_UPLOAD_SIZE_BYTES = int(os.getenv('MAX_UPLOAD_SIZE_BYTES', str(10 * 1024 * 1024)))


def check_security_warnings() -> list[str]:
    """Return a list of security warnings for the current configuration."""
    warnings_list = []
    if AUTH_JWT_SECRET == 'dev-jwt-secret-change-me':
        warnings_list.append('AUTH_JWT_SECRET is using the default value "dev-jwt-secret-change-me". Set a strong secret in production!')
    if ADMIN_DASHBOARD_PASSWORD == 'admin123456':
        warnings_list.append('ADMIN_DASHBOARD_PASSWORD is using the default value "admin123456". Change it in production!')
    if AUTH_ENABLE_DEBUG_USER_HEADER:
        warnings_list.append('AUTH_ENABLE_DEBUG_USER_HEADER is True. X-Debug-User-Id header allows user impersonation. Disable in production!')
    return warnings_list

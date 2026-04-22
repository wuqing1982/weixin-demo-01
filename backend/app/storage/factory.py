from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import StorageBackend
from .config_store import StorageConfigStore
from .local import LocalStorage

_CONFIG_FILE = Path(__file__).resolve().parents[2] / "data" / "storage_config.json"
_store: StorageConfigStore | None = None
_instances: dict[str, StorageBackend] = {}


def get_storage_config_store() -> StorageConfigStore:
    global _store
    if _store is None:
        _store = StorageConfigStore(_CONFIG_FILE)
    return _store


def _create_backend(backend_id: str, config: dict[str, Any]) -> StorageBackend | None:
    backend_type = config.get("type", "")
    backend_config = config.get("config", {})
    if backend_type == "local":
        return LocalStorage(backend_config.get("root_dir", "assets"))
    if backend_type == "r2":
        if not all([backend_config.get("account_id"), backend_config.get("secret_access_key"), backend_config.get("bucket")]):
            return None
        from .r2 import CloudflareR2Storage
        return CloudflareR2Storage(backend_config)
    if backend_type == "cos":
        if not all([backend_config.get("secret_id"), backend_config.get("secret_key"), backend_config.get("bucket")]):
            return None
        from .cos import TencentCOSStorage
        return TencentCOSStorage(backend_config)
    return None


def get_active_storage() -> StorageBackend:
    store = get_storage_config_store()
    config = store.read_config()
    active_id = config.get("activeBackend", "local")
    backends = config.get("backends", {})

    if active_id in _instances:
        return _instances[active_id]

    active_config = backends.get(active_id, {})
    backend = _create_backend(active_id, active_config)

    if backend is None:
        fallback_id = config.get("lastActiveBackend", "local")
        if fallback_id != active_id and fallback_id in _instances:
            return _instances[fallback_id]
        fallback_config = backends.get(fallback_id, {})
        backend = _create_backend(fallback_id, fallback_config)

    if backend is None:
        backend = LocalStorage("assets")

    _instances[active_id] = backend
    return backend


def clear_cache() -> None:
    _instances.clear()

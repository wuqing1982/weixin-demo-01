import os
import stat
from pathlib import Path
from threading import Lock
from typing import Any

from ..store_utils import ensure_json_file, read_json_file, write_json_file

DEFAULT_CONFIG: dict[str, Any] = {
    "activeBackend": "local",
    "lastActiveBackend": "local",
    "backends": {
        "local": {
            "type": "local",
            "name": "本地存储",
            "enabled": True,
            "config": {"root_dir": "assets"},
        },
        "r2": {
            "type": "r2",
            "name": "Cloudflare R2",
            "enabled": False,
            "config": {
                "account_id": "",
                "access_key_id": "",
                "secret_access_key": "",
                "bucket": "",
                "public_url": "",
            },
        },
        "cos": {
            "type": "cos",
            "name": "腾讯云 COS",
            "enabled": False,
            "config": {
                "secret_id": "",
                "secret_key": "",
                "region": "",
                "bucket": "",
                "public_url": "",
            },
        },
    },
}

SENSITIVE_KEYS = {"secret_key", "secret_access_key", "secret_id"}
VALID_BACKEND_IDS = {"local", "r2", "cos"}


class StorageConfigStore:
    def __init__(self, config_file: Path):
        self.config_file = config_file
        self.lock = Lock()
        ensure_json_file(self.config_file, DEFAULT_CONFIG)
        try:
            os.chmod(self.config_file, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass

    def read_config(self) -> dict[str, Any]:
        with self.lock:
            return read_json_file(self.config_file)

    def write_config(self, payload: dict[str, Any]) -> None:
        with self.lock:
            write_json_file(self.config_file, payload)

    def get_all_backends_masked(self) -> dict[str, Any]:
        config = self.read_config()
        backends = config.get("backends", {})
        masked = {}
        for bid, backend in backends.items():
            backend_copy = dict(backend)
            backend_copy["config"] = self._mask_sensitive(backend.get("config", {}))
            masked[bid] = backend_copy
        return {
            "activeBackend": config.get("activeBackend", "local"),
            "lastActiveBackend": config.get("lastActiveBackend", "local"),
            "backends": masked,
        }

    def update_backend(self, backend_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        if backend_id not in VALID_BACKEND_IDS:
            return None
        config = self.read_config()
        backends = config.get("backends", {})
        if backend_id not in backends:
            return None
        backend = backends[backend_id]
        if "name" in updates and updates["name"]:
            backend["name"] = updates["name"]
        if "enabled" in updates:
            if backend_id == "local" and not updates["enabled"]:
                return None
            backend["enabled"] = updates["enabled"]
        if "config" in updates and updates["config"]:
            new_config = updates["config"]
            existing = backend.get("config", {})
            for key, value in new_config.items():
                if isinstance(value, str) and value.startswith("****"):
                    continue
                existing[key] = value
            backend["config"] = existing
        self.write_config(config)
        return backend

    def activate_backend(self, backend_id: str) -> bool:
        if backend_id not in VALID_BACKEND_IDS:
            return False
        config = self.read_config()
        backends = config.get("backends", {})
        if backend_id not in backends or not backends[backend_id].get("enabled", False):
            return False
        config["lastActiveBackend"] = config.get("activeBackend", "local")
        config["activeBackend"] = backend_id
        self.write_config(config)
        return True

    def get_active_backend_id(self) -> str:
        return self.read_config().get("activeBackend", "local")

    def get_active_config(self) -> dict[str, Any]:
        config = self.read_config()
        active_id = config.get("activeBackend", "local")
        return config.get("backends", {}).get(active_id, {})

    @staticmethod
    def _mask_sensitive(cfg: dict[str, str]) -> dict[str, str]:
        result = {}
        for key, value in cfg.items():
            if key in SENSITIVE_KEYS and isinstance(value, str) and len(value) > 4:
                result[key] = "****" + value[-4:]
            else:
                result[key] = value
        return result

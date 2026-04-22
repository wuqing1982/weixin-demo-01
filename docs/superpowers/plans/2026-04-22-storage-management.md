# Storage Management Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a storage management page to the admin panel with abstract storage backend layer, config CRUD, connection testing, usage monitoring, and backend switching.

**Architecture:** New `backend/app/storage/` module defines a `StorageBackend` Protocol with 3 implementations (Local, R2, COS). Config stored in `storage_config.json` with thread-safe reads. Admin API routes in a separate file. Frontend adds a sidebar menu item and renders the storage management view.

**Tech Stack:** Python 3.13, FastAPI, Pydantic v2, boto3 (R2), cos-python-sdk-v5 (COS), vanilla JS frontend

---

## File Structure

```
# New files
backend/app/storage/__init__.py           # Exports: get_active_storage, get_storage_config_store
backend/app/storage/base.py               # Protocol + dataclasses
backend/app/storage/local.py              # LocalStorage
backend/app/storage/r2.py                 # CloudflareR2Storage
backend/app/storage/cos.py                # TencentCOSStorage
backend/app/storage/config_store.py       # StorageConfigStore (thread-safe JSON)
backend/app/storage/factory.py            # Factory with caching
backend/app/routes/storage_admin.py       # 6 API endpoints

# Modified files
backend/admin_web/index.html              # Add sidebar nav group
backend/admin_web/admin.js                # Add storage view + state + renderStorage
backend/admin_web/admin.css               # Storage card styles
backend/app/main.py                       # include_router line
backend/requirements.txt                  # boto3, cos-python-sdk-v5
.gitignore                                # storage_config.json
```

---

## Chunk 1: Backend Storage Abstraction Layer

### Task 1: StorageBackend Protocol and data classes

**Files:**
- Create: `backend/app/storage/__init__.py`
- Create: `backend/app/storage/base.py`

- [ ] **Step 1: Create `backend/app/storage/base.py`**

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class StorageUsage:
    total_bytes: int
    used_bytes: int
    file_count: int
    by_type: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ConnectionTestResult:
    ok: bool
    message: str


@dataclass(frozen=True)
class FileInfo:
    path: str
    size_bytes: int
    last_modified: str | None = None


class StorageBackend(Protocol):
    def upload(self, path: str, content: bytes, content_type: str) -> str: ...
    def download(self, path: str) -> bytes: ...
    def delete(self, path: str) -> bool: ...
    def get_usage(self) -> StorageUsage: ...
    def test_connection(self) -> ConnectionTestResult: ...
    def list_files(self, prefix: str, limit: int) -> list[FileInfo]: ...
```

- [ ] **Step 2: Create `backend/app/storage/__init__.py`**

```python
from .config_store import StorageConfigStore
from .factory import get_active_storage, get_storage_config_store
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/storage/__init__.py backend/app/storage/base.py
git commit -m "feat: add StorageBackend Protocol and data classes"
```

---

### Task 2: StorageConfigStore (thread-safe JSON config)

**Files:**
- Create: `backend/app/storage/config_store.py`

- [ ] **Step 1: Create `backend/app/storage/config_store.py`**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/storage/config_store.py
git commit -m "feat: add StorageConfigStore with thread-safe JSON config"
```

---

### Task 3: LocalStorage implementation

**Files:**
- Create: `backend/app/storage/local.py`

- [ ] **Step 1: Create `backend/app/storage/local.py`**

```python
from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

from .base import ConnectionTestResult, FileInfo, StorageUsage

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
_AUDIO_EXTS = {".mp3", ".wav", ".ogg", ".m4a", ".aac"}
_USAGE_CACHE_TTL = 300  # 5 minutes


class LocalStorage:
    def __init__(self, root_dir: str, repo_root: Path | None = None):
        if repo_root is None:
            repo_root = Path(__file__).resolve().parents[3]
        self.root = repo_root / root_dir
        self._usage_cache: StorageUsage | None = None
        self._usage_cache_time: float = 0

    def upload(self, path: str, content: bytes, content_type: str) -> str:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return f"/{target.relative_to(self.root.parent.parent)}"

    def download(self, path: str) -> bytes:
        target = self._resolve(path)
        return target.read_bytes()

    def delete(self, path: str) -> bool:
        target = self._resolve(path)
        if target.exists():
            target.unlink()
            return True
        return False

    def get_usage(self) -> StorageUsage:
        now = time.monotonic()
        if self._usage_cache and (now - self._usage_cache_time) < _USAGE_CACHE_TTL:
            return self._usage_cache

        total_bytes = 0
        file_count = 0
        by_type: dict[str, int] = {}
        deadline = time.monotonic() + 10

        if self.root.exists():
            for entry in self.root.rglob("*"):
                if time.monotonic() > deadline:
                    break
                if entry.is_file():
                    try:
                        size = entry.stat().st_size
                        total_bytes += size
                        file_count += 1
                        ext = entry.suffix.lower()
                        if ext in _IMAGE_EXTS:
                            by_type["图片"] = by_type.get("图片", 0) + size
                        elif ext in _AUDIO_EXTS:
                            by_type["音频"] = by_type.get("音频", 0) + size
                        else:
                            by_type["其他"] = by_type.get("其他", 0) + size
                    except OSError:
                        pass

        disk_usage = shutil.disk_usage(self.root) if self.root.exists() else shutil.disk_usage(".")
        usage = StorageUsage(
            total_bytes=disk_usage.total,
            used_bytes=total_bytes,
            file_count=file_count,
            by_type=by_type,
        )
        self._usage_cache = usage
        self._usage_cache_time = now
        return usage

    def test_connection(self) -> ConnectionTestResult:
        try:
            if not self.root.exists():
                self.root.mkdir(parents=True, exist_ok=True)
            test_file = self.root / ".storage_test"
            test_file.write_text("ok")
            content = test_file.read_text()
            test_file.unlink()
            if content == "ok":
                return ConnectionTestResult(ok=True, message="本地存储连接正常")
            return ConnectionTestResult(ok=False, message="读写验证失败")
        except Exception as exc:
            return ConnectionTestResult(ok=False, message=f"本地存储不可用: {exc}")

    def list_files(self, prefix: str, limit: int) -> list[FileInfo]:
        results: list[FileInfo] = []
        search_dir = self.root / prefix if prefix else self.root
        if not search_dir.exists():
            return results
        for entry in search_dir.rglob("*"):
            if len(results) >= limit:
                break
            if entry.is_file():
                try:
                    stat = entry.stat()
                    results.append(FileInfo(
                        path=str(entry.relative_to(self.root)),
                        size_bytes=stat.st_size,
                        last_modified=None,
                    ))
                except OSError:
                    pass
        return results

    def _resolve(self, path: str) -> Path:
        relative = path.lstrip("/")
        return self.root.parent.parent / relative
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/storage/local.py
git commit -m "feat: add LocalStorage implementation with usage caching"
```

---

### Task 4: CloudflareR2Storage implementation

**Files:**
- Create: `backend/app/storage/r2.py`

- [ ] **Step 1: Create `backend/app/storage/r2.py`**

```python
from __future__ import annotations

import time
from typing import Any

from .base import ConnectionTestResult, FileInfo, StorageUsage

_USAGE_CACHE_TTL = 300


class CloudflareR2Storage:
    def __init__(self, config: dict[str, Any]):
        self.account_id = config.get("account_id", "")
        self.access_key_id = config.get("access_key_id", "")
        self.secret_access_key = config.get("secret_access_key", "")
        self.bucket = config.get("bucket", "")
        self.public_url = config.get("public_url", "").rstrip("/")
        self._client = None
        self._usage_cache: StorageUsage | None = None
        self._usage_cache_time: float = 0

    @property
    def endpoint_url(self) -> str:
        return f"https://{self.account_id}.r2.cloudflarestorage.com"

    def _get_client(self):
        if self._client is None:
            import boto3
            self._client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                region_name="auto",
            )
        return self._client

    def upload(self, path: str, content: bytes, content_type: str) -> str:
        self._get_client().put_object(
            Bucket=self.bucket, Key=path, Body=content, ContentType=content_type
        )
        return f"{self.public_url}/{path}" if self.public_url else path

    def download(self, path: str) -> bytes:
        resp = self._get_client().get_object(Bucket=self.bucket, Key=path)
        return resp["Body"].read()

    def delete(self, path: str) -> bool:
        self._get_client().delete_object(Bucket=self.bucket, Key=path)
        return True

    def get_usage(self) -> StorageUsage:
        now = time.monotonic()
        if self._usage_cache and (now - self._usage_cache_time) < _USAGE_CACHE_TTL:
            return self._usage_cache

        total_bytes = 0
        file_count = 0
        by_type: dict[str, int] = {}
        deadline = time.monotonic() + 10

        try:
            paginator = self._get_client().get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self.bucket, MaxKeys=1000):
                if time.monotonic() > deadline:
                    break
                for obj in page.get("Contents", []):
                    size = obj.get("Size", 0)
                    total_bytes += size
                    file_count += 1
                    key = obj.get("Key", "")
                    ext = key.rsplit(".", 1)[-1].lower() if "." in key else ""
                    if ext in {"jpg", "jpeg", "png", "webp", "gif", "bmp"}:
                        by_type["图片"] = by_type.get("图片", 0) + size
                    elif ext in {"mp3", "wav", "ogg", "m4a"}:
                        by_type["音频"] = by_type.get("音频", 0) + size
                    else:
                        by_type["其他"] = by_type.get("其他", 0) + size
        except Exception:
            pass

        usage = StorageUsage(
            total_bytes=0, used_bytes=total_bytes, file_count=file_count, by_type=by_type
        )
        self._usage_cache = usage
        self._usage_cache_time = now
        return usage

    def test_connection(self) -> ConnectionTestResult:
        try:
            self._get_client().head_bucket(Bucket=self.bucket)
            return ConnectionTestResult(ok=True, message="Cloudflare R2 连接正常")
        except Exception as exc:
            self._client = None
            return ConnectionTestResult(ok=False, message=f"R2 连接失败: {exc}")

    def list_files(self, prefix: str, limit: int) -> list[FileInfo]:
        results: list[FileInfo] = []
        try:
            resp = self._get_client().list_objects_v2(
                Bucket=self.bucket, Prefix=prefix, MaxKeys=limit
            )
            for obj in resp.get("Contents", []):
                results.append(FileInfo(
                    path=obj.get("Key", ""),
                    size_bytes=obj.get("Size", 0),
                    last_modified=str(obj.get("LastModified", "")),
                ))
        except Exception:
            pass
        return results
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/storage/r2.py
git commit -m "feat: add CloudflareR2Storage implementation"
```

---

### Task 5: TencentCOSStorage implementation

**Files:**
- Create: `backend/app/storage/cos.py`

- [ ] **Step 1: Create `backend/app/storage/cos.py`**

```python
from __future__ import annotations

import time
from typing import Any

from .base import ConnectionTestResult, FileInfo, StorageUsage

_USAGE_CACHE_TTL = 300


class TencentCOSStorage:
    def __init__(self, config: dict[str, Any]):
        self.secret_id = config.get("secret_id", "")
        self.secret_key = config.get("secret_key", "")
        self.region = config.get("region", "")
        self.bucket = config.get("bucket", "")
        self.public_url = config.get("public_url", "").rstrip("/")
        self._client = None
        self._usage_cache: StorageUsage | None = None
        self._usage_cache_time: float = 0

    def _get_client(self):
        if self._client is None:
            from qcloud_cos import CosConfig, CosS3Client
            cos_config = CosConfig(
                Region=self.region,
                SecretId=self.secret_id,
                SecretKey=self.secret_key,
            )
            self._client = CosS3Client(cos_config)
        return self._client

    def upload(self, path: str, content: bytes, content_type: str) -> str:
        self._get_client().put_object(
            Bucket=self.bucket, Key=path, Body=content, ContentType=content_type
        )
        return f"{self.public_url}/{path}" if self.public_url else path

    def download(self, path: str) -> bytes:
        resp = self._get_client().get_object(Bucket=self.bucket, Key=path)
        return resp["Body"].get_stream().read()

    def delete(self, path: str) -> bool:
        self._get_client().delete_object(Bucket=self.bucket, Key=path)
        return True

    def get_usage(self) -> StorageUsage:
        now = time.monotonic()
        if self._usage_cache and (now - self._usage_cache_time) < _USAGE_CACHE_TTL:
            return self._usage_cache

        total_bytes = 0
        file_count = 0
        by_type: dict[str, int] = {}
        deadline = time.monotonic() + 10
        marker = ""

        try:
            while time.monotonic() < deadline:
                resp = self._get_client().list_objects(
                    Bucket=self.bucket, Prefix="", Marker=marker, MaxKeys=1000
                )
                for obj in resp.get("Contents", []):
                    size = int(obj.get("Size", 0))
                    total_bytes += size
                    file_count += 1
                    key = obj.get("Key", "")
                    ext = key.rsplit(".", 1)[-1].lower() if "." in key else ""
                    if ext in {"jpg", "jpeg", "png", "webp", "gif", "bmp"}:
                        by_type["图片"] = by_type.get("图片", 0) + size
                    elif ext in {"mp3", "wav", "ogg", "m4a"}:
                        by_type["音频"] = by_type.get("音频", 0) + size
                    else:
                        by_type["其他"] = by_type.get("其他", 0) + size
                if resp.get("IsTruncated") == "true":
                    marker = resp.get("NextMarker", "")
                else:
                    break
        except Exception:
            pass

        usage = StorageUsage(
            total_bytes=0, used_bytes=total_bytes, file_count=file_count, by_type=by_type
        )
        self._usage_cache = usage
        self._usage_cache_time = now
        return usage

    def test_connection(self) -> ConnectionTestResult:
        try:
            self._get_client().head_bucket(Bucket=self.bucket)
            return ConnectionTestResult(ok=True, message="腾讯云 COS 连接正常")
        except Exception as exc:
            self._client = None
            return ConnectionTestResult(ok=False, message=f"COS 连接失败: {exc}")

    def list_files(self, prefix: str, limit: int) -> list[FileInfo]:
        results: list[FileInfo] = []
        try:
            resp = self._get_client().list_objects(
                Bucket=self.bucket, Prefix=prefix, MaxKeys=limit
            )
            for obj in resp.get("Contents", []):
                results.append(FileInfo(
                    path=obj.get("Key", ""),
                    size_bytes=int(obj.get("Size", 0)),
                    last_modified=obj.get("LastModified", ""),
                ))
        except Exception:
            pass
        return results
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/storage/cos.py
git commit -m "feat: add TencentCOSStorage implementation"
```

---

### Task 6: Factory with caching and fallback

**Files:**
- Create: `backend/app/storage/factory.py`

- [ ] **Step 1: Create `backend/app/storage/factory.py`**

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import StorageBackend
from .config_store import StorageConfigStore
from .local import LocalStorage
from .r2 import CloudflareR2Storage
from .cos import TencentCOSStorage

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
        return CloudflareR2Storage(backend_config)
    if backend_type == "cos":
        if not all([backend_config.get("secret_id"), backend_config.get("secret_key"), backend_config.get("bucket")]):
            return None
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
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/storage/factory.py backend/app/storage/__init__.py
git commit -m "feat: add storage factory with caching and fallback"
```

---

## Chunk 2: Admin API Routes

### Task 7: Storage admin API routes

**Files:**
- Create: `backend/app/routes/storage_admin.py`

- [ ] **Step 1: Create `backend/app/routes/storage_admin.py`**

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..storage.factory import clear_cache, get_active_storage, get_storage_config_store

router = APIRouter(prefix="/api/admin/storage", tags=["admin-storage"])


class StorageConfigUpdateRequest(BaseModel):
    name: str | None = None
    enabled: bool | None = None
    config: dict[str, str] | None = None


def _require_admin(request) -> None:
    from ..security import verify_token
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"code": 4001, "message": "未授权"})
    try:
        verify_token(auth[7:])
    except Exception:
        raise HTTPException(status_code=401, detail={"code": 4001, "message": "token 无效"})
    from ..settings import ADMIN_DASHBOARD_ENABLED
    if not ADMIN_DASHBOARD_ENABLED:
        raise HTTPException(status_code=503, detail={"code": 5003, "message": "admin dashboard disabled"})


@router.get("/overview")
def storage_overview(request: _Request):
    _require_admin(request)
    store = get_storage_config_store()
    configs = store.get_all_backends_masked()
    try:
        usage = get_active_storage().get_usage()
    except Exception:
        usage = {"totalBytes": 0, "usedBytes": 0, "fileCount": 0, "byType": {}}
    return {
        "code": 0,
        "data": {
            "activeBackend": configs["activeBackend"],
            "backends": configs["backends"],
            "usage": {
                "totalBytes": usage.total_bytes if hasattr(usage, "total_bytes") else usage.get("totalBytes", 0),
                "usedBytes": usage.used_bytes if hasattr(usage, "used_bytes") else usage.get("usedBytes", 0),
                "fileCount": usage.file_count if hasattr(usage, "file_count") else usage.get("fileCount", 0),
                "byType": usage.by_type if hasattr(usage, "by_type") else usage.get("byType", {}),
            },
        },
    }


@router.get("/configs")
def storage_configs(request: _Request):
    _require_admin(request)
    store = get_storage_config_store()
    return {"code": 0, "data": store.get_all_backends_masked()}


@router.put("/configs/{backend_id}")
def storage_update_config(backend_id: str, payload: StorageConfigUpdateRequest, request: _Request):
    _require_admin(request)
    store = get_storage_config_store()
    result = store.update_backend(backend_id, payload.model_dump(exclude_none=True))
    if result is None:
        raise HTTPException(status_code=400, detail={"code": 4000, "message": "无效的后端 ID 或不允许的操作"})
    clear_cache()
    return {"code": 0, "data": store.get_all_backends_masked()["backends"].get(backend_id, {})}


@router.post("/test/{backend_id}")
def storage_test_connection(backend_id: str, request: _Request):
    _require_admin(request)
    from ..storage.config_store import VALID_BACKEND_IDS
    if backend_id not in VALID_BACKEND_IDS:
        raise HTTPException(status_code=400, detail={"code": 4000, "message": "无效的后端 ID"})
    store = get_storage_config_store()
    config = store.read_config()
    backend_config = config.get("backends", {}).get(backend_id)
    if not backend_config:
        raise HTTPException(status_code=404, detail={"code": 4004, "message": "后端不存在"})
    from ..storage.factory import _create_backend
    backend = _create_backend(backend_id, backend_config)
    if backend is None:
        return {"code": 0, "data": {"ok": False, "message": "配置不完整，无法创建连接"}}
    result = backend.test_connection()
    return {"code": 0, "data": {"ok": result.ok, "message": result.message}}


@router.post("/activate/{backend_id}")
def storage_activate(backend_id: str, request: _Request):
    _require_admin(request)
    store = get_storage_config_store()
    config = store.read_config()
    backends = config.get("backends", {})
    if backend_id not in backends:
        raise HTTPException(status_code=400, detail={"code": 4000, "message": "无效的后端 ID"})
    if not backends[backend_id].get("enabled", False):
        raise HTTPException(status_code=400, detail={"code": 4000, "message": "后端未启用，请先启用并配置"})
    from ..storage.factory import _create_backend
    backend = _create_backend(backend_id, backends[backend_id])
    if backend is None:
        raise HTTPException(status_code=400, detail={"code": 4000, "message": "配置不完整"})
    result = backend.test_connection()
    if not result.ok:
        raise HTTPException(status_code=400, detail={"code": 4000, "message": f"连接测试失败: {result.message}"})
    store.activate_backend(backend_id)
    clear_cache()
    return {"code": 0, "data": {"activeBackend": backend_id, "message": "已切换活跃后端"}}


@router.get("/usage")
def storage_usage(request: _Request):
    _require_admin(request)
    try:
        usage = get_active_storage().get_usage()
    except Exception as exc:
        return {"code": 0, "data": {"totalBytes": 0, "usedBytes": 0, "fileCount": 0, "byType": {}, "error": str(exc)}}
    return {
        "code": 0,
        "data": {
            "totalBytes": usage.total_bytes,
            "usedBytes": usage.used_bytes,
            "fileCount": usage.file_count,
            "byType": usage.by_type,
        },
    }
```

Note: Replace `_Request` with `from fastapi import Request` and use `request: Request` in all signatures.

- [ ] **Step 2: Commit**

```bash
git add backend/app/routes/storage_admin.py
git commit -m "feat: add storage admin API routes"
```

---

### Task 8: Wire router into main.py

**Files:**
- Modify: `backend/app/main.py` (add ~3 lines near other imports)

- [ ] **Step 1: Add import and include_router to main.py**

Add after line 50 (the existing imports):
```python
from .routes.storage_admin import router as storage_admin_router
```

Add after the app creation (near line ~66, after `app = FastAPI(...)`):
```python
app.include_router(storage_admin_router)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: wire storage admin router into main app"
```

---

### Task 9: Update requirements.txt and .gitignore

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `.gitignore`

- [ ] **Step 1: Add boto3 and cos-python-sdk-v5 to requirements.txt**

Append:
```
boto3>=1.34,<2
cos-python-sdk-v5>=1.9,<2
```

- [ ] **Step 2: Add storage_config.json to .gitignore**

Append:
```
# Storage config (contains cloud credentials)
backend/data/storage_config.json
```

- [ ] **Step 3: Install new dependencies**

Run: `cd backend && pip install -r requirements.txt`

- [ ] **Step 4: Commit**

```bash
git add backend/requirements.txt .gitignore
git commit -m "feat: add boto3, cos-python-sdk-v5 deps and gitignore storage config"
```

---

## Chunk 3: Admin Frontend

### Task 10: Add sidebar menu item

**Files:**
- Modify: `backend/admin_web/index.html` (~line 58, after the 运营管理 nav-group)

- [ ] **Step 1: Add system config nav group after 运营管理**

Insert after the `</div>` closing the 运营管理 nav-group (line 58):
```html
          <div class="nav-group">
            <div class="nav-group-title">系统配置</div>
            <button class="nav-item" type="button" data-view="storage">存储管理</button>
          </div>
```

- [ ] **Step 2: Commit**

```bash
git add backend/admin_web/index.html
git commit -m "feat: add storage management sidebar menu item"
```

---

### Task 11: Add storage view JavaScript

**Files:**
- Modify: `backend/admin_web/admin.js`

- [ ] **Step 1: Add storage state fields**

In the `state` object (~line 8), add:
```javascript
  storageOverview: null,
  storageConfigs: null,
  editingBackend: null,
  testingBackend: null,
```

- [ ] **Step 2: Add `storage` to `VIEW_TITLES`**

In `VIEW_TITLES` (~line 1483), add:
```javascript
  storage: '存储管理',
```

- [ ] **Step 3: Add `renderStorage()` function**

Add before `renderCurrentView()`:
```javascript
function formatBytes(bytes) {
  if (!bytes || bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return (bytes / Math.pow(1024, i)).toFixed(2) + ' ' + units[i];
}

async function loadStorageData() {
  try {
    const [overview, configs] = await Promise.all([
      api('/api/admin/storage/overview'),
      api('/api/admin/storage/configs'),
    ]);
    state.storageOverview = overview;
    state.storageConfigs = configs;
  } catch (error) {
    toast(error.message || '加载存储数据失败', 'error');
  }
}

function renderStorage() {
  const overview = state.storageOverview || {};
  const usage = overview.usage || {};
  const backends = overview.backends || {};
  const activeId = overview.activeBackend || 'local';
  const editing = state.editingBackend;
  const editingConfig = editing ? (backends[editing] || {}) : {};

  const backendCards = Object.entries(backends).map(([id, cfg]) => {
    const isActive = id === activeId;
    const isEnabled = cfg.enabled;
    const statusLabel = isActive ? '使用中' : (isEnabled ? '已启用' : '未启用');
    const statusClass = isActive ? 'scene-tag--public' : (isEnabled ? 'scene-tag--member' : 'scene-tag--private');
    const canActivate = isEnabled && !isActive && id !== 'local';
    return `
      <div class="storage-backend-card ${isActive ? 'storage-backend-card--active' : ''}">
        <div class="storage-backend-header">
          <strong class="storage-backend-name">${escapeHtml(cfg.name || id)}</strong>
          <span class="scene-tag ${statusClass}">${statusLabel}</span>
        </div>
        <div class="storage-backend-type">${escapeHtml(cfg.type || id)}</div>
        <div class="storage-backend-actions">
          <button class="mini-btn" data-action="storage-edit" data-id="${escapeHtml(id)}">配置</button>
          ${canActivate ? `<button class="mini-btn success-btn" data-action="storage-test-activate" data-id="${escapeHtml(id)}">${state.testingBackend === id ? '测试中...' : '设为默认'}</button>` : ''}
          <button class="mini-btn" data-action="storage-test" data-id="${escapeHtml(id)}">${state.testingBackend === id ? '测试中...' : '测试连接'}</button>
        </div>
      </div>
    `;
  }).join('');

  const byTypeEntries = Object.entries(usage.byType || {});
  const maxTypeBytes = Math.max(...byTypeEntries.map(([, v]) => v), 1);
  const typeBreakdown = byTypeEntries.length > 0 ? byTypeEntries.map(([type, bytes]) => `
    <div class="storage-type-row">
      <span class="storage-type-label">${escapeHtml(type)}</span>
      <div class="storage-type-bar-wrap">
        <div class="storage-type-bar" style="width:${Math.max(2, (bytes / maxTypeBytes) * 100)}%"></div>
      </div>
      <span class="storage-type-value">${formatBytes(bytes)}</span>
    </div>
  `).join('') : '<div class="empty-copy">暂无分类数据</div>';

  panelHead.innerHTML = `
    <div>
      <h3 class="panel-title">存储管理</h3>
      <p class="panel-subtitle">配置存储后端、监控用量、切换默认存储。</p>
    </div>
  `;

  panelBody.innerHTML = `
    <div class="storage-metrics">
      ${metricCard('已用空间', formatBytes(usage.usedBytes))}
      ${metricCard('总容量', formatBytes(usage.totalBytes))}
      ${metricCard('剩余空间', formatBytes(Math.max(0, (usage.totalBytes || 0) - (usage.usedBytes || 0))))}
      ${metricCard('文件数量', usage.fileCount || 0)}
    </div>

    <div class="storage-section-title">存储后端配置</div>
    <div class="storage-backends-grid">
      ${backendCards}
    </div>

    <div class="storage-section-title">文件类型分布</div>
    <div class="storage-type-breakdown">
      ${typeBreakdown}
    </div>
  `;
}

function getStorageConfigFields(backendId, config) {
  const type = config.type || backendId;
  const cfg = config.config || {};
  if (type === 'local') {
    return `<label class="full"><span>根目录</span><input name="root_dir" value="${escapeHtml(cfg.root_dir || 'assets')}" readonly></label>`;
  }
  if (type === 'r2') {
    return `
      <label><span>Account ID</span><input name="account_id" value="${escapeHtml(cfg.account_id || '')}"></label>
      <label><span>Access Key ID</span><input name="access_key_id" value="${escapeHtml(cfg.access_key_id || '')}"></label>
      <label><span>Secret Access Key</span><input name="secret_access_key" type="password" value="${escapeHtml(cfg.secret_access_key || '')}" placeholder="留空保持不变"></label>
      <label><span>Bucket</span><input name="bucket" value="${escapeHtml(cfg.bucket || '')}"></label>
      <label class="full"><span>Public URL</span><input name="public_url" value="${escapeHtml(cfg.public_url || '')}"></label>
      <label><span>启用</span>
        <select name="enabled">
          <option value="true" ${cfg.enabled !== false ? 'selected' : ''}>启用</option>
          <option value="false" ${cfg.enabled === false ? 'selected' : ''}>禁用</option>
        </select>
      </label>
    `;
  }
  if (type === 'cos') {
    return `
      <label><span>Secret ID</span><input name="secret_id" value="${escapeHtml(cfg.secret_id || '')}"></label>
      <label><span>Secret Key</span><input name="secret_key" type="password" value="${escapeHtml(cfg.secret_key || '')}" placeholder="留空保持不变"></label>
      <label><span>Region</span><input name="region" value="${escapeHtml(cfg.region || '')}"></label>
      <label><span>Bucket</span><input name="bucket" value="${escapeHtml(cfg.bucket || '')}"></label>
      <label class="full"><span>Public URL</span><input name="public_url" value="${escapeHtml(cfg.public_url || '')}"></label>
      <label><span>启用</span>
        <select name="enabled">
          <option value="true" ${cfg.enabled !== false ? 'selected' : ''}>启用</option>
          <option value="false" ${cfg.enabled === false ? 'selected' : ''}>禁用</option>
        </select>
      </label>
    `;
  }
  return '';
}
```

- [ ] **Step 4: Update `renderCurrentView()` to handle storage**

In `renderCurrentView()`, before the final `renderUsers();` fallback (~line 1547), add:
```javascript
  if (state.currentView === 'storage') {
    if (!state.storageOverview) {
      loadStorageData().then(() => renderStorage());
      panelBody.innerHTML = '<div class="empty-copy">加载中...</div>';
      return;
    }
    renderStorage();
    return;
  }
```

- [ ] **Step 5: Add storage action handlers**

In `handleAction()`, add these cases:
```javascript
  if (action === 'storage-edit') {
    state.editingBackend = id;
    const configs = state.storageConfigs || {};
    const backends = configs.backends || {};
    const cfg = backends[id] || {};
    const formHtml = `
      <form id="storage-config-form">
        <input type="hidden" name="backend_id" value="${escapeHtml(id)}">
        <div class="field-grid">
          ${getStorageConfigFields(id, cfg)}
        </div>
        <div class="form-actions" style="display:flex;gap:10px;margin-top:18px">
          <button class="primary-btn compact" type="submit">保存配置</button>
          <button type="button" class="ghost-btn" data-action="storage-cancel-edit">取消</button>
        </div>
      </form>
    `;
    openModal(`配置 ${escapeHtml(cfg.name || id)}`, formHtml);
    return;
  }
  if (action === 'storage-cancel-edit') {
    state.editingBackend = null;
    closeModal();
    return;
  }
  if (action === 'storage-test') {
    state.testingBackend = id;
    renderStorage();
    try {
      const result = await api(`/api/admin/storage/test/${id}`, { method: 'POST' });
      toast(result.ok ? `${result.message}` : result.message, result.ok ? undefined : 'error');
    } catch (error) {
      toast(error.message || '测试失败', 'error');
    }
    state.testingBackend = null;
    await loadStorageData();
    renderStorage();
    return;
  }
  if (action === 'storage-test-activate') {
    state.testingBackend = id;
    renderStorage();
    try {
      const testResult = await api(`/api/admin/storage/test/${id}`, { method: 'POST' });
      if (!testResult.ok) {
        toast(testResult.message, 'error');
        state.testingBackend = null;
        renderStorage();
        return;
      }
      await api(`/api/admin/storage/activate/${id}`, { method: 'POST' });
      toast('已切换活跃存储后端');
    } catch (error) {
      toast(error.message || '切换失败', 'error');
    }
    state.testingBackend = null;
    await loadStorageData();
    renderStorage();
    return;
  }
```

- [ ] **Step 6: Add storage form submit handler**

In the `panelBody.addEventListener('submit', ...)` block, add:
```javascript
    if (event.target.id === 'storage-config-form') {
      const form = event.target;
      const backendId = form.backend_id.value;
      const config = {};
      const enabledVal = form.querySelector('[name="enabled"]');
      const fields = form.querySelectorAll('input[name]:not([name="backend_id"]):not([name="enabled"]), select[name]:not([name="enabled"])');
      fields.forEach((input) => {
        config[input.name] = input.value;
      });
      const payload = { config };
      if (enabledVal) {
        payload.enabled = enabledVal.value === 'true';
      }
      try {
        await api(`/api/admin/storage/configs/${backendId}`, { method: 'PUT', body: payload });
        toast('配置已保存');
        state.editingBackend = null;
        closeModal();
        await loadStorageData();
        renderStorage();
      } catch (error) {
        toast(error.message || '保存失败', 'error');
      }
      return;
    }
```

- [ ] **Step 7: Commit**

```bash
git add backend/admin_web/admin.js
git commit -m "feat: add storage management frontend view and handlers"
```

---

### Task 12: Add storage CSS styles

**Files:**
- Modify: `backend/admin_web/admin.css`

- [ ] **Step 1: Append storage styles**

```css
/* ========== Storage Management ========== */

.storage-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.storage-section-title {
  font-size: 15px;
  font-weight: 700;
  margin: 24px 0 14px;
  color: var(--ink);
}

.storage-backends-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.storage-backend-card {
  padding: 20px;
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  background: var(--panel);
  transition: box-shadow 0.2s;
}

.storage-backend-card:hover {
  box-shadow: var(--shadow);
}

.storage-backend-card--active {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px rgba(108, 92, 231, 0.12);
}

.storage-backend-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}

.storage-backend-name {
  font-size: 16px;
}

.storage-backend-type {
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 14px;
}

.storage-backend-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.storage-type-breakdown {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.storage-type-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.storage-type-label {
  width: 60px;
  font-size: 13px;
  color: var(--ink);
  font-weight: 500;
}

.storage-type-bar-wrap {
  flex: 1;
  height: 8px;
  border-radius: 4px;
  background: rgba(108, 92, 231, 0.08);
  overflow: hidden;
}

.storage-type-bar {
  height: 100%;
  border-radius: 4px;
  background: var(--accent);
  transition: width 0.3s;
}

.storage-type-value {
  width: 80px;
  text-align: right;
  font-size: 13px;
  color: var(--muted);
}
```

- [ ] **Step 2: Commit**

```bash
git add backend/admin_web/admin.css
git commit -m "style: add storage management CSS styles"
```

---

## Chunk 4: Integration & Verification

### Task 13: Fix route type annotations

**Files:**
- Modify: `backend/app/routes/storage_admin.py`

- [ ] **Step 1: Replace `_Request` with proper FastAPI Request**

Replace all `_Request` with `Request` and add `from fastapi import APIRouter, HTTPException, Request` at the top. Remove the placeholder note.

- [ ] **Step 2: Commit**

```bash
git add backend/app/routes/storage_admin.py
git commit -m "fix: use proper Request type in storage admin routes"
```

---

### Task 14: Manual verification

- [ ] **Step 1: Start the backend server**

Run: `cd backend && python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000`

Expected: Server starts without import errors.

- [ ] **Step 2: Verify API endpoints**

Run in another terminal:
```bash
# Login first
TOKEN=$(curl -s http://localhost:8000/api/admin/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123456"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['accessToken'])")

# Get overview
curl -s http://localhost:8000/api/admin/storage/overview \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.json

# Get configs
curl -s http://localhost:8000/api/admin/storage/configs \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.json

# Test local connection
curl -s -X POST http://localhost:8000/api/admin/storage/test/local \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.json
```

Expected: All return `{"code": 0, "data": {...}}`.

- [ ] **Step 3: Open admin panel in browser**

Navigate to `http://localhost:8000/admin/`, login, click 「存储管理」.

Expected: Storage management page renders with metrics, backend cards, and type breakdown.

---

### Task 15: Final commit and push

- [ ] **Step 1: Ensure clean state**

Run: `git status`

- [ ] **Step 2: Push to remote**

```bash
git push origin 118v3
```

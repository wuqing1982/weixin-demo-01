from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..storage.factory import clear_cache, get_active_storage, get_storage_config_store
from ..storage.config_store import VALID_BACKEND_IDS

router = APIRouter(prefix="/api/admin/storage", tags=["admin-storage"])


class StorageConfigUpdateRequest(BaseModel):
    name: str | None = None
    enabled: bool | None = None
    config: dict[str, str] | None = None


def _admin(request: Request) -> dict:
    from ..main import get_current_admin
    return get_current_admin(request)


@router.get("/overview")
def storage_overview(request: Request):
    _admin(request)
    store = get_storage_config_store()
    configs = store.get_all_backends_masked()
    try:
        usage = get_active_storage().get_usage()
        usage_data = {
            "totalBytes": usage.total_bytes,
            "usedBytes": usage.used_bytes,
            "fileCount": usage.file_count,
            "byType": usage.by_type,
        }
    except Exception:
        usage_data = {"totalBytes": 0, "usedBytes": 0, "fileCount": 0, "byType": {}}
    return {
        "code": 0,
        "data": {
            "activeBackend": configs["activeBackend"],
            "lastActiveBackend": configs.get("lastActiveBackend", "local"),
            "backends": configs["backends"],
            "usage": usage_data,
        },
    }


@router.get("/configs")
def storage_configs(request: Request):
    _admin(request)
    store = get_storage_config_store()
    return {"code": 0, "data": store.get_all_backends_masked()}


@router.put("/configs/{backend_id}")
def storage_update_config(backend_id: str, payload: StorageConfigUpdateRequest, request: Request):
    _admin(request)
    store = get_storage_config_store()
    result = store.update_backend(backend_id, payload.model_dump(exclude_none=True))
    if result is None:
        raise HTTPException(status_code=400, detail={"code": 4000, "message": "无效的后端 ID 或不允许的操作"})
    clear_cache()
    masked = store.get_all_backends_masked()
    return {"code": 0, "data": masked["backends"].get(backend_id, {})}


@router.post("/test/{backend_id}")
def storage_test_connection(backend_id: str, request: Request):
    _admin(request)
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
def storage_activate(backend_id: str, request: Request):
    _admin(request)
    if backend_id not in VALID_BACKEND_IDS:
        raise HTTPException(status_code=400, detail={"code": 4000, "message": "无效的后端 ID"})
    store = get_storage_config_store()
    config = store.read_config()
    backends = config.get("backends", {})
    if backend_id not in backends:
        raise HTTPException(status_code=400, detail={"code": 4000, "message": "后端不存在"})
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
def storage_usage(request: Request):
    _admin(request)
    try:
        usage = get_active_storage().get_usage()
        return {
            "code": 0,
            "data": {
                "totalBytes": usage.total_bytes,
                "usedBytes": usage.used_bytes,
                "fileCount": usage.file_count,
                "byType": usage.by_type,
            },
        }
    except Exception as exc:
        return {"code": 0, "data": {"totalBytes": 0, "usedBytes": 0, "fileCount": 0, "byType": {}, "error": str(exc)}}

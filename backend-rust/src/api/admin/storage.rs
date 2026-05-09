use axum::extract::{Path, State};
use axum::Json;
use serde_json::{json, Value};

use crate::db::storage_config;
use crate::error::AppError;
use crate::middleware::auth::AdminUser;
use crate::models::storage_config::{StorageConfigUpdateRequest, VALID_BACKEND_IDS, required_config_keys};
use crate::response;
use crate::services::storage_config::{build_backends_json, get_disk_stats, get_upload_stats, mask_config};
use crate::services::storage_test::test_connection;
use crate::state::AppState;

pub async fn storage_overview(
    State(state): State<AppState>,
    _admin: AdminUser,
) -> Result<Json<Value>, AppError> {
    let rows = storage_config::list_all_configs(&state.pool).await?;
    let active = storage_config::get_active(&state.pool).await?;
    let backends = build_backends_json(&rows, true);
    let (file_count, used_bytes, by_type) = get_upload_stats(&state.pool).await;
    let (total_bytes, disk_used) = get_disk_stats(&state.config.assets_dir);
    Ok(response::success(json!({
        "activeBackend": active.backend_id,
        "lastActiveBackend": "local",
        "backends": backends,
        "usage": {
            "totalBytes": total_bytes,
            "usedBytes": disk_used.max(used_bytes as u64),
            "fileCount": file_count,
            "byType": by_type,
        },
    })))
}

pub async fn storage_configs(
    State(state): State<AppState>,
    _admin: AdminUser,
) -> Result<Json<Value>, AppError> {
    let rows = storage_config::list_all_configs(&state.pool).await?;
    let active = storage_config::get_active(&state.pool).await?;
    let backends = build_backends_json(&rows, true);
    Ok(response::success(json!({
        "activeBackend": active.backend_id,
        "lastActiveBackend": "local",
        "backends": backends,
    })))
}

pub async fn storage_update_config(
    State(state): State<AppState>,
    _admin: AdminUser,
    Path(backend_id): Path<String>,
    Json(payload): Json<StorageConfigUpdateRequest>,
) -> Result<Json<Value>, AppError> {
    if !VALID_BACKEND_IDS.contains(&backend_id.as_str()) {
        return Err(AppError::BadRequest("无效的后端 ID".into()));
    }
    if backend_id == "local" && payload.enabled == Some(false) {
        return Err(AppError::BadRequest("不能禁用本地存储".into()));
    }
    let result = storage_config::update_config(
        &state.pool, &backend_id, payload.name.as_deref(), payload.enabled, payload.config,
    ).await?;
    let row = match result {
        Some(r) => r,
        None => return Err(AppError::NotFound("后端不存在".into())),
    };
    let masked_config = mask_config(&row.config);
    Ok(response::success(json!({
        "type": row.backend_type,
        "name": row.name,
        "enabled": row.enabled,
        "config": masked_config,
    })))
}

pub async fn storage_test_connection(
    State(state): State<AppState>,
    _admin: AdminUser,
    Path(backend_id): Path<String>,
) -> Result<Json<Value>, AppError> {
    if !VALID_BACKEND_IDS.contains(&backend_id.as_str()) {
        return Err(AppError::BadRequest("无效的后端 ID".into()));
    }
    let row = storage_config::get_config_by_id(&state.pool, &backend_id)
        .await?.ok_or_else(|| AppError::NotFound("后端不存在".into()))?;
    let result = test_connection(&row.backend_type, &row.config).await;
    Ok(response::success(json!({ "ok": result.ok, "message": result.message })))
}

pub async fn storage_activate(
    State(state): State<AppState>,
    _admin: AdminUser,
    Path(backend_id): Path<String>,
) -> Result<Json<Value>, AppError> {
    if !VALID_BACKEND_IDS.contains(&backend_id.as_str()) {
        return Err(AppError::BadRequest("无效的后端 ID".into()));
    }
    let row = storage_config::get_config_by_id(&state.pool, &backend_id)
        .await?.ok_or_else(|| AppError::NotFound("后端不存在".into()))?;
    if !row.enabled {
        return Err(AppError::BadRequest("后端未启用，请先启用并配置".into()));
    }
    let required = required_config_keys(&row.backend_type);
    let empty_map = serde_json::Map::new();
    let config_obj = row.config.as_object().unwrap_or(&empty_map);
    for key in required {
        let empty = config_obj.get(*key).and_then(|v| v.as_str()).map(|s| s.is_empty()).unwrap_or(true);
        if empty {
            return Err(AppError::BadRequest(format!("配置不完整：缺少 {}", key)));
        }
    }
    let result = test_connection(&row.backend_type, &row.config).await;
    if !result.ok {
        return Err(AppError::BadRequest(format!("连接测试失败: {}", result.message)));
    }
    let active = storage_config::set_active(&state.pool, &backend_id).await?;
    Ok(response::success(json!({ "activeBackend": active.backend_id, "message": "已切换活跃后端" })))
}

pub async fn storage_usage(
    State(state): State<AppState>,
    _admin: AdminUser,
) -> Result<Json<Value>, AppError> {
    let (file_count, used_bytes, by_type) = get_upload_stats(&state.pool).await;
    let (total_bytes, _) = get_disk_stats(&state.config.assets_dir);
    Ok(response::success(json!({
        "totalBytes": total_bytes,
        "usedBytes": used_bytes,
        "fileCount": file_count,
        "byType": by_type,
    })))
}

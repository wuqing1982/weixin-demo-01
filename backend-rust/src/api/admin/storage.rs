use axum::extract::State;
use axum::Json;
use serde_json::{json, Value};

use crate::error::AppError;
use crate::middleware::auth::AdminUser;
use crate::response;
use crate::state::AppState;

pub async fn storage_overview(
    State(state): State<AppState>,
    _admin: AdminUser,
) -> Result<Json<Value>, AppError> {
    let (file_count, used_bytes): (i64, i64) = sqlx::query_as(
        "SELECT COALESCE(count(*),0), COALESCE(sum(file_size),0) FROM uploads"
    )
    .fetch_one(&state.pool)
    .await
    .unwrap_or((0, 0));

    Ok(response::success(json!({
        "activeBackend": "local",
        "backends": {},
        "usage": {
            "totalBytes": 0,
            "usedBytes": used_bytes,
            "fileCount": file_count,
            "byType": {},
        },
    })))
}

pub async fn storage_configs(
    _state: State<AppState>,
    _admin: AdminUser,
) -> Result<Json<Value>, AppError> {
    Ok(response::success(json!({
        "activeBackend": "local",
        "backends": {},
    })))
}

pub async fn storage_usage(
    State(state): State<AppState>,
    _admin: AdminUser,
) -> Result<Json<Value>, AppError> {
    let (file_count, used_bytes): (i64, i64) = sqlx::query_as(
        "SELECT COALESCE(count(*),0), COALESCE(sum(file_size),0) FROM uploads"
    )
    .fetch_one(&state.pool)
    .await
    .unwrap_or((0, 0));

    Ok(response::success(json!({
        "totalBytes": 0,
        "usedBytes": used_bytes,
        "fileCount": file_count,
        "byType": {},
    })))
}

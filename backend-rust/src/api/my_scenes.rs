use std::path::Path;

use axum::extract::{Query, State};
use axum::Json;
use serde::Deserialize;
use serde_json::{json, Value};

use crate::api::scene::asset_url;
use crate::db;
use crate::error::AppError;
use crate::middleware::auth::AuthUser;
use crate::response::success;
use crate::state::AppState;

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct BatchDeleteRequest {
    pub scene_ids: Vec<String>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct MyScenesQuery {
    pub page: Option<i64>,
    pub page_size: Option<i64>,
    pub category_id: Option<String>,
}

pub async fn list_my_scenes(
    State(state): State<AppState>,
    auth: AuthUser,
    Query(query): Query<MyScenesQuery>,
) -> Result<Json<Value>, AppError> {
    let storage = crate::storage::resolver::resolve(&state.pool, &state.config)
        .await
        .map_err(|e| AppError::Internal(e.to_string()))?;
    let base_url = storage.base_url();

    let page = query.page.unwrap_or(1).max(1);
    let page_size = query.page_size.unwrap_or(12).min(100);
    let offset = (page - 1) * page_size;
    let category_id = query.category_id.as_deref().filter(|s| !s.is_empty());

    let (scenes, total) = db::scenes::get_user_scenes(&state.pool, &auth.user_id, page_size, offset, category_id).await?;

    let list: Vec<Value> = scenes
        .iter()
        .map(|s| {
            json!({
                "sceneId": s.scene_id,
                "title": s.title,
                "category": s.category,
                "visibility": s.visibility,
                "sceneType": s.scene_type,
                "coverUrl": asset_url(&base_url, &s.cover_path),
                "backgroundUrl": asset_url(&base_url, &s.background_path),
                "itemCount": s.items.as_array().map(|a| a.len()).unwrap_or(0),
                "createdAt": s.created_at.to_rfc3339(),
            })
        })
        .collect();

    Ok(success(json!({
        "list": list,
        "total": total,
        "page": page,
        "pageSize": page_size,
    })))
}

pub async fn batch_delete_my_scenes(
    State(state): State<AppState>,
    auth: AuthUser,
    Json(body): Json<BatchDeleteRequest>,
) -> Result<Json<Value>, AppError> {
    if body.scene_ids.is_empty() {
        return Ok(success(json!({"count": 0})));
    }
    if body.scene_ids.len() > 100 {
        return Err(AppError::BadRequest("单次最多删除100个场景".into()));
    }
    let count = db::scenes::batch_delete_user_scenes(&state.pool, &auth.user_id, &body.scene_ids).await?;

    // 清理存储文件（best-effort，失败不影响响应）
    cleanup_scene_files(&state, &body.scene_ids).await;

    Ok(success(json!({"count": count})))
}

pub async fn cleanup_scene_files(state: &AppState, scene_ids: &[String]) {
    let storage = match crate::storage::resolver::resolve(&state.pool, &state.config).await {
        Ok(s) => s,
        Err(e) => {
            tracing::error!(error = %e, "场景文件清理: 无法获取存储实例");
            return;
        }
    };

    for sid in scene_ids {
        let prefix = format!("generated/{}", sid);
        if let Err(e) = storage.delete_prefix(&prefix).await {
            tracing::warn!(scene_id = %sid, error = %e, "场景文件清理: 存储删除失败");
        }
        let dir = Path::new(&state.config.generated_dir).join(sid);
        let _ = tokio::fs::remove_dir_all(&dir).await;
    }
}

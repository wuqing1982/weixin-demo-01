use axum::extract::{Query, State};
use axum::Json;
use serde::Deserialize;
use serde_json::{json, Value};

use crate::db;
use crate::error::AppError;
use crate::middleware::auth::AuthUser;
use crate::response::success;
use crate::state::AppState;

#[derive(Debug, Deserialize)]
pub struct MyScenesQuery {
    pub page: Option<i64>,
    pub page_size: Option<i64>,
}

pub async fn list_my_scenes(
    State(state): State<AppState>,
    auth: AuthUser,
    Query(query): Query<MyScenesQuery>,
) -> Result<Json<Value>, AppError> {
    let page = query.page.unwrap_or(1).max(1);
    let page_size = query.page_size.unwrap_or(20).min(100);
    let offset = (page - 1) * page_size;

    let (scenes, total) = db::scenes::get_user_scenes(&state.pool, &auth.user_id, page_size, offset).await?;

    let items: Vec<Value> = scenes
        .iter()
        .map(|s| {
            json!({
                "sceneId": s.scene_id,
                "title": s.title,
                "category": s.category,
                "visibility": s.visibility,
                "sceneType": s.scene_type,
                "coverPath": s.cover_path,
                "itemsCount": s.items.as_array().map(|a| a.len()).unwrap_or(0),
                "createdAt": s.created_at.to_rfc3339(),
            })
        })
        .collect();

    Ok(success(json!({
        "items": items,
        "total": total,
        "page": page,
        "pageSize": page_size,
    })))
}

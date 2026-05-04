use axum::extract::{Path, State};
use axum::Json;
use serde::Deserialize;
use serde_json::{json, Value};

use crate::db;
use crate::error::AppError;
use crate::middleware::auth::AuthUser;
use crate::response::success;
use crate::state::AppState;

#[derive(Debug, Deserialize)]
pub struct HotspotUpdateRequest {
    pub items: Vec<HotspotRectUpdate>,
}

#[derive(Debug, Deserialize)]
pub struct HotspotRectUpdate {
    pub id: String,
    pub rect: RectInput,
}

#[derive(Debug, Deserialize)]
pub struct RectInput {
    pub l: f64,
    pub t: f64,
    pub w: f64,
    pub h: f64,
}

pub async fn update_hotspots(
    State(state): State<AppState>,
    auth: AuthUser,
    Path(scene_id): Path<String>,
    Json(body): Json<HotspotUpdateRequest>,
) -> Result<Json<Value>, AppError> {
    if body.items.is_empty() {
        return Err(AppError::BadRequest("at least one hotspot update is required".into()));
    }

    let scene = db::scenes::get_scene(&state.pool, &scene_id)
        .await?
        .ok_or_else(|| AppError::NotFound("scene not found".into()))?;

    // Permission check: admin always allowed, owner allowed for generated scenes
    let is_admin = auth.role == "admin";
    let is_owner = scene.owner_id.as_deref() == Some(&auth.user_id);
    if !is_admin && !is_owner {
        return Err(AppError::Forbidden(
            "only scene owner or admin can edit hotspots".into(),
        ));
    }

    if !state.config.hotspot_editor_enabled && !is_admin {
        return Err(AppError::Forbidden("hotspot editing is disabled".into()));
    }

    // Build updates map
    let updates: std::collections::HashMap<&str, &RectInput> =
        body.items.iter().map(|item| (item.id.as_str(), &item.rect)).collect();

    // Update scene items
    let mut items = scene.items.as_array().cloned().unwrap_or_default();
    let mut found_ids = std::collections::HashSet::new();

    for item in &mut items {
        let item_id = item["id"].as_str().unwrap_or("").to_string();
        if let Some(rect) = updates.get(item_id.as_str()) {
            let old = item.clone();
            *item = json!({
                "id": old["id"],
                "word": old["word"],
                "ipa": old["ipa"],
                "meaning": old["meaning"],
                "sentence": old["sentence"],
                "sentenceTranslation": old["sentenceTranslation"],
                "audioPath": old["audioPath"],
                "rect": {
                    "l": clamp(rect.l),
                    "t": clamp(rect.t),
                    "w": clamp(rect.w),
                    "h": clamp(rect.h),
                },
            });
            found_ids.insert(item_id);
        }
    }

    let missing: Vec<&str> = updates
        .keys()
        .filter(|id| !found_ids.contains(id.to_string().as_str()))
        .copied()
        .collect();

    if !missing.is_empty() {
        return Err(AppError::BadRequest(format!(
            "unknown hotspot ids: {}",
            missing.join(", ")
        )));
    }

    db::scenes::save_hotspots(&state.pool, &scene_id, &items).await?;

    Ok(success(json!({
        "updatedCount": found_ids.len(),
    })))
}

fn clamp(v: f64) -> f64 {
    (v * 100.0).round() / 100.0
}

use axum::extract::{Path, Query, State};
use axum::Json;
use serde::Deserialize;
use serde_json::{json, Value};

use crate::db::scenes;
use crate::error::AppError;
use crate::middleware::auth::OptionalAuthUser;
use crate::response::success;
use crate::state::AppState;

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ListScenesQuery {
    page: Option<i64>,
    page_size: Option<i64>,
    category: Option<String>,
}

pub async fn list_scenes(
    State(state): State<AppState>,
    Query(query): Query<ListScenesQuery>,
    _auth: OptionalAuthUser,
) -> Result<Json<Value>, AppError> {
    let page_size = query.page_size.unwrap_or(state.config.scene_page_size).min(100).max(1);
    let page = query.page.unwrap_or(1).max(1);
    let offset = (page - 1) * page_size;

    let (scenes, total) = scenes::list_public_scenes(&state.pool, page_size, offset).await?;

    let list: Vec<Value> = scenes.iter().map(|s| serialize_scene_summary(&state, s)).collect();

    Ok(success(json!({
        "list": list,
        "total": total,
        "page": page,
        "pageSize": page_size,
    })))
}

pub async fn get_scene(
    State(state): State<AppState>,
    Path(scene_id): Path<String>,
    opt_auth: OptionalAuthUser,
) -> Result<Json<Value>, AppError> {
    let scene = scenes::get_scene(&state.pool, &scene_id)
        .await?
        .ok_or_else(|| AppError::NotFound(format!("scene {scene_id} not found")))?;

    let can_edit = can_edit_hotspots(&state, &scene, opt_auth.0.as_ref());

    Ok(success(json!(serialize_scene_detail(&state, &scene, can_edit))))
}

pub async fn list_scene_categories(
    State(state): State<AppState>,
) -> Result<Json<Value>, AppError> {
    let cats = scenes::list_categories(&state.pool).await?;
    Ok(success(json!({"list": cats})))
}

pub async fn list_scene_collections(
    State(state): State<AppState>,
) -> Result<Json<Value>, AppError> {
    let cols = scenes::list_collections(&state.pool).await?;
    Ok(success(json!({"list": cols})))
}

pub(crate) fn asset_url(base_url: &str, path: &str) -> String {
    if path.is_empty() || path.starts_with("http") {
        return path.to_string();
    }
    let clean_path = path.trim_start_matches('/');
    format!("{}/{}", base_url.trim_end_matches('/'), clean_path)
}

fn serialize_scene_summary(state: &AppState, scene: &crate::models::scene::Scene) -> Value {
    let items = scene.items.as_array().map(|a| a.len()).unwrap_or(0);
    json!({
        "sceneId": scene.scene_id,
        "title": scene.title,
        "category": scene.category,
        "coverUrl": asset_url(&state.config.public_base_url, &scene.cover_path),
        "backgroundUrl": asset_url(&state.config.public_base_url, &scene.background_path),
        "itemCount": items,
        "visibility": scene.visibility,
        "free": scene.meta_json.get("free").and_then(|v| v.as_bool()).unwrap_or(false),
    })
}

pub(crate) fn serialize_scene_detail(state: &AppState, scene: &crate::models::scene::Scene, can_edit: bool) -> Value {
    let hotspots: Vec<crate::models::scene::HotspotItem> = serde_json::from_value(scene.items.clone()).unwrap_or_default();
    let verbs: Vec<crate::models::scene::VerbItem> = serde_json::from_value(scene.verbs.clone()).unwrap_or_default();

    json!({
        "sceneId": scene.scene_id,
        "title": scene.title,
        "category": scene.category,
        "visibility": scene.visibility,
        "sceneType": scene.scene_type,
        "background": asset_url(&state.config.public_base_url, &scene.background_path),
        "cover": asset_url(&state.config.public_base_url, &scene.cover_path),
        "items": hotspots,
        "verbs": verbs,
        "meta": scene.meta_json,
        "free": scene.meta_json.get("free").and_then(|v| v.as_bool()).unwrap_or(false),
        "capabilities": { "canEditHotspots": can_edit },
    })
}

pub(crate) fn can_edit_hotspots(
    state: &AppState,
    scene: &crate::models::scene::Scene,
    auth: Option<&crate::middleware::auth::AuthUser>,
) -> bool {
    if !state.config.hotspot_editor_enabled {
        return false;
    }

    let Some(auth) = auth else { return false };

    // Admin always allowed
    if auth.role == "admin" || auth.role == "super_admin" {
        return true;
    }

    // Owner of generated/private scenes can edit
    if scene.owner_id.as_deref() == Some(&auth.user_id) {
        return true;
    }

    // Check meta.hotspotEditors for explicit per-scene access
    if let Some(editors) = scene.meta_json.get("hotspotEditors").and_then(|v| v.as_array()) {
        if editors.iter().any(|e| e.as_str() == Some("*") || e.as_str() == Some(&auth.user_id)) {
            return true;
        }
    }

    false
}

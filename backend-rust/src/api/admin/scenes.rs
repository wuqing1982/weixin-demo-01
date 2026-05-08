use axum::extract::{Path, Query, State};
use axum::Json;
use serde::Deserialize;
use serde_json::{json, Value};

use crate::error::AppError;
use crate::middleware::auth::AdminUser;
use crate::response;
use crate::state::AppState;

#[derive(Deserialize)]
pub struct LimitQuery {
    pub limit: Option<i64>,
    pub page: Option<i64>,
}

pub async fn list_public_scenes(
    State(state): State<AppState>,
    _admin: AdminUser,
    Query(q): Query<LimitQuery>,
) -> Result<Json<Value>, AppError> {
    let page_size = q.limit.unwrap_or(state.config.admin_page_size).min(200).max(1);
    let page = q.page.unwrap_or(1).max(1);
    let offset = (page - 1) * page_size;
    let (scenes, total) = crate::db::scenes::list_all_public_scenes(&state.pool, page_size, offset).await?;

    let mut list = Vec::with_capacity(scenes.len());
    for scene in &scenes {
        let item_count = scene
            .items
            .as_array()
            .map(|a| a.len())
            .unwrap_or(0);
        let verb_count = scene
            .verbs
            .as_array()
            .map(|a| a.len())
            .unwrap_or(0);

        let category_id = scene
            .meta_json
            .get("categoryId")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();
        let collection_ids: Vec<String> = scene
            .meta_json
            .get("collectionIds")
            .and_then(|v| v.as_array())
            .map(|arr| {
                arr.iter()
                    .filter_map(|v| v.as_str().map(|s| s.to_string()))
                    .collect()
            })
            .unwrap_or_default();
        let free = scene
            .meta_json
            .get("free")
            .and_then(|v| v.as_bool())
            .unwrap_or(false);

        let publication =
            crate::db::scenes::get_publication_by_public_id(&state.pool, &scene.scene_id)
                .await
                .ok()
                .flatten();

        let publication_value = if let Some(ref pub_) = publication {
            let pub_collections =
                crate::db::scenes::list_publication_collections(&state.pool, &scene.scene_id)
                    .await
                    .unwrap_or_default();
            Some(json!({
                "sourceGeneratedSceneId": pub_.source_generated_scene_id,
                "publicSceneId": pub_.public_scene_id,
                "categoryId": pub_.category_id,
                "collectionIds": pub_collections,
                "visibility": pub_.visibility,
                "publishedBy": pub_.published_by,
                "publishedAt": pub_.published_at.map(|t| t.to_rfc3339()),
            }))
        } else {
            None
        };

        list.push(json!({
            "sceneId": scene.scene_id,
            "title": scene.title,
            "category": scene.category,
            "categoryId": category_id,
            "collectionIds": collection_ids,
            "visibility": scene.visibility,
            "sceneType": scene.scene_type,
            "backgroundPath": scene.background_path,
            "coverPath": scene.cover_path,
            "free": free,
            "itemCount": item_count,
            "verbCount": verb_count,
            "items": scene.items,
            "verbs": scene.verbs,
            "meta": scene.meta_json,
            "publication": publication_value,
        }));
    }

    Ok(response::success(json!({ "list": list, "total": total, "page": page, "pageSize": page_size })))
}

pub async fn list_generated_scenes(
    State(state): State<AppState>,
    _admin: AdminUser,
    Query(q): Query<LimitQuery>,
) -> Result<Json<Value>, AppError> {
    let limit = q.limit.unwrap_or(state.config.admin_page_size).min(200).max(1);
    let page = q.page.unwrap_or(1).max(1);
    let offset = (page - 1) * limit;
    let (scenes, total) = crate::db::scenes::list_all_generated_scenes(&state.pool, limit, offset).await?;

    let base_url = &state.config.public_base_url;

    let mut list = Vec::with_capacity(scenes.len());
    for scene in &scenes {
        let item_count = scene
            .items
            .as_array()
            .map(|a| a.len())
            .unwrap_or(0);
        let verb_count = scene
            .verbs
            .as_array()
            .map(|a| a.len())
            .unwrap_or(0);

        let category_id = scene
            .meta_json
            .get("categoryId")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();
        let collection_ids: Vec<String> = scene
            .meta_json
            .get("collectionIds")
            .and_then(|v| v.as_array())
            .map(|arr| {
                arr.iter()
                    .filter_map(|v| v.as_str().map(|s| s.to_string()))
                    .collect()
            })
            .unwrap_or_default();
        let free = scene
            .meta_json
            .get("free")
            .and_then(|v| v.as_bool())
            .unwrap_or(false);

        let background_url = if scene.background_path.is_empty() {
            String::new()
        } else {
            format!("{}/{}", base_url, scene.background_path)
        };
        let cover_url = if scene.cover_path.is_empty() {
            String::new()
        } else {
            format!("{}/{}", base_url, scene.cover_path)
        };

        let owner_id = scene
            .owner_id
            .clone()
            .or_else(|| {
                scene
                    .meta_json
                    .get("ownerId")
                    .and_then(|v| v.as_str())
                    .map(|s| s.to_string())
            })
            .unwrap_or_default();

        let publication =
            crate::db::scenes::get_publication_by_source_id(&state.pool, &scene.scene_id)
                .await
                .ok()
                .flatten();

        let publication_value = if let Some(ref pub_) = publication {
            let pub_collections =
                crate::db::scenes::list_publication_collections(&state.pool, &pub_.public_scene_id)
                    .await
                    .unwrap_or_default();
            Some(json!({
                "sourceGeneratedSceneId": pub_.source_generated_scene_id,
                "publicSceneId": pub_.public_scene_id,
                "categoryId": pub_.category_id,
                "collectionIds": pub_collections,
                "visibility": pub_.visibility,
                "publishedBy": pub_.published_by,
                "publishedAt": pub_.published_at.map(|t| t.to_rfc3339()),
            }))
        } else {
            None
        };

        list.push(json!({
            "sceneId": scene.scene_id,
            "title": scene.title,
            "category": scene.category,
            "categoryId": category_id,
            "collectionIds": collection_ids,
            "visibility": scene.visibility,
            "sceneType": scene.scene_type,
            "backgroundPath": scene.background_path,
            "coverPath": scene.cover_path,
            "backgroundUrl": background_url,
            "coverUrl": cover_url,
            "ownerId": owner_id,
            "free": free,
            "itemCount": item_count,
            "verbCount": verb_count,
            "items": scene.items,
            "verbs": scene.verbs,
            "meta": scene.meta_json,
            "publication": publication_value,
        }));
    }

    Ok(response::success(json!({ "list": list, "total": total, "page": page, "pageSize": limit })))
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct BatchIdsRequest {
    pub scene_ids: Vec<String>,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct BatchVisibilityRequest {
    pub scene_ids: Vec<String>,
    pub visibility: String,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct BatchFreeRequest {
    pub scene_ids: Vec<String>,
    pub free: bool,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct BatchCategoryRequest {
    pub scene_ids: Vec<String>,
    pub category_id: String,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SceneUpsertRequest {
    pub scene_id: Option<String>,
    pub title: String,
    pub category: Option<String>,
    pub visibility: Option<String>,
    pub scene_type: Option<String>,
    pub cover_path: Option<String>,
    pub background_path: Option<String>,
    pub items: Option<serde_json::Value>,
    pub verbs: Option<serde_json::Value>,
    pub meta: Option<serde_json::Value>,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct PublishDraftRequest {
    pub title: Option<String>,
    pub visibility: Option<String>,
    pub category_id: Option<String>,
    pub collection_ids: Option<Vec<String>>,
}

pub async fn batch_delete_scenes(
    State(state): State<AppState>,
    _admin: AdminUser,
    Json(body): Json<BatchIdsRequest>,
) -> Result<Json<Value>, AppError> {
    if body.scene_ids.is_empty() {
        return Ok(response::success(json!({"count": 0})));
    }
    let count = crate::db::scenes::batch_delete_scenes(&state.pool, &body.scene_ids).await?;
    Ok(response::success(json!({"count": count})))
}

pub async fn batch_visibility(
    State(state): State<AppState>,
    _admin: AdminUser,
    Json(body): Json<BatchVisibilityRequest>,
) -> Result<Json<Value>, AppError> {
    if body.scene_ids.is_empty() {
        return Ok(response::success(json!({"count": 0})));
    }
    let count = crate::db::scenes::batch_update_scene_visibility(&state.pool, &body.scene_ids, &body.visibility).await?;
    Ok(response::success(json!({"count": count})))
}

pub async fn batch_free(
    State(state): State<AppState>,
    _admin: AdminUser,
    Json(body): Json<BatchFreeRequest>,
) -> Result<Json<Value>, AppError> {
    if body.scene_ids.is_empty() {
        return Ok(response::success(json!({"count": 0})));
    }
    let count = crate::db::scenes::batch_update_scene_meta_bool(&state.pool, &body.scene_ids, "free", body.free).await?;
    Ok(response::success(json!({"count": count})))
}

pub async fn batch_category(
    State(state): State<AppState>,
    _admin: AdminUser,
    Json(body): Json<BatchCategoryRequest>,
) -> Result<Json<Value>, AppError> {
    if body.scene_ids.is_empty() {
        return Ok(response::success(json!({"count": 0})));
    }
    let count = crate::db::scenes::batch_update_scene_category(&state.pool, &body.scene_ids, &body.category_id).await?;
    Ok(response::success(json!({"count": count})))
}

pub async fn create_scene(
    State(state): State<AppState>,
    _admin: AdminUser,
    Json(body): Json<SceneUpsertRequest>,
) -> Result<Json<Value>, AppError> {
    let scene_id = body.scene_id.clone().unwrap_or_else(|| format!("scene_{}", uuid::Uuid::new_v4()));
    let scene = json!({
        "sceneId": scene_id,
        "title": body.title,
        "category": body.category.unwrap_or_default(),
        "visibility": body.visibility.unwrap_or_else(|| "public".into()),
        "sceneType": body.scene_type.unwrap_or_else(|| "public".into()),
        "coverPath": body.cover_path.unwrap_or_default(),
        "backgroundPath": body.background_path.unwrap_or_default(),
        "items": body.items.unwrap_or(json!([])),
        "verbs": body.verbs.unwrap_or(json!([])),
        "metaJson": body.meta.unwrap_or(json!({})),
    });
    crate::db::scenes::upsert_public_scene(&state.pool, &scene).await?;
    Ok(response::success(json!({"sceneId": scene_id})))
}

pub async fn update_scene(
    State(state): State<AppState>,
    _admin: AdminUser,
    Path(scene_id): Path<String>,
    Json(body): Json<SceneUpsertRequest>,
) -> Result<Json<Value>, AppError> {
    let scene = json!({
        "sceneId": scene_id,
        "title": body.title,
        "category": body.category.unwrap_or_default(),
        "visibility": body.visibility.unwrap_or_else(|| "public".into()),
        "sceneType": body.scene_type.unwrap_or_else(|| "public".into()),
        "coverPath": body.cover_path.unwrap_or_default(),
        "backgroundPath": body.background_path.unwrap_or_default(),
        "items": body.items.unwrap_or(json!([])),
        "verbs": body.verbs.unwrap_or(json!([])),
        "metaJson": body.meta.unwrap_or(json!({})),
    });
    crate::db::scenes::upsert_public_scene(&state.pool, &scene).await?;
    Ok(response::success(json!({})))
}

pub async fn republish_scene(
    State(state): State<AppState>,
    _admin: AdminUser,
    Path(scene_id): Path<String>,
) -> Result<Json<Value>, AppError> {
    let _scene = crate::db::scenes::get_scene(&state.pool, &scene_id)
        .await?
        .ok_or_else(|| AppError::NotFound("场景不存在".into()))?;
    let publication = crate::db::scenes::get_publication_by_public_id(&state.pool, &scene_id)
        .await?
        .ok_or_else(|| AppError::NotFound("场景发布记录不存在".into()))?;

    if let Some(src) = crate::db::scenes::get_scene(&state.pool, &publication.source_generated_scene_id).await? {
        let new_scene = json!({
            "sceneId": scene_id,
            "title": src.title,
            "category": src.category,
            "visibility": publication.visibility,
            "sceneType": "public",
            "coverPath": src.cover_path,
            "backgroundPath": src.background_path,
            "items": src.items,
            "verbs": src.verbs,
            "metaJson": src.meta_json,
        });
        crate::db::scenes::upsert_public_scene(&state.pool, &new_scene).await?;
    }
    Ok(response::success(json!({})))
}

pub async fn publish_draft(
    State(state): State<AppState>,
    admin: AdminUser,
    Path(scene_id): Path<String>,
    Json(body): Json<PublishDraftRequest>,
) -> Result<Json<Value>, AppError> {
    let scene = crate::db::scenes::get_scene(&state.pool, &scene_id)
        .await?
        .ok_or_else(|| AppError::NotFound("场景不存在".into()))?;

    let title = body.title.unwrap_or_else(|| scene.title.clone());
    let visibility = body.visibility.unwrap_or_else(|| "public".into());
    let category_id = body.category_id.unwrap_or_default();
    let collection_ids = body.collection_ids.unwrap_or_default();

    let public_id = format!("scene_{}", uuid::Uuid::new_v4());

    // Create the public scene as a copy
    let public_scene = json!({
        "sceneId": public_id,
        "title": title,
        "category": scene.category,
        "visibility": visibility,
        "sceneType": "public",
        "coverPath": scene.cover_path,
        "backgroundPath": scene.background_path,
        "items": scene.items,
        "verbs": scene.verbs,
        "metaJson": json!({
            "categoryId": category_id,
            "collectionIds": collection_ids,
            "sourceGeneratedSceneId": scene_id,
        }),
    });
    crate::db::scenes::upsert_public_scene(&state.pool, &public_scene).await?;
    crate::db::scenes::publish_generated_scene(&state.pool, &scene_id, &public_id, &category_id, &visibility, &admin.username, &collection_ids).await?;

    Ok(response::success(json!({"publicSceneId": public_id})))
}

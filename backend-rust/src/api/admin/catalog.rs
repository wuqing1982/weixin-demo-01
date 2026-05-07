use axum::extract::{Path, State};
use axum::Json;
use serde::Deserialize;
use serde_json::{json, Value};

use crate::error::AppError;
use crate::middleware::auth::AdminUser;
use crate::response;
use crate::state::AppState;

pub async fn list_categories(
    State(state): State<AppState>,
    _admin: AdminUser,
) -> Result<Json<Value>, AppError> {
    let categories = crate::db::scenes::list_all_categories(&state.pool).await?;

    let list: Vec<Value> = categories
        .into_iter()
        .map(|cat| {
            json!({
                "categoryId": cat.id,
                "categoryCode": cat.category_code,
                "name": cat.name,
                "description": cat.description,
                "status": cat.status,
                "sortOrder": cat.sort_order,
            })
        })
        .collect();

    Ok(response::success(json!({ "list": list })))
}

pub async fn list_collections(
    State(state): State<AppState>,
    _admin: AdminUser,
) -> Result<Json<Value>, AppError> {
    let collections = crate::db::scenes::list_all_collections(&state.pool).await?;

    let list: Vec<Value> = collections
        .into_iter()
        .map(|col| {
            json!({
                "collectionId": col.id,
                "collectionCode": col.collection_code,
                "name": col.name,
                "description": col.description,
                "status": col.status,
                "coverUrl": col.cover_url,
                "sortOrder": col.sort_order,
            })
        })
        .collect();

    Ok(response::success(json!({ "list": list })))
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CategoryUpsertRequest {
    pub name: String,
    pub description: Option<String>,
    pub status: Option<String>,
    pub sort_order: Option<i32>,
    pub category_code: Option<String>,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CollectionUpsertRequest {
    pub collection_code: Option<String>,
    pub name: String,
    pub description: Option<String>,
    pub status: Option<String>,
    pub cover_url: Option<String>,
    pub sort_order: Option<i32>,
}

pub async fn create_category(
    State(state): State<AppState>,
    _admin: AdminUser,
    Json(body): Json<CategoryUpsertRequest>,
) -> Result<Json<Value>, AppError> {
    let id = format!("scene_category_{}", uuid::Uuid::new_v4());
    crate::db::scenes::upsert_category(
        &state.pool, &id,
        &body.category_code.unwrap_or_default(),
        &body.name,
        &body.description.unwrap_or_default(),
        &body.status.unwrap_or_else(|| "active".into()),
        body.sort_order.unwrap_or(0),
    ).await?;
    Ok(response::success(json!({"categoryId": id})))
}

pub async fn update_category(
    State(state): State<AppState>,
    _admin: AdminUser,
    Path(category_id): Path<String>,
    Json(body): Json<CategoryUpsertRequest>,
) -> Result<Json<Value>, AppError> {
    crate::db::scenes::upsert_category(
        &state.pool, &category_id,
        &body.category_code.unwrap_or_default(),
        &body.name,
        &body.description.unwrap_or_default(),
        &body.status.unwrap_or_else(|| "active".into()),
        body.sort_order.unwrap_or(0),
    ).await?;
    Ok(response::success(json!({})))
}

pub async fn delete_category(
    State(state): State<AppState>,
    _admin: AdminUser,
    Path(category_id): Path<String>,
) -> Result<Json<Value>, AppError> {
    crate::db::scenes::delete_category(&state.pool, &category_id).await?;
    Ok(response::success(json!({})))
}

pub async fn create_collection(
    State(state): State<AppState>,
    _admin: AdminUser,
    Json(body): Json<CollectionUpsertRequest>,
) -> Result<Json<Value>, AppError> {
    let id = format!("scene_collection_{}", uuid::Uuid::new_v4());
    crate::db::scenes::upsert_collection(
        &state.pool, &id,
        &body.collection_code.unwrap_or_default(),
        &body.name,
        &body.description.unwrap_or_default(),
        &body.status.unwrap_or_else(|| "active".into()),
        &body.cover_url.unwrap_or_default(),
        body.sort_order.unwrap_or(0),
    ).await?;
    Ok(response::success(json!({"collectionId": id})))
}

pub async fn update_collection(
    State(state): State<AppState>,
    _admin: AdminUser,
    Path(collection_id): Path<String>,
    Json(body): Json<CollectionUpsertRequest>,
) -> Result<Json<Value>, AppError> {
    crate::db::scenes::upsert_collection(
        &state.pool, &collection_id,
        &body.collection_code.unwrap_or_default(),
        &body.name,
        &body.description.unwrap_or_default(),
        &body.status.unwrap_or_else(|| "active".into()),
        &body.cover_url.unwrap_or_default(),
        body.sort_order.unwrap_or(0),
    ).await?;
    Ok(response::success(json!({})))
}

pub async fn delete_collection(
    State(state): State<AppState>,
    _admin: AdminUser,
    Path(collection_id): Path<String>,
) -> Result<Json<Value>, AppError> {
    crate::db::scenes::delete_collection(&state.pool, &collection_id).await?;
    Ok(response::success(json!({})))
}

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
}

fn serialize_user(user: &crate::models::user::User) -> Value {
    json!({
        "id": user.id,
        "role": user.role,
        "isAdmin": user.role == "admin" || user.role == "super_admin",
        "displayName": user.display_name.clone().unwrap_or_default(),
        "avatarUrl": user.avatar_url.clone().unwrap_or_default(),
        "mobile": user.mobile.clone().unwrap_or_default(),
        "mobileVerified": user.mobile_verified,
        "status": user.status,
        "lastLoginAt": user.last_login_at.map(|t| t.to_rfc3339()).unwrap_or_default(),
        "createdAt": user.created_at.to_rfc3339(),
        "updatedAt": user.updated_at.to_rfc3339(),
    })
}

pub async fn list_users(
    State(state): State<AppState>,
    _admin: AdminUser,
    Query(q): Query<LimitQuery>,
) -> Result<Json<Value>, AppError> {
    let limit = q.limit.unwrap_or(50);
    let users = crate::db::users::list_users(&state.pool, limit).await?;

    let mut list = Vec::with_capacity(users.len());
    for user in &users {
        let mut obj = serialize_user(user);

        let member_summary = crate::db::credits::get_membership_summary(&state.pool, &user.id)
            .await
            .ok();
        let credit_summary = crate::db::credits::get_credit_summary(&state.pool, &user.id)
            .await
            .ok();

        obj.as_object_mut().unwrap().insert(
            "memberSummary".into(),
            serde_json::to_value(&member_summary).unwrap_or_default(),
        );
        obj.as_object_mut().unwrap().insert(
            "creditSummary".into(),
            serde_json::to_value(&credit_summary).unwrap_or_default(),
        );

        list.push(obj);
    }

    Ok(response::success(json!({ "list": list })))
}

pub async fn get_user(
    State(state): State<AppState>,
    _admin: AdminUser,
    Path(user_id): Path<String>,
) -> Result<Json<Value>, AppError> {
    let user = crate::db::users::find_user_by_id(&state.pool, &user_id)
        .await?
        .ok_or_else(|| AppError::NotFound("用户不存在".into()))?;

    let mut obj = serialize_user(&user);

    let member_summary = crate::db::credits::get_membership_summary(&state.pool, &user.id)
        .await
        .ok();
    let credit_summary = crate::db::credits::get_credit_summary(&state.pool, &user.id)
        .await
        .ok();

    let orders = crate::db::orders::list_orders(&state.pool, &user.id)
        .await
        .unwrap_or_default();
    let entitlements = crate::db::credits::list_user_entitlements(&state.pool, &user.id, "")
        .await
        .unwrap_or_default();
    let (generated_scenes, _total) =
        crate::db::scenes::get_user_scenes(&state.pool, &user.id, 100, 0)
            .await
            .unwrap_or_default();

    obj.as_object_mut().unwrap().insert(
        "memberSummary".into(),
        serde_json::to_value(&member_summary).unwrap_or_default(),
    );
    obj.as_object_mut().unwrap().insert(
        "creditSummary".into(),
        serde_json::to_value(&credit_summary).unwrap_or_default(),
    );
    obj.as_object_mut().unwrap().insert(
        "orders".into(),
        serde_json::to_value(&orders).unwrap_or_default(),
    );
    obj.as_object_mut().unwrap().insert(
        "entitlements".into(),
        serde_json::to_value(&entitlements).unwrap_or_default(),
    );
    obj.as_object_mut().unwrap().insert(
        "generatedScenes".into(),
        serde_json::to_value(&generated_scenes).unwrap_or_default(),
    );

    Ok(response::success(obj))
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct BatchDeleteRequest {
    pub user_ids: Vec<String>,
}

pub async fn batch_delete_users(
    State(state): State<AppState>,
    _admin: AdminUser,
    Json(body): Json<BatchDeleteRequest>,
) -> Result<Json<Value>, AppError> {
    if body.user_ids.is_empty() {
        return Ok(response::success(json!({"count": 0})));
    }
    let count = crate::db::users::batch_delete_users(&state.pool, &body.user_ids).await?;
    Ok(response::success(json!({"count": count})))
}

pub async fn block_user(
    State(state): State<AppState>,
    _admin: AdminUser,
    Path(user_id): Path<String>,
) -> Result<Json<Value>, AppError> {
    crate::db::users::update_user_status(&state.pool, &user_id, "blocked").await?;
    Ok(response::success(json!({})))
}

pub async fn unblock_user(
    State(state): State<AppState>,
    _admin: AdminUser,
    Path(user_id): Path<String>,
) -> Result<Json<Value>, AppError> {
    crate::db::users::update_user_status(&state.pool, &user_id, "active").await?;
    Ok(response::success(json!({})))
}

pub async fn grant_admin(
    State(state): State<AppState>,
    _admin: AdminUser,
    Path(user_id): Path<String>,
) -> Result<Json<Value>, AppError> {
    crate::db::users::update_user_role(&state.pool, &user_id, "admin").await?;
    Ok(response::success(json!({})))
}

pub async fn revoke_admin(
    State(state): State<AppState>,
    _admin: AdminUser,
    Path(user_id): Path<String>,
) -> Result<Json<Value>, AppError> {
    crate::db::users::update_user_role(&state.pool, &user_id, "user").await?;
    Ok(response::success(json!({})))
}

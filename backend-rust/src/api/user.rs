use axum::extract::State;
use axum::Json;
use serde::Deserialize;
use serde_json::{json, Value};
use sqlx::Row;

use crate::db::users;
use crate::error::AppError;
use crate::middleware::auth::AuthUser;
use crate::response::success;
use crate::state::AppState;

pub async fn get_me(
    State(state): State<AppState>,
    auth: AuthUser,
) -> Result<Json<Value>, AppError> {
    let user = users::find_user_by_id(&state.pool, &auth.user_id)
        .await?
        .ok_or_else(|| AppError::NotFound("user not found".into()))?;

    let profile = crate::models::user::UserProfile::from_user(&user, &auth.role);
    Ok(success(json!(profile)))
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct UpdateProfileRequest {
    display_name: Option<String>,
    avatar_url: Option<String>,
}

pub async fn update_profile(
    State(state): State<AppState>,
    auth: AuthUser,
    Json(body): Json<UpdateProfileRequest>,
) -> Result<Json<Value>, AppError> {
    let user = users::update_user_profile(
        &state.pool,
        &auth.user_id,
        body.display_name.as_deref().unwrap_or(""),
        body.avatar_url.as_deref().unwrap_or(""),
    )
    .await?;

    let profile = crate::models::user::UserProfile::from_user(&user, &auth.role);
    Ok(success(json!(profile)))
}

pub async fn get_membership(
    State(state): State<AppState>,
    auth: AuthUser,
) -> Result<Json<Value>, AppError> {
    let row = sqlx::query_as::<_, (String, Option<chrono::DateTime<chrono::Utc>>, Option<chrono::DateTime<chrono::Utc>>)>(
        "SELECT entitlement_code, starts_at, expires_at FROM user_entitlements WHERE user_id = $1 AND entitlement_type = 'membership' AND status = 'active' ORDER BY expires_at DESC LIMIT 1"
    )
        .bind(&auth.user_id)
        .fetch_optional(&state.pool)
        .await?;

    let (tier, starts_at, expires_at) = match row {
        Some(r) => (r.0, r.1.map(|t| t.to_rfc3339()), r.2.map(|t| t.to_rfc3339())),
        None => ("free".to_string(), None, None),
    };

    Ok(success(json!({
        "tier": tier,
        "startsAt": starts_at,
        "expiresAt": expires_at,
    })))
}

pub async fn get_credits(
    State(state): State<AppState>,
    auth: AuthUser,
) -> Result<Json<Value>, AppError> {
    let rows = sqlx::query_as::<_, (String, i32)>(
        "SELECT credit_type, balance FROM user_credit_accounts WHERE user_id = $1"
    )
        .bind(&auth.user_id)
        .fetch_all(&state.pool)
        .await?;

    let credits: serde_json::Map<String, Value> = rows.into_iter()
        .map(|(k, v)| (k, json!(v)))
        .collect();

    Ok(success(json!(credits)))
}

pub async fn get_entitlements(
    State(state): State<AppState>,
    auth: AuthUser,
) -> Result<Json<Value>, AppError> {
    let rows = sqlx::query(
        "SELECT entitlement_code, entitlement_type, status, starts_at, expires_at FROM user_entitlements WHERE user_id = $1 AND status = 'active'"
    )
        .bind(&auth.user_id)
        .fetch_all(&state.pool)
        .await?;

    let codes: Vec<String> = rows.iter()
        .map(|r| r.try_get::<String, _>("entitlement_code").unwrap_or_default())
        .collect();

    Ok(success(json!({"entitlements": codes})))
}

use axum::extract::State;
use axum::Json;
use serde::Deserialize;
use serde_json::{json, Value};

use crate::error::AppError;
use crate::middleware::auth::AdminUser;
use crate::response;
use crate::services::jwt;
use crate::state::AppState;

#[derive(Deserialize)]
pub struct AdminLoginRequest {
    pub username: String,
    pub password: String,
}

pub async fn login(
    State(state): State<AppState>,
    Json(body): Json<AdminLoginRequest>,
) -> Result<Json<Value>, AppError> {
    if !state.config.admin_dashboard_enabled {
        return Err(AppError::Forbidden("admin dashboard disabled".into()));
    }

    if body.username != state.config.admin_dashboard_username
        || body.password != state.config.admin_dashboard_password
    {
        return Err(AppError::Unauthorized("admin credential invalid".into()));
    }

    let (access_token, expires_at) = jwt::create_access_token(
        &state.config.auth_jwt_secret,
        &body.username,
        "admin_console",
        "admin",
        state.config.auth_access_token_ttl_seconds,
    )
    .map_err(AppError::Internal)?;

    let expires_at_str = chrono::DateTime::from_timestamp(expires_at, 0)
        .map(|t| t.to_rfc3339())
        .unwrap_or_default();

    Ok(response::success(json!({
        "accessToken": access_token,
        "accessTokenExpireAt": expires_at_str,
        "admin": {
            "username": body.username,
            "userId": "",
            "role": "super_admin",
            "loginType": "dashboard_password",
        },
    })))
}

pub async fn me(
    _state: State<AppState>,
    admin: AdminUser,
) -> Result<Json<Value>, AppError> {
    Ok(response::success(json!({
        "username": admin.username,
        "userId": admin.user_id,
        "role": admin.role,
        "loginType": admin.login_type,
    })))
}

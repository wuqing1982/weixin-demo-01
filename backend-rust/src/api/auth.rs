use axum::extract::State;
use axum::Json;
use serde::Deserialize;
use serde_json::{json, Value};

use crate::db::users;
use crate::error::AppError;
use crate::middleware::auth::AuthUser;
use crate::models::user::UserProfile;
use crate::response::{success, success_empty};
use crate::services::{jwt, wechat_auth, wechat_session};
use crate::state::AppState;

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct WechatLoginRequest {
    code: String,
    device: Option<DevicePayload>,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct DevicePayload {
    device_id: Option<String>,
    device_type: Option<String>,
    app_version: Option<String>,
}

#[derive(Deserialize)]
pub struct RefreshRequest {
    refresh_token: String,
}

#[derive(Deserialize)]
pub struct LogoutRequest {
    refresh_token: Option<String>,
}

pub async fn wechat_login(
    State(state): State<AppState>,
    Json(body): Json<WechatLoginRequest>,
) -> Result<Json<Value>, AppError> {
    let config = &state.config;

    let (openid, session_key) = if config.auth_wechat_login_mode == "mock" {
        let fake_openid = format!("mock_{}", &body.code);
        (fake_openid, String::new())
    } else {
        let result = wechat_auth::code2session(
            &config.wechat_mp_app_id,
            &config.wechat_mp_app_secret,
            &body.code,
        )
        .await?;
        (result.openid, result.session_key)
    };

    let pool = &state.pool;
    let identity = users::find_identity_by_provider(pool, "wechat", &openid).await?;

    let (user, _identity) = if let Some(identity) = identity {
        let user = users::find_user_by_id(pool, &identity.user_id)
            .await?
            .ok_or_else(|| AppError::Internal("user not found for identity".into()))?;

        if !session_key.is_empty() {
            let secret = config.wechat_session_key_secret.as_deref().unwrap_or(&config.auth_jwt_secret);
            let encrypted = wechat_session::encrypt_session_key(secret, &session_key);
            users::update_identity_session_key(pool, &identity.id, &encrypted).await?;
        }

        users::update_user_last_login(pool, &user.id).await?;
        (user, identity)
    } else {
        let user_id = format!("user_{}", uuid::Uuid::new_v4().simple());
        let identity_id = format!("id_{}", uuid::Uuid::new_v4().simple());

        let user = users::create_user(pool, &user_id).await?;

        let encrypted_sk = if session_key.is_empty() {
            None
        } else {
            let secret = config.wechat_session_key_secret.as_deref().unwrap_or(&config.auth_jwt_secret);
            Some(wechat_session::encrypt_session_key(secret, &session_key))
        };

        let identity = users::create_identity(
            pool,
            &identity_id,
            &user_id,
            "wechat",
            &openid,
            encrypted_sk.as_deref(),
        )
        .await?;

        (user, identity)
    };

    let session_id = uuid::Uuid::new_v4().to_string();
    let (access_token, access_exp) = jwt::create_access_token(
        &config.auth_jwt_secret,
        &user.id,
        &session_id,
        "user",
        config.auth_access_token_ttl_seconds,
    )
    .map_err(AppError::Internal)?;

    let raw_refresh = jwt::generate_refresh_token();
    let refresh_hash = jwt::hash_refresh_token(&raw_refresh);
    let device = body.device.as_ref();
    let refresh_expires = chrono::Utc::now() + chrono::Duration::seconds(config.auth_refresh_token_ttl_seconds);

    users::create_refresh_token(
        pool,
        &format!("rtid_{}", uuid::Uuid::new_v4().simple()),
        &user.id,
        &refresh_hash,
        device.and_then(|d| d.device_type.as_deref()),
        device.and_then(|d| d.device_id.as_deref()),
        device.and_then(|d| d.app_version.as_deref()),
        refresh_expires,
    )
    .await?;

    let profile = UserProfile::from_user(&user, "user");

    Ok(success(json!({
        "accessToken": access_token,
        "refreshToken": raw_refresh,
        "accessTokenExpireAt": access_exp,
        "refreshTokenExpireAt": refresh_expires.to_rfc3339(),
        "me": profile,
    })))
}

pub async fn refresh_token(
    State(state): State<AppState>,
    Json(body): Json<RefreshRequest>,
) -> Result<Json<Value>, AppError> {
    let token_hash = jwt::hash_refresh_token(&body.refresh_token);
    let stored = users::find_refresh_token_by_hash(&state.pool, &token_hash)
        .await?
        .ok_or_else(|| AppError::Unauthorized("invalid refresh token".into()))?;

    users::revoke_refresh_token(&state.pool, &stored.id).await?;

    let session_id = uuid::Uuid::new_v4().to_string();
    let (access_token, access_exp) = jwt::create_access_token(
        &state.config.auth_jwt_secret,
        &stored.user_id,
        &session_id,
        "user",
        state.config.auth_access_token_ttl_seconds,
    )
    .map_err(AppError::Internal)?;

    let raw_refresh = jwt::generate_refresh_token();
    let refresh_hash = jwt::hash_refresh_token(&raw_refresh);
    let refresh_expires = chrono::Utc::now() + chrono::Duration::seconds(state.config.auth_refresh_token_ttl_seconds);

    users::create_refresh_token(
        &state.pool,
        &format!("rtid_{}", uuid::Uuid::new_v4().simple()),
        &stored.user_id,
        &refresh_hash,
        stored.device_type.as_deref(),
        stored.device_id.as_deref(),
        stored.app_version.as_deref(),
        refresh_expires,
    )
    .await?;

    users::update_user_last_login(&state.pool, &stored.user_id).await?;

    let user = users::find_user_by_id(&state.pool, &stored.user_id)
        .await?
        .ok_or_else(|| AppError::Internal("user not found".into()))?;

    let profile = UserProfile::from_user(&user, "user");

    Ok(success(json!({
        "accessToken": access_token,
        "refreshToken": raw_refresh,
        "accessTokenExpireAt": access_exp,
        "refreshTokenExpireAt": refresh_expires.to_rfc3339(),
        "me": profile,
    })))
}

pub async fn logout(
    State(state): State<AppState>,
    auth: AuthUser,
    Json(body): Json<Option<LogoutRequest>>,
) -> Result<Json<Value>, AppError> {
    let _ = auth; // Just need to be authenticated
    if let Some(body) = body {
        if let Some(rt) = &body.refresh_token {
            let hash = jwt::hash_refresh_token(rt);
            if let Some(stored) = users::find_refresh_token_by_hash(&state.pool, &hash).await? {
                users::revoke_refresh_token(&state.pool, &stored.id).await?;
            }
        }
    }
    Ok(success_empty())
}

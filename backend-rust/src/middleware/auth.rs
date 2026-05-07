use axum::extract::FromRequestParts;
use axum::http::request::Parts;

use crate::error::AppError;
use crate::services::jwt;
use crate::state::AppState;

pub struct AuthUser {
    pub user_id: String,
    pub role: String,
    pub session_id: String,
}

impl FromRequestParts<AppState> for AuthUser {
    type Rejection = AppError;

    async fn from_request_parts(parts: &mut Parts, state: &AppState) -> Result<Self, Self::Rejection> {
        let auth_header = parts
            .headers
            .get("Authorization")
            .and_then(|v| v.to_str().ok())
            .unwrap_or("");

        let token = auth_header
            .strip_prefix("Bearer ")
            .ok_or_else(|| AppError::Unauthorized("missing authorization token".into()))?;

        let claims = jwt::decode_access_token(&state.config.auth_jwt_secret, token)
            .map_err(AppError::Unauthorized)?;

        Ok(AuthUser {
            user_id: claims.sub,
            role: claims.role,
            session_id: claims.sid,
        })
    }
}

pub struct OptionalAuthUser(pub Option<AuthUser>);

impl FromRequestParts<AppState> for OptionalAuthUser {
    type Rejection = std::convert::Infallible;

    async fn from_request_parts(parts: &mut Parts, state: &AppState) -> Result<Self, Self::Rejection> {
        let auth_header = parts
            .headers
            .get("Authorization")
            .and_then(|v| v.to_str().ok())
            .unwrap_or("");

        if let Some(token) = auth_header.strip_prefix("Bearer ") {
            if let Ok(claims) = jwt::decode_access_token(&state.config.auth_jwt_secret, token) {
                return Ok(OptionalAuthUser(Some(AuthUser {
                    user_id: claims.sub,
                    role: claims.role,
                    session_id: claims.sid,
                })));
            }
        }

        if state.config.auth_enable_debug_user_header {
            if let Some(debug_uid) = parts.headers.get("X-Debug-User-Id").and_then(|v| v.to_str().ok()) {
                if !debug_uid.is_empty() {
                    return Ok(OptionalAuthUser(Some(AuthUser {
                        user_id: debug_uid.to_string(),
                        role: "user".to_string(),
                        session_id: String::new(),
                    })));
                }
            }
        }

        Ok(OptionalAuthUser(None))
    }
}

/// Admin-only extractor. Validates Bearer JWT with admin role.
pub struct AdminUser {
    pub username: String,
    pub user_id: String,
    pub role: String,
    pub login_type: String,
}

impl FromRequestParts<AppState> for AdminUser {
    type Rejection = AppError;

    async fn from_request_parts(parts: &mut Parts, state: &AppState) -> Result<Self, Self::Rejection> {
        if !state.config.admin_dashboard_enabled {
            return Err(AppError::Forbidden("admin dashboard disabled".into()));
        }

        let auth_header = parts
            .headers
            .get("Authorization")
            .and_then(|v| v.to_str().ok())
            .unwrap_or("");

        let token = auth_header
            .strip_prefix("Bearer ")
            .ok_or_else(|| AppError::Unauthorized("missing authorization token".into()))?;

        let claims = jwt::decode_access_token(&state.config.auth_jwt_secret, token)
            .map_err(AppError::Unauthorized)?;

        // Dashboard password login: sub=username, sid=admin_console
        if claims.sid == "admin_console" {
            if claims.sub == state.config.admin_dashboard_username
                && (claims.role == "admin" || claims.role == "super_admin")
            {
                return Ok(AdminUser {
                    username: claims.sub,
                    user_id: String::new(),
                    role: "super_admin".into(),
                    login_type: "dashboard_password".into(),
                });
            }
            return Err(AppError::Unauthorized("admin unauthorized".into()));
        }

        // WeChat user with admin role in DB
        let user = sqlx::query_as::<_, crate::models::user::User>(
            "SELECT * FROM users WHERE id = $1"
        )
        .bind(&claims.sub)
        .fetch_optional(&state.pool)
        .await
        .map_err(|e| AppError::Internal(e.to_string()))?
        .ok_or_else(|| AppError::Unauthorized("admin unauthorized".into()))?;

        if user.status == "blocked" {
            return Err(AppError::Unauthorized("admin unauthorized".into()));
        }
        if user.role != "admin" && user.role != "super_admin" {
            return Err(AppError::Unauthorized("admin unauthorized".into()));
        }

        Ok(AdminUser {
            username: user.display_name.clone().unwrap_or_else(|| user.id.clone()),
            user_id: user.id,
            role: user.role,
            login_type: "wechat_user".into(),
        })
    }
}

use serde::{Deserialize, Serialize};
use sqlx::FromRow;

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
#[serde(rename_all = "camelCase")]
pub struct User {
    pub id: String,
    pub status: String,
    pub display_name: Option<String>,
    pub avatar_url: Option<String>,
    pub mobile: Option<String>,
    pub mobile_verified: bool,
    pub last_login_at: Option<chrono::DateTime<chrono::Utc>>,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub updated_at: chrono::DateTime<chrono::Utc>,
    pub role: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
#[serde(rename_all = "camelCase")]
pub struct UserIdentity {
    pub id: String,
    pub user_id: String,
    pub provider: String,
    pub provider_uid: String,
    pub union_id: Option<String>,
    pub session_key_encrypted: Option<String>,
    pub meta_json: serde_json::Value,
    pub last_login_at: Option<chrono::DateTime<chrono::Utc>>,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub updated_at: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct RefreshToken {
    pub id: String,
    pub user_id: String,
    pub token_hash: String,
    pub device_type: Option<String>,
    pub device_id: Option<String>,
    pub app_version: Option<String>,
    pub expires_at: chrono::DateTime<chrono::Utc>,
    pub revoked_at: Option<chrono::DateTime<chrono::Utc>>,
    pub created_at: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct UserProfile {
    pub user_id: String,
    pub display_name: String,
    pub avatar_url: String,
    pub role: String,
    pub status: String,
    pub mobile: String,
    pub mobile_verified: bool,
    pub created_at: String,
}

impl UserProfile {
    pub fn from_user(user: &User, _role: &str) -> Self {
        Self {
            user_id: user.id.clone(),
            display_name: user.display_name.clone().unwrap_or_default(),
            avatar_url: user.avatar_url.clone().unwrap_or_default(),
            role: if user.role.is_empty() { _role.to_string() } else { user.role.clone() },
            status: user.status.clone(),
            mobile: user.mobile.clone().unwrap_or_default(),
            mobile_verified: user.mobile_verified,
            created_at: user.created_at.to_rfc3339(),
        }
    }
}

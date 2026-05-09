use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};
use sqlx::FromRow;

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct StorageConfigRow {
    pub id: i32,
    pub backend_id: String,
    pub name: String,
    pub backend_type: String,
    pub enabled: bool,
    pub config: Value,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub updated_at: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct StorageActiveRow {
    pub id: i32,
    pub backend_id: String,
    pub updated_at: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Deserialize)]
pub struct StorageConfigUpdateRequest {
    pub name: Option<String>,
    pub enabled: Option<bool>,
    pub config: Option<Map<String, Value>>,
}

#[derive(Debug, Serialize)]
pub struct ConnectionTestResult {
    pub ok: bool,
    pub message: String,
}

pub const SENSITIVE_KEYS: &[&str] = &["secret_access_key", "secret_key", "secret_id"];
pub const VALID_BACKEND_IDS: &[&str] = &["local", "r2", "cos"];

pub fn required_config_keys(backend_type: &str) -> &'static [&'static str] {
    match backend_type {
        "r2" => &["account_id", "access_key_id", "secret_access_key", "bucket", "public_url"],
        "cos" => &["secret_id", "secret_key", "region", "bucket"],
        "local" => &[],
        _ => &[],
    }
}

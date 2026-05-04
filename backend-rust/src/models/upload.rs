use serde::{Deserialize, Serialize};
use sqlx::FromRow;

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct Upload {
    pub id: String,
    pub owner_id: String,
    pub filename: String,
    pub content_type: String,
    pub file_suffix: String,
    pub width: Option<i32>,
    pub height: Option<i32>,
    pub file_size: i64,
    pub created_at: chrono::DateTime<chrono::Utc>,
}

use serde::{Deserialize, Serialize};
use sqlx::FromRow;

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct Task {
    pub id: String,
    pub owner_id: String,
    pub status: String,
    pub step: String,
    pub progress: i32,
    pub payload: serde_json::Value,
    pub scene_id: Option<String>,
    pub published_scene_id: Option<String>,
    pub error_message: Option<String>,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub updated_at: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SceneGenerateRequest {
    pub upload_id: String,
    pub title: Option<String>,
    pub include_verbs: Option<bool>,
    pub source_lang: Option<String>,
    pub accent: Option<String>,
    pub voice_gender: Option<String>,
    pub voice_name: Option<String>,
    pub auto_publish: Option<bool>,
    pub category_id: Option<String>,
    pub collection_ids: Option<Vec<String>>,
    pub publish_visibility: Option<String>,
}

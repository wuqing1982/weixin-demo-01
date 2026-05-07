use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Rect {
    pub l: f64,
    pub t: f64,
    pub w: f64,
    pub h: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct HotspotItem {
    pub id: String,
    pub word: String,
    #[serde(default)]
    pub ipa: String,
    #[serde(default)]
    pub meaning: String,
    #[serde(default)]
    pub pos: Option<String>,
    #[serde(default)]
    pub sentence: String,
    #[serde(default)]
    pub sentence_translation: String,
    #[serde(default)]
    pub audio_path: String,
    #[serde(default)]
    pub rect: Option<Rect>,
    #[serde(default)]
    pub hidden: bool,
    #[serde(default)]
    pub locked: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct VerbItem {
    pub id: String,
    pub word: String,
    #[serde(default)]
    pub ipa: String,
    #[serde(default)]
    pub meaning: String,
    #[serde(default)]
    pub related_item: String,
    #[serde(default)]
    pub sentence: String,
    #[serde(default)]
    pub sentence_translation: String,
    #[serde(default)]
    pub audio_path: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, sqlx::FromRow)]
#[serde(rename_all = "camelCase")]
pub struct Scene {
    pub scene_id: String,
    pub title: String,
    pub category: String,
    pub visibility: String,
    pub scene_type: String,
    pub cover_path: String,
    pub background_path: String,
    pub items: serde_json::Value,
    pub verbs: serde_json::Value,
    pub meta_json: serde_json::Value,
    pub owner_id: Option<String>,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub updated_at: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize, sqlx::FromRow)]
#[serde(rename_all = "camelCase")]
pub struct SceneCategory {
    pub id: String,
    pub category_code: String,
    pub name: String,
    pub description: String,
    pub status: String,
    pub sort_order: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize, sqlx::FromRow)]
#[serde(rename_all = "camelCase")]
pub struct SceneCollection {
    pub id: String,
    pub collection_code: String,
    pub name: String,
    pub description: String,
    pub status: String,
    pub cover_url: String,
    pub sort_order: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize, sqlx::FromRow)]
#[serde(rename_all = "camelCase")]
pub struct ScenePublication {
    pub source_generated_scene_id: String,
    pub public_scene_id: String,
    pub category_id: Option<String>,
    pub visibility: String,
    pub published_by: Option<String>,
    pub published_at: Option<chrono::DateTime<chrono::Utc>>,
}

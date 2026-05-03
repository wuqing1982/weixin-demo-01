use axum::extract::{Query, State};
use axum::Json;
use serde::Deserialize;
use serde_json::{json, Value};

use crate::error::AppError;
use crate::response::success;
use crate::state::AppState;

#[derive(Deserialize)]
pub struct TtsQuery {
    text: String,
}

pub async fn health() -> Json<Value> {
    success(json!({"status": "ok"}))
}

pub async fn get_config(State(state): State<AppState>) -> Json<Value> {
    success(json!({
        "hotspotEditorEnabled": state.config.hotspot_editor_enabled,
    }))
}

pub async fn tts_proxy(
    State(state): State<AppState>,
    Query(query): Query<TtsQuery>,
) -> Result<axum::response::Response, AppError> {
    if query.text.is_empty() || query.text.len() > 500 {
        return Err(AppError::BadRequest("text must be 1-500 characters".into()));
    }

    let client = reqwest::Client::new();
    let url = format!("{}/api/tts/speak", state.config.core100_tts_url);

    let resp = client
        .post(&url)
        .json(&json!({"text": query.text, "voice": "en-US-JennyNeural"}))
        .timeout(std::time::Duration::from_secs(30))
        .send()
        .await
        .map_err(|e| AppError::ExternalApi(format!("TTS request failed: {e}")))?;

    if !resp.status().is_success() {
        return Err(AppError::ExternalApi("TTS service error".into()));
    }

    let bytes = resp.bytes().await.map_err(|e| AppError::Internal(e.to_string()))?;
    Ok(axum::response::Response::builder()
        .header("content-type", "audio/mpeg")
        .body(axum::body::Body::from(bytes.to_vec()))
        .unwrap())
}

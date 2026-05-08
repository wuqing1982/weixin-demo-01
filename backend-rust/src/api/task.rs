use axum::extract::{Path, State};
use axum::Json;
use serde::Deserialize;
use serde_json::{json, Value};

use crate::db;
use crate::error::AppError;
use crate::middleware::auth::AuthUser;
use crate::response::success;
use crate::services::scene_worker;
use crate::state::AppState;

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

pub async fn create_scene_generate_task(
    State(state): State<AppState>,
    auth: AuthUser,
    Json(body): Json<SceneGenerateRequest>,
) -> Result<Json<Value>, AppError> {
    // Check and deduct scene generation credit
    let balance = db::credits::get_scene_credit_balance(&state.pool, &auth.user_id).await?;
    if balance < 1 {
        return Err(AppError::BadRequest("积分不足，无法生成场景".into()));
    }

    // Validate upload ownership
    let upload = db::uploads::get_upload(&state.pool, &body.upload_id)
        .await?
        .ok_or_else(|| AppError::NotFound("upload not found".into()))?;

    if upload.owner_id != auth.user_id {
        return Err(AppError::Forbidden("not your upload".into()));
    }

    let task_id = format!("task_{}", uuid::Uuid::new_v4());
    let payload = json!({
        "uploadId": body.upload_id,
        "title": body.title.unwrap_or_default(),
        "includeVerbs": body.include_verbs.unwrap_or(true),
        "sourceLang": body.source_lang.unwrap_or_else(|| "en".into()),
        "accent": body.accent.unwrap_or_else(|| "en-US".into()),
        "voiceGender": body.voice_gender.unwrap_or_else(|| "Female".into()),
        "voiceName": body.voice_name.unwrap_or_else(|| "JennyNeural".into()),
        "autoPublish": body.auto_publish.unwrap_or(true),
        "categoryId": body.category_id.unwrap_or_default(),
        "collectionIds": body.collection_ids.unwrap_or_default(),
        "publishVisibility": body.publish_visibility.unwrap_or_else(|| "private".into()),
    });

    let task = db::tasks::create_task(&state.pool, &task_id, &auth.user_id, &payload).await?;

    // Credit deduction moved to worker - only charged on successful generation

    // Spawn background worker
    let worker_state = state.clone();
    let worker_task_id = task_id.clone();
    tokio::spawn(async move {
        scene_worker::process_scene_task(worker_state, worker_task_id).await;
    });

    Ok(success(json!({
        "taskId": task.id,
        "status": task.status,
        "step": task.step,
    })))
}

pub async fn get_task_status(
    State(state): State<AppState>,
    auth: AuthUser,
    Path(task_id): Path<String>,
) -> Result<Json<Value>, AppError> {
    let task = db::tasks::get_task(&state.pool, &task_id)
        .await?
        .ok_or_else(|| AppError::NotFound("task not found".into()))?;

    if task.owner_id != auth.user_id && auth.role != "admin" {
        return Err(AppError::Forbidden("not your task".into()));
    }

    Ok(success(json!({
        "taskId": task.id,
        "status": task.status,
        "step": task.step,
        "progress": task.progress,
        "sceneId": task.scene_id,
        "publishedSceneId": task.published_scene_id,
        "errorMessage": task.error_message,
        "payload": task.payload,
        "createdAt": task.created_at.to_rfc3339(),
        "updatedAt": task.updated_at.to_rfc3339(),
    })))
}

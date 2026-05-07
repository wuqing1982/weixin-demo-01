use axum::extract::{Path, Query, State};
use axum::Json;
use serde::Deserialize;
use serde_json::{json, Value};

use crate::error::AppError;
use crate::middleware::auth::AdminUser;
use crate::response;
use crate::state::AppState;

#[derive(Deserialize)]
pub struct LimitQuery {
    pub limit: Option<i64>,
}

fn serialize_task(
    task: &crate::models::task::Task,
    cover_url: &str,
) -> Value {
    let payload = &task.payload;
    let title = payload
        .get("title")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();
    let upload_id = payload
        .get("uploadId")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();
    let auto_publish = payload
        .get("autoPublish")
        .and_then(|v| v.as_bool())
        .unwrap_or(false);
    let category_id = payload
        .get("categoryId")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();
    let collection_ids: Vec<String> = payload
        .get("collectionIds")
        .and_then(|v| v.as_array())
        .map(|arr| {
            arr.iter()
                .filter_map(|v| v.as_str().map(|s| s.to_string()))
                .collect()
        })
        .unwrap_or_default();
    let publish_visibility = payload
        .get("publishVisibility")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();
    let request_source = payload
        .get("requestSource")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();

    json!({
        "taskId": task.id,
        "ownerId": task.owner_id,
        "uploadId": upload_id,
        "coverUrl": cover_url,
        "title": title,
        "requestSource": request_source,
        "autoPublish": auto_publish,
        "categoryId": category_id,
        "collectionIds": collection_ids,
        "publishVisibility": publish_visibility,
        "status": task.status,
        "step": task.step,
        "progress": task.progress,
        "sceneId": task.scene_id,
        "publishedSceneId": task.published_scene_id,
        "errorMessage": task.error_message,
        "createdAt": task.created_at.to_rfc3339(),
        "updatedAt": task.updated_at.to_rfc3339(),
    })
}

pub async fn list_tasks(
    State(state): State<AppState>,
    _admin: AdminUser,
    Query(q): Query<LimitQuery>,
) -> Result<Json<Value>, AppError> {
    let limit = q.limit.unwrap_or(50);
    let tasks = crate::db::tasks::list_all_tasks(&state.pool, limit).await?;

    let base_url = &state.config.public_base_url;

    let mut list = Vec::with_capacity(tasks.len());
    for task in &tasks {
        let upload_id = task
            .payload
            .get("uploadId")
            .and_then(|v| v.as_str())
            .unwrap_or("");

        let cover_url = if !upload_id.is_empty() {
            crate::db::uploads::get_upload(&state.pool, upload_id)
                .await
                .ok()
                .flatten()
                .map(|upload| {
                    format!(
                        "{}/assets/uploads/{}/source.{}",
                        base_url,
                        upload.id,
                        upload.file_suffix
                    )
                })
                .unwrap_or_default()
        } else {
            String::new()
        };

        list.push(serialize_task(task, &cover_url));
    }

    Ok(response::success(json!({ "list": list })))
}

pub async fn get_task(
    State(state): State<AppState>,
    _admin: AdminUser,
    Path(task_id): Path<String>,
) -> Result<Json<Value>, AppError> {
    let task = crate::db::tasks::get_task(&state.pool, &task_id)
        .await?
        .ok_or_else(|| AppError::NotFound("任务不存在".into()))?;

    let base_url = &state.config.public_base_url;

    let upload_id = task
        .payload
        .get("uploadId")
        .and_then(|v| v.as_str())
        .unwrap_or("");

    let cover_url = if !upload_id.is_empty() {
        crate::db::uploads::get_upload(&state.pool, upload_id)
            .await
            .ok()
            .flatten()
            .map(|upload| {
                format!(
                    "{}/assets/uploads/{}/source.{}",
                    base_url,
                    upload.id,
                    upload.file_suffix
                )
            })
            .unwrap_or_default()
    } else {
        String::new()
    };

    Ok(response::success(serialize_task(&task, &cover_url)))
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct BatchDeleteTasksRequest {
    pub task_ids: Vec<String>,
}

pub async fn batch_delete_tasks(
    State(state): State<AppState>,
    _admin: AdminUser,
    Json(body): Json<BatchDeleteTasksRequest>,
) -> Result<Json<Value>, AppError> {
    if body.task_ids.is_empty() {
        return Ok(response::success(json!({"count": 0})));
    }
    let count = crate::db::tasks::batch_delete_tasks(&state.pool, &body.task_ids).await?;
    Ok(response::success(json!({"count": count})))
}

pub async fn retry_task(
    State(state): State<AppState>,
    _admin: AdminUser,
    Path(task_id): Path<String>,
) -> Result<Json<Value>, AppError> {
    let task = crate::db::tasks::get_task(&state.pool, &task_id)
        .await?
        .ok_or_else(|| AppError::NotFound("任务不存在".into()))?;
    if task.status != "failed" {
        return Err(AppError::BadRequest("只能重试失败的任务".into()));
    }
    crate::db::tasks::retry_task(&state.pool, &task_id).await?;

    // Re-spawn worker for retried task
    let worker_state = state.clone();
    tokio::spawn(async move {
        crate::services::scene_worker::process_scene_task(worker_state, task_id).await;
    });

    Ok(response::success(json!({})))
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SceneGenerateBatchRequest {
    pub items: Vec<GenerateBatchItem>,
    pub include_verbs: Option<bool>,
    pub auto_publish: Option<bool>,
    pub category_id: Option<String>,
    pub collection_ids: Option<Vec<String>>,
    pub publish_visibility: Option<String>,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct GenerateBatchItem {
    pub upload_id: String,
    pub title: Option<String>,
}

pub async fn scene_generate_batch(
    State(state): State<AppState>,
    admin: AdminUser,
    Json(body): Json<SceneGenerateBatchRequest>,
) -> Result<Json<Value>, AppError> {
    if body.items.is_empty() {
        return Ok(response::success(json!({"list": []})));
    }

    let owner_id = if admin.user_id.is_empty() {
        "admin".to_string()
    } else {
        admin.user_id.clone()
    };

    let mut list = Vec::with_capacity(body.items.len());
    for item in &body.items {
        let task_id = format!("task_{}", uuid::Uuid::new_v4());
        let payload = json!({
            "uploadId": item.upload_id,
            "title": item.title.clone().unwrap_or_default(),
            "includeVerbs": body.include_verbs.unwrap_or(true),
            "autoPublish": body.auto_publish.unwrap_or(false),
            "categoryId": body.category_id.clone().unwrap_or_default(),
            "collectionIds": body.collection_ids.clone().unwrap_or_default(),
            "publishVisibility": body.publish_visibility.clone().unwrap_or_else(|| "public".into()),
            "requestSource": "admin_console",
        });

        let task = crate::db::tasks::create_task(&state.pool, &task_id, &owner_id, &payload).await?;

        // Spawn background worker
        let worker_state = state.clone();
        let worker_task_id = task_id.clone();
        tokio::spawn(async move {
            crate::services::scene_worker::process_scene_task(worker_state, worker_task_id).await;
        });

        list.push(json!({
            "taskId": task.id,
            "status": task.status,
            "uploadId": item.upload_id,
        }));
    }

    Ok(response::success(json!({"list": list})))
}

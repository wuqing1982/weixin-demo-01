use axum::extract::{Path, State};
use axum::Json;
use serde_json::{json, Value};
use std::path::PathBuf;

use crate::error::AppError;
use crate::middleware::auth::AdminUser;
use crate::response;
use crate::state::AppState;

pub async fn list_scene_logs(
    State(state): State<AppState>,
    _admin: AdminUser,
) -> Result<Json<Value>, AppError> {
    let logs_dir = get_logs_dir(&state.config.generated_dir);
    let mut entries = Vec::new();

    if let Ok(mut rd) = tokio::fs::read_dir(&logs_dir).await {
        while let Ok(Some(entry)) = rd.next_entry().await {
            let name = entry.file_name().to_string_lossy().to_string();
            if name.starts_with("scene-worker-") && name.ends_with(".log") {
                let meta = entry.metadata().await.ok();
                entries.push(json!({
                    "filename": name,
                    "size": meta.as_ref().map(|m| m.len()).unwrap_or(0),
                    "modified": meta.as_ref().map(|m| m.modified().ok().map(|t| {
                        let dt: chrono::DateTime<chrono::Local> = t.into();
                        dt.to_rfc3339()
                    }).unwrap_or_default()).unwrap_or_default(),
                }));
            }
        }
    }

    entries.sort_by(|a, b| {
        b["filename"].as_str().unwrap_or("").cmp(&a["filename"].as_str().unwrap_or(""))
    });

    Ok(response::success(json!({ "list": entries })))
}

pub async fn get_scene_log(
    State(state): State<AppState>,
    _admin: AdminUser,
    Path(filename): Path<String>,
) -> Result<Json<Value>, AppError> {
    // Prevent path traversal
    if filename.contains('/') || filename.contains('\\') || filename.contains("..") {
        return Err(AppError::BadRequest("invalid filename".into()));
    }
    if !filename.starts_with("scene-worker-") || !filename.ends_with(".log") {
        return Err(AppError::BadRequest("invalid log filename".into()));
    }

    let logs_dir = get_logs_dir(&state.config.generated_dir);
    let path = logs_dir.join(&filename);

    if !path.exists() {
        return Err(AppError::NotFound("log file not found".into()));
    }

    let content = tokio::fs::read_to_string(&path)
        .await
        .map_err(|e| AppError::Internal(e.to_string()))?;

    Ok(response::success(json!({
        "filename": filename,
        "content": content,
    })))
}

fn get_logs_dir(generated_dir: &str) -> PathBuf {
    PathBuf::from(generated_dir)
        .parent()
        .unwrap_or(std::path::Path::new("."))
        .join("logs")
}

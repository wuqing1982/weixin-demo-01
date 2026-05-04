use axum::extract::{Path, State};
use axum::Json;
use serde_json::{json, Value};

use crate::db;
use crate::error::AppError;
use crate::middleware::auth::AuthUser;
use crate::response::success;
use crate::services::video_export;
use crate::state::AppState;

pub async fn export_video(
    State(state): State<AppState>,
    auth: AuthUser,
    Path(scene_id): Path<String>,
) -> Result<Json<Value>, AppError> {
    // Verify scene exists
    let scene = db::scenes::get_scene(&state.pool, &scene_id)
        .await?
        .ok_or_else(|| AppError::NotFound("scene not found".into()))?;

    // Permission check
    let is_admin = auth.role == "admin";
    let is_owner = scene.owner_id.as_deref() == Some(&auth.user_id);
    let is_public = scene.visibility == "public";
    if !is_admin && !is_owner && !is_public {
        return Err(AppError::Forbidden("cannot export this scene".into()));
    }

    let job_id = format!("vexp_{}", uuid::Uuid::new_v4());
    let job =
        db::videos::create_video_export_job(&state.pool, &job_id, &scene_id, &auth.user_id)
            .await?;

    // Spawn background worker
    let worker_state = state.clone();
    let worker_job_id = job_id.clone();
    tokio::spawn(async move {
        video_export::process_video_export(worker_state, worker_job_id).await;
    });

    Ok(success(json!({
        "jobId": job.id,
        "status": job.status,
        "createdAt": job.created_at.to_rfc3339(),
    })))
}

pub async fn get_video_export_status(
    State(state): State<AppState>,
    auth: AuthUser,
    Path(job_id): Path<String>,
) -> Result<Json<Value>, AppError> {
    let job = db::videos::get_video_export_job(&state.pool, &job_id)
        .await?
        .ok_or_else(|| AppError::NotFound("export job not found".into()))?;

    if job.user_id != auth.user_id && auth.role != "admin" {
        return Err(AppError::Forbidden("not your export job".into()));
    }

    let video_url = job.output_path.map(|p| {
        format!("{}/assets/generated/videos/{}", state.config.public_base_url, p.split('/').last().unwrap_or(""))
    });

    Ok(success(json!({
        "jobId": job.id,
        "sceneId": job.scene_id,
        "status": job.status,
        "progress": job.progress,
        "videoUrl": video_url,
        "errorMessage": job.error_message,
        "createdAt": job.created_at.to_rfc3339(),
        "completedAt": job.completed_at.map(|t| t.to_rfc3339()),
    })))
}

pub async fn list_my_video_exports(
    State(state): State<AppState>,
    auth: AuthUser,
) -> Result<Json<Value>, AppError> {
    let jobs = db::videos::list_user_video_exports(&state.pool, &auth.user_id, 20).await?;

    let items: Vec<Value> = jobs
        .iter()
        .map(|job| {
            let video_url = job.output_path.as_ref().map(|p| {
                format!("{}/assets/generated/videos/{}", state.config.public_base_url, p.split('/').last().unwrap_or(""))
            });
            json!({
                "jobId": job.id,
                "sceneId": job.scene_id,
                "status": job.status,
                "progress": job.progress,
                "videoUrl": video_url,
                "createdAt": job.created_at.to_rfc3339(),
            })
        })
        .collect();

    Ok(success(json!({ "items": items })))
}

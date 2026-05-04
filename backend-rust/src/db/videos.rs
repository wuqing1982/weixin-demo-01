use sqlx::PgPool;

use crate::models::video::VideoExportJob;

pub async fn create_video_export_job(
    pool: &PgPool,
    id: &str,
    scene_id: &str,
    user_id: &str,
) -> Result<VideoExportJob, sqlx::Error> {
    sqlx::query_as::<_, VideoExportJob>(
        "INSERT INTO video_export_jobs (id, scene_id, user_id) VALUES ($1, $2, $3) RETURNING *",
    )
    .bind(id)
    .bind(scene_id)
    .bind(user_id)
    .fetch_one(pool)
    .await
}

pub async fn get_video_export_job(
    pool: &PgPool,
    job_id: &str,
) -> Result<Option<VideoExportJob>, sqlx::Error> {
    sqlx::query_as::<_, VideoExportJob>(
        "SELECT * FROM video_export_jobs WHERE id = $1",
    )
    .bind(job_id)
    .fetch_optional(pool)
    .await
}

pub async fn list_user_video_exports(
    pool: &PgPool,
    user_id: &str,
    limit: i64,
) -> Result<Vec<VideoExportJob>, sqlx::Error> {
    sqlx::query_as::<_, VideoExportJob>(
        "SELECT * FROM video_export_jobs WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2",
    )
    .bind(user_id)
    .bind(limit)
    .fetch_all(pool)
    .await
}

pub async fn update_video_export(
    pool: &PgPool,
    job_id: &str,
    status: &str,
    progress: i32,
    output_path: Option<&str>,
    error_message: Option<&str>,
) -> Result<(), sqlx::Error> {
    let completed_at = if status == "completed" || status == "failed" {
        Some(chrono::Utc::now())
    } else {
        None
    };

    sqlx::query(
        "UPDATE video_export_jobs SET status = $1, progress = $2, output_path = COALESCE($3, output_path), \
         error_message = $4, completed_at = COALESCE($5, completed_at) WHERE id = $6",
    )
    .bind(status)
    .bind(progress)
    .bind(output_path)
    .bind(error_message)
    .bind(completed_at)
    .bind(job_id)
    .execute(pool)
    .await?;
    Ok(())
}

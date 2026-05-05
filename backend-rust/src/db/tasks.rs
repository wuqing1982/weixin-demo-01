use sqlx::PgPool;

use crate::models::task::Task;

pub async fn create_task(
    pool: &PgPool,
    id: &str,
    owner_id: &str,
    payload: &serde_json::Value,
) -> Result<Task, sqlx::Error> {
    sqlx::query_as::<_, Task>(
        "INSERT INTO tasks (id, owner_id, status, step, payload) \
         VALUES ($1, $2, 'queued', 'queued', $3) RETURNING *",
    )
    .bind(id)
    .bind(owner_id)
    .bind(payload)
    .fetch_one(pool)
    .await
}

pub async fn get_task(pool: &PgPool, task_id: &str) -> Result<Option<Task>, sqlx::Error> {
    sqlx::query_as::<_, Task>("SELECT * FROM tasks WHERE id = $1")
        .bind(task_id)
        .fetch_optional(pool)
        .await
}

pub async fn list_tasks_by_owner(
    pool: &PgPool,
    owner_id: &str,
    limit: i64,
) -> Result<Vec<Task>, sqlx::Error> {
    sqlx::query_as::<_, Task>(
        "SELECT * FROM tasks WHERE owner_id = $1 ORDER BY created_at DESC LIMIT $2",
    )
    .bind(owner_id)
    .bind(limit)
    .fetch_all(pool)
    .await
}

pub async fn update_task(
    pool: &PgPool,
    task_id: &str,
    status: &str,
    step: &str,
    progress: i32,
    scene_id: Option<&str>,
    error_message: Option<&str>,
) -> Result<(), sqlx::Error> {
    sqlx::query(
        "UPDATE tasks SET status = $1, step = $2, progress = $3, \
         scene_id = COALESCE($4, scene_id), error_message = $5, updated_at = now() \
         WHERE id = $6",
    )
    .bind(status)
    .bind(step)
    .bind(progress)
    .bind(scene_id)
    .bind(error_message)
    .bind(task_id)
    .execute(pool)
    .await?;
    Ok(())
}

pub async fn set_published_scene(
    pool: &PgPool,
    task_id: &str,
    published_scene_id: &str,
) -> Result<(), sqlx::Error> {
    sqlx::query(
        "UPDATE tasks SET published_scene_id = $1, status = 'done', step = 'done', \
         progress = 100, updated_at = now() WHERE id = $2",
    )
    .bind(published_scene_id)
    .bind(task_id)
    .execute(pool)
    .await?;
    Ok(())
}

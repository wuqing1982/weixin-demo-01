use std::path::Path;

use crate::state::AppState;

pub async fn run_upload_cleanup_loop(state: AppState) {
    let mut interval = tokio::time::interval(std::time::Duration::from_secs(600));
    loop {
        interval.tick().await;
        match do_cleanup(&state).await {
            Ok(count) if count > 0 => {
                tracing::info!(deleted = count, "upload cleanup: removed expired uploads");
            }
            Ok(_) => {}
            Err(e) => {
                tracing::error!(error = %e, "upload cleanup error");
            }
        }
    }
}

async fn do_cleanup(state: &AppState) -> Result<usize, String> {
    let storage = crate::storage::resolver::resolve(&state.pool, &state.config)
        .await
        .map_err(|e| format!("storage: {e}"))?;

    // Query DB for expired uploads
    let expired: Vec<(String,)> = sqlx::query_as(
        "SELECT id FROM uploads WHERE created_at < now() - interval '1 second' * $1"
    )
    .bind(state.config.upload_max_age_seconds)
    .fetch_all(&state.pool)
    .await
    .map_err(|e| format!("db query: {e}"))?;

    if expired.is_empty() {
        return Ok(0);
    }

    let mut count = 0;
    for (id,) in &expired {
        // Delete from active storage provider (handles R2 objects)
        let prefix = format!("uploads/{}", id);
        let _ = storage.delete_prefix(&prefix).await;

        // Also try local filesystem delete as fallback
        let dir = Path::new(&state.config.uploads_dir).join(id);
        let _ = tokio::fs::remove_dir_all(&dir).await;

        // Delete from DB
        let _ = sqlx::query("DELETE FROM uploads WHERE id = $1")
            .bind(id)
            .execute(&state.pool)
            .await;

        count += 1;
    }

    Ok(count)
}

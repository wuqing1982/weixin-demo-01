use std::path::Path;

use crate::state::AppState;

pub async fn run_video_cleanup_loop(state: AppState) {
    let mut interval = tokio::time::interval(std::time::Duration::from_secs(300));
    loop {
        interval.tick().await;
        match do_cleanup(&state).await {
            Ok(count) if count > 0 => {
                tracing::info!(deleted = count, "video cleanup: removed expired exports");
            }
            Ok(_) => {}
            Err(e) => {
                tracing::error!(error = %e, "video cleanup error");
            }
        }
    }
}

async fn do_cleanup(state: &AppState) -> Result<usize, String> {
    let job_ids = crate::db::videos::cleanup_expired_video_jobs(&state.pool, state.config.video_max_age_seconds)
        .await
        .map_err(|e| format!("db cleanup: {e}"))?;

    if job_ids.is_empty() {
        return Ok(0);
    }

    let storage = crate::storage::resolver::resolve(&state.pool, &state.config)
        .await
        .map_err(|e| format!("storage: {e}"))?;

    for job_id in &job_ids {
        // Delete from active storage provider
        let key = crate::storage::provider::StorageKey::new(&["generated", "videos", &format!("{job_id}.mp4")]);
        if let Err(e) = storage.delete(&key).await {
            tracing::warn!(%job_id, %e, "video delete from storage failed");
        }

        // Also try local filesystem delete as fallback
        let local_path = Path::new(&state.config.generated_dir).join("videos").join(format!("{job_id}.mp4"));
        let _ = tokio::fs::remove_file(&local_path).await;
    }

    Ok(job_ids.len())
}

use std::path::Path;

use crate::db;
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
    let job_ids = db::videos::cleanup_expired_video_jobs(&state.pool, state.config.video_max_age_seconds)
        .await
        .map_err(|e| format!("db cleanup: {e}"))?;

    if job_ids.is_empty() {
        return Ok(0);
    }

    let video_dir = Path::new(&state.config.generated_dir).join("videos");
    for job_id in &job_ids {
        let path = video_dir.join(format!("{job_id}.mp4"));
        if path.exists() {
            if let Err(e) = tokio::fs::remove_file(&path).await {
                tracing::warn!(path = %path.display(), error = %e, "failed to delete video file");
            }
        }
    }

    Ok(job_ids.len())
}

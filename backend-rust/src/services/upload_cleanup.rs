use std::path::Path;
use std::time::SystemTime;

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
    let max_age = std::time::Duration::from_secs(state.config.upload_max_age_seconds as u64);
    let cutoff = SystemTime::now() - max_age;

    let uploads_dir = Path::new(&state.config.uploads_dir);
    if !uploads_dir.exists() {
        return Ok(0);
    }

    let mut entries = tokio::fs::read_dir(uploads_dir)
        .await
        .map_err(|e| format!("read uploads dir: {e}"))?;

    let mut count = 0;
    while let Some(entry) = entries.next_entry().await.map_err(|e| format!("iterate: {e}"))? {
        let meta = match entry.metadata().await {
            Ok(m) => m,
            Err(_) => continue,
        };
        if !meta.is_dir() {
            continue;
        }

        let modified = match entry.metadata().await {
            Ok(m) => m.modified().unwrap_or(SystemTime::UNIX_EPOCH),
            Err(_) => continue,
        };

        if modified < cutoff {
            if let Err(e) = tokio::fs::remove_dir_all(entry.path()).await {
                tracing::warn!(path = %entry.path().display(), error = %e, "failed to delete upload dir");
            } else {
                count += 1;
            }
        }
    }

    Ok(count)
}

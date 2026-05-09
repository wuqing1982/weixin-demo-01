use sqlx::PgPool;

use crate::config::Config;
use crate::db::storage_config;

use super::local::LocalStorageProvider;
use super::provider::{StorageProvider, StorageResult};
use super::r2::R2StorageProvider;

/// Resolve the active storage provider from DB config.
/// Called per request — single-row PK lookup, sub-millisecond.
pub async fn resolve(
    pool: &PgPool,
    config: &Config,
) -> StorageResult<Box<dyn StorageProvider>> {
    let active = storage_config::get_active(pool)
        .await
        .map_err(|e| super::provider::StorageError::S3(e.to_string()))?;

    match active.backend_id.as_str() {
        "r2" => {
            let row = storage_config::get_config_by_id(pool, "r2")
                .await
                .map_err(|e| super::provider::StorageError::S3(e.to_string()))?
                .ok_or_else(|| {
                    super::provider::StorageError::NotFound("r2 config not found".into())
                })?;
            let provider = R2StorageProvider::from_config(&row.config)?;
            Ok(Box::new(provider))
        }
        _ => {
            let provider = LocalStorageProvider::new(&config.assets_dir, &config.public_base_url);
            Ok(Box::new(provider))
        }
    }
}

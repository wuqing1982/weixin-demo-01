use sqlx::PgPool;
use crate::models::storage_config::{StorageActiveRow, StorageConfigRow};

pub async fn list_all_configs(pool: &PgPool) -> Result<Vec<StorageConfigRow>, sqlx::Error> {
    sqlx::query_as::<_, StorageConfigRow>("SELECT * FROM storage_configs ORDER BY id")
        .fetch_all(pool)
        .await
}

pub async fn get_config_by_id(pool: &PgPool, backend_id: &str) -> Result<Option<StorageConfigRow>, sqlx::Error> {
    sqlx::query_as::<_, StorageConfigRow>("SELECT * FROM storage_configs WHERE backend_id = $1")
        .bind(backend_id)
        .fetch_optional(pool)
        .await
}

pub async fn update_config(
    pool: &PgPool,
    backend_id: &str,
    name: Option<&str>,
    enabled: Option<bool>,
    config: Option<serde_json::Map<String, serde_json::Value>>,
) -> Result<Option<StorageConfigRow>, sqlx::Error> {
    let row = get_config_by_id(pool, backend_id).await?;
    let row = match row {
        Some(r) => r,
        None => return Ok(None),
    };
    let new_name = name.unwrap_or(&row.name);
    let new_enabled = enabled.unwrap_or(row.enabled);
    let mut new_config_map = match row.config.as_object() {
        Some(obj) => obj.clone(),
        None => serde_json::Map::new(),
    };
    if let Some(updates) = config {
        for (key, value) in updates {
            if let serde_json::Value::String(s) = &value {
                if s.starts_with("****") {
                    continue;
                }
            }
            new_config_map.insert(key, value);
        }
    }
    let result = sqlx::query_as::<_, StorageConfigRow>(
        "UPDATE storage_configs SET name = $1, enabled = $2, config = $3, updated_at = now() WHERE backend_id = $4 RETURNING *"
    )
    .bind(new_name)
    .bind(new_enabled)
    .bind(serde_json::Value::Object(new_config_map))
    .bind(backend_id)
    .fetch_optional(pool)
    .await?;
    Ok(result)
}

pub async fn get_active(pool: &PgPool) -> Result<StorageActiveRow, sqlx::Error> {
    sqlx::query_as::<_, StorageActiveRow>("SELECT * FROM storage_active LIMIT 1")
        .fetch_one(pool)
        .await
}

pub async fn set_active(pool: &PgPool, backend_id: &str) -> Result<StorageActiveRow, sqlx::Error> {
    sqlx::query_as::<_, StorageActiveRow>(
        "UPDATE storage_active SET backend_id = $1, updated_at = now() RETURNING *"
    )
    .bind(backend_id)
    .fetch_one(pool)
    .await
}

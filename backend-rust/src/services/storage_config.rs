use serde_json::{Map, Value};
use sqlx::PgPool;
use crate::models::storage_config::SENSITIVE_KEYS;

pub fn mask_config(config: &Value) -> Value {
    match config.as_object() {
        Some(obj) => {
            let masked: Map<String, Value> = obj.iter().map(|(k, v)| {
                if SENSITIVE_KEYS.contains(&k.as_str()) {
                    if let Value::String(s) = v {
                        if s.len() > 4 {
                            (k.clone(), Value::String(format!("****{}", &s[s.len() - 4..])))
                        } else {
                            (k.clone(), v.clone())
                        }
                    } else {
                        (k.clone(), v.clone())
                    }
                } else {
                    (k.clone(), v.clone())
                }
            }).collect();
            Value::Object(masked)
        }
        None => config.clone(),
    }
}

pub fn build_backends_json(rows: &[crate::models::storage_config::StorageConfigRow], should_mask: bool) -> Map<String, Value> {
    let mut backends = Map::new();
    for row in rows {
        let config_value = if should_mask { mask_config(&row.config) } else { row.config.clone() };
        let mut entry = Map::new();
        entry.insert("type".into(), Value::String(row.backend_type.clone()));
        entry.insert("name".into(), Value::String(row.name.clone()));
        entry.insert("enabled".into(), Value::Bool(row.enabled));
        entry.insert("config".into(), config_value);
        backends.insert(row.backend_id.clone(), Value::Object(entry));
    }
    backends
}

pub async fn get_upload_stats(pool: &PgPool) -> (i64, i64, Map<String, Value>) {
    let (file_count, used_bytes): (i64, i64) = sqlx::query_as(
        "SELECT COALESCE(count(*),0), COALESCE(sum(file_size),0) FROM uploads"
    )
    .fetch_one(pool).await.unwrap_or((0, 0));

    let mut by_type = Map::new();
    let rows: Vec<(String, i64)> = match sqlx::query_as(
        "SELECT file_suffix, count(*) FROM uploads GROUP BY file_suffix"
    ).fetch_all(pool).await {
        Ok(r) => r,
        Err(_) => return (file_count, used_bytes, by_type),
    };
    for (suffix, count) in rows {
        let category = match suffix.to_lowercase().as_str() {
            "jpg" | "jpeg" | "png" | "webp" | "gif" => "image",
            "mp3" | "wav" | "ogg" | "m4a" => "audio",
            "mp4" | "webm" => "video",
            _ => "other",
        };
        let current = by_type.get(category).and_then(|v| v.as_i64()).unwrap_or(0);
        by_type.insert(category.to_string(), Value::Number((current + count).into()));
    }
    (file_count, used_bytes, by_type)
}

pub fn get_disk_stats(dir: &str) -> (u64, u64) {
    let path = std::path::Path::new(dir);
    let canonical = match std::fs::canonicalize(path) {
        Ok(c) => c,
        Err(_) => return (0, 0),
    };
    #[cfg(target_os = "linux")]
    {
        let canonical_str = canonical.to_string_lossy();
        let mut stat: libc::statvfs = unsafe { std::mem::zeroed() };
        let c_path = std::ffi::CString::new(canonical_str.as_ref()).unwrap_or_default();
        let ret = unsafe { libc::statvfs(c_path.as_ptr(), &mut stat) };
        if ret == 0 {
            let block_size = stat.f_frsize as u64;
            let total = stat.f_blocks * block_size;
            let available = stat.f_bavail * block_size;
            let used = total.saturating_sub(available);
            return (total, used);
        }
    }
    (0, 0)
}

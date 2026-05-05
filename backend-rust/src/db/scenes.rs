use sqlx::PgPool;

use crate::models::scene::{Scene, SceneCategory, SceneCollection};

pub async fn list_public_scenes(
    pool: &PgPool,
    limit: i64,
    offset: i64,
) -> Result<(Vec<Scene>, i64), sqlx::Error> {
    let count: (i64,) = sqlx::query_as(
        "SELECT count(*) FROM scenes WHERE visibility = 'public' AND scene_type = 'public'"
    )
        .fetch_one(pool)
        .await?;

    let scenes = sqlx::query_as::<_, Scene>(
        "SELECT * FROM scenes WHERE visibility = 'public' AND scene_type = 'public' ORDER BY created_at DESC LIMIT $1 OFFSET $2"
    )
        .bind(limit)
        .bind(offset)
        .fetch_all(pool)
        .await?;

    Ok((scenes, count.0))
}

pub async fn get_scene(pool: &PgPool, scene_id: &str) -> Result<Option<Scene>, sqlx::Error> {
    sqlx::query_as::<_, Scene>("SELECT * FROM scenes WHERE scene_id = $1")
        .bind(scene_id)
        .fetch_optional(pool)
        .await
}

pub async fn get_scenes_by_ids(pool: &PgPool, ids: &[&str]) -> Result<Vec<Scene>, sqlx::Error> {
    if ids.is_empty() {
        return Ok(Vec::new());
    }
    let placeholders: Vec<String> = ids.iter().enumerate().map(|(i, _)| format!("${}", i + 1)).collect();
    let query = format!("SELECT * FROM scenes WHERE scene_id IN ({})", placeholders.join(","));
    let mut q = sqlx::query_as::<_, Scene>(&query);
    for id in ids {
        q = q.bind(id);
    }
    q.fetch_all(pool).await
}

pub async fn get_user_scenes(
    pool: &PgPool,
    user_id: &str,
    limit: i64,
    offset: i64,
) -> Result<(Vec<Scene>, i64), sqlx::Error> {
    let count: (i64,) = sqlx::query_as(
        "SELECT count(*) FROM scenes WHERE owner_id = $1"
    )
        .bind(user_id)
        .fetch_one(pool)
        .await?;

    let scenes = sqlx::query_as::<_, Scene>(
        "SELECT * FROM scenes WHERE owner_id = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3"
    )
        .bind(user_id)
        .bind(limit)
        .bind(offset)
        .fetch_all(pool)
        .await?;

    Ok((scenes, count.0))
}

pub async fn list_categories(pool: &PgPool) -> Result<Vec<SceneCategory>, sqlx::Error> {
    sqlx::query_as::<_, SceneCategory>(
        "SELECT * FROM scene_categories WHERE status = 'active' ORDER BY sort_order, name"
    )
        .fetch_all(pool)
        .await
}

pub async fn list_collections(pool: &PgPool) -> Result<Vec<SceneCollection>, sqlx::Error> {
    sqlx::query_as::<_, SceneCollection>(
        "SELECT * FROM scene_collections WHERE status = 'active' ORDER BY sort_order, name"
    )
        .fetch_all(pool)
        .await
}

pub async fn save_hotspots(
    pool: &PgPool,
    scene_id: &str,
    items: &[serde_json::Value],
) -> Result<(), sqlx::Error> {
    let items_json = serde_json::to_value(items).unwrap_or_default();
    sqlx::query("UPDATE scenes SET items = $1, updated_at = now() WHERE scene_id = $2")
        .bind(items_json)
        .bind(scene_id)
        .execute(pool)
        .await?;
    Ok(())
}

pub async fn upsert_scene(
    pool: &PgPool,
    scene: &serde_json::Value,
) -> Result<(), sqlx::Error> {
    sqlx::query(
        "INSERT INTO scenes (scene_id, title, category, visibility, scene_type, cover_path, background_path, items, verbs, meta_json, owner_id) \
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11) \
         ON CONFLICT (scene_id) DO UPDATE SET \
         title = $2, category = $3, items = $8, verbs = $9, meta_json = $10, updated_at = now()"
    )
    .bind(scene["sceneId"].as_str().unwrap_or(""))
    .bind(scene["title"].as_str().unwrap_or(""))
    .bind(scene["category"].as_str().unwrap_or(""))
    .bind(scene["visibility"].as_str().unwrap_or("private"))
    .bind(scene["sceneType"].as_str().unwrap_or("private"))
    .bind(scene["coverPath"].as_str().unwrap_or(""))
    .bind(scene["backgroundPath"].as_str().unwrap_or(""))
    .bind(&scene["items"])
    .bind(&scene["verbs"])
    .bind(&scene["metaJson"])
    .bind(scene["metaJson"]["ownerId"].as_str())
    .execute(pool)
    .await?;
    Ok(())
}

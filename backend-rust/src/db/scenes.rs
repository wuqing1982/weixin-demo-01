use sqlx::PgPool;

use crate::models::scene::{Scene, SceneCategory, SceneCollection};

pub async fn list_public_scenes(
    pool: &PgPool,
    limit: i64,
    offset: i64,
    category_id: Option<&str>,
    collection_id: Option<&str>,
) -> Result<(Vec<Scene>, i64), sqlx::Error> {
    let mut conditions = vec![
        "scenes.visibility = 'public'".to_string(),
        "scenes.scene_type = 'public'".to_string(),
    ];
    let mut join = String::new();
    let mut next_param = 1u32;

    if let Some(_) = category_id {
        conditions.push(format!("(scenes.meta_json->>'categoryId') = ${}", next_param));
        next_param += 1;
    }

    if collection_id.is_some() {
        join = "JOIN scene_publication_collections spc ON scenes.scene_id = spc.public_scene_id".to_string();
        conditions.push(format!("spc.collection_id = ${}", next_param));
        next_param += 1;
    }

    let where_sql = conditions.join(" AND ");
    let limit_param = next_param;
    let offset_param = next_param + 1;

    let count_sql = format!("SELECT count(*) FROM scenes {} WHERE {}", join, where_sql);
    let query_sql = format!(
        "SELECT scenes.* FROM scenes {} WHERE {} ORDER BY scenes.created_at DESC LIMIT ${} OFFSET ${}",
        join, where_sql, limit_param, offset_param
    );

    let mut count_q = sqlx::query_as::<_, (i64,)>(&count_sql);
    let mut query_q = sqlx::query_as::<_, Scene>(&query_sql);

    if let Some(cid) = category_id {
        count_q = count_q.bind(cid);
        query_q = query_q.bind(cid);
    }
    if let Some(col_id) = collection_id {
        count_q = count_q.bind(col_id);
        query_q = query_q.bind(col_id);
    }

    count_q = count_q.bind(limit).bind(offset);
    query_q = query_q.bind(limit).bind(offset);

    let count = count_q.fetch_one(pool).await?;
    let scenes = query_q.fetch_all(pool).await?;

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

pub async fn list_all_categories(pool: &PgPool) -> Result<Vec<SceneCategory>, sqlx::Error> {
    sqlx::query_as::<_, SceneCategory>(
        "SELECT * FROM scene_categories ORDER BY sort_order, name"
    )
    .fetch_all(pool)
    .await
}

pub async fn list_all_collections(pool: &PgPool) -> Result<Vec<SceneCollection>, sqlx::Error> {
    sqlx::query_as::<_, SceneCollection>(
        "SELECT * FROM scene_collections ORDER BY sort_order, name"
    )
    .fetch_all(pool)
    .await
}

use crate::models::scene::ScenePublication;

pub async fn list_all_public_scenes(pool: &PgPool) -> Result<Vec<Scene>, sqlx::Error> {
    sqlx::query_as::<_, Scene>(
        "SELECT * FROM scenes WHERE scene_type = 'public' ORDER BY created_at DESC"
    )
    .fetch_all(pool)
    .await
}

pub async fn list_all_generated_scenes(pool: &PgPool, limit: i64) -> Result<Vec<Scene>, sqlx::Error> {
    sqlx::query_as::<_, Scene>(
        "SELECT * FROM scenes WHERE scene_type != 'public' ORDER BY created_at DESC LIMIT $1"
    )
    .bind(limit)
    .fetch_all(pool)
    .await
}

pub async fn get_publication_by_public_id(pool: &PgPool, public_scene_id: &str) -> Result<Option<ScenePublication>, sqlx::Error> {
    sqlx::query_as::<_, ScenePublication>(
        "SELECT * FROM scene_publications WHERE public_scene_id = $1"
    )
    .bind(public_scene_id)
    .fetch_optional(pool)
    .await
}

pub async fn get_publication_by_source_id(pool: &PgPool, source_scene_id: &str) -> Result<Option<ScenePublication>, sqlx::Error> {
    sqlx::query_as::<_, ScenePublication>(
        "SELECT * FROM scene_publications WHERE source_generated_scene_id = $1"
    )
    .bind(source_scene_id)
    .fetch_optional(pool)
    .await
}

pub async fn list_publication_collections(pool: &PgPool, public_scene_id: &str) -> Result<Vec<String>, sqlx::Error> {
    let rows: Vec<(String,)> = sqlx::query_as(
        "SELECT collection_id FROM scene_publication_collections WHERE public_scene_id = $1 ORDER BY sort_order"
    )
    .bind(public_scene_id)
    .fetch_all(pool)
    .await?;
    Ok(rows.into_iter().map(|r| r.0).collect())
}

pub async fn batch_delete_scenes(pool: &PgPool, scene_ids: &[String]) -> Result<u64, sqlx::Error> {
    let mut tx = pool.begin().await?;
    for sid in scene_ids {
        sqlx::query("DELETE FROM scene_publication_collections WHERE public_scene_id = $1")
            .bind(sid).execute(&mut *tx).await?;
        sqlx::query("DELETE FROM scene_publications WHERE public_scene_id = $1 OR source_generated_scene_id = $1")
            .bind(sid).execute(&mut *tx).await?;
        sqlx::query("DELETE FROM scenes WHERE scene_id = $1")
            .bind(sid).execute(&mut *tx).await?;
    }
    tx.commit().await?;
    Ok(scene_ids.len() as u64)
}

pub async fn batch_update_scene_visibility(pool: &PgPool, scene_ids: &[String], visibility: &str) -> Result<u64, sqlx::Error> {
    let mut tx = pool.begin().await?;
    let mut count = 0u64;
    for sid in scene_ids {
        let result = sqlx::query("UPDATE scenes SET visibility = $1, updated_at = now() WHERE scene_id = $2")
            .bind(visibility)
            .bind(sid)
            .execute(&mut *tx)
            .await?;
        count += result.rows_affected();
    }
    tx.commit().await?;
    Ok(count)
}

pub async fn batch_update_scene_meta_bool(pool: &PgPool, scene_ids: &[String], key: &str, value: bool) -> Result<u64, sqlx::Error> {
    let mut tx = pool.begin().await?;
    let mut count = 0u64;
    for sid in scene_ids {
        let result = sqlx::query("UPDATE scenes SET meta_json = jsonb_set(COALESCE(meta_json, '{}'), $1, $2), updated_at = now() WHERE scene_id = $3")
            .bind(format!("{{{key}}}"))
            .bind(serde_json::Value::Bool(value))
            .bind(sid)
            .execute(&mut *tx)
            .await?;
        count += result.rows_affected();
    }
    tx.commit().await?;
    Ok(count)
}

pub async fn batch_update_scene_category(pool: &PgPool, scene_ids: &[String], category_id: &str) -> Result<u64, sqlx::Error> {
    let mut tx = pool.begin().await?;
    let mut count = 0u64;
    for sid in scene_ids {
        let result = sqlx::query("UPDATE scenes SET meta_json = jsonb_set(COALESCE(meta_json, '{}'), '{categoryId}', $1), updated_at = now() WHERE scene_id = $2")
            .bind(serde_json::Value::String(category_id.to_string()))
            .bind(sid)
            .execute(&mut *tx)
            .await?;
        count += result.rows_affected();
    }
    tx.commit().await?;
    Ok(count)
}

pub async fn upsert_category(
    pool: &PgPool,
    id: &str,
    category_code: &str,
    name: &str,
    description: &str,
    status: &str,
    sort_order: i32,
) -> Result<(), sqlx::Error> {
    sqlx::query(
        "INSERT INTO scene_categories (id, category_code, name, description, status, sort_order) \
         VALUES ($1, $2, $3, $4, $5, $6) \
         ON CONFLICT (id) DO UPDATE SET category_code = $2, name = $3, description = $4, status = $5, sort_order = $6"
    )
    .bind(id).bind(category_code).bind(name).bind(description).bind(status).bind(sort_order)
    .execute(pool).await?;
    Ok(())
}

pub async fn delete_category(pool: &PgPool, id: &str) -> Result<(), sqlx::Error> {
    sqlx::query("DELETE FROM scene_categories WHERE id = $1")
        .bind(id).execute(pool).await?;
    Ok(())
}

pub async fn upsert_collection(
    pool: &PgPool,
    id: &str,
    collection_code: &str,
    name: &str,
    description: &str,
    status: &str,
    cover_url: &str,
    sort_order: i32,
) -> Result<(), sqlx::Error> {
    sqlx::query(
        "INSERT INTO scene_collections (id, collection_code, name, description, status, cover_url, sort_order) \
         VALUES ($1, $2, $3, $4, $5, $6, $7) \
         ON CONFLICT (id) DO UPDATE SET collection_code = $2, name = $3, description = $4, status = $5, cover_url = $6, sort_order = $7"
    )
    .bind(id).bind(collection_code).bind(name).bind(description).bind(status).bind(cover_url).bind(sort_order)
    .execute(pool).await?;
    Ok(())
}

pub async fn delete_collection(pool: &PgPool, id: &str) -> Result<(), sqlx::Error> {
    sqlx::query("DELETE FROM scene_publication_collections WHERE collection_id = $1")
        .bind(id).execute(pool).await?;
    sqlx::query("DELETE FROM scene_collections WHERE id = $1")
        .bind(id).execute(pool).await?;
    Ok(())
}

pub async fn upsert_public_scene(pool: &PgPool, scene: &serde_json::Value) -> Result<(), sqlx::Error> {
    let meta = &scene["meta"];
    let category_id = meta.get("categoryId").and_then(|v| v.as_str()).unwrap_or("");
    let collection_ids: Vec<String> = meta.get("collectionIds")
        .and_then(|v| v.as_array())
        .map(|arr| arr.iter().filter_map(|v| v.as_str().map(|s| s.to_string())).collect())
        .unwrap_or_default();

    sqlx::query(
        "INSERT INTO scenes (scene_id, title, category, visibility, scene_type, cover_path, background_path, items, verbs, meta_json, owner_id) \
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11) \
         ON CONFLICT (scene_id) DO UPDATE SET \
         title = $2, category = $3, visibility = $4, scene_type = $5, cover_path = $6, background_path = $7, \
         items = $8, verbs = $9, meta_json = $10, updated_at = now()"
    )
    .bind(scene["sceneId"].as_str().unwrap_or(""))
    .bind(scene["title"].as_str().unwrap_or(""))
    .bind(scene["category"].as_str().unwrap_or(""))
    .bind(scene["visibility"].as_str().unwrap_or("private"))
    .bind(scene["sceneType"].as_str().unwrap_or("public"))
    .bind(scene["coverPath"].as_str().unwrap_or(""))
    .bind(scene["backgroundPath"].as_str().unwrap_or(""))
    .bind(&scene["items"])
    .bind(&scene["verbs"])
    .bind(meta)
    .bind(scene["metaJson"]["ownerId"].as_str())
    .execute(pool).await?;

    // Update publication category if publication exists
    let scene_id = scene["sceneId"].as_str().unwrap_or("");
    if get_publication_by_public_id(pool, scene_id).await?.is_some() {
        sqlx::query("UPDATE scene_publications SET category_id = $1, visibility = $2 WHERE public_scene_id = $3")
            .bind(if category_id.is_empty() { None } else { Some(category_id) })
            .bind(scene["visibility"].as_str().unwrap_or("public"))
            .bind(scene_id)
            .execute(pool).await?;

        // Update publication collections
        sqlx::query("DELETE FROM scene_publication_collections WHERE public_scene_id = $1")
            .bind(scene_id).execute(pool).await?;
        for (i, col_id) in collection_ids.iter().enumerate() {
            sqlx::query("INSERT INTO scene_publication_collections (public_scene_id, collection_id, sort_order) VALUES ($1, $2, $3)")
                .bind(scene_id).bind(col_id).bind(i as i32)
                .execute(pool).await?;
        }
    }

    Ok(())
}

pub async fn publish_generated_scene(
    pool: &PgPool,
    source_scene_id: &str,
    public_scene_id: &str,
    category_id: &str,
    visibility: &str,
    published_by: &str,
    collection_ids: &[String],
) -> Result<(), sqlx::Error> {
    sqlx::query(
        "INSERT INTO scene_publications (source_generated_scene_id, public_scene_id, category_id, visibility, published_by) \
         VALUES ($1, $2, $3, $4, $5) \
         ON CONFLICT (source_generated_scene_id) DO UPDATE SET public_scene_id = $2, category_id = $3, visibility = $4, published_by = $5, published_at = now()"
    )
    .bind(source_scene_id).bind(public_scene_id).bind(if category_id.is_empty() { None } else { Some(category_id) }).bind(visibility).bind(published_by)
    .execute(pool).await?;

    sqlx::query("DELETE FROM scene_publication_collections WHERE public_scene_id = $1")
        .bind(public_scene_id).execute(pool).await?;
    for (i, col_id) in collection_ids.iter().enumerate() {
        sqlx::query("INSERT INTO scene_publication_collections (public_scene_id, collection_id, sort_order) VALUES ($1, $2, $3)")
            .bind(public_scene_id).bind(col_id).bind(i as i32)
            .execute(pool).await?;
    }
    Ok(())
}

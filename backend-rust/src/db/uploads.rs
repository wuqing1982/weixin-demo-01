use sqlx::PgPool;

use crate::models::upload::Upload;

pub async fn create_upload(
    pool: &PgPool,
    id: &str,
    owner_id: &str,
    filename: &str,
    content_type: &str,
    file_suffix: &str,
    width: Option<i32>,
    height: Option<i32>,
    file_size: i64,
) -> Result<Upload, sqlx::Error> {
    sqlx::query_as::<_, Upload>(
        "INSERT INTO uploads (id, owner_id, filename, content_type, file_suffix, width, height, file_size) \
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8) RETURNING *",
    )
    .bind(id)
    .bind(owner_id)
    .bind(filename)
    .bind(content_type)
    .bind(file_suffix)
    .bind(width)
    .bind(height)
    .bind(file_size)
    .fetch_one(pool)
    .await
}

pub async fn get_upload(pool: &PgPool, upload_id: &str) -> Result<Option<Upload>, sqlx::Error> {
    sqlx::query_as::<_, Upload>("SELECT * FROM uploads WHERE id = $1")
        .bind(upload_id)
        .fetch_optional(pool)
        .await
}

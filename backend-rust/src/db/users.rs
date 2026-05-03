use sqlx::PgPool;

use crate::models::user::{RefreshToken, User, UserIdentity};

pub async fn find_user_by_id(pool: &PgPool, user_id: &str) -> Result<Option<User>, sqlx::Error> {
    sqlx::query_as::<_, User>("SELECT * FROM users WHERE id = $1")
        .bind(user_id)
        .fetch_optional(pool)
        .await
}

pub async fn find_identity_by_provider(pool: &PgPool, provider: &str, provider_uid: &str) -> Result<Option<UserIdentity>, sqlx::Error> {
    sqlx::query_as::<_, UserIdentity>(
        "SELECT * FROM user_identities WHERE provider = $1 AND provider_uid = $2"
    )
        .bind(provider)
        .bind(provider_uid)
        .fetch_optional(pool)
        .await
}

pub async fn create_user(pool: &PgPool, user_id: &str) -> Result<User, sqlx::Error> {
    sqlx::query_as::<_, User>(
        "INSERT INTO users (id) VALUES ($1) RETURNING *"
    )
        .bind(user_id)
        .fetch_one(pool)
        .await
}

pub async fn create_identity(
    pool: &PgPool,
    id: &str,
    user_id: &str,
    provider: &str,
    provider_uid: &str,
    session_key_encrypted: Option<&str>,
) -> Result<UserIdentity, sqlx::Error> {
    sqlx::query_as::<_, UserIdentity>(
        "INSERT INTO user_identities (id, user_id, provider, provider_uid, session_key_encrypted) VALUES ($1, $2, $3, $4, $5) RETURNING *"
    )
        .bind(id)
        .bind(user_id)
        .bind(provider)
        .bind(provider_uid)
        .bind(session_key_encrypted)
        .fetch_one(pool)
        .await
}

pub async fn update_identity_session_key(
    pool: &PgPool,
    identity_id: &str,
    session_key_encrypted: &str,
) -> Result<(), sqlx::Error> {
    sqlx::query("UPDATE user_identities SET session_key_encrypted = $1, updated_at = now() WHERE id = $2")
        .bind(session_key_encrypted)
        .bind(identity_id)
        .execute(pool)
        .await?;
    Ok(())
}

pub async fn update_user_last_login(pool: &PgPool, user_id: &str) -> Result<(), sqlx::Error> {
    sqlx::query("UPDATE users SET last_login_at = now(), updated_at = now() WHERE id = $1")
        .bind(user_id)
        .execute(pool)
        .await?;
    Ok(())
}

pub async fn create_refresh_token(
    pool: &PgPool,
    id: &str,
    user_id: &str,
    token_hash: &str,
    device_type: Option<&str>,
    device_id: Option<&str>,
    app_version: Option<&str>,
    expires_at: chrono::DateTime<chrono::Utc>,
) -> Result<RefreshToken, sqlx::Error> {
    sqlx::query_as::<_, RefreshToken>(
        "INSERT INTO auth_refresh_tokens (id, user_id, token_hash, device_type, device_id, app_version, expires_at) VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING *"
    )
        .bind(id)
        .bind(user_id)
        .bind(token_hash)
        .bind(device_type)
        .bind(device_id)
        .bind(app_version)
        .bind(expires_at)
        .fetch_one(pool)
        .await
}

pub async fn find_refresh_token_by_hash(pool: &PgPool, token_hash: &str) -> Result<Option<RefreshToken>, sqlx::Error> {
    sqlx::query_as::<_, RefreshToken>(
        "SELECT * FROM auth_refresh_tokens WHERE token_hash = $1 AND revoked_at IS NULL AND expires_at > now()"
    )
        .bind(token_hash)
        .fetch_optional(pool)
        .await
}

pub async fn revoke_refresh_token(pool: &PgPool, token_id: &str) -> Result<(), sqlx::Error> {
    sqlx::query("UPDATE auth_refresh_tokens SET revoked_at = now() WHERE id = $1")
        .bind(token_id)
        .execute(pool)
        .await?;
    Ok(())
}

pub async fn revoke_all_user_tokens(pool: &PgPool, user_id: &str) -> Result<(), sqlx::Error> {
    sqlx::query("UPDATE auth_refresh_tokens SET revoked_at = now() WHERE user_id = $1 AND revoked_at IS NULL")
        .bind(user_id)
        .execute(pool)
        .await?;
    Ok(())
}

pub async fn update_user_profile(
    pool: &PgPool,
    user_id: &str,
    display_name: &str,
    avatar_url: &str,
) -> Result<User, sqlx::Error> {
    sqlx::query_as::<_, User>(
        "UPDATE users SET display_name = $1, avatar_url = $2, updated_at = now() WHERE id = $3 RETURNING *"
    )
        .bind(display_name)
        .bind(avatar_url)
        .bind(user_id)
        .fetch_one(pool)
        .await
}

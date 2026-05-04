# Rust 后端重写 — 阶段 1：骨架 + 核心 API

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让微信小程序能登录、浏览场景、播放 TTS，后端从 Python 切换到 Rust 无感切换。

**Architecture:** Axum 0.8 + SQLx (PostgreSQL) + Tokio 单进程。JWT 手写 HS256 与 Python 端格式兼容。API 响应格式 `{"code":0,"data":...,"message":"ok"}` 与 Python 端完全一致。

**Tech Stack:** Rust (edition 2024), Axum 0.8, Tokio 1, SQLx 0.8 (postgres), Reqwest 0.12, serde/serde_json, hmac/sha2/base64, tower-http, tracing, dotenvy

**Spec:** `docs/superpowers/specs/2026-05-03-rust-backend-rewrite-design.md`

**Reference code:** `/www/wwwroot/e.cps.vin/english-loong-back/demo/backend/src/` — 可复用 hotspot models, zhipu AI, tts, audio_naming, error 模块

---

## File Map

| File | Responsibility |
|------|---------------|
| `backend-rust/Cargo.toml` | 依赖声明 |
| `backend-rust/.env` | 环境变量（复用 Python 端格式） |
| `backend-rust/.gitignore` | 忽略 target/, .env |
| `src/main.rs` | 入口：加载配置、初始化 DB pool、注册路由、启动 server |
| `src/config.rs` | 从 .env / 环境变量读取 Config struct |
| `src/error.rs` | AppError 枚举 → 统一 JSON 响应 |
| `src/state.rs` | AppState（PgPool, Arc<Config>），共享状态 |
| `src/response.rs` | `success()` / `fail()` 响应辅助函数 |
| `src/models/mod.rs` | 模块声明 |
| `src/models/user.rs` | User, UserIdentity, RefreshToken 结构体 |
| `src/models/scene.rs` | Scene, HotspotItem, VerbItem, Rect, SceneCategory, SceneCollection |
| `src/services/mod.rs` | 模块声明 |
| `src/services/jwt.rs` | JWT HS256 签发/验证（兼容 Python 格式） |
| `src/services/wechat_session.rs` | Session key XOR 流加解密 |
| `src/services/wechat_auth.rs` | 微信 code2session HTTP 调用 |
| `src/db/mod.rs` | 模块声明 |
| `src/db/users.rs` | 用户相关 SQL 查询 |
| `src/db/scenes.rs` | 场景相关 SQL 查询 |
| `src/middleware/mod.rs` | 模块声明 |
| `src/middleware/auth.rs` | JWT 认证中间件，提取当前用户 |
| `src/api/mod.rs` | 路由汇总 |
| `src/api/health.rs` | GET /api/health, GET /api/tts, GET /api/config |
| `src/api/auth.rs` | POST /api/auth/wechat/login, POST /api/auth/refresh, POST /api/auth/logout |
| `src/api/user.rs` | GET /api/me, PUT /api/me/profile, GET /api/me/membership, GET /api/me/credits, GET /api/me/entitlements |
| `src/api/scene.rs` | GET /api/scenes, GET /api/scenes/{id}, GET /api/scene-categories, GET /api/scene-collections |

---

## Chunk 1: Project Skeleton

### Task 1: Create Cargo.toml and project skeleton

**Files:**
- Create: `backend-rust/Cargo.toml`
- Create: `backend-rust/.gitignore`
- Create: `backend-rust/src/main.rs` (minimal hello world)

- [ ] **Step 1: Create project directory and Cargo.toml**

```bash
mkdir -p /www/wwwroot/e.cps.vin/weixin-demo-01/backend-rust/src
```

Create `backend-rust/Cargo.toml`:

```toml
[package]
name = "backend-rust"
version = "0.1.0"
edition = "2024"

[dependencies]
axum = { version = "0.8", features = ["multipart"] }
tokio = { version = "1", features = ["full"] }
sqlx = { version = "0.8", features = ["runtime-tokio", "tls-rustls", "postgres", "chrono", "uuid"] }
reqwest = { version = "0.12", features = ["json"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
hmac = "0.12"
sha2 = "0.10"
base64 = "0.22"
uuid = { version = "1", features = ["v4", "serde"] }
chrono = { version = "0.4", features = ["serde"] }
tower-http = { version = "0.6", features = ["cors", "fs"] }
tracing = "0.1"
tracing-subscriber = "0.3"
dotenvy = "0.15"
hex = "0.4"
```

- [ ] **Step 2: Create .gitignore**

Create `backend-rust/.gitignore`:

```
/target
.env
*.env
```

- [ ] **Step 3: Create minimal main.rs**

Create `backend-rust/src/main.rs`:

```rust
fn main() {
    println!("backend-rust starting...");
}
```

- [ ] **Step 4: Verify it compiles**

Run: `cd /www/wwwroot/e.cps.vin/weixin-demo-01/backend-rust && cargo build`
Expected: Compiles successfully.

- [ ] **Step 5: Commit**

```bash
cd /www/wwwroot/e.cps.vin/weixin-demo-01
git add backend-rust/Cargo.toml backend-rust/.gitignore backend-rust/src/main.rs
git commit -m "feat: initialize backend-rust project skeleton"
```

---

### Task 2: Config, Error, Response modules

**Files:**
- Create: `backend-rust/src/config.rs`
- Create: `backend-rust/src/error.rs`
- Create: `backend-rust/src/response.rs`
- Create: `backend-rust/src/state.rs`
- Modify: `backend-rust/src/main.rs`

- [ ] **Step 1: Write config.rs**

Create `backend-rust/src/config.rs`. Read all env vars matching Python backend's `settings.py`:

```rust
use std::env;

pub struct Config {
    pub database_url: String,
    pub database_schema: String,
    pub auth_jwt_secret: String,
    pub auth_access_token_ttl_seconds: i64,
    pub auth_refresh_token_ttl_seconds: i64,
    pub auth_wechat_login_mode: String,
    pub auth_enable_debug_user_header: bool,
    pub wechat_mp_app_id: String,
    pub wechat_mp_app_secret: String,
    pub wechat_session_key_secret: Option<String>,
    pub default_mock_user_id: String,
    pub public_base_url: String,
    pub cors_allowed_origins: Vec<String>,
    pub assets_dir: String,
    pub core100_tts_url: String,
    pub scene_page_size: i64,
    pub hotspot_editor_enabled: bool,
    pub server_port: u16,
}

fn env_or(key: &str, default: &str) -> String {
    env::var(key).unwrap_or_else(|_| default.to_string())
}

fn env_bool(key: &str, default: bool) -> bool {
    env::var(key)
        .map(|v| matches!(v.to_lowercase().as_str(), "1" | "true" | "yes" | "on"))
        .unwrap_or(default)
}

fn env_int(key: &str, default: i64) -> i64 {
    env::var(key).ok().and_then(|v| v.parse().ok()).unwrap_or(default)
}

impl Config {
    pub fn load() -> Self {
        // Try loading .env from backend-rust/ directory and parent backend/ directory
        let backend_env = env::current_dir().unwrap().join(".env");
        let _ = dotenvy::from_path(&backend_env);

        Self {
            database_url: env_or("DATABASE_URL", "postgresql://localhost:5432/weixin_saas"),
            database_schema: env_or("DATABASE_SCHEMA", "public"),
            auth_jwt_secret: env_or("AUTH_JWT_SECRET", "dev-jwt-secret-change-me"),
            auth_access_token_ttl_seconds: env_int("AUTH_ACCESS_TOKEN_TTL_SECONDS", 7200),
            auth_refresh_token_ttl_seconds: env_int("AUTH_REFRESH_TOKEN_TTL_SECONDS", 2592000),
            auth_wechat_login_mode: env_or("AUTH_WECHAT_LOGIN_MODE", "mock"),
            auth_enable_debug_user_header: env_bool("AUTH_ENABLE_DEBUG_USER_HEADER", false),
            wechat_mp_app_id: env_or("WECHAT_MP_APP_ID", ""),
            wechat_mp_app_secret: env_or("WECHAT_MP_APP_SECRET", ""),
            wechat_session_key_secret: env::var("WECHAT_SESSION_KEY_SECRET").ok().filter(|s| !s.is_empty()),
            default_mock_user_id: env_or("DEFAULT_MOCK_USER_ID", "mock_user_001"),
            public_base_url: env_or("PUBLIC_BASE_URL", "http://localhost:8000"),
            cors_allowed_origins: env_or("CORS_ALLOWED_ORIGINS", "http://localhost:8000")
                .split(',')
                .map(|s| s.trim().to_string())
                .filter(|s| !s.is_empty())
                .collect(),
            assets_dir: env_or("ASSETS_DIR", "../assets"),
            core100_tts_url: env_or("CORE100_TTS_URL", "http://127.0.0.1:5003"),
            scene_page_size: env_int("SCENE_PAGE_SIZE", 20),
            hotspot_editor_enabled: env_bool("HOTSPOT_EDITOR_ENABLED", true),
            server_port: env::var("SERVER_PORT").ok().and_then(|v| v.parse().ok()).unwrap_or(8000),
        }
    }
}
```

- [ ] **Step 2: Write error.rs**

Create `backend-rust/src/error.rs`. Extend reference code's AppError with more variants:

```rust
use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use serde_json::json;

#[derive(Debug)]
pub enum AppError {
    BadRequest(String),
    Unauthorized(String),
    Forbidden(String),
    NotFound(String),
    Internal(String),
    ExternalApi(String),
}

impl std::fmt::Display for AppError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            AppError::BadRequest(msg) => write!(f, "Bad request: {msg}"),
            AppError::Unauthorized(msg) => write!(f, "Unauthorized: {msg}"),
            AppError::Forbidden(msg) => write!(f, "Forbidden: {msg}"),
            AppError::NotFound(msg) => write!(f, "Not found: {msg}"),
            AppError::Internal(msg) => write!(f, "Internal error: {msg}"),
            AppError::ExternalApi(msg) => write!(f, "External API error: {msg}"),
        }
    }
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let (status, code, message) = match &self {
            AppError::BadRequest(msg) => (StatusCode::BAD_REQUEST, 400, msg.clone()),
            AppError::Unauthorized(msg) => (StatusCode::UNAUTHORIZED, 4001, msg.clone()),
            AppError::Forbidden(msg) => (StatusCode::FORBIDDEN, 4003, msg.clone()),
            AppError::NotFound(msg) => (StatusCode::NOT_FOUND, 4004, msg.clone()),
            AppError::Internal(msg) => (StatusCode::INTERNAL_SERVER_ERROR, 5000, msg.clone()),
            AppError::ExternalApi(msg) => (StatusCode::BAD_GATEWAY, 5002, msg.clone()),
        };
        tracing::error!("Error: {self}");
        (status, axum::Json(json!({"code": code, "data": null, "message": message}))).into_response()
    }
}

impl From<sqlx::Error> for AppError {
    fn from(err: sqlx::Error) -> Self {
        AppError::Internal(err.to_string())
    }
}

impl From<std::io::Error> for AppError {
    fn from(err: std::io::Error) -> Self {
        AppError::Internal(err.to_string())
    }
}
```

- [ ] **Step 3: Write response.rs**

Create `backend-rust/src/response.rs`. Must match Python's `success(data)` and error format exactly:

```rust
use axum::http::StatusCode;
use axum::Json;
use serde::Serialize;
use serde_json::{json, Value};

pub fn success<T: Serialize>(data: T) -> Json<Value> {
    Json(json!({
        "code": 0,
        "data": data,
        "message": "ok"
    }))
}

pub fn success_empty() -> Json<Value> {
    Json(json!({
        "code": 0,
        "data": null,
        "message": "ok"
    }))
}

pub fn fail(status: StatusCode, code: i32, message: &str) -> (StatusCode, Json<Value>) {
    (status, Json(json!({
        "code": code,
        "data": null,
        "message": message
    })))
}
```

- [ ] **Step 4: Write state.rs**

Create `backend-rust/src/state.rs`:

```rust
use sqlx::PgPool;
use std::sync::Arc;

use crate::config::Config;

#[derive(Clone)]
pub struct AppState {
    pub pool: PgPool,
    pub config: Arc<Config>,
}
```

- [ ] **Step 5: Update main.rs with module declarations**

Replace `backend-rust/src/main.rs`:

```rust
mod config;
mod error;
mod response;
mod state;

use std::sync::Arc;
use axum::Router;
use tower_http::cors::CorsLayer;
use state::AppState;

#[tokio::main]
async fn main() {
    let c = config::Config::load();
    let port = c.server_port;

    let pool = sqlx::postgres::PgPoolOptions::new()
        .max_connections(10)
        .connect(&c.database_url)
        .await
        .expect("Failed to connect to PostgreSQL");

    let state = AppState {
        pool,
        config: Arc::new(c),
    };

    let cors = CorsLayer::permissive();

    let app = Router::new()
        .layer(cors)
        .with_state(state);

    let addr = format!("0.0.0.0:{port}");
    tracing::info!("Server starting on {}", addr);

    let listener = tokio::net::TcpListener::bind(&addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}
```

- [ ] **Step 6: Verify it compiles**

Run: `cd /www/wwwroot/e.cps.vin/weixin-demo-01/backend-rust && cargo build`
Expected: Compiles. May need `OPENSSL_DIR` or use `tls-rustls` feature — if build fails on openssl, confirm sqlx uses `tls-rustls`.

- [ ] **Step 7: Commit**

```bash
cd /www/wwwroot/e.cps.vin/weixin-demo-01
git add backend-rust/
git commit -m "feat(rust): add config, error, response, state modules"
```

---

## Chunk 2: JWT + Auth Foundation

### Task 3: JWT service (HS256, Python-compatible)

**Files:**
- Create: `backend-rust/src/services/mod.rs`
- Create: `backend-rust/src/services/jwt.rs`

**Reference:** Python `backend/app/security.py` — must produce identical tokens.

- [ ] **Step 1: Write services/mod.rs**

```rust
pub mod jwt;
```

- [ ] **Step 2: Write jwt.rs**

Create `backend-rust/src/services/jwt.rs`. This is a precise port of Python's `security.py`:

```rust
use base64::engine::general_purpose::URL_SAFE_NO_PAD;
use base64::Engine;
use hmac::{Hmac, Mac};
use serde::{Deserialize, Serialize};
use serde_json::json;
use sha2::Sha256;

type HmacSha256 = Hmac<Sha256>;

fn b64url_encode(data: &[u8]) -> String {
    URL_SAFE_NO_PAD.encode(data)
}

fn b64url_decode(input: &str) -> Result<Vec<u8>, base64::DecodeError> {
    URL_SAFE_NO_PAD.decode(input)
}

fn json_compact(value: &serde_json::Value) -> Vec<u8> {
    serde_json::to_string(value)
        .unwrap()
        .as_bytes()
        .to_vec()
}

fn utc_now_ts() -> i64 {
    chrono::Utc::now().timestamp()
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct TokenClaims {
    pub sub: String,
    pub typ: String,
    pub role: String,
    pub sid: String,
    pub iat: i64,
    pub exp: i64,
}

pub fn create_access_token(
    secret: &str,
    user_id: &str,
    session_id: &str,
    role: &str,
    expires_in: i64,
) -> Result<(String, i64), String> {
    let issued_at = utc_now_ts();
    let expires_at = issued_at + expires_in.max(1);

    let header = json!({"alg": "HS256", "typ": "JWT"});
    let payload = json!({
        "sub": user_id,
        "typ": "access",
        "role": role,
        "sid": session_id,
        "iat": issued_at,
        "exp": expires_at,
    });

    let signing_input = format!(
        "{}.{}",
        b64url_encode(&json_compact(&header)),
        b64url_encode(&json_compact(&payload))
    );

    let mut mac = HmacSha256::new_from_slice(secret.as_bytes())
        .map_err(|e| format!("HMAC init failed: {e}"))?;
    mac.update(signing_input.as_bytes());
    let signature = mac.finalize().into_bytes();

    let token = format!("{}.{}", signing_input, b64url_encode(&signature));
    Ok((token, expires_at))
}

pub fn decode_access_token(secret: &str, token: &str) -> Result<TokenClaims, String> {
    let parts: Vec<&str> = token.split('.').collect();
    if parts.len() != 3 {
        return Err("invalid token".into());
    }

    let signing_input = format!("{}.{}", parts[0], parts[1]);
    let mut mac = HmacSha256::new_from_slice(secret.as_bytes())
        .map_err(|e| format!("HMAC init failed: {e}"))?;
    mac.update(signing_input.as_bytes());
    let expected_sig = mac.finalize().into_bytes();

    let actual_sig = b64url_decode(parts[2])
        .map_err(|e| format!("signature decode failed: {e}"))?;

    if !hmac::digest::Mac::verify_slice(&expected_sig, &actual_sig).is_ok() {
        return Err("invalid token signature".into());
    }

    let payload_bytes = b64url_decode(parts[1])
        .map_err(|e| format!("payload decode failed: {e}"))?;

    let claims: TokenClaims = serde_json::from_slice(&payload_bytes)
        .map_err(|e| format!("payload parse failed: {e}"))?;

    if claims.typ != "access" {
        return Err("invalid token type".into());
    }
    if claims.exp <= utc_now_ts() {
        return Err("token expired".into());
    }

    Ok(claims)
}

pub fn generate_refresh_token() -> String {
    format!("rt_{}", uuid::Uuid::new_v4().simple())
}

pub fn hash_refresh_token(token: &str) -> String {
    use sha2::Digest;
    let mut hasher = Sha256::new();
    hasher.update(token.as_bytes());
    hex::encode(hasher.finalize())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_create_and_decode_token() {
        let secret = "test-secret";
        let (token, exp) = create_access_token(secret, "user1", "sess1", "user", 3600).unwrap();
        assert!(token.contains('.'));
        assert!(exp > 0);

        let claims = decode_access_token(secret, &token).unwrap();
        assert_eq!(claims.sub, "user1");
        assert_eq!(claims.typ, "access");
        assert_eq!(claims.role, "user");
        assert_eq!(claims.sid, "sess1");
    }

    #[test]
    fn test_reject_expired_token() {
        let secret = "test-secret";
        let (token, _) = create_access_token(secret, "user1", "sess1", "user", -1).unwrap();
        // Token already expired
        assert!(decode_access_token(secret, &token).is_err());
    }

    #[test]
    fn test_reject_wrong_secret() {
        let secret = "correct-secret";
        let (token, _) = create_access_token(secret, "user1", "sess1", "user", 3600).unwrap();
        assert!(decode_access_token("wrong-secret", &token).is_err());
    }

    #[test]
    fn test_refresh_token_format() {
        let rt = generate_refresh_token();
        assert!(rt.starts_with("rt_"));
        assert!(rt.len() > 10);
    }

    #[test]
    fn test_hash_refresh_token_deterministic() {
        let hash1 = hash_refresh_token("rt_abc123");
        let hash2 = hash_refresh_token("rt_abc123");
        assert_eq!(hash1, hash2);
    }
}
```

- [ ] **Step 3: Run tests**

Run: `cd backend-rust && cargo test`
Expected: All 5 tests pass.

- [ ] **Step 4: Commit**

```bash
cd /www/wwwroot/e.cps.vin/weixin-demo-01
git add backend-rust/src/services/
git commit -m "feat(rust): add JWT service with HS256 (Python-compatible)"
```

---

### Task 4: WeChat session key encryption

**Files:**
- Create: `backend-rust/src/services/wechat_session.rs`
- Modify: `backend-rust/src/services/mod.rs`

**Reference:** Python `security.py:encrypt_wechat_session_key` / `decrypt_wechat_session_key`

- [ ] **Step 1: Write wechat_session.rs**

Precisely port Python's XOR stream cipher:

```rust
use base64::engine::general_purpose::URL_SAFE_NO_PAD;
use base64::Engine;
use hmac::{Hmac, Mac};
use sha2::{Digest, Sha256};

type HmacSha256 = Hmac<Sha256>;

fn build_stream(secret: &[u8], nonce: &[u8], length: usize) -> Vec<u8> {
    let mut output = Vec::new();
    let mut counter: u32 = 0;
    while output.len() < length {
        let mut hasher = Sha256::new();
        hasher.update(secret);
        hasher.update(nonce);
        hasher.update(counter.to_be_bytes());
        output.extend_from_slice(&hasher.finalize());
        counter += 1;
    }
    output.truncate(length);
    output
}

pub fn encrypt_session_key(secret: &str, raw_value: &str) -> String {
    if raw_value.is_empty() {
        return String::new();
    }

    let secret_bytes = secret.as_bytes();
    let nonce: [u8; 16] = rand::random();
    let plaintext = raw_value.as_bytes();
    let stream = build_stream(secret_bytes, &nonce, plaintext.len());

    let ciphertext: Vec<u8> = plaintext.iter().zip(stream.iter()).map(|(a, b)| a ^ b).collect();

    let mut mac = HmacSha256::new_from_slice(secret_bytes).unwrap();
    mac.update(&nonce);
    mac.update(&ciphertext);
    let mac_bytes = &mac.finalize().into_bytes()[..12];

    format!(
        "wsk1.{}.{}.{}",
        URL_SAFE_NO_PAD.encode(nonce),
        URL_SAFE_NO_PAD.encode(&ciphertext),
        URL_SAFE_NO_PAD.encode(mac_bytes)
    )
}

pub fn decrypt_session_key(secret: &str, cipher_text: &str) -> Result<String, String> {
    if cipher_text.is_empty() {
        return Ok(String::new());
    }

    let parts: Vec<&str> = cipher_text.split('.').collect();
    if parts.len() != 4 || parts[0] != "wsk1" {
        return Err("invalid encrypted wechat session key".into());
    }

    let nonce = URL_SAFE_NO_PAD.decode(parts[1]).map_err(|e| format!("nonce decode: {e}"))?;
    let ciphertext = URL_SAFE_NO_PAD.decode(parts[2]).map_err(|e| format!("ciphertext decode: {e}"))?;
    let actual_mac = URL_SAFE_NO_PAD.decode(parts[3]).map_err(|e| format!("mac decode: {e}"))?;

    let secret_bytes = secret.as_bytes();
    let mut mac = HmacSha256::new_from_slice(secret_bytes).unwrap();
    mac.update(&nonce);
    mac.update(&ciphertext);
    let expected_mac = &mac.finalize().into_bytes()[..12];

    if !hmac::digest::Mac::verify_slice(HmacSha256::new_from_slice(secret_bytes).unwrap(), &expected_mac).is_ok()
        || expected_mac != actual_mac.as_slice()
    {
        // Use constant-time comparison
        use hmac::digest::ConstantTimeEq;
        if !expected_mac.ct_eq(&actual_mac.as_slice()).into() {
            return Err("wechat session key integrity check failed".into());
        }
    }

    let stream = build_stream(secret_bytes, &nonce, ciphertext.len());
    let plaintext: Vec<u8> = ciphertext.iter().zip(stream.iter()).map(|(a, b)| a ^ b).collect();

    String::from_utf8(plaintext).map_err(|e| format!("utf8 decode: {e}"))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_encrypt_decrypt_roundtrip() {
        let secret = "test-session-secret";
        let original = "abc123sessionkey";
        let encrypted = encrypt_session_key(secret, original);
        assert!(encrypted.starts_with("wsk1."));

        let decrypted = decrypt_session_key(secret, &encrypted).unwrap();
        assert_eq!(decrypted, original);
    }

    #[test]
    fn test_decrypt_empty() {
        assert_eq!(decrypt_session_key("secret", "").unwrap(), "");
    }

    #[test]
    fn test_encrypt_empty() {
        assert_eq!(encrypt_session_key("secret", ""), "");
    }

    #[test]
    fn test_reject_wrong_secret() {
        let encrypted = encrypt_session_key("secret-a", "value");
        assert!(decrypt_session_key("secret-b", &encrypted).is_err());
    }
}
```

Add `rand = "0.9"` to `Cargo.toml` dependencies.

- [ ] **Step 2: Update services/mod.rs**

```rust
pub mod jwt;
pub mod wechat_session;
```

- [ ] **Step 3: Run tests**

Run: `cd backend-rust && cargo test`
Expected: All tests pass including new session key tests.

- [ ] **Step 4: Commit**

```bash
cd /www/wwwroot/e.cps.vin/weixin-demo-01
git add backend-rust/
git commit -m "feat(rust): add WeChat session key encryption (Python-compatible)"
```

---

## Chunk 3: DB Layer + Models

### Task 5: User models and DB queries

**Files:**
- Create: `backend-rust/src/models/mod.rs`
- Create: `backend-rust/src/models/user.rs`
- Create: `backend-rust/src/db/mod.rs`
- Create: `backend-rust/src/db/users.rs`
- Modify: `backend-rust/src/main.rs` (add mod declarations)

- [ ] **Step 1: Write models/user.rs**

```rust
use serde::{Deserialize, Serialize};
use sqlx::FromRow;

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct User {
    pub id: String,
    pub status: String,
    pub display_name: Option<String>,
    pub avatar_url: Option<String>,
    pub mobile: Option<String>,
    pub mobile_verified: bool,
    pub last_login_at: Option<chrono::DateTime<chrono::Utc>>,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub updated_at: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct UserIdentity {
    pub id: String,
    pub user_id: String,
    pub provider: String,
    pub provider_uid: String,
    pub union_id: Option<String>,
    pub session_key_encrypted: Option<String>,
    pub meta_json: serde_json::Value,
    pub last_login_at: Option<chrono::DateTime<chrono::Utc>>,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub updated_at: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct RefreshToken {
    pub id: String,
    pub user_id: String,
    pub token_hash: String,
    pub device_type: Option<String>,
    pub device_id: Option<String>,
    pub app_version: Option<String>,
    pub expires_at: chrono::DateTime<chrono::Utc>,
    pub revoked_at: Option<chrono::DateTime<chrono::Utc>>,
    pub created_at: chrono::DateTime<chrono::Utc>,
}

/// Profile response for /api/me
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct UserProfile {
    pub user_id: String,
    pub display_name: String,
    pub avatar_url: String,
    pub role: String,
    pub status: String,
    pub mobile: String,
    pub mobile_verified: bool,
    pub created_at: String,
}

impl UserProfile {
    pub fn from_user(user: &User, role: &str) -> Self {
        Self {
            user_id: user.id.clone(),
            display_name: user.display_name.clone().unwrap_or_default(),
            avatar_url: user.avatar_url.clone().unwrap_or_default(),
            role: role.to_string(),
            status: user.status.clone(),
            mobile: user.mobile.clone().unwrap_or_default(),
            mobile_verified: user.mobile_verified,
            created_at: user.created_at.to_rfc3339(),
        }
    }
}
```

- [ ] **Step 2: Write models/mod.rs**

```rust
pub mod user;
```

- [ ] **Step 3: Write db/users.rs**

```rust
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
```

- [ ] **Step 4: Write db/mod.rs**

```rust
pub mod users;
pub mod scenes;
```

- [ ] **Step 5: Write db/scenes.rs (stub for now)**

```rust
// Full scene queries will be implemented in Chunk 4
```

- [ ] **Step 6: Update main.rs with mod declarations**

Add to `main.rs` top:

```rust
mod models;
mod db;
mod services;
```

- [ ] **Step 7: Verify it compiles**

Run: `cd backend-rust && cargo build`
Expected: Compiles.

- [ ] **Step 8: Commit**

```bash
cd /www/wwwroot/e.cps.vin/weixin-demo-01
git add backend-rust/
git commit -m "feat(rust): add user models and DB query layer"
```

---

## Chunk 4: Auth Middleware + Auth API

### Task 6: Auth middleware

**Files:**
- Create: `backend-rust/src/middleware/mod.rs`
- Create: `backend-rust/src/middleware/auth.rs`
- Create: `backend-rust/src/services/wechat_auth.rs`
- Modify: `backend-rust/src/services/mod.rs`

- [ ] **Step 1: Write middleware/auth.rs**

JWT middleware that extracts current user from Bearer token:

```rust
use axum::extract::{FromRequestParts, State};
use axum::http::request::Parts;
use axum::http::StatusCode;
use axum::Json;
use serde_json::json;

use crate::error::AppError;
use crate::models::user::User;
use crate::services::jwt;
use crate::state::AppState;

/// Extracts authenticated user from JWT Bearer token.
/// Returns 401 if no token or invalid.
pub struct AuthUser {
    pub user_id: String,
    pub role: String,
    pub session_id: String,
}

#[async_trait::async_trait]
impl FromRequestParts<AppState> for AuthUser {
    type Rejection = AppError;

    async fn from_request_parts(parts: &mut Parts, state: &AppState) -> Result<Self, Self::Rejection> {
        let auth_header = parts
            .headers
            .get("Authorization")
            .and_then(|v| v.to_str().ok())
            .unwrap_or("");

        let token = auth_header
            .strip_prefix("Bearer ")
            .ok_or_else(|| AppError::Unauthorized("missing authorization token".into()))?;

        let claims = jwt::decode_access_token(&state.config.auth_jwt_secret, token)
            .map_err(|e| AppError::Unauthorized(e))?;

        Ok(AuthUser {
            user_id: claims.sub,
            role: claims.role,
            session_id: claims.sid,
        })
    }
}

/// Optional auth — returns user if token present, None otherwise.
pub struct OptionalAuthUser(pub Option<AuthUser>);

#[async_trait::async_trait]
impl FromRequestParts<AppState> for OptionalAuthUser {
    type Rejection = std::convert::Infallible;

    async fn from_request_parts(parts: &mut Parts, state: &AppState) -> Result<Self, Self::Rejection> {
        let auth_header = parts
            .headers
            .get("Authorization")
            .and_then(|v| v.to_str().ok())
            .unwrap_or("");

        if let Some(token) = auth_header.strip_prefix("Bearer ") {
            if let Ok(claims) = jwt::decode_access_token(&state.config.auth_jwt_secret, token) {
                return Ok(OptionalAuthUser(Some(AuthUser {
                    user_id: claims.sub,
                    role: claims.role,
                    session_id: claims.sid,
                })));
            }
        }

        // Debug user header support
        if state.config.auth_enable_debug_user_header {
            if let Some(debug_uid) = parts.headers.get("X-Debug-User-Id").and_then(|v| v.to_str().ok()) {
                if !debug_uid.is_empty() {
                    return Ok(OptionalAuthUser(Some(AuthUser {
                        user_id: debug_uid.to_string(),
                        role: "user".to_string(),
                        session_id: String::new(),
                    })));
                }
            }
        }

        Ok(OptionalAuthUser(None))
    }
}
```

Add `async-trait = "0.1"` to `Cargo.toml`.

- [ ] **Step 2: Write middleware/mod.rs**

```rust
pub mod auth;
```

- [ ] **Step 3: Write services/wechat_auth.rs**

```rust
use serde::Deserialize;
use crate::error::AppError;

#[derive(Deserialize)]
struct Code2SessionResponse {
    openid: Option<String>,
    session_key: Option<String>,
    unionid: Option<String>,
    errcode: Option<i32>,
    errmsg: Option<String>,
}

pub struct WechatAuthResult {
    pub openid: String,
    pub session_key: String,
    pub unionid: Option<String>,
}

pub async fn code2session(
    app_id: &str,
    app_secret: &str,
    code: &str,
) -> Result<WechatAuthResult, AppError> {
    let url = format!(
        "https://api.weixin.qq.com/sns/jscode2session?appid={}&secret={}&js_code={}&grant_type=authorization_code",
        app_id, app_secret, code
    );

    let client = reqwest::Client::new();
    let resp: Code2SessionResponse = client
        .get(&url)
        .timeout(std::time::Duration::from_secs(10))
        .send()
        .await
        .map_err(|e| AppError::ExternalApi(format!("WeChat code2session request failed: {e}")))?
        .json()
        .await
        .map_err(|e| AppError::ExternalApi(format!("WeChat code2session parse failed: {e}")))?;

    if let Some(errcode) = resp.errcode {
        if errcode != 0 {
            return Err(AppError::ExternalApi(format!(
                "WeChat code2session error {}: {}",
                errcode,
                resp.errmsg.unwrap_or_default()
            )));
        }
    }

    let openid = resp.openid.ok_or_else(|| AppError::ExternalApi("missing openid".into()))?;
    let session_key = resp.session_key.ok_or_else(|| AppError::ExternalApi("missing session_key".into()))?;

    Ok(WechatAuthResult {
        openid,
        session_key,
        unionid: resp.unionid,
    })
}
```

- [ ] **Step 4: Update services/mod.rs**

```rust
pub mod jwt;
pub mod wechat_session;
pub mod wechat_auth;
```

- [ ] **Step 5: Update main.rs**

Add `mod middleware;` to main.rs.

- [ ] **Step 6: Verify it compiles**

Run: `cd backend-rust && cargo build`
Expected: Compiles.

- [ ] **Step 7: Commit**

```bash
cd /www/wwwroot/e.cps.vin/weixin-demo-01
git add backend-rust/
git commit -m "feat(rust): add auth middleware and WeChat code2session service"
```

---

### Task 7: Auth API endpoints

**Files:**
- Create: `backend-rust/src/api/mod.rs`
- Create: `backend-rust/src/api/auth.rs`
- Create: `backend-rust/src/api/user.rs`
- Create: `backend-rust/src/api/health.rs`
- Modify: `backend-rust/src/main.rs` (wire routes)

This is the critical task — login, refresh, logout, and /me endpoints must produce byte-identical responses to the Python backend.

- [ ] **Step 1: Write api/health.rs**

```rust
use axum::extract::State;
use axum::Json;
use serde_json::{json, Value};

use crate::response::success;
use crate::state::AppState;

pub async fn health() -> Json<Value> {
    success(json!({"status": "ok"}))
}

pub async fn get_config(State(state): State<AppState>) -> Json<Value> {
    success(json!({
        "hotspotEditorEnabled": state.config.hotspot_editor_enabled,
    }))
}
```

- [ ] **Step 2: Write api/auth.rs**

```rust
use axum::extract::State;
use axum::Json;
use serde::Deserialize;
use serde_json::{json, Value};

use crate::db::users;
use crate::error::AppError;
use crate::middleware::auth::AuthUser;
use crate::models::user::UserProfile;
use crate::response::{success, success_empty};
use crate::services::{jwt, wechat_auth, wechat_session};
use crate::state::AppState;

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct WechatLoginRequest {
    code: String,
    device: Option<DevicePayload>,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct DevicePayload {
    device_id: Option<String>,
    device_type: Option<String>,
    app_version: Option<String>,
}

#[derive(Deserialize)]
pub struct RefreshRequest {
    refresh_token: String,
}

#[derive(Deserialize)]
pub struct LogoutRequest {
    refresh_token: Option<String>,
}

pub async fn wechat_login(
    State(state): State<AppState>,
    Json(body): Json<WechatLoginRequest>,
) -> Result<Json<Value>, AppError> {
    let config = &state.config;

    // Step 1: Resolve openid + session_key
    let (openid, session_key) = if config.auth_wechat_login_mode == "mock" {
        // Mock mode: derive deterministic openid from code
        let fake_openid = format!("mock_{}", &body.code);
        (fake_openid, String::new())
    } else {
        let result = wechat_auth::code2session(
            &config.wechat_mp_app_id,
            &config.wechat_mp_app_secret,
            &body.code,
        )
        .await?;
        (result.openid, result.session_key)
    };

    // Step 2: Find or create user
    let pool = &state.pool;
    let identity = users::find_identity_by_provider(pool, "wechat", &openid).await?;

    let (user, identity) = if let Some(identity) = identity {
        let user = users::find_user_by_id(pool, &identity.user_id)
            .await?
            .ok_or_else(|| AppError::Internal("user not found for identity".into()))?;

        // Update session key if we got one
        if !session_key.is_empty() {
            let secret = config.wechat_session_key_secret.as_deref().unwrap_or(&config.auth_jwt_secret);
            let encrypted = wechat_session::encrypt_session_key(secret, &session_key);
            users::update_identity_session_key(pool, &identity.id, &encrypted).await?;
        }

        users::update_user_last_login(pool, &user.id).await?;
        (user, identity)
    } else {
        // Create new user + identity
        let user_id = format!("user_{}", uuid::Uuid::new_v4().simple());
        let identity_id = format!("id_{}", uuid::Uuid::new_v4().simple());

        let user = users::create_user(pool, &user_id).await?;

        let encrypted_sk = if session_key.is_empty() {
            None
        } else {
            let secret = config.wechat_session_key_secret.as_deref().unwrap_or(&config.auth_jwt_secret);
            Some(wechat_session::encrypt_session_key(secret, &session_key))
        };

        let identity = users::create_identity(
            pool,
            &identity_id,
            &user_id,
            "wechat",
            &openid,
            encrypted_sk.as_deref(),
        )
        .await?;

        (user, identity)
    };

    // Step 3: Create session (access token + refresh token)
    let session_id = uuid::Uuid::new_v4().to_string();
    let (access_token, _exp) = jwt::create_access_token(
        &config.auth_jwt_secret,
        &user.id,
        &session_id,
        "user",
        config.auth_access_token_ttl_seconds,
    )
    .map_err(AppError::Internal)?;

    let raw_refresh = jwt::generate_refresh_token();
    let refresh_hash = jwt::hash_refresh_token(&raw_refresh);
    let device = body.device.as_ref();
    let refresh_expires = chrono::Utc::now() + chrono::Duration::seconds(config.auth_refresh_token_ttl_seconds);

    users::create_refresh_token(
        pool,
        &format!("rtid_{}", uuid::Uuid::new_v4().simple()),
        &user.id,
        &refresh_hash,
        device.and_then(|d| d.device_type.as_deref()),
        device.and_then(|d| d.device_id.as_deref()),
        device.and_then(|d| d.app_version.as_deref()),
        refresh_expires,
    )
    .await?;

    let profile = UserProfile::from_user(&user, "user");

    Ok(success(json!({
        "accessToken": access_token,
        "refreshToken": raw_refresh,
        "accessTokenExpireAt": _exp,
        "refreshTokenExpireAt": refresh_expires.to_rfc3339(),
        "me": profile,
    })))
}

pub async fn refresh_token(
    State(state): State<AppState>,
    Json(body): Json<RefreshRequest>,
) -> Result<Json<Value>, AppError> {
    let token_hash = jwt::hash_refresh_token(&body.refresh_token);
    let stored = users::find_refresh_token_by_hash(&state.pool, &token_hash)
        .await?
        .ok_or_else(|| AppError::Unauthorized("invalid refresh token".into()))?;

    // Revoke old refresh token
    users::revoke_refresh_token(&state.pool, &stored.id).await?;

    // Create new session
    let session_id = uuid::Uuid::new_v4().to_string();
    let (access_token, _exp) = jwt::create_access_token(
        &state.config.auth_jwt_secret,
        &stored.user_id,
        &session_id,
        "user",
        state.config.auth_access_token_ttl_seconds,
    )
    .map_err(AppError::Internal)?;

    let raw_refresh = jwt::generate_refresh_token();
    let refresh_hash = jwt::hash_refresh_token(&raw_refresh);
    let refresh_expires = chrono::Utc::now() + chrono::Duration::seconds(state.config.auth_refresh_token_ttl_seconds);

    users::create_refresh_token(
        &state.pool,
        &format!("rtid_{}", uuid::Uuid::new_v4().simple()),
        &stored.user_id,
        &refresh_hash,
        stored.device_type.as_deref(),
        stored.device_id.as_deref(),
        stored.app_version.as_deref(),
        refresh_expires,
    )
    .await?;

    users::update_user_last_login(&state.pool, &stored.user_id).await?;

    let user = users::find_user_by_id(&state.pool, &stored.user_id)
        .await?
        .ok_or_else(|| AppError::Internal("user not found".into()))?;

    let profile = UserProfile::from_user(&user, "user");

    Ok(success(json!({
        "accessToken": access_token,
        "refreshToken": raw_refresh,
        "accessTokenExpireAt": _exp,
        "refreshTokenExpireAt": refresh_expires.to_rfc3339(),
        "me": profile,
    })))
}

pub async fn logout(
    State(state): State<AppState>,
    auth: AuthUser,
    Json(body): Json<Option<LogoutRequest>>,
) -> Result<Json<Value>, AppError> {
    if let Some(body) = body {
        if let Some(rt) = &body.refresh_token {
            let hash = jwt::hash_refresh_token(rt);
            if let Some(stored) = users::find_refresh_token_by_hash(&state.pool, &hash).await? {
                users::revoke_refresh_token(&state.pool, &stored.id).await?;
            }
        }
    }
    Ok(success_empty())
}
```

- [ ] **Step 3: Write api/user.rs**

```rust
use axum::extract::State;
use axum::Json;
use serde::Deserialize;
use serde_json::{json, Value};

use crate::db::users;
use crate::error::AppError;
use crate::middleware::auth::AuthUser;
use crate::response::success;
use crate::state::AppState;

pub async fn get_me(
    State(state): State<AppState>,
    auth: AuthUser,
) -> Result<Json<Value>, AppError> {
    let user = users::find_user_by_id(&state.pool, &auth.user_id)
        .await?
        .ok_or_else(|| AppError::NotFound("user not found".into()))?;

    let profile = crate::models::user::UserProfile::from_user(&user, &auth.role);
    Ok(success(json!(profile)))
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct UpdateProfileRequest {
    display_name: Option<String>,
    avatar_url: Option<String>,
}

pub async fn update_profile(
    State(state): State<AppState>,
    auth: AuthUser,
    Json(body): Json<UpdateProfileRequest>,
) -> Result<Json<Value>, AppError> {
    let user = users::update_user_profile(
        &state.pool,
        &auth.user_id,
        body.display_name.as_deref().unwrap_or(""),
        body.avatar_url.as_deref().unwrap_or(""),
    )
    .await?;

    let profile = crate::models::user::UserProfile::from_user(&user, &auth.role);
    Ok(success(json!(profile)))
}

pub async fn get_membership(
    State(state): State<AppState>,
    auth: AuthUser,
) -> Result<Json<Value>, AppError> {
    // Query entitlements for membership tier
    let row = sqlx::query_as::<_, (String, Option<chrono::DateTime<chrono::Utc>>, Option<chrono::DateTime<chrono::Utc>>)>(
        "SELECT entitlement_code, starts_at, expires_at FROM user_entitlements WHERE user_id = $1 AND entitlement_type = 'membership' AND status = 'active' ORDER BY expires_at DESC LIMIT 1"
    )
        .bind(&auth.user_id)
        .fetch_optional(&state.pool)
        .await?;

    let (tier, starts_at, expires_at) = match row {
        Some(r) => (r.0, r.1.map(|t| t.to_rfc3339()), r.2.map(|t| t.to_rfc3339())),
        None => ("free".to_string(), None, None),
    };

    Ok(success(json!({
        "tier": tier,
        "startsAt": starts_at,
        "expiresAt": expires_at,
    })))
}

pub async fn get_credits(
    State(state): State<AppState>,
    auth: AuthUser,
) -> Result<Json<Value>, AppError> {
    let rows = sqlx::query_as::<_, (String, i32)>(
        "SELECT credit_type, balance FROM user_credit_accounts WHERE user_id = $1"
    )
        .bind(&auth.user_id)
        .fetch_all(&state.pool)
        .await?;

    let credits: serde_json::Map<String, Value> = rows.into_iter()
        .map(|(k, v)| (k, json!(v)))
        .collect();

    Ok(success(json!(credits)))
}

pub async fn get_entitlements(
    State(state): State<AppState>,
    auth: AuthUser,
) -> Result<Json<Value>, AppError> {
    let rows = sqlx::query(
        "SELECT entitlement_code, entitlement_type, status, starts_at, expires_at FROM user_entitlements WHERE user_id = $1 AND status = 'active'"
    )
        .bind(&auth.user_id)
        .fetch_all(&state.pool)
        .await?;

    // Simplified: return list of active entitlement codes
    let codes: Vec<String> = rows.iter()
        .map(|r| r.try_get::<String, _>("entitlement_code").unwrap_or_default())
        .collect();

    Ok(success(json!({"entitlements": codes})))
}
```

- [ ] **Step 4: Write api/mod.rs**

```rust
pub mod auth;
pub mod health;
pub mod user;

use axum::routing::{get, post, put};
use axum::Router;

use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        // Health & config
        .route("/api/health", get(health::health))
        .route("/api/config", get(health::get_config))
        // Auth
        .route("/api/auth/wechat/login", post(auth::wechat_login))
        .route("/api/auth/refresh", post(auth::refresh_token))
        .route("/api/auth/logout", post(auth::logout))
        // User
        .route("/api/me", get(user::get_me))
        .route("/api/me/profile", put(user::update_profile))
        .route("/api/me/membership", get(user::get_membership))
        .route("/api/me/credits", get(user::get_credits))
        .route("/api/me/entitlements", get(user::get_entitlements))
}
```

- [ ] **Step 5: Update main.rs to wire routes**

Replace main.rs body with:

```rust
mod api;
mod config;
mod db;
mod error;
mod middleware;
mod models;
mod response;
mod services;
mod state;

use state::AppState;
use std::sync::Arc;
use tower_http::cors::CorsLayer;

#[tokio::main]
async fn main() {
    dotenvy::dotenv().ok();
    tracing_subscriber::fmt::init();

    let c = config::Config::load();
    let port = c.server_port;

    let pool = sqlx::postgres::PgPoolOptions::new()
        .max_connections(10)
        .connect(&c.database_url)
        .await
        .expect("Failed to connect to PostgreSQL");

    let state = AppState {
        pool,
        config: Arc::new(c),
    };

    let cors = CorsLayer::permissive();
    let app = api::routes().layer(cors).with_state(state);

    let addr = format!("0.0.0.0:{port}");
    tracing::info!("Server starting on {}", addr);

    let listener = tokio::net::TcpListener::bind(&addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}
```

- [ ] **Step 6: Verify it compiles**

Run: `cd backend-rust && cargo build`
Expected: Compiles. Fix any import/type errors.

- [ ] **Step 7: Start server and test health**

Run: `cd backend-rust && cargo run` (in another terminal)
Run: `curl http://localhost:8000/api/health`
Expected: `{"code":0,"data":{"status":"ok"},"message":"ok"}`

- [ ] **Step 8: Commit**

```bash
cd /www/wwwroot/e.cps.vin/weixin-demo-01
git add backend-rust/
git commit -m "feat(rust): add auth API endpoints (login/refresh/logout/me)"
```

---

## Chunk 5: Scene API

### Task 8: Scene models, DB queries, and API endpoints

**Files:**
- Create: `backend-rust/src/models/scene.rs`
- Modify: `backend-rust/src/models/mod.rs`
- Modify: `backend-rust/src/db/scenes.rs`
- Create: `backend-rust/src/api/scene.rs`
- Modify: `backend-rust/src/api/mod.rs`

- [ ] **Step 1: Write models/scene.rs**

```rust
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Rect {
    pub l: f64,
    pub t: f64,
    pub w: f64,
    pub h: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct HotspotItem {
    pub id: String,
    pub word: String,
    #[serde(default)]
    pub ipa: String,
    #[serde(default)]
    pub meaning: String,
    #[serde(default)]
    pub pos: Option<String>,
    #[serde(default)]
    pub sentence: String,
    #[serde(default)]
    pub sentence_translation: String,
    #[serde(default)]
    pub rect: Option<Rect>,
    #[serde(default)]
    pub hidden: bool,
    #[serde(default)]
    pub locked: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct VerbItem {
    pub id: String,
    pub word: String,
    #[serde(default)]
    pub ipa: String,
    #[serde(default)]
    pub meaning: String,
    #[serde(default)]
    pub related_item: String,
    #[serde(default)]
    pub sentence: String,
    #[serde(default)]
    pub sentence_translation: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, sqlx::FromRow)]
#[serde(rename_all = "camelCase")]
pub struct Scene {
    pub scene_id: String,
    pub title: String,
    pub category: String,
    pub visibility: String,
    pub scene_type: String,
    pub cover_path: String,
    pub background_path: String,
    pub items: serde_json::Value,
    pub verbs: serde_json::Value,
    pub meta_json: serde_json::Value,
    pub owner_id: Option<String>,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub updated_at: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize, sqlx::FromRow)]
#[serde(rename_all = "camelCase")]
pub struct SceneCategory {
    pub id: String,
    pub category_code: String,
    pub name: String,
    pub description: String,
    pub status: String,
    pub sort_order: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize, sqlx::FromRow)]
#[serde(rename_all = "camelCase")]
pub struct SceneCollection {
    pub id: String,
    pub collection_code: String,
    pub name: String,
    pub description: String,
    pub status: String,
    pub cover_url: String,
    pub sort_order: i32,
}
```

Update `models/mod.rs`:
```rust
pub mod user;
pub mod scene;
```

- [ ] **Step 2: Write db/scenes.rs**

```rust
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
```

- [ ] **Step 3: Write api/scene.rs**

```rust
use axum::extract::{Path, Query, State};
use axum::Json;
use serde::Deserialize;
use serde_json::{json, Value};

use crate::db::scenes;
use crate::error::AppError;
use crate::middleware::auth::OptionalAuthUser;
use crate::response::success;
use crate::state::AppState;

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ListScenesQuery {
    page: Option<i64>,
    page_size: Option<i64>,
    category: Option<String>,
}

pub async fn list_scenes(
    State(state): State<AppState>,
    Query(query): Query<ListScenesQuery>,
    _auth: OptionalAuthUser,
) -> Result<Json<Value>, AppError> {
    let page_size = query.page_size.unwrap_or(state.config.scene_page_size).min(100).max(1);
    let page = query.page.unwrap_or(1).max(1);
    let offset = (page - 1) * page_size;

    let (scenes, total) = scenes::list_public_scenes(&state.pool, page_size, offset).await?;

    let list: Vec<Value> = scenes.iter().map(|s| serialize_scene_summary(&state, s)).collect();

    Ok(success(json!({
        "list": list,
        "total": total,
        "page": page,
        "pageSize": page_size,
    })))
}

pub async fn get_scene(
    State(state): State<AppState>,
    Path(scene_id): Path<String>,
    _auth: OptionalAuthUser,
) -> Result<Json<Value>, AppError> {
    let scene = scenes::get_scene(&state.pool, &scene_id)
        .await?
        .ok_or_else(|| AppError::NotFound(format!("scene {scene_id} not found")))?;

    Ok(success(json!(serialize_scene_detail(&state, &scene))))
}

pub async fn list_scene_categories(
    State(state): State<AppState>,
) -> Result<Json<Value>, AppError> {
    let cats = scenes::list_categories(&state.pool).await?;
    Ok(success(json!({"list": cats})))
}

pub async fn list_scene_collections(
    State(state): State<AppState>,
) -> Result<Json<Value>, AppError> {
    let cols = scenes::list_collections(&state.pool).await?;
    Ok(success(json!({"list": cols})))
}

fn asset_url(base_url: &str, path: &str) -> String {
    if path.is_empty() || path.starts_with("http") {
        return path.to_string();
    }
    format!("{}/assets/{}", base_url.trim_end_matches('/'), path.trim_start_matches('/'))
}

fn serialize_scene_summary(state: &AppState, scene: &crate::models::scene::Scene) -> Value {
    let items = scene.items.as_array().map(|a| a.len()).unwrap_or(0);
    json!({
        "sceneId": scene.scene_id,
        "title": scene.title,
        "category": scene.category,
        "coverUrl": asset_url(&state.config.public_base_url, &scene.cover_path),
        "backgroundUrl": asset_url(&state.config.public_base_url, &scene.background_path),
        "itemCount": items,
        "visibility": scene.visibility,
        "free": scene.meta_json.get("free").and_then(|v| v.as_bool()).unwrap_or(false),
    })
}

fn serialize_scene_detail(state: &AppState, scene: &crate::models::scene::Scene) -> Value {
    let hotspots: Vec<crate::models::scene::HotspotItem> = serde_json::from_value(scene.items.clone()).unwrap_or_default();
    let verbs: Vec<crate::models::scene::VerbItem> = serde_json::from_value(scene.verbs.clone()).unwrap_or_default();

    json!({
        "sceneId": scene.scene_id,
        "title": scene.title,
        "category": scene.category,
        "visibility": scene.visibility,
        "sceneType": scene.scene_type,
        "backgroundUrl": asset_url(&state.config.public_base_url, &scene.background_path),
        "coverUrl": asset_url(&state.config.public_base_url, &scene.cover_path),
        "items": hotspots,
        "verbs": verbs,
        "meta": scene.meta_json,
        "free": scene.meta_json.get("free").and_then(|v| v.as_bool()).unwrap_or(false),
        "createdAt": scene.created_at.to_rfc3339(),
    })
}
```

- [ ] **Step 4: Update api/mod.rs to include scene routes**

```rust
pub mod auth;
pub mod health;
pub mod scene;
pub mod user;

use axum::routing::{get, post, put};
use axum::Router;

use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        // Health & config
        .route("/api/health", get(health::health))
        .route("/api/config", get(health::get_config))
        // Auth
        .route("/api/auth/wechat/login", post(auth::wechat_login))
        .route("/api/auth/refresh", post(auth::refresh_token))
        .route("/api/auth/logout", post(auth::logout))
        // User
        .route("/api/me", get(user::get_me))
        .route("/api/me/profile", put(user::update_profile))
        .route("/api/me/membership", get(user::get_membership))
        .route("/api/me/credits", get(user::get_credits))
        .route("/api/me/entitlements", get(user::get_entitlements))
        // Scenes
        .route("/api/scenes", get(scene::list_scenes))
        .route("/api/scenes/{scene_id}", get(scene::get_scene))
        .route("/api/scene-categories", get(scene::list_scene_categories))
        .route("/api/scene-collections", get(scene::list_scene_collections))
}
```

- [ ] **Step 5: Verify it compiles**

Run: `cd backend-rust && cargo build`
Expected: Compiles.

- [ ] **Step 6: Start server and test scenes**

Run: `cd backend-rust && cargo run`
Run: `curl http://localhost:8000/api/scenes`
Expected: `{"code":0,"data":{"list":[...],"total":N,...},"message":"ok"}`

- [ ] **Step 7: Test with real mini program**

Switch Nginx to point to the Rust server (port 8000). Open mini program → login → browse scenes → verify everything works.

- [ ] **Step 8: Commit**

```bash
cd /www/wwwroot/e.cps.vin/weixin-demo-01
git add backend-rust/
git commit -m "feat(rust): add scene API endpoints (list/detail/categories/collections)"
```

---

## Chunk 6: TTS Proxy + Final Integration

### Task 9: TTS proxy endpoint

**Files:**
- Modify: `backend-rust/src/api/health.rs`
- Modify: `backend-rust/src/api/mod.rs`

- [ ] **Step 1: Add TTS proxy to health.rs**

```rust
use axum::extract::{Query, State};
use axum::Json;
use serde::Deserialize;
use serde_json::{json, Value};

use crate::error::AppError;
use crate::response::success;
use crate::state::AppState;

#[derive(Deserialize)]
pub struct TtsQuery {
    text: String,
}

pub async fn health() -> Json<Value> {
    success(json!({"status": "ok"}))
}

pub async fn get_config(State(state): State<AppState>) -> Json<Value> {
    success(json!({
        "hotspotEditorEnabled": state.config.hotspot_editor_enabled,
    }))
}

pub async fn tts_proxy(
    State(state): State<AppState>,
    Query(query): Query<TtsQuery>,
) -> Result<axum::response::Response, AppError> {
    if query.text.is_empty() || query.text.len() > 500 {
        return Err(AppError::BadRequest("text must be 1-500 characters".into()));
    }

    let client = reqwest::Client::new();
    let url = format!("{}/api/tts/speak", state.config.core100_tts_url);

    let resp = client
        .post(&url)
        .json(&json!({"text": query.text, "voice": "en-US-JennyNeural"}))
        .timeout(std::time::Duration::from_secs(30))
        .send()
        .await
        .map_err(|e| AppError::ExternalApi(format!("TTS request failed: {e}")))?;

    if !resp.status().is_success() {
        return Err(AppError::ExternalApi("TTS service error".into()));
    }

    let bytes = resp.bytes().await.map_err(|e| AppError::Internal(e.to_string()))?;
    Ok(axum::response::Response::builder()
        .header("content-type", "audio/mpeg")
        .body(axum::body::Body::from(bytes.to_vec()))
        .unwrap())
}
```

- [ ] **Step 2: Update api/mod.rs with TTS route**

Add `.route("/api/tts", get(health::tts_proxy))` to the router.

- [ ] **Step 3: Verify it compiles and test**

Run: `cd backend-rust && cargo build && cargo run`
Run: `curl "http://localhost:8000/api/tts?text=hello" -o /tmp/test.mp3`
Expected: Downloads an MP3 file.

- [ ] **Step 4: Final integration test with mini program**

1. Ensure Rust server is running on port 8000
2. Open mini program in WeChat DevTools
3. Test flow: Login → Browse scenes → Play TTS audio → Check /api/me
4. Verify all API responses match Python backend format

- [ ] **Step 5: Commit**

```bash
cd /www/wwwroot/e.cps.vin/weixin-demo-01
git add backend-rust/
git commit -m "feat(rust): add TTS proxy and complete Phase 1 integration"
```

---

## Phase 1 Complete — Acceptance Criteria

- [ ] `cargo build --release` produces a working binary
- [ ] `curl /api/health` returns `{"code":0,"data":{"status":"ok"},"message":"ok"}`
- [ ] Mini program can login via WeChat auth
- [ ] Mini program can browse scenes (list, detail, categories, collections)
- [ ] Mini program can play TTS audio
- [ ] `/api/me` returns correct user profile
- [ ] JWT tokens from Python backend can be verified by Rust (and vice versa)
- [ ] All API responses use `{"code":0,"data":...,"message":"ok"}` format

**Next phase:** Phase 2 (Scene generation + Video export) — see separate plan.

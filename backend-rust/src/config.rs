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
    pub uploads_dir: String,
    pub max_upload_size_mb: i64,
    pub core100_tts_url: String,
    pub zhipuai_api_key: String,
    pub core100_model: String,
    pub generated_dir: String,
    pub video_max_age_seconds: i64,
    pub upload_max_age_seconds: i64,
    pub scene_page_size: i64,
    pub hotspot_editor_enabled: bool,
    pub server_port: u16,
    // Commerce
    pub payment_mode: String,
    pub wx_virtual_pay_app_id: String,
    pub wx_virtual_pay_offer_id: String,
    pub wx_virtual_pay_app_key: String,
    pub wx_virtual_pay_env: i64,
    // Admin dashboard
    pub admin_dashboard_enabled: bool,
    pub admin_dashboard_username: String,
    pub admin_dashboard_password: String,
    pub admin_web_dir: String,
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
            uploads_dir: env_or("UPLOADS_DIR", "../assets/uploads"),
            max_upload_size_mb: env_int("MAX_UPLOAD_SIZE_MB", 10),
            core100_tts_url: env_or("CORE100_TTS_URL", "http://127.0.0.1:5003"),
            zhipuai_api_key: env_or("ZHIPUAI_API_KEY", ""),
            core100_model: env_or("CORE100_MODEL", "glm-4v-flash"),
            generated_dir: env_or("GENERATED_DIR", "../assets/generated"),
            video_max_age_seconds: env_int("VIDEO_MAX_AGE_SECONDS", 10800),
            upload_max_age_seconds: env_int("UPLOAD_MAX_AGE_SECONDS", 10800),
            scene_page_size: env_int("SCENE_PAGE_SIZE", 20),
            hotspot_editor_enabled: env_bool("HOTSPOT_EDITOR_ENABLED", true),
            server_port: env::var("SERVER_PORT").ok().and_then(|v| v.parse().ok()).unwrap_or(8000),
            payment_mode: env_or("PAYMENT_MODE", "mock"),
            wx_virtual_pay_app_id: env_or("WX_VIRTUAL_PAY_APP_ID", ""),
            wx_virtual_pay_offer_id: env_or("WX_VIRTUAL_PAY_OFFER_ID", ""),
            wx_virtual_pay_app_key: env_or("WX_VIRTUAL_PAY_APP_KEY", ""),
            wx_virtual_pay_env: env_int("WX_VIRTUAL_PAY_ENV", 1),
            admin_dashboard_enabled: env_bool("ADMIN_DASHBOARD_ENABLED", true),
            admin_dashboard_username: env_or("ADMIN_DASHBOARD_USERNAME", "admin"),
            admin_dashboard_password: env_or("ADMIN_DASHBOARD_PASSWORD", "admin123456"),
            admin_web_dir: env_or("ADMIN_WEB_DIR", "../backend/admin_web"),
        }
    }
}

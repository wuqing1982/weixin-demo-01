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
        .route("/api/tts", get(health::tts_proxy))
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

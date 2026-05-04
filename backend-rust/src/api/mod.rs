pub mod auth;
pub mod cdk;
pub mod health;
pub mod order;
pub mod payment;
pub mod product;
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
        .route("/api/me/upgrade-preview", get(user::upgrade_preview))
        // Scenes
        .route("/api/scenes", get(scene::list_scenes))
        .route("/api/scenes/{scene_id}", get(scene::get_scene))
        .route("/api/scene-categories", get(scene::list_scene_categories))
        .route("/api/scene-collections", get(scene::list_scene_collections))
        // Products
        .route("/api/products", get(product::list_products))
        .route("/api/products/{product_id}", get(product::get_product))
        .route("/api/products/{product_id}/skus", get(product::list_product_skus))
        // Orders
        .route("/api/orders", post(order::create_order).get(order::list_orders))
        .route("/api/orders/{order_id}", get(order::get_order))
        .route("/api/orders/{order_id}/pay", post(order::pay_order))
        .route("/api/orders/{order_id}/mock-pay-success", post(order::mock_pay_success))
        .route("/api/orders/{order_id}/payment-sync", post(order::payment_sync))
        // Payment callbacks
        .route("/api/payments/virtual/notify", get(payment::virtual_notify_get).post(payment::virtual_notify_post))
        // CDK
        .route("/api/cdk/redeem", post(cdk::redeem_cdk))
        .route("/api/cdk/my-redemptions", get(cdk::my_redemptions))
}

pub mod auth;
pub mod catalog;
pub mod cdk;
pub mod orders;
pub mod overview;
pub mod products;
pub mod scene_logs;
pub mod scenes;
pub mod storage;
pub mod tasks;
pub mod uploads;
pub mod users;

use axum::routing::{get, post, put};
use axum::Router;

use crate::error::AppError;
use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        // Auth
        .route("/api/admin/auth/login", post(auth::login))
        .route("/api/admin/auth/me", get(auth::me))
        // Overview
        .route("/api/admin/overview", get(overview::overview))
        // Users
        .route("/api/admin/users", get(users::list_users))
        .route("/api/admin/users/{user_id}", get(users::get_user))
        .route("/api/admin/users/batch-delete", post(users::batch_delete_users))
        .route("/api/admin/users/{user_id}/block", post(users::block_user))
        .route("/api/admin/users/{user_id}/unblock", post(users::unblock_user))
        .route("/api/admin/users/{user_id}/grant-admin", post(users::grant_admin))
        .route("/api/admin/users/{user_id}/revoke-admin", post(users::revoke_admin))
        // Scenes
        .route("/api/admin/public-scenes", get(scenes::list_public_scenes).post(scenes::create_scene))
        .route("/api/admin/public-scenes/batch-delete", post(scenes::batch_delete_scenes))
        .route("/api/admin/public-scenes/batch-visibility", post(scenes::batch_visibility))
        .route("/api/admin/public-scenes/batch-free", post(scenes::batch_free))
        .route("/api/admin/public-scenes/batch-category", post(scenes::batch_category))
        .route("/api/admin/public-scenes/{scene_id}", put(scenes::update_scene))
        .route("/api/admin/public-scenes/{scene_id}/republish", post(scenes::republish_scene))
        .route("/api/admin/generated-scenes", get(scenes::list_generated_scenes))
        .route("/api/admin/generated-scenes/{scene_id}/publish", post(scenes::publish_draft))
        // Tasks
        .route("/api/admin/tasks", get(tasks::list_tasks))
        .route("/api/admin/tasks/batch-delete", post(tasks::batch_delete_tasks))
        .route("/api/admin/tasks/scene-generate-batch", post(tasks::scene_generate_batch))
        .route("/api/admin/tasks/{task_id}", get(tasks::get_task))
        .route("/api/admin/tasks/{task_id}/retry", post(tasks::retry_task))
        // Products
        .route("/api/admin/products", get(products::list_products).post(products::create_product))
        .route("/api/admin/products/{product_id}", get(products::get_product).put(products::update_product))
        .route("/api/admin/products/{product_id}/publish", post(products::publish_product))
        .route("/api/admin/products/{product_id}/disable", post(products::disable_product))
        .route("/api/admin/products/skus", get(products::list_skus))
        .route("/api/admin/skus", get(products::list_skus).post(products::create_sku))
        .route("/api/admin/skus/{sku_id}", put(products::update_sku))
        // Orders
        .route("/api/admin/orders", get(orders::list_orders))
        .route("/api/admin/orders/batch-delete", post(orders::batch_delete_orders))
        .route("/api/admin/orders/{order_id}", get(orders::get_order))
        // Catalog
        .route("/api/admin/scene-categories", get(catalog::list_categories).post(catalog::create_category))
        .route("/api/admin/scene-categories/{category_id}", put(catalog::update_category).delete(catalog::delete_category))
        .route("/api/admin/scene-collections", get(catalog::list_collections).post(catalog::create_collection))
        .route("/api/admin/scene-collections/{collection_id}", put(catalog::update_collection).delete(catalog::delete_collection))
        // CDK
        .route("/api/admin/cdk-codes", get(cdk::list_cdk_codes))
        .route("/api/admin/cdk-codes/batch-delete", post(cdk::batch_delete_cdk_codes))
        .route("/api/admin/cdk-codes/generate", post(cdk::generate_cdk_codes))
        // Uploads
        .route("/api/admin/uploads/image", post(uploads::upload_image))
        // Storage
        .route("/api/admin/storage/overview", get(storage::storage_overview))
        .route("/api/admin/storage/configs", get(storage::storage_configs))
        .route("/api/admin/storage/configs/{backend_id}", put(storage::storage_update_config))
        .route("/api/admin/storage/test/{backend_id}", post(storage::storage_test_connection))
        .route("/api/admin/storage/activate/{backend_id}", post(storage::storage_activate))
        .route("/api/admin/storage/usage", get(storage::storage_usage))
        // Scene generation logs
        .route("/api/admin/scene-logs", get(scene_logs::list_scene_logs))
        .route("/api/admin/scene-logs/{filename}", get(scene_logs::get_scene_log))
        // Admin page
        .route("/admin", get(serve_admin_index))
        .route("/admin/", get(serve_admin_index))
}

async fn serve_admin_index(
    axum::extract::State(state): axum::extract::State<AppState>,
) -> Result<axum::response::Html<String>, AppError> {
    if !state.config.admin_dashboard_enabled {
        return Err(AppError::Forbidden("admin dashboard disabled".into()));
    }
    let path = std::path::Path::new(&state.config.admin_web_dir).join("index.html");
    let content = tokio::fs::read_to_string(&path)
        .await
        .map_err(|_| AppError::NotFound("admin page not found".into()))?;
    Ok(axum::response::Html(content))
}

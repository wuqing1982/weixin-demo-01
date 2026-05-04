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
    let assets_dir = state.config.assets_dir.clone();
    let app = api::routes()
        .layer(cors)
        .nest_service("/assets", tower_http::services::ServeDir::new(&assets_dir))
        .with_state(state);

    let addr = format!("0.0.0.0:{port}");
    tracing::info!("Server starting on {}", addr);

    let listener = tokio::net::TcpListener::bind(&addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}

mod api;

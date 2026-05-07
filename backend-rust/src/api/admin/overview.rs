use axum::extract::State;
use axum::Json;
use serde_json::{json, Value};

use crate::error::AppError;
use crate::middleware::auth::AdminUser;
use crate::response;
use crate::state::AppState;

pub async fn overview(
    State(state): State<AppState>,
    _admin: AdminUser,
) -> Result<Json<Value>, AppError> {
    let user_count = crate::db::users::count_users(&state.pool)
        .await
        .unwrap_or(0);

    // Scene counts
    let public_scene_count: i64 = sqlx::query_as::<_, (i64,)>(
        "SELECT count(*) FROM scenes WHERE scene_type = 'public'",
    )
    .fetch_one(&state.pool)
    .await
    .unwrap_or((0,))
    .0;

    let generated_scene_count: i64 = sqlx::query_as::<_, (i64,)>(
        "SELECT count(*) FROM scenes WHERE scene_type != 'public'",
    )
    .fetch_one(&state.pool)
    .await
    .unwrap_or((0,))
    .0;

    // Order counts
    let order_count: i64 =
        sqlx::query_as::<_, (i64,)>("SELECT count(*) FROM orders")
            .fetch_one(&state.pool)
            .await
            .unwrap_or((0,))
            .0;

    let paid_order_count: i64 = sqlx::query_as::<_, (i64,)>(
        "SELECT count(*) FROM orders WHERE payment_status = 'paid'",
    )
    .fetch_one(&state.pool)
    .await
    .unwrap_or((0,))
    .0;

    // Total paid amount
    let total_paid_amount: String = sqlx::query_as::<_, (Option<rust_decimal::Decimal>,)>(
        "SELECT sum(paid_amount) FROM orders WHERE payment_status = 'paid'",
    )
    .fetch_one(&state.pool)
    .await
    .unwrap_or((None,))
    .0
    .map(|d| d.to_string())
    .unwrap_or_else(|| "0.00".into());

    // Product counts
    let product_count: i64 =
        sqlx::query_as::<_, (i64,)>("SELECT count(*) FROM products")
            .fetch_one(&state.pool)
            .await
            .unwrap_or((0,))
            .0;

    let active_product_count: i64 = sqlx::query_as::<_, (i64,)>(
        "SELECT count(*) FROM products WHERE status = 'active'",
    )
    .fetch_one(&state.pool)
    .await
    .unwrap_or((0,))
    .0;

    // Task stats
    let tasks = crate::db::tasks::list_all_tasks(&state.pool, 500).await.unwrap_or_default();

    let queued_count = tasks.iter().filter(|t| t.status == "queued").count();
    let running_count = tasks.iter().filter(|t| t.status == "running").count();
    let failed_count = tasks.iter().filter(|t| t.status == "failed").count();
    let done_count = tasks.iter().filter(|t| t.status == "done").count();

    let today = chrono::Utc::now().format("%Y-%m-%d").to_string();
    let today_task_count = tasks
        .iter()
        .filter(|t| t.created_at.to_rfc3339().starts_with(&today))
        .count();

    Ok(response::success(json!({
        "userCount": user_count,
        "publicSceneCount": public_scene_count,
        "generatedSceneCount": generated_scene_count,
        "orderCount": order_count,
        "paidOrderCount": paid_order_count,
        "totalPaidAmount": total_paid_amount,
        "productCount": product_count,
        "activeProductCount": active_product_count,
        "taskStats": {
            "queued": queued_count,
            "running": running_count,
            "failed": failed_count,
            "done": done_count,
            "total": tasks.len(),
            "todayCount": today_task_count,
        },
    })))
}

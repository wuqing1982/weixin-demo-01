use axum::extract::{Path, Query, State};
use axum::Json;
use serde::Deserialize;
use serde_json::{json, Value};

use crate::error::AppError;
use crate::middleware::auth::AdminUser;
use crate::response;
use crate::state::AppState;

#[derive(Deserialize)]
pub struct LimitQuery {
    pub limit: Option<i64>,
}

pub async fn list_orders(
    State(state): State<AppState>,
    _admin: AdminUser,
    Query(q): Query<LimitQuery>,
) -> Result<Json<Value>, AppError> {
    let limit = q.limit.unwrap_or(50);
    let orders = crate::db::orders::list_all_orders(&state.pool, limit).await?;
    let orders_json = serde_json::to_value(&orders).map_err(|e| AppError::Internal(e.to_string()))?;
    Ok(response::success(json!({ "list": orders_json })))
}

pub async fn get_order(
    State(state): State<AppState>,
    _admin: AdminUser,
    Path(order_id): Path<String>,
) -> Result<Json<Value>, AppError> {
    let order = crate::db::orders::get_order_admin(&state.pool, &order_id)
        .await?
        .ok_or_else(|| AppError::NotFound("订单不存在".into()))?;

    let order_json = serde_json::to_value(&order).map_err(|e| AppError::Internal(e.to_string()))?;
    Ok(response::success(order_json))
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct BatchDeleteOrdersRequest {
    pub order_ids: Vec<String>,
}

pub async fn batch_delete_orders(
    State(state): State<AppState>,
    _admin: AdminUser,
    Json(body): Json<BatchDeleteOrdersRequest>,
) -> Result<Json<Value>, AppError> {
    if body.order_ids.is_empty() {
        return Ok(response::success(json!({"count": 0})));
    }
    let count = crate::db::orders::batch_delete_orders(&state.pool, &body.order_ids).await?;
    Ok(response::success(json!({"count": count})))
}

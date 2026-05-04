use axum::extract::{Query, State};
use axum::http::StatusCode;
use axum::Json;
use serde::Deserialize;
use serde_json::{json, Value};

use crate::error::AppError;
use crate::state::AppState;

#[derive(Debug, Deserialize)]
pub struct EchostrQuery {
    pub echostr: Option<String>,
    pub signature: Option<String>,
    pub timestamp: Option<String>,
    pub nonce: Option<String>,
}

/// GET /api/payments/virtual/notify — WeChat verification (echostr)
pub async fn virtual_notify_get(
    Query(params): Query<EchostrQuery>,
) -> Result<(StatusCode, String), AppError> {
    let echostr = params.echostr.unwrap_or_default();
    Ok((StatusCode::OK, echostr))
}

/// POST /api/payments/virtual/notify — xpay delivery notification
pub async fn virtual_notify_post(
    State(state): State<AppState>,
    body: String,
) -> Result<Json<Value>, AppError> {
    tracing::info!("virtual_pay notify received: {}", &body[..body.len().min(500)]);

    // Parse the notification to extract order_no
    let order_no = extract_field_from_xml(&body, "out_trade_no")
        .unwrap_or_else(|| "".to_string());

    if order_no.is_empty() {
        return Ok(Json(json!({"errcode": 0, "errmsg": "ok"})));
    }

    // Find and complete the order
    if let Some(order) = crate::db::orders::find_order_by_no(&state.pool, &order_no).await? {
        if order.status == "pending" {
            if let Some(payment) = crate::db::orders::get_pending_payment_for_order(&state.pool, &order.id).await? {
                let trade_no = format!("xpay_{order_no}");
                let payload = json!({"tradeState": "SUCCESS", "notifySource": "xpay_delivery_notify"});

                crate::db::orders::complete_payment(&state.pool, &payment.id, &trade_no, &payload).await?;

                // Grant benefits
                let items = sqlx::query_as::<_, crate::models::order::OrderItem>(
                    "SELECT * FROM order_items WHERE order_id = $1"
                )
                .bind(&order.id)
                .fetch_all(&state.pool)
                .await?;

                if let Some(item) = items.first() {
                    let benefits = crate::db::products::get_sku_with_benefits(&state.pool, &item.sku_id)
                        .await?
                        .map(|b| b.benefits)
                        .unwrap_or_default();

                    let sku = sqlx::query_as::<_, crate::models::product::ProductSku>(
                        "SELECT * FROM product_skus WHERE id = $1"
                    )
                    .bind(&item.sku_id)
                    .fetch_optional(&state.pool)
                    .await?;

                    let duration_days = sku.and_then(|s| s.duration_days).unwrap_or(365);

                    crate::db::credits::grant_sku_benefits(
                        &state.pool,
                        &order.user_id,
                        "order",
                        &order.id,
                        &benefits,
                        item.quantity,
                        duration_days,
                    )
                    .await?;
                }
            }
        }
    }

    Ok(Json(json!({"errcode": 0, "errmsg": "ok"})))
}

fn extract_field_from_xml(xml: &str, field: &str) -> Option<String> {
    let open = format!("<{field}>");
    let close = format!("</{field}>");
    let start = xml.find(&open)?;
    let end = xml.find(&close)?;
    Some(xml[start + open.len()..end].to_string())
}

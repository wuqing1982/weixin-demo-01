use axum::extract::{Query, State};
use axum::http::{HeaderMap, StatusCode};
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
    tracing::info!(
        "virtual_pay notify received: {}",
        &body[..body.len().min(500)]
    );

    let order_no = extract_field_from_xml(&body, "out_trade_no").unwrap_or_default();

    if order_no.is_empty() {
        return Ok(Json(json!({"errcode": 0, "errmsg": "ok"})));
    }

    if let Some(order) = crate::db::orders::find_order_by_no(&state.pool, &order_no).await? {
        if order.status == "pending" {
            if let Some(payment) =
                crate::db::orders::get_pending_payment_for_order(&state.pool, &order.id).await?
            {
                let trade_no = format!("xpay_{order_no}");
                let payload =
                    json!({"tradeState": "SUCCESS", "notifySource": "xpay_delivery_notify"});

                crate::db::orders::complete_payment(&state.pool, &payment.id, &trade_no, &payload)
                    .await?;

                let items = sqlx::query_as::<_, crate::models::order::OrderItem>(
                    "SELECT * FROM order_items WHERE order_id = $1",
                )
                .bind(&order.id)
                .fetch_all(&state.pool)
                .await?;

                if let Some(item) = items.first() {
                    let benefits = crate::db::products::get_sku_with_benefits(
                        &state.pool,
                        &item.sku_id,
                    )
                    .await?
                    .map(|b| b.benefits)
                    .unwrap_or_default();

                    let sku = sqlx::query_as::<_, crate::models::product::ProductSku>(
                        "SELECT * FROM product_skus WHERE id = $1",
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

/// POST /api/payments/wechat/notify — WeChat Pay V3 callback
pub async fn wechat_pay_notify(
    State(state): State<AppState>,
    _headers: HeaderMap,
    body: String,
) -> Result<Json<Value>, AppError> {
    tracing::info!("wechat pay notify received, content-length: {}", body.len());

    // In mock mode, parse the body as JSON and process directly
    if state.config.payment_mode == "mock" {
        let notify_data: Value = serde_json::from_str(&body).unwrap_or_else(|_| json!({}));
        let order_no = notify_data["out_trade_no"]
            .as_str()
            .unwrap_or("")
            .to_string();

        if order_no.is_empty() {
            return Ok(Json(json!({"code": "SUCCESS", "message": "成功"})));
        }

        if let Some(order) = crate::db::orders::find_order_by_no(&state.pool, &order_no).await? {
            if order.status == "pending" {
                if let Some(payment) =
                    crate::db::orders::get_pending_payment_for_order(&state.pool, &order.id).await?
                {
                    let trade_no = notify_data["transaction_id"]
                        .as_str()
                        .unwrap_or("mock_txn")
                        .to_string();
                    let payload = json!({
                        "paymentMode": "wechat_pay",
                        "tradeState": "SUCCESS",
                        "wechatNotify": notify_data,
                    });

                    crate::db::orders::complete_payment(
                        &state.pool,
                        &payment.id,
                        &trade_no,
                        &payload,
                    )
                    .await?;

                    let items = sqlx::query_as::<_, crate::models::order::OrderItem>(
                        "SELECT * FROM order_items WHERE order_id = $1",
                    )
                    .bind(&order.id)
                    .fetch_all(&state.pool)
                    .await?;

                    if let Some(item) = items.first() {
                        let benefits = crate::db::products::get_sku_with_benefits(
                            &state.pool,
                            &item.sku_id,
                        )
                        .await?
                        .map(|b| b.benefits)
                        .unwrap_or_default();

                        let sku = sqlx::query_as::<_, crate::models::product::ProductSku>(
                            "SELECT * FROM product_skus WHERE id = $1",
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

        return Ok(Json(json!({"code": "SUCCESS", "message": "成功"})));
    }

    // TODO: For wechat_pay mode, implement V3 signature verification + AES-GCM decryption
    tracing::warn!("wechat_pay mode not fully implemented for notify callback");
    Ok(Json(json!({"code": "SUCCESS", "message": "成功"})))
}

fn extract_field_from_xml(xml: &str, field: &str) -> Option<String> {
    let open = format!("<{field}>");
    let close = format!("</{field}>");
    let start = xml.find(&open)?;
    let end = xml.find(&close)?;
    Some(xml[start + open.len()..end].to_string())
}

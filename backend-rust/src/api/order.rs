use axum::extract::{Path, State};
use axum::Json;
use serde_json::{json, Value};

use crate::db;
use crate::error::AppError;
use crate::middleware::auth::AuthUser;
use crate::models::order::*;
use crate::response;
use crate::services::{virtual_pay, wechat_auth, wechat_session};
use crate::state::AppState;

pub async fn create_order(
    State(state): State<AppState>,
    auth: AuthUser,
    Json(body): Json<CreateOrderRequest>,
) -> Result<Json<Value>, AppError> {
    let quantity = body.quantity.unwrap_or(1).clamp(1, 99);
    let sku_id = &body.sku_id;

    // Get SKU + benefits
    let sku_bundle = db::products::get_sku_with_benefits(&state.pool, sku_id)
        .await?
        .ok_or_else(|| AppError::BadRequest("SKU 不存在".into()))?;

    if sku_bundle.sku.status != "active" {
        return Err(AppError::BadRequest("SKU 不可用".into()));
    }

    // Validate tier purchase (no downgrade)
    if let Some(mb) = sku_bundle.benefits.iter().find(|b| b.benefit_type == "membership") {
        let target_tier = mb.benefit_value.as_deref().unwrap_or("");
        let membership = db::credits::get_membership_summary(&state.pool, &auth.user_id).await?;
        if membership.is_active && !membership.entitlement_code.is_empty() {
            let current_rank = tier_rank(&membership.entitlement_code);
            let target_rank = tier_rank(target_tier);
            if target_rank > 0 && current_rank > target_rank {
                return Err(AppError::BadRequest("不能降级会员".into()));
            }
        }
    }

    let order_id = format!("ord_{}", uuid::Uuid::new_v4());
    let ts = chrono::Utc::now().format("%Y%m%d%H%M%S").to_string();
    let rand_hex: String = (0..6).map(|_| format!("{:x}", rand::random::<u8>() % 16)).collect();
    let order_no = format!("ORD{ts}{rand_hex}");

    let product_id = &sku_bundle.sku.product_id;
    let product_name = get_product_name(&state.pool, product_id).await?;
    let sku_name = &sku_bundle.sku.name;
    let unit_price = sku_bundle.sku.sale_price;
    let total_price = unit_price * rust_decimal::Decimal::from(quantity);
    let currency = &sku_bundle.sku.currency;

    let benefit_snapshot = json!(sku_bundle.benefits.iter().map(|b| json!({
        "benefitType": b.benefit_type,
        "benefitValue": b.benefit_value,
        "benefitJson": b.benefit_json,
    })).collect::<Vec<_>>());

    let item_id = format!("oi_{}", uuid::Uuid::new_v4());

    let order = db::orders::create_order(
        &state.pool,
        &order_id,
        &order_no,
        &auth.user_id,
        sku_id,
        product_id,
        &product_name,
        sku_name,
        quantity,
        unit_price,
        total_price,
        currency,
        &benefit_snapshot,
        &item_id,
    )
    .await?;

    Ok(response::success(order))
}

pub async fn list_orders(
    State(state): State<AppState>,
    auth: AuthUser,
) -> Result<Json<Value>, AppError> {
    let orders = db::orders::list_orders(&state.pool, &auth.user_id).await?;
    Ok(response::success(json!({ "list": orders })))
}

pub async fn get_order(
    State(state): State<AppState>,
    auth: AuthUser,
    Path(order_id): Path<String>,
) -> Result<Json<Value>, AppError> {
    let order = db::orders::get_order(&state.pool, &order_id, &auth.user_id)
        .await?
        .ok_or_else(|| AppError::NotFound("订单不存在".into()))?;
    Ok(response::success(order))
}

pub async fn pay_order(
    State(state): State<AppState>,
    auth: AuthUser,
    Path(order_id): Path<String>,
    Json(body): Json<PayOrderRequest>,
) -> Result<Json<Value>, AppError> {
    let order_detail = db::orders::get_order(&state.pool, &order_id, &auth.user_id)
        .await?
        .ok_or_else(|| AppError::NotFound("订单不存在".into()))?;

    if order_detail.order.status == "paid" {
        return Ok(response::success(json!({
            "paymentMode": state.config.payment_mode,
            "orderId": order_id,
            "order": order_detail,
            "alreadyPaid": true,
        })));
    }

    if order_detail.order.status != "pending" {
        return Err(AppError::BadRequest("订单状态不允许支付".into()));
    }

    let payment_id = format!("pay_{}", uuid::Uuid::new_v4());
    let ts = chrono::Utc::now().format("%Y%m%d%H%M%S").to_string();
    let rand_hex: String = (0..6).map(|_| format!("{:x}", rand::random::<u8>() % 16)).collect();
    let payment_no = format!("PAY{ts}{rand_hex}");

    let _payment = db::orders::create_payment(
        &state.pool,
        &payment_id,
        &payment_no,
        &order_detail.order.id,
        &auth.user_id,
        &state.config.payment_mode,
        order_detail.order.payable_amount,
        None,
    )
    .await?;

    let payment_mode = state.config.payment_mode.as_str();

    match payment_mode {
        "mock" => {
            let mock_params = json!({
                "timeStamp": format!("{}", chrono::Utc::now().timestamp()),
                "nonceStr": uuid::Uuid::new_v4().to_string(),
                "package": "prepay_id=mock_prepay_id",
                "signType": "MD5",
                "paySign": "mock_sign",
            });

            let payload = json!({"mock": true, "paymentNo": payment_no});
            db::orders::update_payment_payload(&state.pool, &payment_id, &payload).await?;

            // Refresh order detail
            let order = db::orders::get_order(&state.pool, &order_id, &auth.user_id)
                .await?
                .ok_or_else(|| AppError::NotFound("订单不存在".into()))?;

            Ok(response::success(json!({
                "paymentMode": "mock",
                "paymentId": payment_id,
                "orderId": order_id,
                "order": order,
                "alreadyPaid": false,
                "requestPayment": mock_params,
            })))
        }
        "virtual_pay" => {
            // Resolve session_key: prefer fresh wx_code, fall back to stored
            let identities = db::users::find_user_identities(&state.pool, &auth.user_id).await?;
            let wechat_identity = identities.iter().find(|i| i.provider == "wechat");

            let session_key = if let Some(code) = &body.wx_code {
                // Fresh login: call code2session to get a valid session_key
                let result = wechat_auth::code2session(
                    &state.config.wechat_mp_app_id,
                    &state.config.wechat_mp_app_secret,
                    code,
                ).await.map_err(|e| AppError::Internal(format!("code2session failed: {e}")))?;

                // Update stored session_key
                if let Some(identity) = wechat_identity {
                    let secret = state.config.wechat_session_key_secret.as_deref()
                        .unwrap_or(&state.config.auth_jwt_secret);
                    let encrypted = wechat_session::encrypt_session_key(secret, &result.session_key);
                    db::users::update_identity_session_key(&state.pool, &identity.id, &encrypted).await?;
                }
                result.session_key
            } else {
                // Fallback: use stored session_key
                let session_key_encrypted = wechat_identity
                    .and_then(|i| i.session_key_encrypted.as_ref());

                match session_key_encrypted {
                    Some(encrypted) if !encrypted.is_empty() => {
                        let secret = state.config.wechat_session_key_secret.as_deref()
                            .unwrap_or(&state.config.auth_jwt_secret);
                        wechat_session::decrypt_session_key(secret, encrypted)
                            .map_err(|e| AppError::Internal(e))?
                    }
                    _ => return Err(AppError::BadRequest("缺少 session_key，请重新登录".into())),
                }
            };

            // Map sku_id to virtual product ID
            let sku_id_str = order_detail.items.first().map(|i| i.sku_id.as_str()).unwrap_or("");
            let virtual_product_id = map_sku_to_virtual_product(sku_id_str);
            let fen_decimal = (order_detail.order.payable_amount * rust_decimal::Decimal::from(100)).round();
            let price_fen = fen_decimal.mantissa() as i64 / 10i64.pow(fen_decimal.scale() as u32);

            let params = virtual_pay::build_virtual_payment_params(
                &state.config.wx_virtual_pay_offer_id,
                state.config.wx_virtual_pay_env as i32,
                &order_detail.order.order_no,
                virtual_product_id,
                price_fen,
                &session_key,
                &state.config.wx_virtual_pay_app_key,
                order_detail.items.first().map(|i| i.quantity).unwrap_or(1),
                &order_detail.order.order_no,
            );

            let payload = json!({
                "virtualPay": true,
                "paymentNo": payment_no,
                "params": params,
            });
            db::orders::update_payment_payload(&state.pool, &payment_id, &payload).await?;

            let order = db::orders::get_order(&state.pool, &order_id, &auth.user_id)
                .await?
                .ok_or_else(|| AppError::NotFound("订单不存在".into()))?;

            Ok(response::success(json!({
                "paymentMode": "virtual_pay",
                "paymentId": payment_id,
                "orderId": order_id,
                "order": order,
                "alreadyPaid": false,
                "requestPayment": params,
            })))
        }
        _ => Err(AppError::BadRequest(format!("不支持的支付模式: {payment_mode}"))),
    }
}

pub async fn mock_pay_success(
    State(state): State<AppState>,
    auth: AuthUser,
    Path(order_id): Path<String>,
    Json(body): Json<MockPayRequest>,
) -> Result<Json<Value>, AppError> {
    let order_detail = db::orders::get_order(&state.pool, &order_id, &auth.user_id)
        .await?
        .ok_or_else(|| AppError::NotFound("订单不存在".into()))?;

    if order_detail.order.status == "paid" {
        return Ok(response::success(json!({ "order": order_detail, "me": null })));
    }

    // Find pending payment
    let payment = if let Some(ref pid) = body.payment_id {
        db::orders::get_pending_payment_for_order(&state.pool, &order_id)
            .await?
            .filter(|p| p.id == *pid)
    } else {
        db::orders::get_pending_payment_for_order(&state.pool, &order_id).await?
    }
    .ok_or_else(|| AppError::BadRequest("没有待支付记录".into()))?;

    let trade_no = format!("mock_{}", uuid::Uuid::new_v4());
    let payload = json!({"tradeState": "SUCCESS", "mockPay": true});

    db::orders::complete_payment(&state.pool, &payment.id, &trade_no, &payload).await?;

    // Grant benefits
    let order = db::orders::get_order(&state.pool, &order_id, &auth.user_id)
        .await?
        .ok_or_else(|| AppError::NotFound("订单不存在".into()))?;

    if let Some(item) = order.items.first() {
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

        db::credits::grant_sku_benefits(
            &state.pool,
            &auth.user_id,
            "order",
            &order_id,
            &benefits,
            item.quantity,
            duration_days,
        )
        .await?;
    }

    let final_order = db::orders::get_order(&state.pool, &order_id, &auth.user_id)
        .await?
        .ok_or_else(|| AppError::NotFound("订单不存在".into()))?;

    Ok(response::success(json!({ "order": final_order, "me": null })))
}

pub async fn payment_sync(
    State(state): State<AppState>,
    auth: AuthUser,
    Path(order_id): Path<String>,
) -> Result<Json<Value>, AppError> {
    let order_detail = db::orders::get_order(&state.pool, &order_id, &auth.user_id)
        .await?
        .ok_or_else(|| AppError::NotFound("订单不存在".into()))?;

    if order_detail.order.status == "paid" {
        return Ok(response::success(json!({
            "order": order_detail,
            "me": null,
            "tradeState": "SUCCESS",
        })));
    }

    // For virtual_pay, client-driven confirmation
    if state.config.payment_mode == "virtual_pay" {
        let trade_no = format!("virtual_pay_{}", order_detail.order.order_no);
        let payload = json!({"tradeState": "SUCCESS", "syncSource": "client_confirm"});

        if let Some(payment) = db::orders::get_pending_payment_for_order(&state.pool, &order_id).await? {
            db::orders::complete_payment(&state.pool, &payment.id, &trade_no, &payload).await?;

            // Grant benefits
            if let Some(item) = order_detail.items.first() {
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

                db::credits::grant_sku_benefits(
                    &state.pool,
                    &auth.user_id,
                    "order",
                    &order_id,
                    &benefits,
                    item.quantity,
                    duration_days,
                )
                .await?;
            }
        }

        let final_order = db::orders::get_order(&state.pool, &order_id, &auth.user_id)
            .await?
            .ok_or_else(|| AppError::NotFound("订单不存在".into()))?;

        return Ok(response::success(json!({
            "order": final_order,
            "me": null,
            "tradeState": "SUCCESS",
        })));
    }

    Err(AppError::BadRequest("支付状态同步失败".into()))
}

fn map_sku_to_virtual_product(sku_id: &str) -> &str {
    match sku_id {
        s if s.contains("tier_pro") => "sku_pro_yearly",
        s if s.contains("tier_plus") => "sku_plus_yearly",
        s if s.contains("tier_max") => "sku_max_yearly",
        _ => sku_id,
    }
}

async fn get_product_name(pool: &sqlx::PgPool, product_id: &str) -> Result<String, AppError> {
    let product = db::products::get_product(pool, product_id).await?;
    Ok(product.map(|p| p.name).unwrap_or_default())
}

fn tier_rank(tier: &str) -> i32 {
    match tier {
        "pro" => 1,
        "plus" => 2,
        "max" => 3,
        _ => 0,
    }
}

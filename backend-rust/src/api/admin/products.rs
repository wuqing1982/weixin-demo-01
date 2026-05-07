use axum::extract::{Path, State};
use axum::Json;
use serde::Deserialize;
use serde_json::{json, Value};

use crate::error::AppError;
use crate::middleware::auth::AdminUser;
use crate::response;
use crate::state::AppState;

pub async fn list_products(
    State(state): State<AppState>,
    _admin: AdminUser,
) -> Result<Json<Value>, AppError> {
    let products = crate::db::products::list_all_products(&state.pool).await?;

    let mut list = Vec::with_capacity(products.len());
    for product in products {
        let skus = crate::db::products::list_product_skus(&state.pool, &product.id).await?;
        let product_json = serde_json::to_value(&product).map_err(|e| AppError::Internal(e.to_string()))?;
        let skus_json = serde_json::to_value(&skus).map_err(|e| AppError::Internal(e.to_string()))?;

        let mut obj = product_json.as_object().cloned().unwrap_or_default();
        obj.insert("skus".to_string(), skus_json);
        list.push(Value::Object(obj));
    }

    Ok(response::success(json!({ "list": list })))
}

pub async fn get_product(
    State(state): State<AppState>,
    _admin: AdminUser,
    Path(product_id): Path<String>,
) -> Result<Json<Value>, AppError> {
    let product = crate::db::products::get_product(&state.pool, &product_id)
        .await?
        .ok_or_else(|| AppError::NotFound("商品不存在".into()))?;

    let skus = crate::db::products::list_product_skus(&state.pool, &product.id).await?;

    let product_json = serde_json::to_value(&product).map_err(|e| AppError::Internal(e.to_string()))?;
    let skus_json = serde_json::to_value(&skus).map_err(|e| AppError::Internal(e.to_string()))?;

    let mut obj = product_json.as_object().cloned().unwrap_or_default();
    obj.insert("skus".to_string(), skus_json);

    Ok(response::success(Value::Object(obj)))
}

pub async fn list_skus(
    State(state): State<AppState>,
    _admin: AdminUser,
) -> Result<Json<Value>, AppError> {
    let skus = crate::db::products::list_all_product_skus(&state.pool).await?;
    let skus_json = serde_json::to_value(&skus).map_err(|e| AppError::Internal(e.to_string()))?;
    Ok(response::success(json!({ "list": skus_json })))
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ProductUpsertRequest {
    pub product_code: Option<String>,
    pub product_type: Option<String>,
    pub name: String,
    pub subtitle: Option<String>,
    pub description: Option<String>,
    pub status: Option<String>,
    pub cover_url: Option<String>,
    pub sort_order: Option<i32>,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SkuUpsertRequest {
    pub product_id: Option<String>,
    pub sku_code: Option<String>,
    pub name: Option<String>,
    pub billing_type: Option<String>,
    pub duration_days: Option<i32>,
    pub status: Option<String>,
    pub list_price: Option<String>,
    pub sale_price: Option<String>,
    pub currency: Option<String>,
    pub stock_type: Option<String>,
    pub stock_count: Option<i32>,
    pub sort_order: Option<i32>,
    pub benefits: Option<serde_json::Value>,
}

pub async fn create_product(
    State(state): State<AppState>,
    _admin: AdminUser,
    Json(body): Json<ProductUpsertRequest>,
) -> Result<Json<Value>, AppError> {
    let id = format!("product_{}", uuid::Uuid::new_v4());
    let product = crate::db::products::upsert_product(
        &state.pool, &id,
        &body.product_code.unwrap_or_default(),
        &body.product_type.unwrap_or_else(|| "membership".into()),
        &body.name,
        body.subtitle.as_deref(),
        body.description.as_deref(),
        &body.status.unwrap_or_else(|| "draft".into()),
        body.cover_url.as_deref(),
        body.sort_order.unwrap_or(0),
    ).await?;
    Ok(response::success(serde_json::to_value(&product).unwrap_or_default()))
}

pub async fn update_product(
    State(state): State<AppState>,
    _admin: AdminUser,
    Path(product_id): Path<String>,
    Json(body): Json<ProductUpsertRequest>,
) -> Result<Json<Value>, AppError> {
    let product = crate::db::products::upsert_product(
        &state.pool, &product_id,
        &body.product_code.unwrap_or_default(),
        &body.product_type.unwrap_or_else(|| "membership".into()),
        &body.name,
        body.subtitle.as_deref(),
        body.description.as_deref(),
        &body.status.unwrap_or_else(|| "draft".into()),
        body.cover_url.as_deref(),
        body.sort_order.unwrap_or(0),
    ).await?;
    Ok(response::success(serde_json::to_value(&product).unwrap_or_default()))
}

pub async fn publish_product(
    State(state): State<AppState>,
    _admin: AdminUser,
    Path(product_id): Path<String>,
) -> Result<Json<Value>, AppError> {
    crate::db::products::update_product_status(&state.pool, &product_id, "active").await?;
    Ok(response::success(json!({})))
}

pub async fn disable_product(
    State(state): State<AppState>,
    _admin: AdminUser,
    Path(product_id): Path<String>,
) -> Result<Json<Value>, AppError> {
    crate::db::products::update_product_status(&state.pool, &product_id, "disabled").await?;
    Ok(response::success(json!({})))
}

pub async fn create_sku(
    State(state): State<AppState>,
    _admin: AdminUser,
    Json(body): Json<SkuUpsertRequest>,
) -> Result<Json<Value>, AppError> {
    let id = format!("sku_{}", uuid::Uuid::new_v4());
    let list_price: rust_decimal::Decimal = body.list_price.as_deref().unwrap_or("0").parse().unwrap_or(rust_decimal::Decimal::ZERO);
    let sale_price: rust_decimal::Decimal = body.sale_price.as_deref().unwrap_or("0").parse().unwrap_or(rust_decimal::Decimal::ZERO);
    let sku = crate::db::products::upsert_sku(
        &state.pool, &id,
        &body.sku_code.unwrap_or_default(),
        &body.product_id.unwrap_or_default(),
        &body.name.unwrap_or_default(),
        &body.billing_type.unwrap_or_else(|| "recurring".into()),
        body.duration_days,
        &body.status.unwrap_or_else(|| "active".into()),
        list_price, sale_price,
        &body.currency.unwrap_or_else(|| "CNY".into()),
        &body.stock_type.unwrap_or_else(|| "unlimited".into()),
        body.stock_count,
        body.sort_order.unwrap_or(0),
    ).await?;
    if let Some(benefits) = &body.benefits {
        if let Some(arr) = benefits.as_array() {
            crate::db::products::replace_sku_benefits(&state.pool, &id, arr).await?;
        }
    }
    Ok(response::success(serde_json::to_value(&sku).unwrap_or_default()))
}

pub async fn update_sku(
    State(state): State<AppState>,
    _admin: AdminUser,
    Path(sku_id): Path<String>,
    Json(body): Json<SkuUpsertRequest>,
) -> Result<Json<Value>, AppError> {
    let list_price: rust_decimal::Decimal = body.list_price.as_deref().unwrap_or("0").parse().unwrap_or(rust_decimal::Decimal::ZERO);
    let sale_price: rust_decimal::Decimal = body.sale_price.as_deref().unwrap_or("0").parse().unwrap_or(rust_decimal::Decimal::ZERO);
    let sku = crate::db::products::upsert_sku(
        &state.pool, &sku_id,
        &body.sku_code.unwrap_or_default(),
        &body.product_id.unwrap_or_default(),
        &body.name.unwrap_or_default(),
        &body.billing_type.unwrap_or_else(|| "recurring".into()),
        body.duration_days,
        &body.status.unwrap_or_else(|| "active".into()),
        list_price, sale_price,
        &body.currency.unwrap_or_else(|| "CNY".into()),
        &body.stock_type.unwrap_or_else(|| "unlimited".into()),
        body.stock_count,
        body.sort_order.unwrap_or(0),
    ).await?;
    if let Some(benefits) = &body.benefits {
        if let Some(arr) = benefits.as_array() {
            crate::db::products::replace_sku_benefits(&state.pool, &sku_id, arr).await?;
        }
    }
    Ok(response::success(serde_json::to_value(&sku).unwrap_or_default()))
}

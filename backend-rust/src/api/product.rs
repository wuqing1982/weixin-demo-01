use axum::extract::{Path, Query, State};
use axum::Json;
use serde::Deserialize;
use serde_json::{json, Value};

use crate::error::AppError;
use crate::models::product::ProductList;
use crate::response;
use crate::state::AppState;

#[derive(Debug, Deserialize)]
pub struct ProductQuery {
    pub product_type: Option<String>,
}

pub async fn list_products(
    State(state): State<AppState>,
    Query(params): Query<ProductQuery>,
) -> Result<Json<Value>, AppError> {
    let product_type = params.product_type.unwrap_or_default();
    let products = crate::db::products::list_products(&state.pool, &product_type).await?;
    Ok(response::success(ProductList { list: products }))
}

pub async fn get_product(
    State(state): State<AppState>,
    Path(product_id): Path<String>,
) -> Result<Json<Value>, AppError> {
    let product = crate::db::products::get_product(&state.pool, &product_id)
        .await?
        .ok_or_else(|| AppError::NotFound("产品不存在".into()))?;
    Ok(response::success(product))
}

pub async fn list_product_skus(
    State(state): State<AppState>,
    Path(product_id): Path<String>,
) -> Result<Json<Value>, AppError> {
    let skus = crate::db::products::list_product_skus(&state.pool, &product_id).await?;
    Ok(response::success(json!({ "list": skus })))
}

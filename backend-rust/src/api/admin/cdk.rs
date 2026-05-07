use axum::extract::{Query, State};
use axum::Json;
use serde::Deserialize;
use serde_json::{json, Value};

use crate::error::AppError;
use crate::middleware::auth::AdminUser;
use crate::response;
use crate::state::AppState;

#[derive(Deserialize)]
pub struct CdkQuery {
    pub status: Option<String>,
    pub sku_id: Option<String>,
    pub limit: Option<i64>,
    pub offset: Option<i64>,
}

pub async fn list_cdk_codes(
    State(state): State<AppState>,
    _admin: AdminUser,
    Query(q): Query<CdkQuery>,
) -> Result<Json<Value>, AppError> {
    let status = q.status.unwrap_or_default();
    let sku_id = q.sku_id.unwrap_or_default();
    let limit = q.limit.unwrap_or(50);
    let offset = q.offset.unwrap_or(0);

    let codes = crate::db::credits::list_cdk_codes_admin(&state.pool, &status, &sku_id, limit, offset)
        .await
        .unwrap_or_default();

    let list: Vec<Value> = codes
        .into_iter()
        .map(|cdk| {
            json!({
                "cdkId": cdk.id,
                "code": cdk.code,
                "skuId": cdk.sku_id,
                "status": cdk.status,
                "batchId": cdk.batch_id,
                "redeemedBy": cdk.redeemed_by,
                "redeemedAt": cdk.redeemed_at.map(|t| t.to_rfc3339()),
                "note": cdk.note,
                "createdAt": cdk.created_at.to_rfc3339(),
                "updatedAt": cdk.updated_at.to_rfc3339(),
            })
        })
        .collect();

    Ok(response::success(json!({ "list": list })))
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct BatchDeleteCdkRequest {
    pub cdk_ids: Vec<String>,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct GenerateCdkRequest {
    pub sku_id: String,
    pub quantity: i32,
    pub note: Option<String>,
}

pub async fn batch_delete_cdk_codes(
    State(state): State<AppState>,
    _admin: AdminUser,
    Json(body): Json<BatchDeleteCdkRequest>,
) -> Result<Json<Value>, AppError> {
    if body.cdk_ids.is_empty() {
        return Ok(response::success(json!({"count": 0})));
    }
    let count = crate::db::credits::batch_delete_cdk_codes(&state.pool, &body.cdk_ids).await?;
    Ok(response::success(json!({"count": count})))
}

pub async fn generate_cdk_codes(
    State(state): State<AppState>,
    _admin: AdminUser,
    Json(body): Json<GenerateCdkRequest>,
) -> Result<Json<Value>, AppError> {
    if body.quantity <= 0 || body.quantity > 100 {
        return Err(AppError::BadRequest("数量须在 1-100 之间".into()));
    }
    let codes = crate::db::credits::generate_cdk_codes(
        &state.pool, &body.sku_id, body.quantity, body.note.as_deref(),
    ).await?;
    let list: Vec<Value> = codes.iter().map(|cdk| {
        json!({
            "cdkId": cdk.id,
            "code": cdk.code,
            "skuId": cdk.sku_id,
            "status": cdk.status,
            "batchId": cdk.batch_id,
            "note": cdk.note,
            "createdAt": cdk.created_at.to_rfc3339(),
        })
    }).collect();
    Ok(response::success(json!({"list": list})))
}

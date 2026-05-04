use axum::extract::State;
use axum::Json;
use serde_json::{json, Value};

use crate::db;
use crate::error::AppError;
use crate::middleware::auth::AuthUser;
use crate::models::commerce::*;
use crate::response;
use crate::state::AppState;

pub async fn redeem_cdk(
    State(state): State<AppState>,
    auth: AuthUser,
    Json(body): Json<CdkRedeemRequest>,
) -> Result<Json<Value>, AppError> {
    let code = body.code.trim().to_uppercase();
    if code.is_empty() {
        return Err(AppError::BadRequest("请输入兑换码".into()));
    }

    let result = db::credits::redeem_cdk(&state.pool, &code, &auth.user_id).await?;
    Ok(response::success(result))
}

pub async fn my_redemptions(
    State(state): State<AppState>,
    auth: AuthUser,
) -> Result<Json<Value>, AppError> {
    let list = db::credits::list_user_cdk_redemptions(&state.pool, &auth.user_id).await?;
    Ok(response::success(json!({ "list": list })))
}

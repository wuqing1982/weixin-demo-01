use axum::extract::{Query, State};
use axum::Json;
use serde::Deserialize;
use serde_json::{json, Value};
use sqlx::Row;

use crate::db::users;
use crate::error::AppError;
use crate::middleware::auth::AuthUser;
use crate::response::success;
use crate::state::AppState;

pub async fn get_me(
    State(state): State<AppState>,
    auth: AuthUser,
) -> Result<Json<Value>, AppError> {
    let user = users::find_user_by_id(&state.pool, &auth.user_id)
        .await?
        .ok_or_else(|| AppError::NotFound("user not found".into()))?;

    let profile = crate::models::user::UserProfile::from_user(&user, &auth.role);

    // Add memberSummary + creditSummary
    let member_summary = crate::db::credits::get_membership_summary(&state.pool, &auth.user_id).await?;
    let credit_summary = crate::db::credits::get_credit_summary(&state.pool, &auth.user_id).await?;

    Ok(success(json!({
        "userId": profile.user_id,
        "displayName": profile.display_name,
        "avatarUrl": profile.avatar_url,
        "role": profile.role,
        "status": profile.status,
        "mobile": profile.mobile,
        "mobileVerified": profile.mobile_verified,
        "createdAt": profile.created_at,
        "memberSummary": member_summary,
        "creditSummary": credit_summary,
    })))
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct UpdateProfileRequest {
    display_name: Option<String>,
    avatar_url: Option<String>,
}

pub async fn update_profile(
    State(state): State<AppState>,
    auth: AuthUser,
    Json(body): Json<UpdateProfileRequest>,
) -> Result<Json<Value>, AppError> {
    let user = users::update_user_profile(
        &state.pool,
        &auth.user_id,
        body.display_name.as_deref().unwrap_or(""),
        body.avatar_url.as_deref().unwrap_or(""),
    )
    .await?;

    let profile = crate::models::user::UserProfile::from_user(&user, &auth.role);
    Ok(success(json!(profile)))
}

pub async fn get_membership(
    State(state): State<AppState>,
    auth: AuthUser,
) -> Result<Json<Value>, AppError> {
    let row = sqlx::query_as::<_, (String, Option<chrono::DateTime<chrono::Utc>>, Option<chrono::DateTime<chrono::Utc>>)>(
        "SELECT entitlement_code, starts_at, expires_at FROM user_entitlements WHERE user_id = $1 AND entitlement_type = 'membership' AND status = 'active' ORDER BY expires_at DESC LIMIT 1"
    )
        .bind(&auth.user_id)
        .fetch_optional(&state.pool)
        .await?;

    let (tier, starts_at, expires_at) = match row {
        Some(r) => (r.0, r.1.map(|t| t.to_rfc3339()), r.2.map(|t| t.to_rfc3339())),
        None => ("free".to_string(), None, None),
    };

    Ok(success(json!({
        "tier": tier,
        "startsAt": starts_at,
        "expiresAt": expires_at,
    })))
}

pub async fn get_credits(
    State(state): State<AppState>,
    auth: AuthUser,
) -> Result<Json<Value>, AppError> {
    let rows = sqlx::query_as::<_, (String, i32)>(
        "SELECT credit_type, balance FROM user_credit_accounts WHERE user_id = $1"
    )
        .bind(&auth.user_id)
        .fetch_all(&state.pool)
        .await?;

    let credits: serde_json::Map<String, Value> = rows.into_iter()
        .map(|(k, v)| (k, json!(v)))
        .collect();

    Ok(success(json!(credits)))
}

pub async fn get_entitlements(
    State(state): State<AppState>,
    auth: AuthUser,
) -> Result<Json<Value>, AppError> {
    let rows = sqlx::query(
        "SELECT entitlement_code, entitlement_type, status, starts_at, expires_at FROM user_entitlements WHERE user_id = $1 AND status = 'active'"
    )
        .bind(&auth.user_id)
        .fetch_all(&state.pool)
        .await?;

    let codes: Vec<String> = rows.iter()
        .map(|r| r.try_get::<String, _>("entitlement_code").unwrap_or_default())
        .collect();

    Ok(success(json!({"entitlements": codes})))
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct UpgradePreviewQuery {
    pub sku_id: String,
}

pub async fn upgrade_preview(
    State(state): State<AppState>,
    auth: AuthUser,
    Query(params): Query<UpgradePreviewQuery>,
) -> Result<Json<Value>, AppError> {
    let sku_id = &params.sku_id;
    if sku_id.is_empty() {
        return Err(AppError::BadRequest("skuId 不能为空".into()));
    }

    let sku_bundle = crate::db::products::get_sku_with_benefits(&state.pool, sku_id)
        .await?
        .ok_or_else(|| AppError::BadRequest("SKU 不存在".into()))?;

    // Find membership benefit
    let membership_benefit = sku_bundle
        .benefits
        .iter()
        .find(|b| b.benefit_type == "membership")
        .ok_or_else(|| AppError::BadRequest("SKU 不包含会员权益".into()))?;

    let target_tier = membership_benefit.benefit_value.as_deref().unwrap_or("");
    let duration_days = sku_bundle.sku.duration_days.unwrap_or(365);

    let membership = crate::db::credits::get_membership_summary(&state.pool, &auth.user_id).await?;

    let (action, remaining_days, converted_days, new_expires_at) = if !membership.is_active || membership.entitlement_code.is_empty() {
        ("fresh".to_string(), 0i64, 0i64, chrono::Utc::now() + chrono::Duration::days(duration_days as i64))
    } else {
        let current_tier = membership.entitlement_code.as_str();
        let current_rank = tier_rank(current_tier);
        let target_rank = tier_rank(target_tier);

        if target_rank == current_rank {
            // Renewal
            let old_expires = membership.expires_at
                .and_then(|s| chrono::DateTime::parse_from_rfc3339(&s).ok())
                .map(|dt| dt.to_utc())
                .unwrap_or(chrono::Utc::now());
            let base = if old_expires < chrono::Utc::now() { chrono::Utc::now() } else { old_expires };
            let remaining = (old_expires - chrono::Utc::now()).num_days().max(0);
            ("renewal".to_string(), remaining, 0i64, base + chrono::Duration::days(duration_days as i64))
        } else if target_rank > current_rank {
            // Upgrade
            let old_expires = membership.expires_at
                .and_then(|s| chrono::DateTime::parse_from_rfc3339(&s).ok())
                .map(|dt| dt.to_utc())
                .unwrap_or(chrono::Utc::now());
            let remaining = (old_expires - chrono::Utc::now()).num_days().max(0);
            let old_price = tier_price(current_tier);
            let new_price = tier_price(target_tier);
            let converted = if new_price > 0.0 {
                (remaining as f64 * old_price / new_price) as i64
            } else {
                0
            };
            let final_days = converted + duration_days as i64;
            ("upgrade".to_string(), remaining, converted, chrono::Utc::now() + chrono::Duration::days(final_days))
        } else {
            ("blocked".to_string(), 0, 0, chrono::Utc::now())
        }
    };

    Ok(success(json!({
        "action": action,
        "currentTier": if membership.is_active { Some(membership.entitlement_code) } else { None::<String> },
        "targetTier": target_tier,
        "remainingDays": remaining_days,
        "convertedDays": converted_days,
        "newDurationDays": duration_days,
        "newExpiresAt": new_expires_at.to_rfc3339(),
    })))
}

fn tier_rank(tier: &str) -> i32 {
    match tier {
        "pro" => 1,
        "plus" => 2,
        "max" => 3,
        _ => 0,
    }
}

fn tier_price(tier: &str) -> f64 {
    match tier {
        "pro" => 39.90,
        "plus" => 99.00,
        "max" => 199.00,
        _ => 0.0,
    }
}

use sqlx::PgPool;

use crate::error::AppError;
use crate::models::commerce::*;

const SCENE_CREDIT_TYPE: &str = "scene_generation_credits";

pub async fn get_membership_summary(pool: &PgPool, user_id: &str) -> Result<MembershipSummary, AppError> {
    let row = sqlx::query_as::<_, UserEntitlement>(
        "SELECT * FROM user_entitlements \
         WHERE user_id = $1 AND entitlement_type = 'membership' AND status = 'active' \
         AND (expires_at IS NULL OR expires_at > now()) \
         ORDER BY expires_at DESC NULLS LAST LIMIT 1"
    )
    .bind(user_id)
    .fetch_optional(pool)
    .await?;

    Ok(match row {
        Some(e) => MembershipSummary {
            is_active: true,
            entitlement_code: e.entitlement_code,
            expires_at: e.expires_at.map(|t| t.to_rfc3339()),
        },
        None => MembershipSummary {
            is_active: false,
            entitlement_code: String::new(),
            expires_at: None,
        },
    })
}

pub async fn get_credit_summary(pool: &PgPool, user_id: &str) -> Result<CreditSummary, AppError> {
    let accounts = sqlx::query_as::<_, UserCreditAccount>(
        "SELECT * FROM user_credit_accounts WHERE user_id = $1 ORDER BY credit_type ASC"
    )
    .bind(user_id)
    .fetch_all(pool)
    .await?;

    let scene_balance = accounts
        .iter()
        .find(|a| a.credit_type == SCENE_CREDIT_TYPE)
        .map(|a| a.balance)
        .unwrap_or(0);

    Ok(CreditSummary {
        scene_generate_balance: scene_balance,
        accounts: accounts
            .into_iter()
            .map(|a| CreditAccountInfo {
                account_id: a.id,
                credit_type: a.credit_type,
                balance: a.balance,
                frozen_balance: a.frozen_balance,
                updated_at: a.updated_at.to_rfc3339(),
            })
            .collect(),
    })
}

pub async fn list_user_entitlements(
    pool: &PgPool,
    user_id: &str,
    entitlement_type: &str,
) -> Result<Vec<UserEntitlement>, AppError> {
    let rows = if entitlement_type.is_empty() {
        sqlx::query_as::<_, UserEntitlement>(
            "SELECT * FROM user_entitlements WHERE user_id = $1 ORDER BY created_at DESC"
        )
        .bind(user_id)
        .fetch_all(pool)
        .await?
    } else {
        sqlx::query_as::<_, UserEntitlement>(
            "SELECT * FROM user_entitlements WHERE user_id = $1 AND entitlement_type = $2 ORDER BY created_at DESC"
        )
        .bind(user_id)
        .bind(entitlement_type)
        .fetch_all(pool)
        .await?
    };
    Ok(rows)
}

/// Grant all benefits from an SKU to a user. Called after payment success or CDK redeem.
pub async fn grant_sku_benefits(
    pool: &PgPool,
    user_id: &str,
    source_type: &str,
    source_id: &str,
    benefits: &[crate::models::product::SkuBenefit],
    quantity: i32,
    duration_days: i32,
) -> Result<(), AppError> {
    let mut tx = pool.begin().await?;

    let mut membership_expires_at: Option<chrono::DateTime<chrono::Utc>> = None;

    for benefit in benefits {
        match benefit.benefit_type.as_str() {
            "membership" => {
                let tier = benefit.benefit_value.as_deref().unwrap_or("");
                let target_rank = tier_rank(tier);
                let days = (duration_days as i64) * (quantity as i64);

                // Check existing membership
                let existing = sqlx::query_as::<_, UserEntitlement>(
                    "SELECT * FROM user_entitlements \
                     WHERE user_id = $1 AND entitlement_type = 'membership' AND status = 'active' \
                     AND (expires_at IS NULL OR expires_at > now()) \
                     ORDER BY expires_at DESC NULLS LAST LIMIT 1 FOR UPDATE"
                )
                .bind(user_id)
                .fetch_optional(&mut *tx)
                .await?;

                let (starts_at, expires_at) = if let Some(ref old) = existing {
                    let old_tier = old.entitlement_code.as_str();
                    let old_rank = tier_rank(old_tier);

                    if target_rank > old_rank {
                        // Upgrade: convert remaining days
                        let remaining = (old.expires_at.unwrap_or(chrono::Utc::now()) - chrono::Utc::now())
                            .num_days()
                            .max(0);
                        let old_price = tier_price(old_tier);
                        let new_price = tier_price(tier);
                        let converted = if new_price > 0.0 {
                            (remaining as f64 * old_price / new_price) as i64
                        } else {
                            0
                        };
                        let final_days = converted + days;

                        // Supersede old membership and its feature entitlements
                        sqlx::query("UPDATE user_entitlements SET status = 'superseded', updated_at = now() WHERE id = $1")
                            .bind(&old.id)
                            .execute(&mut *tx)
                            .await?;
                        sqlx::query(
                            "UPDATE user_entitlements SET status = 'superseded', updated_at = now() \
                             WHERE user_id = $1 AND entitlement_type = 'feature' AND status = 'active' \
                             AND source_id = $2"
                        )
                        .bind(user_id)
                        .bind(&old.id)
                        .execute(&mut *tx)
                        .await?;

                        let exp = chrono::Utc::now() + chrono::Duration::days(final_days);
                        (chrono::Utc::now(), exp)
                    } else if target_rank == old_rank {
                        // Renewal
                        let base = old.expires_at.unwrap_or(chrono::Utc::now());
                        let base = if base < chrono::Utc::now() { chrono::Utc::now() } else { base };
                        (chrono::Utc::now(), base + chrono::Duration::days(days))
                    } else {
                        // Same or lower tier — skip (downgrade blocked at order time)
                        continue;
                    }
                } else {
                    // Fresh
                    (chrono::Utc::now(), chrono::Utc::now() + chrono::Duration::days(days))
                };

                let ent_id = format!("ent_{}", uuid::Uuid::new_v4());
                sqlx::query(
                    "INSERT INTO user_entitlements (id, user_id, source_type, source_id, entitlement_type, entitlement_code, status, starts_at, expires_at, payload_json) \
                     VALUES ($1, $2, $3, $4, 'membership', $5, 'active', $6, $7, '{}')"
                )
                .bind(&ent_id)
                .bind(user_id)
                .bind(source_type)
                .bind(source_id)
                .bind(tier)
                .bind(starts_at)
                .bind(expires_at)
                .execute(&mut *tx)
                .await?;

                membership_expires_at = Some(expires_at);
            }
            "credits" => {
                let credit_type = benefit.benefit_value.as_deref().unwrap_or("scene_generate");
                let amount = benefit.benefit_json
                    .get("amount")
                    .and_then(|v| v.as_i64())
                    .unwrap_or(0) * (quantity as i64);

                if amount == 0 {
                    continue;
                }

                // Upsert credit account
                let account = sqlx::query_as::<_, UserCreditAccount>(
                    "INSERT INTO user_credit_accounts (id, user_id, credit_type, balance, frozen_balance) \
                     VALUES ($1, $2, $3, $4, 0) \
                     ON CONFLICT (user_id, credit_type) DO UPDATE SET balance = user_credit_accounts.balance + $4, updated_at = now() \
                     RETURNING *"
                )
                .bind(format!("ca_{}", uuid::Uuid::new_v4()))
                .bind(user_id)
                .bind(credit_type)
                .bind(amount as i32)
                .fetch_one(&mut *tx)
                .await?;

                let ledger_id = format!("cl_{}", uuid::Uuid::new_v4());
                sqlx::query(
                    "INSERT INTO credit_ledger (id, user_id, credit_type, change_amount, balance_after, reason_type, reason_id, remark) \
                     VALUES ($1, $2, $3, $4, $5, 'purchase', $6, 'Order benefit grant')"
                )
                .bind(&ledger_id)
                .bind(user_id)
                .bind(credit_type)
                .bind(amount as i32)
                .bind(account.balance)
                .bind(source_id)
                .execute(&mut *tx)
                .await?;
            }
            "feature" => {
                let feature_code = benefit.benefit_value.as_deref().unwrap_or("");
                let expires = membership_expires_at
                    .unwrap_or(chrono::Utc::now() + chrono::Duration::days((duration_days * quantity) as i64));

                let ent_id = format!("ent_{}", uuid::Uuid::new_v4());
                sqlx::query(
                    "INSERT INTO user_entitlements (id, user_id, source_type, source_id, entitlement_type, entitlement_code, status, starts_at, expires_at, payload_json) \
                     VALUES ($1, $2, $3, $4, 'feature', $5, 'active', now(), $6, '{}')"
                )
                .bind(&ent_id)
                .bind(user_id)
                .bind(source_type)
                .bind(source_id)
                .bind(feature_code)
                .bind(expires)
                .execute(&mut *tx)
                .await?;
            }
            _ => {}
        }
    }

    tx.commit().await?;
    Ok(())
}

pub async fn redeem_cdk(
    pool: &PgPool,
    code: &str,
    user_id: &str,
) -> Result<CdkCode, AppError> {
    let mut tx = pool.begin().await?;

    let cdk = sqlx::query_as::<_, CdkCode>(
        "SELECT * FROM cdk_codes WHERE code = $1 FOR UPDATE"
    )
    .bind(code)
    .fetch_optional(&mut *tx)
    .await?;

    let Some(cdk) = cdk else {
        tx.rollback().await?;
        return Err(AppError::BadRequest("卡密码无效，请检查后重新输入".into()));
    };

    if cdk.status != "unused" {
        tx.rollback().await?;
        return Err(AppError::BadRequest("该卡密已被兑换，不可重复使用".into()));
    }

    let now = chrono::Utc::now();
    let updated = sqlx::query_as::<_, CdkCode>(
        "UPDATE cdk_codes SET status = 'redeemed', redeemed_by = $1, redeemed_at = $2, updated_at = $2 \
         WHERE id = $3 RETURNING *"
    )
    .bind(user_id)
    .bind(now)
    .bind(&cdk.id)
    .fetch_one(&mut *tx)
    .await?;

    // Get SKU benefits for granting
    let benefits = sqlx::query_as::<_, crate::models::product::SkuBenefit>(
        "SELECT * FROM sku_benefits WHERE sku_id = $1 ORDER BY created_at ASC"
    )
    .bind(&cdk.sku_id)
    .fetch_all(&mut *tx)
    .await?;

    let sku = sqlx::query_as::<_, crate::models::product::ProductSku>(
        "SELECT * FROM product_skus WHERE id = $1"
    )
    .bind(&cdk.sku_id)
    .fetch_optional(&mut *tx)
    .await?;

    let duration_days = sku.and_then(|s| s.duration_days).unwrap_or(365);

    // Grant benefits within the same transaction
    // We need to commit first, then grant — or grant within same tx
    // Actually we should grant within the same tx for atomicity
    // But grant_sku_benefits opens its own tx, so let's inline the simple version
    for benefit in &benefits {
        match benefit.benefit_type.as_str() {
            "membership" => {
                let tier = benefit.benefit_value.as_deref().unwrap_or("");
                let days = duration_days as i64;
                let existing = sqlx::query_as::<_, UserEntitlement>(
                    "SELECT * FROM user_entitlements \
                     WHERE user_id = $1 AND entitlement_type = 'membership' AND status = 'active' \
                     AND (expires_at IS NULL OR expires_at > now()) \
                     ORDER BY expires_at DESC NULLS LAST LIMIT 1 FOR UPDATE"
                )
                .bind(user_id)
                .fetch_optional(&mut *tx)
                .await?;

                let expires_at = if let Some(ref old) = existing {
                    let base = old.expires_at.unwrap_or(now);
                    let base = if base < now { now } else { base };
                    base + chrono::Duration::days(days)
                } else {
                    now + chrono::Duration::days(days)
                };

                let ent_id = format!("ent_{}", uuid::Uuid::new_v4());
                sqlx::query(
                    "INSERT INTO user_entitlements (id, user_id, source_type, source_id, entitlement_type, entitlement_code, status, starts_at, expires_at, payload_json) \
                     VALUES ($1, $2, 'cdk', $3, 'membership', $4, 'active', $5, $6, '{}')"
                )
                .bind(&ent_id)
                .bind(user_id)
                .bind(&updated.id)
                .bind(tier)
                .bind(now)
                .bind(expires_at)
                .execute(&mut *tx)
                .await?;
            }
            "credits" => {
                let credit_type = benefit.benefit_value.as_deref().unwrap_or("scene_generate");
                let amount = benefit.benefit_json
                    .get("amount")
                    .and_then(|v| v.as_i64())
                    .unwrap_or(0);

                if amount == 0 { continue; }

                let account = sqlx::query_as::<_, UserCreditAccount>(
                    "INSERT INTO user_credit_accounts (id, user_id, credit_type, balance, frozen_balance) \
                     VALUES ($1, $2, $3, $4, 0) \
                     ON CONFLICT (user_id, credit_type) DO UPDATE SET balance = user_credit_accounts.balance + $4, updated_at = now() \
                     RETURNING *"
                )
                .bind(format!("ca_{}", uuid::Uuid::new_v4()))
                .bind(user_id)
                .bind(credit_type)
                .bind(amount as i32)
                .fetch_one(&mut *tx)
                .await?;

                let ledger_id = format!("cl_{}", uuid::Uuid::new_v4());
                sqlx::query(
                    "INSERT INTO credit_ledger (id, user_id, credit_type, change_amount, balance_after, reason_type, reason_id, remark) \
                     VALUES ($1, $2, $3, $4, $5, 'cdk_redeem', $6, 'CDK redeem')"
                )
                .bind(&ledger_id)
                .bind(user_id)
                .bind(credit_type)
                .bind(amount as i32)
                .bind(account.balance)
                .bind(&updated.id)
                .execute(&mut *tx)
                .await?;
            }
            _ => {}
        }
    }

    tx.commit().await?;
    Ok(updated)
}

pub async fn list_user_cdk_redemptions(pool: &PgPool, user_id: &str) -> Result<Vec<CdkRedemption>, AppError> {
    let cdks = sqlx::query_as::<_, CdkCode>(
        "SELECT c.* FROM cdk_codes c \
         WHERE c.redeemed_by = $1 AND c.status = 'redeemed' ORDER BY c.redeemed_at DESC"
    )
    .bind(user_id)
    .fetch_all(pool)
    .await?;

    let mut result = Vec::with_capacity(cdks.len());
    for cdk in cdks {
        let sku_name = sqlx::query_scalar::<_, String>(
            "SELECT name FROM product_skus WHERE id = $1"
        )
        .bind(&cdk.sku_id)
        .fetch_optional(pool)
        .await?
        .unwrap_or_default();

        result.push(CdkRedemption { cdk, sku_name });
    }
    Ok(result)
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

/// Get the user's scene generation credit balance.
pub async fn get_scene_credit_balance(pool: &PgPool, user_id: &str) -> Result<i32, AppError> {
    let balance = sqlx::query_scalar::<_, i32>(
        "SELECT COALESCE((SELECT balance FROM user_credit_accounts WHERE user_id = $1 AND credit_type = $2), 0)"
    )
    .bind(user_id)
    .bind(SCENE_CREDIT_TYPE)
    .fetch_one(pool)
    .await?;
    Ok(balance)
}

/// Deduct credits from a user's account. Returns the balance after deduction.
/// Fails if insufficient balance.
pub async fn deduct_credit(
    pool: &PgPool,
    user_id: &str,
    credit_type: &str,
    amount: i32,
    reason_type: &str,
    reason_id: &str,
    remark: &str,
) -> Result<i32, AppError> {
    let mut tx = pool.begin().await?;

    // Lock and check balance
    let current = sqlx::query_as::<_, UserCreditAccount>(
        "SELECT * FROM user_credit_accounts WHERE user_id = $1 AND credit_type = $2 FOR UPDATE"
    )
    .bind(user_id)
    .bind(credit_type)
    .fetch_optional(&mut *tx)
    .await?;

    let account = current.ok_or_else(|| AppError::BadRequest("积分账户不存在".into()))?;

    if account.balance < amount {
        tx.rollback().await?;
        return Err(AppError::BadRequest(format!(
            "积分不足，当前 {}，需要 {}",
            account.balance, amount
        )));
    }

    let new_balance = account.balance - amount;

    sqlx::query(
        "UPDATE user_credit_accounts SET balance = $1, updated_at = now() WHERE id = $2"
    )
    .bind(new_balance)
    .bind(&account.id)
    .execute(&mut *tx)
    .await?;

    let ledger_id = format!("cl_{}", uuid::Uuid::new_v4());
    sqlx::query(
        "INSERT INTO credit_ledger (id, user_id, credit_type, change_amount, balance_after, reason_type, reason_id, remark) \
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8)"
    )
    .bind(&ledger_id)
    .bind(user_id)
    .bind(credit_type)
    .bind(-amount)
    .bind(new_balance)
    .bind(reason_type)
    .bind(reason_id)
    .bind(remark)
    .execute(&mut *tx)
    .await?;

    tx.commit().await?;
    Ok(new_balance)
}

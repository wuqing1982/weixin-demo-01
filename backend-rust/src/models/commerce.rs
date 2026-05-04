use serde::{Deserialize, Serialize};
use sqlx::FromRow;

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
#[serde(rename_all = "camelCase")]
pub struct UserEntitlement {
    pub id: String,
    pub user_id: String,
    pub source_type: String,
    pub source_id: Option<String>,
    pub entitlement_type: String,
    pub entitlement_code: String,
    pub status: String,
    pub starts_at: chrono::DateTime<chrono::Utc>,
    pub expires_at: Option<chrono::DateTime<chrono::Utc>>,
    pub payload_json: serde_json::Value,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub updated_at: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
#[serde(rename_all = "camelCase")]
pub struct UserCreditAccount {
    pub id: String,
    pub user_id: String,
    pub credit_type: String,
    pub balance: i32,
    pub frozen_balance: i32,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub updated_at: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
#[serde(rename_all = "camelCase")]
pub struct CreditLedger {
    pub id: String,
    pub user_id: String,
    pub credit_type: String,
    pub change_amount: i32,
    pub balance_after: i32,
    pub reason_type: String,
    pub reason_id: Option<String>,
    pub remark: Option<String>,
    pub created_at: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
#[serde(rename_all = "camelCase")]
pub struct CdkCode {
    pub id: String,
    pub code: String,
    pub sku_id: String,
    pub status: String,
    pub batch_id: Option<String>,
    pub redeemed_by: Option<String>,
    pub redeemed_at: Option<chrono::DateTime<chrono::Utc>>,
    pub note: Option<String>,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub updated_at: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct MembershipSummary {
    pub is_active: bool,
    pub entitlement_code: String,
    pub expires_at: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct CreditAccountInfo {
    pub account_id: String,
    pub credit_type: String,
    pub balance: i32,
    pub frozen_balance: i32,
    pub updated_at: String,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct CreditSummary {
    pub scene_generate_balance: i32,
    pub accounts: Vec<CreditAccountInfo>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct UpgradePreview {
    pub action: String,
    pub current_tier: Option<String>,
    pub target_tier: String,
    pub remaining_days: i64,
    pub converted_days: i64,
    pub new_duration_days: i32,
    pub new_expires_at: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CdkRedeemRequest {
    pub code: String,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct CdkRedemption {
    #[serde(flatten)]
    pub cdk: CdkCode,
    pub sku_name: String,
}

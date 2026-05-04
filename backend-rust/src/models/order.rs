use serde::{Deserialize, Serialize};
use sqlx::FromRow;

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct Order {
    pub id: String,
    pub order_no: String,
    pub user_id: String,
    pub status: String,
    pub total_amount: rust_decimal::Decimal,
    pub payable_amount: rust_decimal::Decimal,
    pub paid_amount: Option<rust_decimal::Decimal>,
    pub currency: String,
    pub payment_status: String,
    pub paid_at: Option<chrono::DateTime<chrono::Utc>>,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub updated_at: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct OrderItem {
    pub id: String,
    pub order_id: String,
    pub product_id: String,
    pub sku_id: String,
    pub product_name: String,
    pub sku_name: String,
    pub quantity: i32,
    pub unit_price: rust_decimal::Decimal,
    pub total_price: rust_decimal::Decimal,
    pub benefit_snapshot: serde_json::Value,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub updated_at: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct Payment {
    pub id: String,
    pub payment_no: String,
    pub order_id: String,
    pub user_id: String,
    pub channel: String,
    pub status: String,
    pub amount: rust_decimal::Decimal,
    pub channel_trade_no: Option<String>,
    pub channel_payload: Option<serde_json::Value>,
    pub paid_at: Option<chrono::DateTime<chrono::Utc>>,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub updated_at: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct OrderDetail {
    #[serde(flatten)]
    pub order: Order,
    pub items: Vec<OrderItem>,
    pub payments: Vec<Payment>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CreateOrderRequest {
    pub sku_id: String,
    pub quantity: Option<i32>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct MockPayRequest {
    pub payment_id: Option<String>,
}

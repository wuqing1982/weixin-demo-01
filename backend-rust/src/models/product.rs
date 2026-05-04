use serde::{Deserialize, Serialize};
use sqlx::FromRow;

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct Product {
    pub id: String,
    pub product_code: String,
    pub product_type: String,
    pub name: String,
    pub subtitle: Option<String>,
    pub description: Option<String>,
    pub status: String,
    pub cover_url: Option<String>,
    pub sort_order: i32,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub updated_at: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct ProductSku {
    pub id: String,
    pub sku_code: String,
    pub product_id: String,
    pub name: String,
    pub billing_type: String,
    pub duration_days: Option<i32>,
    pub status: String,
    pub list_price: rust_decimal::Decimal,
    pub sale_price: rust_decimal::Decimal,
    pub currency: String,
    pub stock_type: String,
    pub stock_count: Option<i32>,
    pub sort_order: i32,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub updated_at: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct SkuBenefit {
    pub id: String,
    pub sku_id: String,
    pub benefit_type: String,
    pub benefit_value: Option<String>,
    pub benefit_json: serde_json::Value,
    pub created_at: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SkuWithBenefits {
    #[serde(flatten)]
    pub sku: ProductSku,
    pub benefits: Vec<SkuBenefit>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ProductDetail {
    #[serde(flatten)]
    pub product: Product,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ProductList {
    pub list: Vec<Product>,
}

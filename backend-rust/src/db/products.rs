use sqlx::PgPool;

use crate::error::AppError;
use crate::models::product::*;

pub async fn list_products(pool: &PgPool, product_type: &str) -> Result<Vec<Product>, AppError> {
    let rows = if product_type.is_empty() {
        sqlx::query_as::<_, Product>(
            "SELECT * FROM products WHERE status = 'active' ORDER BY sort_order ASC, created_at ASC"
        )
        .fetch_all(pool)
        .await?
    } else {
        sqlx::query_as::<_, Product>(
            "SELECT * FROM products WHERE status = 'active' AND product_type = $1 ORDER BY sort_order ASC, created_at ASC"
        )
        .bind(product_type)
        .fetch_all(pool)
        .await?
    };
    Ok(rows)
}

pub async fn get_product(pool: &PgPool, product_id: &str) -> Result<Option<Product>, AppError> {
    let row = sqlx::query_as::<_, Product>("SELECT * FROM products WHERE id = $1")
        .bind(product_id)
        .fetch_optional(pool)
        .await?;
    Ok(row)
}

pub async fn list_product_skus(pool: &PgPool, product_id: &str) -> Result<Vec<SkuWithBenefits>, AppError> {
    let skus = sqlx::query_as::<_, ProductSku>(
        "SELECT * FROM product_skus WHERE product_id = $1 AND status = 'active' ORDER BY sort_order ASC, created_at ASC"
    )
    .bind(product_id)
    .fetch_all(pool)
    .await?;

    let sku_ids: Vec<&str> = skus.iter().map(|s| s.id.as_str()).collect();
    let benefits = if sku_ids.is_empty() {
        Vec::new()
    } else {
        sqlx::query_as::<_, SkuBenefit>(
            "SELECT * FROM sku_benefits WHERE sku_id = ANY($1) ORDER BY created_at ASC"
        )
        .bind(&sku_ids)
        .fetch_all(pool)
        .await?
    };

    let mut benefits_by_sku: std::collections::HashMap<&str, Vec<SkuBenefit>> = std::collections::HashMap::new();
    for b in &benefits {
        benefits_by_sku.entry(&b.sku_id).or_default().push(b.clone());
    }

    let result = skus
        .into_iter()
        .map(|sku| {
            let sku_id = sku.id.clone();
            SkuWithBenefits {
                benefits: benefits_by_sku.remove(sku_id.as_str()).unwrap_or_default(),
                sku,
            }
        })
        .collect();

    Ok(result)
}

pub async fn get_sku_with_benefits(pool: &PgPool, sku_id: &str) -> Result<Option<SkuWithBenefits>, AppError> {
    let sku = sqlx::query_as::<_, ProductSku>("SELECT * FROM product_skus WHERE id = $1")
        .bind(sku_id)
        .fetch_optional(pool)
        .await?;

    let Some(sku) = sku else { return Ok(None) };

    let benefits = sqlx::query_as::<_, SkuBenefit>(
        "SELECT * FROM sku_benefits WHERE sku_id = $1 ORDER BY created_at ASC"
    )
    .bind(sku_id)
    .fetch_all(pool)
    .await?;

    Ok(Some(SkuWithBenefits { sku, benefits }))
}

pub async fn list_all_products(pool: &PgPool) -> Result<Vec<Product>, AppError> {
    let rows = sqlx::query_as::<_, Product>(
        "SELECT * FROM products ORDER BY sort_order ASC, created_at ASC"
    )
    .fetch_all(pool)
    .await?;
    Ok(rows)
}

pub async fn list_all_product_skus(pool: &PgPool) -> Result<Vec<SkuWithBenefits>, AppError> {
    let skus = sqlx::query_as::<_, ProductSku>(
        "SELECT * FROM product_skus ORDER BY sort_order ASC, created_at ASC"
    )
    .fetch_all(pool)
    .await?;

    let sku_ids: Vec<&str> = skus.iter().map(|s| s.id.as_str()).collect();
    let benefits = if sku_ids.is_empty() {
        Vec::new()
    } else {
        sqlx::query_as::<_, SkuBenefit>(
            "SELECT * FROM sku_benefits WHERE sku_id = ANY($1) ORDER BY created_at ASC"
        )
        .bind(&sku_ids)
        .fetch_all(pool)
        .await?
    };

    let mut benefits_by_sku: std::collections::HashMap<&str, Vec<SkuBenefit>> = std::collections::HashMap::new();
    for b in &benefits {
        benefits_by_sku.entry(&b.sku_id).or_default().push(b.clone());
    }

    let result = skus.into_iter().map(|sku| {
        let sku_id = sku.id.clone();
        SkuWithBenefits {
            benefits: benefits_by_sku.remove(sku_id.as_str()).unwrap_or_default(),
            sku,
        }
    }).collect();

    Ok(result)
}

pub async fn upsert_product(
    pool: &PgPool,
    id: &str,
    product_code: &str,
    product_type: &str,
    name: &str,
    subtitle: Option<&str>,
    description: Option<&str>,
    status: &str,
    cover_url: Option<&str>,
    sort_order: i32,
) -> Result<Product, AppError> {
    let row = sqlx::query_as::<_, Product>(
        "INSERT INTO products (id, product_code, product_type, name, subtitle, description, status, cover_url, sort_order) \
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) \
         ON CONFLICT (id) DO UPDATE SET product_code = $2, product_type = $3, name = $4, subtitle = $5, description = $6, status = $7, cover_url = $8, sort_order = $9, updated_at = now() \
         RETURNING *"
    )
    .bind(id).bind(product_code).bind(product_type).bind(name)
    .bind(subtitle).bind(description).bind(status).bind(cover_url).bind(sort_order)
    .fetch_one(pool).await?;
    Ok(row)
}

pub async fn update_product_status(pool: &PgPool, product_id: &str, status: &str) -> Result<(), AppError> {
    sqlx::query("UPDATE products SET status = $1, updated_at = now() WHERE id = $2")
        .bind(status).bind(product_id)
        .execute(pool).await?;
    Ok(())
}

pub async fn upsert_sku(
    pool: &PgPool,
    id: &str,
    sku_code: &str,
    product_id: &str,
    name: &str,
    billing_type: &str,
    duration_days: Option<i32>,
    status: &str,
    list_price: rust_decimal::Decimal,
    sale_price: rust_decimal::Decimal,
    currency: &str,
    stock_type: &str,
    stock_count: Option<i32>,
    sort_order: i32,
) -> Result<ProductSku, AppError> {
    let row = sqlx::query_as::<_, ProductSku>(
        "INSERT INTO product_skus (id, sku_code, product_id, name, billing_type, duration_days, status, list_price, sale_price, currency, stock_type, stock_count, sort_order) \
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13) \
         ON CONFLICT (id) DO UPDATE SET sku_code = $2, product_id = $3, name = $4, billing_type = $5, duration_days = $6, status = $7, list_price = $8, sale_price = $9, currency = $10, stock_type = $11, stock_count = $12, sort_order = $13, updated_at = now() \
         RETURNING *"
    )
    .bind(id).bind(sku_code).bind(product_id).bind(name)
    .bind(billing_type).bind(duration_days).bind(status)
    .bind(list_price).bind(sale_price).bind(currency)
    .bind(stock_type).bind(stock_count).bind(sort_order)
    .fetch_one(pool).await?;
    Ok(row)
}

pub async fn replace_sku_benefits(pool: &PgPool, sku_id: &str, benefits: &[serde_json::Value]) -> Result<(), AppError> {
    sqlx::query("DELETE FROM sku_benefits WHERE sku_id = $1")
        .bind(sku_id).execute(pool).await?;
    for b in benefits {
        let benefit_id = format!("benefit_{}", uuid::Uuid::new_v4());
        sqlx::query(
            "INSERT INTO sku_benefits (id, sku_id, benefit_type, benefit_value, benefit_json) VALUES ($1, $2, $3, $4, $5)"
        )
        .bind(&benefit_id)
        .bind(sku_id)
        .bind(b["benefitType"].as_str().unwrap_or(""))
        .bind(b["benefitValue"].as_str())
        .bind(b.get("benefitJson").cloned().unwrap_or(serde_json::Value::Null))
        .execute(pool).await?;
    }
    Ok(())
}

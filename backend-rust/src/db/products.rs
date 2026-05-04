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

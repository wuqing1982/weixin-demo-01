use sqlx::PgPool;

use crate::error::AppError;
use crate::models::order::*;

pub async fn create_order(
    pool: &PgPool,
    order_id: &str,
    order_no: &str,
    user_id: &str,
    sku_id: &str,
    product_id: &str,
    product_name: &str,
    sku_name: &str,
    quantity: i32,
    unit_price: rust_decimal::Decimal,
    total_price: rust_decimal::Decimal,
    currency: &str,
    benefit_snapshot: &serde_json::Value,
    item_id: &str,
) -> Result<OrderDetail, AppError> {
    let mut tx = pool.begin().await?;

    let order = sqlx::query_as::<_, Order>(
        "INSERT INTO orders (id, order_no, user_id, status, total_amount, payable_amount, currency, payment_status) \
         VALUES ($1, $2, $3, 'pending', $4, $4, $5, 'pending') RETURNING *"
    )
    .bind(order_id)
    .bind(order_no)
    .bind(user_id)
    .bind(total_price)
    .bind(currency)
    .fetch_one(&mut *tx)
    .await?;

    sqlx::query(
        "INSERT INTO order_items (id, order_id, product_id, sku_id, product_name, sku_name, quantity, unit_price, total_price, benefit_snapshot) \
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)"
    )
    .bind(item_id)
    .bind(&order.id)
    .bind(product_id)
    .bind(sku_id)
    .bind(product_name)
    .bind(sku_name)
    .bind(quantity)
    .bind(unit_price)
    .bind(total_price)
    .bind(benefit_snapshot)
    .execute(&mut *tx)
    .await?;

    tx.commit().await?;

    let items = sqlx::query_as::<_, OrderItem>(
        "SELECT * FROM order_items WHERE order_id = $1"
    )
    .bind(&order.id)
    .fetch_all(pool)
    .await?;

    let payments = sqlx::query_as::<_, Payment>(
        "SELECT * FROM payments WHERE order_id = $1"
    )
    .bind(&order.id)
    .fetch_all(pool)
    .await?;

    Ok(OrderDetail { order, items, payments })
}

pub async fn list_orders(pool: &PgPool, user_id: &str) -> Result<Vec<OrderDetail>, AppError> {
    let orders = sqlx::query_as::<_, Order>(
        "SELECT * FROM orders WHERE user_id = $1 ORDER BY created_at DESC"
    )
    .bind(user_id)
    .fetch_all(pool)
    .await?;

    let mut result = Vec::with_capacity(orders.len());
    for order in orders {
        let items = sqlx::query_as::<_, OrderItem>(
            "SELECT * FROM order_items WHERE order_id = $1"
        )
        .bind(&order.id)
        .fetch_all(pool)
        .await?;

        let payments = sqlx::query_as::<_, Payment>(
            "SELECT * FROM payments WHERE order_id = $1"
        )
        .bind(&order.id)
        .fetch_all(pool)
        .await?;

        result.push(OrderDetail { order, items, payments });
    }
    Ok(result)
}

pub async fn get_order(pool: &PgPool, order_id: &str, user_id: &str) -> Result<Option<OrderDetail>, AppError> {
    let order = sqlx::query_as::<_, Order>(
        "SELECT * FROM orders WHERE id = $1 AND user_id = $2"
    )
    .bind(order_id)
    .bind(user_id)
    .fetch_optional(pool)
    .await?;

    let Some(order) = order else { return Ok(None) };

    let items = sqlx::query_as::<_, OrderItem>(
        "SELECT * FROM order_items WHERE order_id = $1"
    )
    .bind(&order.id)
    .fetch_all(pool)
    .await?;

    let payments = sqlx::query_as::<_, Payment>(
        "SELECT * FROM payments WHERE order_id = $1"
    )
    .bind(&order.id)
    .fetch_all(pool)
    .await?;

    Ok(Some(OrderDetail { order, items, payments }))
}

pub async fn create_payment(
    pool: &PgPool,
    payment_id: &str,
    payment_no: &str,
    order_id: &str,
    user_id: &str,
    channel: &str,
    amount: rust_decimal::Decimal,
    payload: Option<&serde_json::Value>,
) -> Result<Payment, AppError> {
    let payment = sqlx::query_as::<_, Payment>(
        "INSERT INTO payments (id, payment_no, order_id, user_id, channel, status, amount, channel_payload) \
         VALUES ($1, $2, $3, $4, $5, 'pending', $6, COALESCE($7, '{}'::jsonb)) RETURNING *"
    )
    .bind(payment_id)
    .bind(payment_no)
    .bind(order_id)
    .bind(user_id)
    .bind(channel)
    .bind(amount)
    .bind(payload)
    .fetch_one(pool)
    .await?;
    Ok(payment)
}

pub async fn update_payment_payload(pool: &PgPool, payment_id: &str, payload: &serde_json::Value) -> Result<(), AppError> {
    sqlx::query("UPDATE payments SET channel_payload = $1, updated_at = now() WHERE id = $2")
        .bind(payload)
        .bind(payment_id)
        .execute(pool)
        .await?;
    Ok(())
}

pub async fn get_pending_payment_for_order(pool: &PgPool, order_id: &str) -> Result<Option<Payment>, AppError> {
    let payment = sqlx::query_as::<_, Payment>(
        "SELECT * FROM payments WHERE order_id = $1 AND status = 'pending' ORDER BY created_at DESC LIMIT 1"
    )
    .bind(order_id)
    .fetch_optional(pool)
    .await?;
    Ok(payment)
}

pub async fn complete_payment(
    pool: &PgPool,
    payment_id: &str,
    trade_no: &str,
    payload: &serde_json::Value,
) -> Result<(), AppError> {
    let mut tx = pool.begin().await?;

    let payment = sqlx::query_as::<_, Payment>(
        "UPDATE payments SET status = 'success', channel_trade_no = $1, channel_payload = $2, paid_at = now(), updated_at = now() \
         WHERE id = $3 RETURNING *"
    )
    .bind(trade_no)
    .bind(payload)
    .bind(payment_id)
    .fetch_one(&mut *tx)
    .await?;

    sqlx::query(
        "UPDATE orders SET status = 'paid', payment_status = 'success', paid_amount = payable_amount, paid_at = now(), updated_at = now() \
         WHERE id = $1 AND status = 'pending'"
    )
    .bind(&payment.order_id)
    .execute(&mut *tx)
    .await?;

    tx.commit().await?;
    Ok(())
}

pub async fn find_order_by_no(pool: &PgPool, order_no: &str) -> Result<Option<Order>, AppError> {
    let order = sqlx::query_as::<_, Order>(
        "SELECT * FROM orders WHERE order_no = $1"
    )
    .bind(order_no)
    .fetch_optional(pool)
    .await?;
    Ok(order)
}

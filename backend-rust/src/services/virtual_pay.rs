use hmac::{Hmac, Mac};
use sha2::Sha256;

type HmacSha256 = Hmac<Sha256>;

/// Calculate pay_sig: HMAC-SHA256(app_key, uri + "&" + body).
pub fn calc_pay_sig(uri: &str, body: &str, app_key: &str) -> String {
    let message = format!("{uri}&{body}");
    let mut mac = HmacSha256::new_from_slice(app_key.as_bytes())
        .expect("HMAC key length is valid");
    mac.update(message.as_bytes());
    hex::encode(mac.finalize().into_bytes())
}

/// Calculate user-session signature: HMAC-SHA256(session_key, body).
pub fn calc_signature(body: &str, session_key: &str) -> String {
    let mut mac = HmacSha256::new_from_slice(session_key.as_bytes())
        .expect("HMAC key length is valid");
    mac.update(body.as_bytes());
    hex::encode(mac.finalize().into_bytes())
}

#[derive(Debug, Clone, serde::Serialize)]
#[serde(rename_all = "camelCase")]
pub struct VirtualPaymentParams {
    pub mode: String,
    pub sign_data: String,
    pub pay_sig: String,
    pub signature: String,
}

/// Build parameters for wx.requestVirtualPayment (mode=short_series_goods).
pub fn build_virtual_payment_params(
    offer_id: &str,
    env: i32,
    order_no: &str,
    product_id: &str,
    price_fen: i64,
    session_key: &str,
    app_key: &str,
    buy_quantity: i32,
    attach: &str,
) -> VirtualPaymentParams {
    use serde_json::json;

    let sign_data_dict = json!({
        "offerId": offer_id,
        "buyQuantity": buy_quantity,
        "env": env,
        "currencyType": "CNY",
        "productId": product_id,
        "goodsPrice": price_fen,
        "outTradeNo": order_no,
        "attach": if attach.is_empty() { order_no } else { attach },
    });

    let sign_data_str = serde_json::to_string(&sign_data_dict).unwrap_or_default();

    let pay_sig = calc_pay_sig("requestVirtualPayment", &sign_data_str, app_key);
    let signature = calc_signature(&sign_data_str, session_key);

    VirtualPaymentParams {
        mode: "short_series_goods".to_string(),
        sign_data: sign_data_str,
        pay_sig,
        signature,
    }
}

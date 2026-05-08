use serde::Deserialize;
use crate::error::AppError;

#[derive(Deserialize)]
struct Code2SessionResponse {
    openid: Option<String>,
    session_key: Option<String>,
    unionid: Option<String>,
    errcode: Option<i32>,
    errmsg: Option<String>,
}

#[derive(Deserialize)]
struct AccessTokenResponse {
    access_token: Option<String>,
    errcode: Option<i32>,
    errmsg: Option<String>,
}

#[derive(Deserialize)]
struct PhoneNumberResponse {
    phone_info: Option<PhoneInfo>,
    errcode: Option<i32>,
    errmsg: Option<String>,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct PhoneInfo {
    pure_phone_number: Option<String>,
}

pub struct PhoneNumberResult {
    pub pure_phone_number: String,
}

pub struct WechatAuthResult {
    pub openid: String,
    pub session_key: String,
    pub unionid: Option<String>,
}

pub async fn code2session(
    app_id: &str,
    app_secret: &str,
    code: &str,
) -> Result<WechatAuthResult, AppError> {
    let url = format!(
        "https://api.weixin.qq.com/sns/jscode2session?appid={}&secret={}&js_code={}&grant_type=authorization_code",
        app_id, app_secret, code
    );

    let client = reqwest::Client::new();
    let resp: Code2SessionResponse = client
        .get(&url)
        .timeout(std::time::Duration::from_secs(10))
        .send()
        .await
        .map_err(|e| AppError::ExternalApi(format!("WeChat code2session request failed: {e}")))?
        .json()
        .await
        .map_err(|e| AppError::ExternalApi(format!("WeChat code2session parse failed: {e}")))?;

    if let Some(errcode) = resp.errcode {
        if errcode != 0 {
            return Err(AppError::ExternalApi(format!(
                "WeChat code2session error {}: {}",
                errcode,
                resp.errmsg.unwrap_or_default()
            )));
        }
    }

    let openid = resp.openid.ok_or_else(|| AppError::ExternalApi("missing openid".into()))?;
    let session_key = resp.session_key.ok_or_else(|| AppError::ExternalApi("missing session_key".into()))?;

    Ok(WechatAuthResult {
        openid,
        session_key,
        unionid: resp.unionid,
    })
}

async fn get_access_token(app_id: &str, app_secret: &str) -> Result<String, AppError> {
    let url = format!(
        "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={}&secret={}",
        app_id, app_secret
    );
    let client = reqwest::Client::new();
    let resp: AccessTokenResponse = client
        .get(&url)
        .timeout(std::time::Duration::from_secs(10))
        .send()
        .await
        .map_err(|e| AppError::ExternalApi(format!("WeChat access_token request failed: {e}")))?
        .json()
        .await
        .map_err(|e| AppError::ExternalApi(format!("WeChat access_token parse failed: {e}")))?;

    if let Some(errcode) = resp.errcode {
        if errcode != 0 {
            return Err(AppError::ExternalApi(format!(
                "WeChat access_token error {}: {}",
                errcode,
                resp.errmsg.unwrap_or_default()
            )));
        }
    }

    resp.access_token
        .ok_or_else(|| AppError::ExternalApi("missing access_token".into()))
}

pub async fn get_user_phone_number(
    app_id: &str,
    app_secret: &str,
    code: &str,
) -> Result<PhoneNumberResult, AppError> {
    let access_token = get_access_token(app_id, app_secret).await?;

    let url = format!(
        "https://api.weixin.qq.com/wxa/business/getuserphonenumber?access_token={}",
        access_token
    );
    let client = reqwest::Client::new();
    let resp: PhoneNumberResponse = client
        .post(&url)
        .json(&serde_json::json!({ "code": code }))
        .timeout(std::time::Duration::from_secs(10))
        .send()
        .await
        .map_err(|e| AppError::ExternalApi(format!("WeChat getuserphonenumber request failed: {e}")))?
        .json()
        .await
        .map_err(|e| AppError::ExternalApi(format!("WeChat getuserphonenumber parse failed: {e}")))?;

    if let Some(errcode) = resp.errcode {
        if errcode != 0 {
            return Err(AppError::ExternalApi(format!(
                "WeChat getuserphonenumber error {}: {}",
                errcode,
                resp.errmsg.unwrap_or_default()
            )));
        }
    }

    let phone_info = resp
        .phone_info
        .ok_or_else(|| AppError::ExternalApi("missing phone_info".into()))?;
    let pure_phone_number = phone_info
        .pure_phone_number
        .ok_or_else(|| AppError::ExternalApi("missing pure_phone_number".into()))?;

    Ok(PhoneNumberResult { pure_phone_number })
}

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

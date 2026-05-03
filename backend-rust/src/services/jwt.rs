use base64::engine::general_purpose::URL_SAFE_NO_PAD;
use base64::Engine;
use hmac::{Hmac, Mac};
use serde::{Deserialize, Serialize};
use serde_json::json;
use sha2::Sha256;

type HmacSha256 = Hmac<Sha256>;

fn b64url_encode(data: &[u8]) -> String {
    URL_SAFE_NO_PAD.encode(data)
}

fn b64url_decode(input: &str) -> Result<Vec<u8>, base64::DecodeError> {
    URL_SAFE_NO_PAD.decode(input)
}

fn json_compact(value: &serde_json::Value) -> Vec<u8> {
    serde_json::to_string(value).unwrap().as_bytes().to_vec()
}

fn utc_now_ts() -> i64 {
    chrono::Utc::now().timestamp()
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct TokenClaims {
    pub sub: String,
    pub typ: String,
    pub role: String,
    pub sid: String,
    pub iat: i64,
    pub exp: i64,
}

pub fn create_access_token(
    secret: &str,
    user_id: &str,
    session_id: &str,
    role: &str,
    expires_in: i64,
) -> Result<(String, i64), String> {
    let issued_at = utc_now_ts();
    let expires_at = issued_at + expires_in;

    let header = json!({"alg": "HS256", "typ": "JWT"});
    let payload = json!({
        "sub": user_id,
        "typ": "access",
        "role": role,
        "sid": session_id,
        "iat": issued_at,
        "exp": expires_at,
    });

    let signing_input = format!(
        "{}.{}",
        b64url_encode(&json_compact(&header)),
        b64url_encode(&json_compact(&payload))
    );

    let mut mac = HmacSha256::new_from_slice(secret.as_bytes())
        .map_err(|e| format!("HMAC init failed: {e}"))?;
    mac.update(signing_input.as_bytes());
    let signature = mac.finalize().into_bytes();

    let token = format!("{}.{}", signing_input, b64url_encode(&signature));
    Ok((token, expires_at))
}

pub fn decode_access_token(secret: &str, token: &str) -> Result<TokenClaims, String> {
    let parts: Vec<&str> = token.split('.').collect();
    if parts.len() != 3 {
        return Err("invalid token".into());
    }

    let signing_input = format!("{}.{}", parts[0], parts[1]);
    let mut mac = HmacSha256::new_from_slice(secret.as_bytes())
        .map_err(|e| format!("HMAC init failed: {e}"))?;
    mac.update(signing_input.as_bytes());
    let expected_sig = mac.finalize().into_bytes();

    let actual_sig = b64url_decode(parts[2])
        .map_err(|e| format!("signature decode failed: {e}"))?;

    // Constant-time comparison
    use subtle::ConstantTimeEq;
    if expected_sig.as_slice().ct_eq(&actual_sig).unwrap_u8() == 0 {
        return Err("invalid token signature".into());
    }

    let payload_bytes = b64url_decode(parts[1])
        .map_err(|e| format!("payload decode failed: {e}"))?;

    let claims: TokenClaims = serde_json::from_slice(&payload_bytes)
        .map_err(|e| format!("payload parse failed: {e}"))?;

    if claims.typ != "access" {
        return Err("invalid token type".into());
    }
    if claims.exp <= utc_now_ts() {
        return Err("token expired".into());
    }

    Ok(claims)
}

pub fn generate_refresh_token() -> String {
    format!("rt_{}", uuid::Uuid::new_v4().simple())
}

pub fn hash_refresh_token(token: &str) -> String {
    use sha2::Digest;
    let mut hasher = Sha256::new();
    hasher.update(token.as_bytes());
    hex::encode(hasher.finalize())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_create_and_decode_token() {
        let secret = "test-secret";
        let (token, exp) = create_access_token(secret, "user1", "sess1", "user", 3600).unwrap();
        assert!(token.contains('.'));
        assert!(exp > 0);

        let claims = decode_access_token(secret, &token).unwrap();
        assert_eq!(claims.sub, "user1");
        assert_eq!(claims.typ, "access");
        assert_eq!(claims.role, "user");
        assert_eq!(claims.sid, "sess1");
    }

    #[test]
    fn test_reject_expired_token() {
        let secret = "test-secret";
        let (token, _) = create_access_token(secret, "user1", "sess1", "user", -1).unwrap();
        assert!(decode_access_token(secret, &token).is_err());
    }

    #[test]
    fn test_reject_wrong_secret() {
        let secret = "correct-secret";
        let (token, _) = create_access_token(secret, "user1", "sess1", "user", 3600).unwrap();
        assert!(decode_access_token("wrong-secret", &token).is_err());
    }

    #[test]
    fn test_refresh_token_format() {
        let rt = generate_refresh_token();
        assert!(rt.starts_with("rt_"));
        assert!(rt.len() > 10);
    }

    #[test]
    fn test_hash_refresh_token_deterministic() {
        let hash1 = hash_refresh_token("rt_abc123");
        let hash2 = hash_refresh_token("rt_abc123");
        assert_eq!(hash1, hash2);
    }
}

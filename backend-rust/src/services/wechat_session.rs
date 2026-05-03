use base64::engine::general_purpose::URL_SAFE_NO_PAD;
use base64::Engine;
use hmac::{Hmac, Mac};
use sha2::{Digest, Sha256};
use subtle::ConstantTimeEq;

type HmacSha256 = Hmac<Sha256>;

fn build_stream(secret: &[u8], nonce: &[u8], length: usize) -> Vec<u8> {
    let mut output = Vec::new();
    let mut counter: u32 = 0;
    while output.len() < length {
        let mut hasher = Sha256::new();
        hasher.update(secret);
        hasher.update(nonce);
        hasher.update(counter.to_be_bytes());
        output.extend_from_slice(&hasher.finalize());
        counter += 1;
    }
    output.truncate(length);
    output
}

pub fn encrypt_session_key(secret: &str, raw_value: &str) -> String {
    if raw_value.is_empty() {
        return String::new();
    }

    let secret_bytes = secret.as_bytes();
    let nonce: [u8; 16] = rand::random();
    let plaintext = raw_value.as_bytes();
    let stream = build_stream(secret_bytes, &nonce, plaintext.len());

    let ciphertext: Vec<u8> = plaintext.iter().zip(stream.iter()).map(|(a, b)| a ^ b).collect();

    let mut mac = HmacSha256::new_from_slice(secret_bytes).unwrap();
    mac.update(&nonce);
    mac.update(&ciphertext);
    let mac_bytes = &mac.finalize().into_bytes()[..12];

    format!(
        "wsk1.{}.{}.{}",
        URL_SAFE_NO_PAD.encode(nonce),
        URL_SAFE_NO_PAD.encode(&ciphertext),
        URL_SAFE_NO_PAD.encode(mac_bytes)
    )
}

pub fn decrypt_session_key(secret: &str, cipher_text: &str) -> Result<String, String> {
    if cipher_text.is_empty() {
        return Ok(String::new());
    }

    let parts: Vec<&str> = cipher_text.split('.').collect();
    if parts.len() != 4 || parts[0] != "wsk1" {
        return Err("invalid encrypted wechat session key".into());
    }

    let nonce = URL_SAFE_NO_PAD.decode(parts[1]).map_err(|e| format!("nonce decode: {e}"))?;
    let ciphertext = URL_SAFE_NO_PAD.decode(parts[2]).map_err(|e| format!("ciphertext decode: {e}"))?;
    let actual_mac = URL_SAFE_NO_PAD.decode(parts[3]).map_err(|e| format!("mac decode: {e}"))?;

    let secret_bytes = secret.as_bytes();
    let mut mac = HmacSha256::new_from_slice(secret_bytes).unwrap();
    mac.update(&nonce);
    mac.update(&ciphertext);
    let expected_mac = &mac.finalize().into_bytes()[..12];

    if expected_mac.ct_eq(&actual_mac.as_slice()).unwrap_u8() == 0 {
        return Err("wechat session key integrity check failed".into());
    }

    let stream = build_stream(secret_bytes, &nonce, ciphertext.len());
    let plaintext: Vec<u8> = ciphertext.iter().zip(stream.iter()).map(|(a, b)| a ^ b).collect();

    String::from_utf8(plaintext).map_err(|e| format!("utf8 decode: {e}"))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_encrypt_decrypt_roundtrip() {
        let secret = "test-session-secret";
        let original = "abc123sessionkey";
        let encrypted = encrypt_session_key(secret, original);
        assert!(encrypted.starts_with("wsk1."));

        let decrypted = decrypt_session_key(secret, &encrypted).unwrap();
        assert_eq!(decrypted, original);
    }

    #[test]
    fn test_decrypt_empty() {
        assert_eq!(decrypt_session_key("secret", "").unwrap(), "");
    }

    #[test]
    fn test_encrypt_empty() {
        assert_eq!(encrypt_session_key("secret", ""), "");
    }

    #[test]
    fn test_reject_wrong_secret() {
        let encrypted = encrypt_session_key("secret-a", "value");
        assert!(decrypt_session_key("secret-b", &encrypted).is_err());
    }
}

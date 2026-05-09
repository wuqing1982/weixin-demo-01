use crate::models::storage_config::ConnectionTestResult;

pub async fn test_local(config: &serde_json::Value) -> ConnectionTestResult {
    let root_dir = config.get("root_dir").and_then(|v| v.as_str()).unwrap_or("assets");
    let base = std::env::current_dir().unwrap_or_default();
    let path = if std::path::Path::new(root_dir).is_absolute() {
        std::path::PathBuf::from(root_dir)
    } else {
        base.join("..").join(root_dir)
    };
    if !path.exists() {
        return ConnectionTestResult { ok: false, message: format!("目录不存在: {}", path.display()) };
    }
    let test_file = path.join(".storage_test");
    match tokio::fs::write(&test_file, b"test").await {
        Ok(_) => {
            let _ = tokio::fs::remove_file(&test_file).await;
            ConnectionTestResult { ok: true, message: format!("本地存储正常 ({})", path.display()) }
        }
        Err(e) => ConnectionTestResult { ok: false, message: format!("目录不可写: {}", e) },
    }
}

pub async fn test_r2(config: &serde_json::Value) -> ConnectionTestResult {
    let account_id = match config.get("account_id").and_then(|v| v.as_str()) {
        Some(v) if !v.is_empty() => v.to_string(),
        _ => return ConnectionTestResult { ok: false, message: "缺少 account_id 配置".into() },
    };
    let access_key_id = match config.get("access_key_id").and_then(|v| v.as_str()) {
        Some(v) if !v.is_empty() => v.to_string(),
        _ => return ConnectionTestResult { ok: false, message: "缺少 access_key_id 配置".into() },
    };
    let secret_access_key = match config.get("secret_access_key").and_then(|v| v.as_str()) {
        Some(v) if !v.is_empty() => v.to_string(),
        _ => return ConnectionTestResult { ok: false, message: "缺少 secret_access_key 配置".into() },
    };
    let bucket = match config.get("bucket").and_then(|v| v.as_str()) {
        Some(v) if !v.is_empty() => v.to_string(),
        _ => return ConnectionTestResult { ok: false, message: "缺少 bucket 配置".into() },
    };

    let credentials = match s3::creds::Credentials::new(Some(&access_key_id), Some(&secret_access_key), None, None, None) {
        Ok(c) => c,
        Err(e) => return ConnectionTestResult { ok: false, message: format!("凭证创建失败: {}", e) },
    };

    let s3_bucket = match s3::Bucket::new(&bucket, s3::Region::R2 { account_id }, credentials) {
        Ok(b) => b.with_path_style(),
        Err(e) => return ConnectionTestResult { ok: false, message: format!("Bucket 创建失败: {}", e) },
    };

    match s3_bucket.exists().await {
        Ok(true) => ConnectionTestResult { ok: true, message: "R2 连接成功，Bucket 可访问".into() },
        Ok(false) => ConnectionTestResult { ok: false, message: "R2 Bucket 不存在或无访问权限".into() },
        Err(e) => ConnectionTestResult { ok: false, message: format!("R2 连接失败: {}", e) },
    }
}

pub async fn test_cos(config: &serde_json::Value) -> ConnectionTestResult {
    let secret_id = match config.get("secret_id").and_then(|v| v.as_str()) {
        Some(v) if !v.is_empty() => v.to_string(),
        _ => return ConnectionTestResult { ok: false, message: "缺少 secret_id 配置".into() },
    };
    let secret_key = match config.get("secret_key").and_then(|v| v.as_str()) {
        Some(v) if !v.is_empty() => v.to_string(),
        _ => return ConnectionTestResult { ok: false, message: "缺少 secret_key 配置".into() },
    };
    let region = match config.get("region").and_then(|v| v.as_str()) {
        Some(v) if !v.is_empty() => v.to_string(),
        _ => return ConnectionTestResult { ok: false, message: "缺少 region 配置".into() },
    };
    let bucket = match config.get("bucket").and_then(|v| v.as_str()) {
        Some(v) if !v.is_empty() => v.to_string(),
        _ => return ConnectionTestResult { ok: false, message: "缺少 bucket 配置".into() },
    };

    let endpoint = format!("https://cos.{}.myqcloud.com", region);
    let credentials = match s3::creds::Credentials::new(Some(&secret_id), Some(&secret_key), None, None, None) {
        Ok(c) => c,
        Err(e) => return ConnectionTestResult { ok: false, message: format!("凭证创建失败: {}", e) },
    };
    let s3_bucket = match s3::Bucket::new(&bucket, s3::Region::Custom { region: region.clone(), endpoint }, credentials) {
        Ok(b) => b.with_path_style(),
        Err(e) => return ConnectionTestResult { ok: false, message: format!("Bucket 创建失败: {}", e) },
    };
    match s3_bucket.exists().await {
        Ok(true) => ConnectionTestResult { ok: true, message: "COS 连接成功，Bucket 可访问".into() },
        Ok(false) => ConnectionTestResult { ok: false, message: "COS Bucket 不存在或无访问权限".into() },
        Err(e) => ConnectionTestResult { ok: false, message: format!("COS 连接失败: {}", e) },
    }
}

pub async fn test_connection(backend_type: &str, config: &serde_json::Value) -> ConnectionTestResult {
    match backend_type {
        "local" => test_local(config).await,
        "r2" => test_r2(config).await,
        "cos" => test_cos(config).await,
        _ => ConnectionTestResult { ok: false, message: format!("不支持的后端类型: {}", backend_type) },
    }
}

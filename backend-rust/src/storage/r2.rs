use async_trait::async_trait;

use super::provider::{StorageError, StorageKey, StorageProvider, StorageResult};

pub struct R2StorageProvider {
    bucket: Box<s3::Bucket>,
    public_url_base: String,
}

impl R2StorageProvider {
    pub fn from_config(config: &serde_json::Value) -> Result<Self, StorageError> {
        let account_id = config
            .get("account_id")
            .and_then(|v| v.as_str())
            .ok_or_else(|| StorageError::S3("missing account_id".into()))?;
        let access_key_id = config
            .get("access_key_id")
            .and_then(|v| v.as_str())
            .ok_or_else(|| StorageError::S3("missing access_key_id".into()))?;
        let secret_access_key = config
            .get("secret_access_key")
            .and_then(|v| v.as_str())
            .ok_or_else(|| StorageError::S3("missing secret_access_key".into()))?;
        let bucket_name = config
            .get("bucket")
            .and_then(|v| v.as_str())
            .ok_or_else(|| StorageError::S3("missing bucket".into()))?;
        let public_url = config
            .get("public_url")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();

        let credentials = s3::creds::Credentials::new(
            Some(access_key_id),
            Some(secret_access_key),
            None,
            None,
            None,
        )
        .map_err(|e| StorageError::S3(format!("credentials: {e}")))?;

        let bucket = s3::Bucket::new(bucket_name, s3::Region::R2 { account_id: account_id.to_string() }, credentials)
            .map_err(|e| StorageError::S3(format!("bucket: {e}")))?
            .with_path_style();

        Ok(Self {
            bucket,
            public_url_base: public_url.trim_end_matches('/').to_string(),
        })
    }
}

#[async_trait]
impl StorageProvider for R2StorageProvider {
    async fn put(&self, key: &StorageKey, data: &[u8], content_type: &str) -> StorageResult<()> {
        self.bucket
            .put_object_with_content_type(key.as_str(), data, content_type)
            .await
            .map_err(|e| StorageError::S3(format!("put: {e}")))?;
        Ok(())
    }

    async fn get(&self, key: &StorageKey) -> StorageResult<Vec<u8>> {
        let resp = self
            .bucket
            .get_object(key.as_str())
            .await
            .map_err(|e| StorageError::S3(format!("get: {e}")))?;
        Ok(resp.to_vec())
    }

    async fn delete(&self, key: &StorageKey) -> StorageResult<()> {
        self.bucket
            .delete_object(key.as_str())
            .await
            .map_err(|e| StorageError::S3(format!("delete: {e}")))?;
        Ok(())
    }

    async fn copy_object(&self, src: &StorageKey, dst: &StorageKey) -> StorageResult<()> {
        // R2 copy via get + put (simple, works universally)
        let data = self.get(src).await?;
        self.put(dst, &data, "application/octet-stream").await?;
        Ok(())
    }

    async fn delete_prefix(&self, prefix: &str) -> StorageResult<()> {
        let results = self
            .bucket
            .list(prefix.to_string(), None)
            .await
            .map_err(|e| StorageError::S3(format!("list: {e}")))?;

        for result in results {
            for obj in result.contents {
                if let Err(e) = self.delete(&StorageKey::new(&[&obj.key])).await {
                    tracing::warn!(key = %obj.key, error = %e, "failed to delete R2 object");
                }
            }
        }
        Ok(())
    }

    fn public_url(&self, key: &StorageKey) -> String {
        format!("{}/{}", self.public_url_base, key.as_str())
    }

    fn base_url(&self) -> String {
        self.public_url_base.clone()
    }

    async fn ensure_local(&self, key: &StorageKey, local_path: &std::path::Path) -> StorageResult<()> {
        if let Some(parent) = local_path.parent() {
            tokio::fs::create_dir_all(parent).await?;
        }
        let data = self.get(key).await?;
        tokio::fs::write(local_path, data).await?;
        Ok(())
    }
}

use std::path::PathBuf;

use async_trait::async_trait;

use super::provider::{StorageError, StorageKey, StorageProvider, StorageResult};

pub struct LocalStorageProvider {
    root: PathBuf,
    base_url: String,
}

impl LocalStorageProvider {
    pub fn new(root_dir: &str, public_base_url: &str) -> Self {
        let root = if PathBuf::from(root_dir).is_absolute() {
            PathBuf::from(root_dir)
        } else {
            std::env::current_dir().unwrap_or_default().join(root_dir)
        };
        Self {
            root,
            base_url: format!("{}/assets", public_base_url.trim_end_matches('/')),
        }
    }

    fn key_to_path(&self, key: &StorageKey) -> PathBuf {
        self.root.join(key.as_str())
    }
}

#[async_trait]
impl StorageProvider for LocalStorageProvider {
    async fn put(&self, key: &StorageKey, data: &[u8], _content_type: &str) -> StorageResult<()> {
        let path = self.key_to_path(key);
        if let Some(parent) = path.parent() {
            tokio::fs::create_dir_all(parent).await?;
        }
        tokio::fs::write(&path, data).await?;
        Ok(())
    }

    async fn get(&self, key: &StorageKey) -> StorageResult<Vec<u8>> {
        let path = self.key_to_path(key);
        let data = tokio::fs::read(&path).await.map_err(|e| {
            if e.kind() == std::io::ErrorKind::NotFound {
                StorageError::NotFound(key.as_str().to_string())
            } else {
                StorageError::Io(e)
            }
        })?;
        Ok(data)
    }

    async fn delete(&self, key: &StorageKey) -> StorageResult<()> {
        let path = self.key_to_path(key);
        if path.exists() {
            tokio::fs::remove_file(&path).await?;
        }
        Ok(())
    }

    async fn copy_object(&self, src: &StorageKey, dst: &StorageKey) -> StorageResult<()> {
        let src_path = self.key_to_path(src);
        let dst_path = self.key_to_path(dst);
        if let Some(parent) = dst_path.parent() {
            tokio::fs::create_dir_all(parent).await?;
        }
        tokio::fs::copy(&src_path, &dst_path).await?;
        Ok(())
    }

    async fn delete_prefix(&self, prefix: &str) -> StorageResult<()> {
        let dir = self.root.join(prefix);
        if dir.exists() && dir.is_dir() {
            tokio::fs::remove_dir_all(&dir).await?;
        }
        Ok(())
    }

    fn public_url(&self, key: &StorageKey) -> String {
        format!("{}/{}", self.base_url.trim_end_matches('/'), key.as_str())
    }

    fn base_url(&self) -> String {
        self.base_url.clone()
    }

    async fn ensure_local(&self, key: &StorageKey, local_path: &std::path::Path) -> StorageResult<()> {
        let src = self.key_to_path(key);
        if local_path.exists() {
            return Ok(());
        }
        if let Some(parent) = local_path.parent() {
            tokio::fs::create_dir_all(parent).await?;
        }
        tokio::fs::copy(&src, local_path).await?;
        Ok(())
    }
}

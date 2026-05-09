use async_trait::async_trait;

#[derive(Debug)]
pub enum StorageError {
    Io(std::io::Error),
    S3(String),
    NotFound(String),
}

impl std::fmt::Display for StorageError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            StorageError::Io(e) => write!(f, "IO: {e}"),
            StorageError::S3(e) => write!(f, "S3: {e}"),
            StorageError::NotFound(e) => write!(f, "Not found: {e}"),
        }
    }
}

impl From<std::io::Error> for StorageError {
    fn from(e: std::io::Error) -> Self {
        StorageError::Io(e)
    }
}

pub type StorageResult<T> = Result<T, StorageError>;

/// Storage-relative path, forward-slash separated, no leading slash.
/// Examples: "uploads/{id}/source.jpg", "generated/{scene_id}/background.jpg"
#[derive(Clone, Debug)]
pub struct StorageKey(String);

impl StorageKey {
    pub fn new(parts: &[&str]) -> Self {
        Self(parts.join("/"))
    }

    /// From a relative web path like "assets/generated/scene_x/bg.jpg"
    /// Strips the "assets/" prefix if present.
    pub fn from_web_path(path: &str) -> Self {
        let clean = path.trim_start_matches('/');
        let stripped = clean.strip_prefix("assets/").unwrap_or(clean);
        Self(stripped.to_string())
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

#[async_trait]
pub trait StorageProvider: Send + Sync {
    async fn put(&self, key: &StorageKey, data: &[u8], content_type: &str) -> StorageResult<()>;
    async fn get(&self, key: &StorageKey) -> StorageResult<Vec<u8>>;
    async fn delete(&self, key: &StorageKey) -> StorageResult<()>;
    async fn copy_object(&self, src: &StorageKey, dst: &StorageKey) -> StorageResult<()>;
    async fn delete_prefix(&self, prefix: &str) -> StorageResult<()>;

    /// Full public URL for a given key.
    fn public_url(&self, key: &StorageKey) -> String;

    /// Base URL prefix for asset resolution (no trailing slash).
    fn base_url(&self) -> String;

    /// Ensure the object is available at a local path (for ffmpeg).
    /// Local: no-op copy or verify exists. R2: download to path.
    async fn ensure_local(&self, key: &StorageKey, local_path: &std::path::Path) -> StorageResult<()>;
}

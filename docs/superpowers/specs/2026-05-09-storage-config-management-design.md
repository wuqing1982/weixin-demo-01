# Storage Config Management + Connection Test - Design

**Date:** 2026-05-09
**Status:** Phase 1 Design
**Scope:** Rust backend admin API for storage backend configuration, connection testing, and activation

## Background

### Current State

The Rust production backend (`backend-rust/`) uses pure local filesystem storage with no abstraction. The admin storage API at `/api/admin/storage/*` is a set of stubs that hardcode `"activeBackend": "local"` and return empty data.

The admin web UI (`backend/admin_web/admin.js`) already has a complete storage management interface with:
- Storage metrics cards (disk usage, file count)
- Backend cards for local, R2, and COS (with configure/test/activate buttons)
- Configuration modals with fields for each backend type
- Connection test and activate workflows

The UI is non-functional because the Rust backend API returns stub data.

### Reference Implementations

1. **Python backend** (`backend/app/storage/`) - Complete implementation with `StorageBackend` Protocol, Local/R2/COS implementations, `StorageConfigStore` (JSON file), factory pattern, and full admin API with connection testing and sensitive field masking.

2. **PHP system** (`/www/wwwroot/english.cps.vin/`) - MySQL table for config, no connection test, no runtime storage abstraction. Uses environment variables for actual storage routing.

3. **Existing R2 credentials** - Python backend's `storage_config.json` has R2 credentials (bucket: `english-loong`, account_id configured) that are disabled.

## Phased Approach

### Phase 1 (this spec): Admin Config + Connection Test

Make the Rust admin storage API functional. Config persistence in PostgreSQL. Connection testing for R2 and COS. Admin UI works end-to-end. Uploads still go to local filesystem.

### Phase 2 (future): Storage Trait + R2 Upload

Define `StorageBackend` trait, implement Local and R2 backends using `rust-s3`, refactor upload handlers to use the trait. End-to-end verification of R2 uploads.

### Phase 3 (future): Switch Back to Local

After verifying R2 works, switch active backend back to local. Keep all infrastructure ready for future switch when storage fills up.

---

## Phase 1 Design

### 1. Database Schema

New migration file: `backend-rust/sql/005_storage_configs.sql`

```sql
-- Storage backend configurations
CREATE TABLE IF NOT EXISTS storage_configs (
    id           SERIAL PRIMARY KEY,
    backend_id   VARCHAR(32) NOT NULL UNIQUE,
    name         VARCHAR(100) NOT NULL,
    backend_type VARCHAR(32) NOT NULL,
    enabled      BOOLEAN NOT NULL DEFAULT FALSE,
    config       JSONB NOT NULL DEFAULT '{}',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Seed default backends
INSERT INTO storage_configs (backend_id, name, backend_type, enabled, config) VALUES
    ('local', '本地存储', 'local', true, '{"root_dir": "assets"}'),
    ('r2', 'Cloudflare R2', 'r2', false, '{}'),
    ('cos', '腾讯云 COS', 'cos', false, '{}');

-- Active backend tracker (single row)
CREATE TABLE IF NOT EXISTS storage_active (
    id         SERIAL PRIMARY KEY,
    backend_id VARCHAR(32) NOT NULL DEFAULT 'local',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO storage_active (backend_id) VALUES ('local');
```

**Config JSONB structure by backend type:**

- **local**: `{"root_dir": "assets"}`
- **r2**: `{"account_id": "...", "access_key_id": "...", "secret_access_key": "...", "bucket": "...", "public_url": "..."}`
- **cos**: `{"secret_id": "...", "secret_key": "...", "region": "...", "bucket": "...", "public_url": "..."}`

### 2. Rust Module Structure

```
backend-rust/src/
├── models/
│   └── storage_config.rs     -- StorageConfig, StorageActive models
├── db/
│   └── storage_config.rs     -- DB queries for config CRUD
├── services/
│   ├── storage_config.rs     -- Config read/write/mask/activate logic
│   └── storage_test.rs       -- Connection test for R2, COS, local
└── api/admin/
    └── storage.rs            -- Replace stub with real endpoints
```

### 3. Admin API Endpoints

All endpoints require admin auth. Replace existing stubs and add missing endpoints.

| Method | Path | Purpose | Current | Target |
|--------|------|---------|---------|--------|
| GET | `/api/admin/storage/overview` | Active backend + all configs + usage | Stub | Read DB + disk stats |
| GET | `/api/admin/storage/configs` | All backend configs (masked) | Stub | Read DB + mask |
| PUT | `/api/admin/storage/configs/{id}` | Update backend config | Missing | New: validate + save |
| POST | `/api/admin/storage/test/{id}` | Test connection | Missing | New: R2/COS/local test |
| POST | `/api/admin/storage/activate/{id}` | Activate backend | Missing | New: test + activate |
| GET | `/api/admin/storage/usage` | Usage stats | Stub | DB aggregate + disk |

### 4. Sensitive Field Masking

Fields to mask in API responses: `secret_access_key`, `secret_key`, `secret_id`.

Masking format: `****xxxx` (show last 4 characters only).

When the admin UI sends back masked values in an update, the server skips updating those fields (preserves the stored secret). Only non-masked values are written to DB.

### 5. Connection Testing

**R2 (via `rust-s3` crate):**
- Create S3 client with endpoint `https://{account_id}.r2.cloudflarestorage.com`
- Region: `auto`
- Call `head_bucket()` to verify connectivity and credentials
- Return `{ ok: true, message: "..." }` result

**COS (via `rust-s3` with COS-compatible endpoint or direct `reqwest`):**
- Tencent COS is S3-compatible but uses different auth
- Option A: Use `rust-s3` with COS endpoint configuration
- Option B: Direct HTTP HEAD bucket request with COS authorization
- Start with Option B (simpler for just testing), migrate to Option A in Phase 2

**Local:**
- Check configured directory exists and is writable
- Create and delete a test file

### 6. Activation Flow

1. Admin clicks "Activate" on a backend
2. Backend validates: backend exists, is enabled, has required config fields
3. Backend runs connection test
4. If test passes: update `storage_active` table, return success
5. If test fails: return error with test result message

This matches the Python backend's safety-first activation pattern.

### 7. Usage Statistics

For Phase 1, usage stats come from:
- **File count and total size**: Aggregate from `uploads` PostgreSQL table
- **Disk info**: `statvfs` on the assets directory (total/used/available)
- **By-type breakdown**: Group uploads by `content_type` or `file_suffix`

No actual storage backend querying for usage (that's Phase 2).

### 8. New Dependencies

`Cargo.toml` additions:

```toml
rust-s3 = { version = "0.35", default-features = false, features = ["with-tokio"] }
```

This brings in the S3-compatible client needed for R2 connection testing and later Phase 2 uploads. For COS connection testing, `reqwest` (already a dependency) with manual COS authorization headers.

### 9. Admin UI Compatibility

The admin UI (`backend/admin_web/admin.js`) expects these response shapes from the Python backend. The Rust API must return the same JSON structure to avoid modifying the frontend:

**GET /api/admin/storage/overview response:**
```json
{
    "activeBackend": "local",
    "lastActiveBackend": "local",
    "backends": {
        "local": { "type": "local", "name": "本地存储", "enabled": true, "config": { "root_dir": "assets" } },
        "r2": { "type": "r2", "name": "Cloudflare R2", "enabled": false, "config": { "account_id": "917...", "access_key_id": "****abcd" } },
        "cos": { "type": "cos", "name": "腾讯云 COS", "enabled": false, "config": {} }
    },
    "usage": {
        "total_bytes": 107374182400,
        "used_bytes": 53687091200,
        "file_count": 1234,
        "by_type": { "image": 800, "audio": 200, "other": 234 }
    }
}
```

**PUT /api/admin/storage/configs/{id} request:**
```json
{ "name": "Cloudflare R2", "enabled": true, "config": { "account_id": "...", "secret_access_key": "****xxxx" } }
```

**POST /api/admin/storage/test/{id} response:**
```json
{ "ok": true, "message": "Connection successful" }
```

**POST /api/admin/storage/activate/{id} response:**
```json
{ "activeBackend": "r2" }
```

### 10. What Does NOT Change

- Admin UI code (`backend/admin_web/`) - no modifications needed
- Upload handlers (`api/upload.rs`, `api/admin/uploads.rs`) - still write to local filesystem
- Video export (`services/video_export.rs`) - still writes to local filesystem
- No storage trait or abstraction yet
- No actual cloud storage operations yet
- Cleanup services unchanged

---

## Out of Scope (Phase 2+)

- `StorageBackend` trait definition
- `LocalStorage` implementation (wrapping current filesystem ops)
- `R2Storage` implementation (actual upload/download/delete)
- `COSStorage` implementation
- Upload handler refactoring to use storage trait
- Migrating existing local files to R2
- Automatic fallback from local to cloud storage

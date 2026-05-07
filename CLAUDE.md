# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WeChat Mini Program (微信小程序) + dual backend (Python FastAPI + Rust Axum) for **English learning through interactive panoramic/VR scenes** ("英语场景"). Users view panoramic images with interactive hotspots that teach English vocabulary and sentences via TTS audio.

**Live domains:** `https://e.cps.vin` (production), `https://stag.cps.vin` (staging) — API at `/api`, static assets served from root.

## Architecture

### Frontend — WeChat Mini Program

Standard WeChat Mini Program structure. Pages in `pages/`, services in `services/`, shared logic in `shared/`, components in `components/`.

**AppID:** `wx8e3f9b18fc8f3241`. SASS compiler plugin enabled. Component lazy loading (`lazyCodeLoading: "requiredComponents"`).

**Pages** (registered in `app.json`):
- `login` — WeChat auth login
- `home` — Scene browsing home
- `library` — Scene library with categories/collections
- `scene_runtime` — Core panoramic scene viewer with hotspot interaction, swipe navigation between scenes
- `create_scene` — Upload images to generate new scenes
- `my_scenes` — User's created scenes
- `my_videos` — Video export list and management
- `products` / `orders` — Commerce (product catalog, order management)
- `cdk_records` — CDK redemption code history

**Key service modules** (`services/`):
- `api.js` — HTTP client wrapping `wx.request`, auto-injects auth headers, waits for auth readiness before requests
- `auth.js` — WeChat login flow (silent login → token refresh → full re-login)
- `session.js` — Access/refresh token storage in `wx.getStorageSync`
- `config.js` — Reads `apiBaseUrl`/`staticBaseUrl` from app globalData, falls back to `config/runtime.js`
- `scene.js`, `product.js`, `order.js`, `payment.js`, `upload.js`, `task.js`, `user.js`, `cdk.js` — Domain API wrappers

**Shared modules** (`shared/`):
- `scene/scene-page.js` — Factory function creating scene page logic (complex interaction handling: panorama touch, hotspot tap, audio playback, navigation)
- `scene/hotspot-editor.js` — Geometry calculations for hotspot positioning (clamp, normalize, move/resize deltas)
- `scene/scene-registry.js` — Scene navigation and neighbor lookup
- `theme-helper.js` — Theme management for navigation bar

**Reusable components** (`components/`): `empty-state`, `loading`.

**Environment switching:** Edit `CURRENT_ENV` in `config/runtime.js`. Profiles: `local` (localhost:8000), `staging` (stag.cps.vin), `production` (e.cps.vin).

**Auth flow:** `app.js` → `initializeAuth()` tries cached access token → refresh token → silent `wx.login`. Tokens are JWT (HS256) with access + refresh token pair.

### Backend — Python FastAPI

Located in `backend/`. Entry point: `app.main:app` (a single large FastAPI application in `backend/app/main.py`).

**Key backend modules** (`backend/app/`):
- `main.py` — All API routes (single file, large). Prefix `/api`.
- `settings.py` — Config from env vars with `.env` file support. Controls auth mode, payment mode, storage backend.
- `security.py` — Hand-rolled JWT (HS256), refresh tokens, WeChat session key encryption
- `schemas.py` — Pydantic v2 request models
- `scene_store.py` / `generated_scene_store.py` / `scene_store_postgres.py` — Scene storage (JSON files or PostgreSQL)
- `auth_store.py` / `auth_store_postgres.py` — Auth storage (JSON or PostgreSQL)
- `commerce_store.py` — Products/SKU/Orders/CDK storage
- `wechat_auth.py` — WeChat `code2session` integration
- `wechat_pay.py` — WeChat Pay v3 API integration
- `scene_adapter.py` / `scene_publication.py` — Scene generation and publishing pipeline
- `hotspot_permissions.py` — Role-based hotspot editing permissions
- `access_control.py` — Authorization helpers
- `postgres.py` — Database connection pool

**Scene worker** (`backend/app/scene_worker/`):
- `analyze_scene.py` — AI-powered scene analysis using Core100/智谱AI vision model
- `generate_audio.py` — TTS audio generation for vocabulary
- `scene_assets.py` — Asset management for generated scenes
- `json_repair.py` — Robustness layer for AI-generated JSON output

**File storage** (`backend/app/storage/`):
- `factory.py` — Storage backend selection based on `STORAGE_BACKEND` env var
- `local.py` — Local filesystem storage
- `cos.py` — Tencent Cloud COS storage
- `r2.py` — Cloudflare R2 storage
- `config_store.py` — Storage configuration persistence
- `base.py` — Abstract storage interface

**Admin routes** (`backend/app/routes/`):
- `storage_admin.py` — Admin API for storage configuration

**Operational scripts** (`backend/scripts/`):
- `run_scene_worker.py` — Standalone scene worker with daemon mode and parallel workers (`--workers N`)
- `republish_unpublished_scenes.py` — Finds and publishes scenes with `autoPublish=True` but no `publishedSceneId`
- `seed_demo_catalog.py` — Seeds 3 membership tiers (Pro/Plus/Max) with SKU benefits
- `migrate_auth_to_postgres.py` / `migrate_scenes_to_postgres.py` — JSON → PostgreSQL migration

**Storage backend selection** (controlled by env vars):
- `AUTH_STORE_BACKEND`: `json` (default) or `postgres`
- `COMMERCE_STORE_BACKEND`: `disabled` (default) or `postgres`
- `SCENE_STORE_BACKEND`: `json` (default) or `postgres`
- `PAYMENT_MODE`: `mock` (default) or `wechat_pay` or `virtual_pay`

**Data files** (`backend/data/`): JSON files for scenes, tasks, uploads, auth when using JSON storage.

### Backend — Rust Axum (new, production backend)

Located in `backend-rust/`. Entry point: `src/main.rs`. Axum + SQLx + Tokio. Connects to the same PostgreSQL database.

**Structure** (`backend-rust/src/`):
- `main.rs` — Server bootstrap, DB pool, CORS, static assets, video cleanup spawn
- `config.rs` — Env-based configuration
- `state.rs` — Shared AppState (pool + config)
- `error.rs` / `response.rs` — Error handling and response types
- `api/` — Route handlers: auth, scene, product, order, payment, task, upload, user, video, hotspot, cdk, health, my_scenes
- `services/` — Business logic: jwt, scene_worker, video_export, video_cleanup, virtual_pay, wechat_auth, wechat_session
- `db/` — Database access: users, scenes, products, orders, tasks, uploads, videos, credits
- `models/` — Data structures: user, scene, product, order, task, upload, video, commerce
- `middleware/` — Auth middleware

**Important:** The env file in the repo is named `env` (no dot prefix). Rust's `dotenvy` reads `.env`. First deployment requires `cp env .env`.

## Development Commands

### Python Backend
```bash
# Start API server (from backend/)
cd backend && bash start-api.sh
# Or directly:
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Run all backend tests
cd backend && python3 -m pytest tests/ -v

# Run a single test file
cd backend && python3 -m pytest tests/test_auth_api.py -v

# Run a single test function
cd backend && python3 -m pytest tests/test_auth_api.py::test_login -v

# Run standalone scene worker (daemon mode, 2 parallel workers)
cd backend && python3 scripts/run_scene_worker.py --daemon --workers 2
```

### Rust Backend
```bash
# Build (from backend-rust/)
cd backend-rust && cargo build

# Run in dev mode
cd backend-rust && cargo run

# Build for release
cd backend-rust && cargo build --release
```

### Frontend (Mini Program)
No build step. Open the project root directory in WeChat DevTools (微信开发者工具). ES6 transpilation and SASS provided by DevTools.

```bash
# Run miniapp-side tests (Node.js based)
node tests/hotspot-editor-geometry.test.js
```

### Database Migrations
```bash
# SQL schemas in backend/sql/ and backend-rust/sql/
# Auth: backend/sql/auth_postgres_schema.sql
# Commerce: backend/sql/commerce_postgres_schema.sql
# Scenes: backend/sql/scene_postgres_schema.sql
# CDK: backend/sql/cdk_codes_schema.sql

# Seed demo data
cd backend && python3 scripts/seed_demo_catalog.py

# Migrate auth from JSON to PostgreSQL
cd backend && python3 scripts/migrate_auth_to_postgres.py

# Migrate scenes to PostgreSQL
cd backend && python3 scripts/migrate_scenes_to_postgres.py
```

## Deployment (Staging Server)

**Server:** Ubuntu 24.04, 宝塔面板, Nginx, PostgreSQL 18.0

**Request flow:** WeChat Mini Program → Nginx (443/SSL) → Rust backend (127.0.0.1:8001) → PostgreSQL (localhost:5432, database `weixin_saas_rust`)

**Nginx config:** `/www/server/panel/vhost/nginx/stag.cps.vin.conf` — `/api/` and `/assets/` proxied to Rust backend. **Do not modify via 宝塔 panel** — config is hand-written.

```bash
# Deploy Rust binary (from local machine)
cd backend-rust && cargo build --release
scp target/release/backend-rust root@118.24.42.187:/www/wwwroot/stag.cps.vin/weixin-demo-01/backend-rust/target/release/

# Remote: restart Rust backend
kill $(pgrep -f 'target/release/backend-rust')
cd /www/wwwroot/stag.cps.vin/weixin-demo-01/backend-rust && nohup ./target/release/backend-rust > /tmp/rust-backend.log 2>&1 &

# Remote: check logs
tail -f /tmp/rust-backend.log

# Nginx reload after config change
/www/server/nginx/sbin/nginx -t && /www/server/nginx/sbin/nginx -s reload

# Database: backup
su - postgres -c "/www/server/pgsql/bin/pg_dump weixin_saas_rust" > backup.sql
```

## Key Configuration

Environment variables loaded from `backend/.env` (Python) or `backend-rust/.env` (Rust). Important ones:

| Variable | Default | Purpose |
|----------|---------|---------|
| `AUTH_WECHAT_LOGIN_MODE` | `mock` | `mock` or `code2session` |
| `AUTH_ENABLE_DEBUG_USER_HEADER` | `false` | Allow `X-Debug-User-Id` header (dev only) |
| `PAYMENT_MODE` | `mock` | `mock`, `wechat_pay`, or `virtual_pay` |
| `DATABASE_URL` | — | PostgreSQL connection string |
| `DATABASE_SCHEMA` | `public` | PostgreSQL schema |
| `SCENE_STORE_BACKEND` | `json` | `json` or `postgres` |
| `CORE100_MODEL` | `glm-4v-flash` | AI model for scene generation |
| `ZHIPUAI_API_KEY` | — | 智谱AI API key for scene worker |
| `HOTSPOT_EDITOR_ENABLED` | `true` | Enable hotspot editing UI |
| `STORAGE_BACKEND` | `local` | `local`, `cos`, or `r2` |
| `VIDEO_RETENTION_HOURS` | `3` | Auto-delete exported videos after N hours |
| `SERVER_PORT` | `8000` | Rust backend listen port (`8001` on staging) |
| `PUBLIC_BASE_URL` | — | Public-facing URL for this backend instance |

## API Structure

All API routes under `/api`:
- `/api/auth/*` — WeChat login, token refresh, logout
- `/api/me` — User profile
- `/api/scenes/*` — Public scenes, generated scenes, hotspot editing
- `/api/products/*`, `/api/orders/*` — Commerce
- `/api/payments/*` — WeChat Pay integration
- `/api/virtual-pay/*` — WeChat virtual payment (xpay)
- `/api/uploads/*` — Image upload
- `/api/tasks/*` — Scene generation tasks
- `/api/videos/*` — Video export and management
- `/api/cdk/*` — CDK redemption codes
- `/api/admin/*` — Admin dashboard (basic auth protected)

## Key Patterns

**Dual backend:** Python backend is the original, fully-featured implementation. Rust backend is the newer production backend sharing the same PostgreSQL database. Both can run independently. Staging/production runs Rust.

**Scene data flow:** User uploads image → task created → scene worker (AI analysis + TTS generation) → scene published with hotspots → viewed in scene_runtime with interactive hotspots.

**Video export:** Scenes can be exported as video files. Exported videos are auto-deleted after `VIDEO_RETENTION_HOURS` (default 3h). A background cleanup task runs periodically (Rust: `video_cleanup` service).

**Factory pattern for storage:** Auth, commerce, scene, and file storage all use factory functions that select the backend implementation based on env vars. Adding a new storage backend means implementing the existing interface and updating the factory.

**JWT auth chain:** Access token (short-lived, 2h) + refresh token (30d). Frontend `services/api.js` transparently refreshes on 401. Backend verifies via `security.py` (Python) or `services/jwt.rs` (Rust).

**Audio playback:** Uses `InnerAudioContext` with playback rate control. Pre-generated TTS audio preferred; falls back to live TTS if unavailable.

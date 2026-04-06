# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WeChat Mini Program (微信小程序) + FastAPI backend for **English learning through interactive panoramic/VR scenes** ("英语场景"). Users view panoramic images with interactive hotspots that teach English vocabulary and sentences via TTS audio.

**Live domain:** `https://e.cps.vin` — API at `/api`, static assets served from root.

## Architecture

### Frontend — WeChat Mini Program

Standard WeChat Mini Program structure. Pages are in `pages/`, services in `services/`, shared logic in `shared/`.

**Pages** (registered in `app.json`):
- `login` — WeChat auth login
- `home` — Scene browsing home
- `library` — Scene library with categories/collections
- `scene_runtime` — Core panoramic scene viewer with hotspot interaction, swipe navigation between scenes
- `create_scene` — Upload images to generate new scenes
- `my_scenes` — User's created scenes
- `products` / `orders` — Commerce (product catalog, order management)

**Key service modules** (`services/`):
- `api.js` — HTTP client wrapping `wx.request`, auto-injects auth headers, waits for auth readiness before requests
- `auth.js` — WeChat login flow (silent login → token refresh → full re-login)
- `session.js` — Access/refresh token storage in `wx.getStorageSync`
- `config.js` — Reads `apiBaseUrl`/`staticBaseUrl` from app globalData, falls back to `config/runtime.js`
- `scene.js`, `product.js`, `order.js`, `payment.js`, `upload.js`, `task.js`, `user.js` — Domain API wrappers

**Shared scene logic** (`shared/scene/`):
- `scene-registry.js` — Static list of built-in scenes with navigation helpers
- `scene-page.js` — Scene page behavior mixin: hotspot editing, swipe detection, navigation between scenes
- `hotspot-editor.js` — Hotspot position/resize geometry calculations

**Auth flow:** `app.js` → `initializeAuth()` tries cached access token → refresh token → silent `wx.login`. Tokens are JWT (HS256) with access + refresh token pair.

### Backend — FastAPI (Python)

Located in `backend/`. Entry point: `app.main:app` (a single large FastAPI application in `backend/app/main.py`).

**Key backend modules** (`backend/app/`):
- `main.py` — All API routes (single file, large). Prefix `/api` via static mount.
- `settings.py` — Config from env vars with `.env` file support. Controls auth mode, payment mode, storage backend.
- `security.py` — Hand-rolled JWT (HS256), refresh tokens, WeChat session key encryption
- `schemas.py` — Pydantic v2 request models
- `scene_store.py` / `generated_scene_store.py` — JSON file-based scene storage with thread locking
- `auth_store.py` / `auth_store_postgres.py` — Auth storage (JSON or PostgreSQL)
- `commerce_store.py` — Products/SKU/Orders storage
- `wechat_auth.py` — WeChat `code2session` integration
- `wechat_pay.py` — WeChat Pay v3 API integration (signature, encryption, notifications)
- `scene_adapter.py` / `scene_publication.py` — Scene generation and publishing pipeline
- `worker_runner.py` — Inline scene generation worker (uses Core100/智谱AI for scene analysis)
- `postgres.py` — Database connection pool
- `hotspot_permissions.py` — Role-based hotspot editing permissions

**Storage backends** (controlled by env vars):
- `AUTH_STORE_BACKEND`: `json` (default) or `postgres`
- `COMMERCE_STORE_BACKEND`: `disabled` (default) or `postgres`
- `PAYMENT_MODE`: `mock` (default) or `wechat_pay`

**Data files** (`backend/data/`): JSON files for scenes, tasks, uploads, auth when using JSON storage.

## Development Commands

### Backend
```bash
# Start API server (from backend/)
cd backend && bash start-api.sh
# Or directly:
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Run backend tests
cd backend && python3 -m pytest tests/ -v

# Run a single test file
cd backend && python3 -m pytest tests/test_auth_api.py -v
```

### Frontend (Mini Program)
No build step. Open the project root directory in WeChat DevTools (微信开发者工具). The mini program uses ES6 transpilation provided by DevTools.

```bash
# Run miniapp-side tests (Node.js based, if configured)
node tests/<test-file>.test.js
```

### Database Migrations
```bash
# SQL schemas in backend/sql/
# Auth: backend/sql/auth_postgres_schema.sql
# Commerce: backend/sql/commerce_postgres_schema.sql

# Seed demo data
cd backend && python3 scripts/seed_demo_catalog.py

# Migrate auth from JSON to PostgreSQL
cd backend && python3 scripts/migrate_auth_to_postgres.py
```

## Key Configuration

Environment variables are loaded from `backend/.env`. Important ones:

| Variable | Default | Purpose |
|----------|---------|---------|
| `AUTH_WECHAT_LOGIN_MODE` | `mock` | `mock` or `code2session` |
| `AUTH_ENABLE_DEBUG_USER_HEADER` | `true` | Allow `X-Debug-User-Id` header |
| `PAYMENT_MODE` | `mock` | `mock` or `wechat_pay` |
| `DATABASE_URL` | — | PostgreSQL connection string |
| `CORE100_MODEL` | `glm-4v-flash` | AI model for scene generation |
| `HOTSPOT_EDITOR_ENABLED` | `true` | Enable hotspot editing UI |

## API Structure

All API routes are in `backend/app/main.py` under these prefixes:
- `/api/auth/*` — WeChat login, token refresh, logout
- `/api/me` — User profile
- `/api/scenes/*` — Public scenes, generated scenes, hotspot editing
- `/api/products/*`, `/api/orders/*` — Commerce
- `/api/payments/*` — WeChat Pay integration
- `/api/uploads/*` — Image upload
- `/api/tasks/*` — Scene generation tasks
- `/api/admin/*` — Admin dashboard (basic auth protected)

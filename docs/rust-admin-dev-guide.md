# Rust Admin Backend 开发指导

> 日期: 2026-05-07
> 关联文档: [API 契约 PRD](./rust-admin-backend-prd.md)

---

## 1. 架构决策

**在现有 `backend-rust/` 内开发，不做独立目录。**

- Admin 代码全部放在 `backend-rust/src/api/admin/` 子目录
- 复用现有 `db/`、`models/`、`services/`、`middleware/`、`config.rs`、`state.rs`、`error.rs`、`response.rs`
- 现有用户侧代码的文件一个都不改，只在 `api/mod.rs` 加一行 `.merge(admin::routes())`
- 开发期间 Nginx 不动，admin 继续走 Python（8000），开发完再切

---

## 2. 目标目录结构

```
backend-rust/src/
├── api/
│   ├── mod.rs                    # [改] 加一行 .merge(admin::routes())
│   ├── admin/                    # [新增] 全部 admin 代码
│   │   ├── mod.rs                # admin Router 注册
│   │   ├── auth.rs               # POST login, GET me
│   │   ├── overview.rs           # GET overview
│   │   ├── users.rs              # 用户 CRUD + 批量操作
│   │   ├── products.rs           # 商品 CRUD
│   │   ├── skus.rs               # SKU CRUD
│   │   ├── orders.rs             # 订单查询 + 批量删除
│   │   ├── cdk.rs                # CDK 生成 + 管理
│   │   ├── tasks.rs              # 任务查询 + 重试 + 批量生成
│   │   ├── public_scenes.rs      # 公开场景 CRUD + 批量操作
│   │   ├── generated_scenes.rs   # 生成场景列表 + 发布
│   │   ├── categories.rs         # 分类 CRUD
│   │   ├── collections.rs        # 合集 CRUD
│   │   ├── storage.rs            # 存储后端管理
│   │   └── uploads.rs            # Admin 图片上传
│   ├── auth.rs                   # [不改]
│   ├── scene.rs                  # [不改]
│   └── ...                       # [不改]
├── middleware/
│   ├── auth.rs                   # [不改] 已有 AuthUser
│   ├── mod.rs                    # [改] 加 pub mod admin_auth;
│   └── admin_auth.rs             # [新增] AdminUser extractor
├── config.rs                     # [改] 加 admin 相关字段
├── db/                           # [改] 加 admin 需要的查询方法
├── models/                       # [改] 加 admin 专用 response struct
├── services/jwt.rs               # [不改] 已有 create/decode
└── main.rs                       # [改] 加 admin_web ServeDir
```

标记说明：
- `[不改]` — 不修改，直接复用
- `[改]` — 小幅修改（加字段/加方法/加一行 merge）
- `[新增]` — 新文件

---

## 3. 需要修改的现有文件

### 3.1 `config.rs` — 新增字段

```rust
// 在 Config struct 中新增:
pub admin_dashboard_enabled: bool,
pub admin_dashboard_username: String,
pub admin_dashboard_password: String,
pub admin_web_dir: String,

// 在 Config::load() 中新增:
admin_dashboard_enabled: env_bool("ADMIN_DASHBOARD_ENABLED", true),
admin_dashboard_username: env_or("ADMIN_DASHBOARD_USERNAME", "admin"),
admin_dashboard_password: env_or("ADMIN_DASHBOARD_PASSWORD", "admin123456"),
admin_web_dir: env_or("ADMIN_WEB_DIR", "../backend/admin_web".to_string()),
```

### 3.2 `middleware/mod.rs` — 新增 admin_auth 模块

```rust
pub mod admin_auth;   // 新增
```

### 3.3 `api/mod.rs` — 合并 admin 路由

```rust
pub mod admin;   // 新增

pub fn routes() -> Router<AppState> {
    Router::new()
        // ... 现有路由不动 ...
        .merge(admin::routes())   // 新增这一行
}
```

### 3.4 `main.rs` — 挂载 admin_web 静态文件

在 `nest_service("/assets", ...)` 后面加：

```rust
// Admin 前端静态文件
if state.config.admin_dashboard_enabled {
    let admin_dir = state.config.admin_web_dir.clone();
    let admin_path = std::path::Path::new(&admin_dir);
    if admin_path.exists() {
        app = app.nest_service("/admin", tower_http::services::ServeDir::new(admin_path));
    }
}
```

### 3.5 `db/` — 新增 admin 需要的查询

在现有 db 文件中追加函数，不改现有函数：

| 文件 | 新增函数 |
|------|----------|
| `db/users.rs` | `list_users()`, `count_users()`, `update_user_status()`, `update_user_role()`, `delete_users_batch()` |
| `db/scenes.rs` | `list_all_public_scenes()`, `list_all_generated_scenes()`, `count_public_scenes()`, `count_generated_scenes()`, `create_scene()`, `update_scene()`, `delete_scenes_batch()`, `update_scenes_visibility_batch()`, `update_scenes_free_batch()`, `update_scenes_category_batch()`, `list_categories()`, `create_category()`, `update_category()`, `delete_category()`, `count_scenes_by_category()`, `list_collections()`, `create_collection()`, `update_collection()`, `delete_collection()`, `count_scenes_by_collection()` |
| `db/tasks.rs` | `list_all_tasks()`, `count_tasks()`, `count_tasks_by_status()`, `count_today_tasks()`, `reset_task_to_queued()`, `delete_tasks_batch()`, `create_task_batch()` |
| `db/products.rs` | `list_all_products()`, `create_product()`, `update_product()`, `update_product_status()`, `list_all_skus()`, `create_sku()`, `update_sku()` |
| `db/orders.rs` | `list_all_orders()`, `get_order_detail()`, `delete_orders_batch()`, `count_orders()`, `sum_paid_amount()` |
| `db/credits.rs` | `get_membership_summary()`, `get_credit_summary()`, `count_active_members()` |
| `db/videos.rs` | (无需新增) |
| `db/uploads.rs` | `create_admin_upload()` |
| `db/mod.rs` | 可能需要新增 `cdk.rs` (CDK 查询) 和 `storage.rs` (存储配置) |

### 3.6 `models/` — 新增 admin response struct

建议新增文件 `models/admin.rs`：

```rust
// Admin 登录响应
pub struct AdminLoginResponse { ... }
// Admin 用户视图
pub struct AdminUserView { ... }
// Admin 任务视图
pub struct AdminTaskView { ... }
// Admin 场景视图
pub struct AdminSceneView { ... }
// Admin 概览
pub struct AdminOverview { ... }
// Admin 请求体
pub struct AdminLoginRequest { ... }
pub struct AdminProductRequest { ... }
// ... 等等
```

在 `models/mod.rs` 中加 `pub mod admin;`。

---

## 4. 新增文件详解

### 4.1 `middleware/admin_auth.rs` — Admin 鉴权中间件

复用现有 `services/jwt.rs` 的 `decode_access_token`，新增一个 `AdminUser` extractor：

```rust
use axum::extract::FromRequestParts;
use crate::services::jwt;
use crate::state::AppState;
use crate::error::AppError;

pub struct AdminUser {
    pub username: String,
    pub role: String,
}

impl FromRequestParts<AppState> for AdminUser {
    type Rejection = AppError;

    async fn from_request_parts(parts: &mut Parts, state: &AppState) -> Result<Self, Self::Rejection> {
        // 1. 提取 Bearer token（复用 AuthUser 的逻辑）
        // 2. decode_access_token
        // 3. 校验 role == "admin" || role == "super_admin"
        // 4. 校验 sid == "admin_console"
        // 5. 返回 AdminUser
    }
}
```

与现有 `AuthUser` 的区别：
- `AuthUser` 校验的是微信用户的 JWT（sub 是 user_id）
- `AdminUser` 校验的是 admin JWT（sub 是 "admin"，sid 是 "admin_console"）

### 4.2 `api/admin/mod.rs` — 路由注册

```rust
pub mod auth;
pub mod overview;
pub mod users;
pub mod products;
pub mod skus;
pub mod orders;
pub mod cdk;
pub mod tasks;
pub mod public_scenes;
pub mod generated_scenes;
pub mod categories;
pub mod collections;
pub mod storage;
pub mod uploads;

use axum::Router;
use axum::routing::{get, post, put, delete};
use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        // 认证
        .route("/api/admin/auth/login", post(auth::login))
        .route("/api/admin/auth/me", get(auth::me))
        // 概览
        .route("/api/admin/overview", get(overview::get_overview))
        // 用户
        .route("/api/admin/users", get(users::list_users))
        .route("/api/admin/users/{user_id}", get(users::get_user))
        .route("/api/admin/users/{user_id}/block", post(users::block_user))
        .route("/api/admin/users/{user_id}/unblock", post(users::unblock_user))
        .route("/api/admin/users/{user_id}/grant-admin", post(users::grant_admin))
        .route("/api/admin/users/{user_id}/revoke-admin", post(users::revoke_admin))
        .route("/api/admin/users/batch-delete", post(users::batch_delete))
        // 商品
        .route("/api/admin/products", get(products::list).post(products::create))
        .route("/api/admin/products/{product_id}", get(products::get).put(products::update))
        .route("/api/admin/products/{product_id}/publish", post(products::publish))
        .route("/api/admin/products/{product_id}/disable", post(products::disable))
        // SKU
        .route("/api/admin/skus", get(skus::list).post(skus::create))
        .route("/api/admin/skus/{sku_id}", put(skus::update))
        // 订单
        .route("/api/admin/orders", get(orders::list))
        .route("/api/admin/orders/{order_id}", get(orders::get))
        .route("/api/admin/orders/batch-delete", post(orders::batch_delete))
        // CDK
        .route("/api/admin/cdk-codes", get(cdk::list))
        .route("/api/admin/cdk-codes/generate", post(cdk::generate))
        .route("/api/admin/cdk-codes/batch-delete", post(cdk::batch_delete))
        // 任务
        .route("/api/admin/tasks", get(tasks::list))
        .route("/api/admin/tasks/{task_id}", get(tasks::get))
        .route("/api/admin/tasks/{task_id}/retry", post(tasks::retry))
        .route("/api/admin/tasks/batch-delete", post(tasks::batch_delete))
        .route("/api/admin/tasks/scene-generate-batch", post(tasks::scene_generate_batch))
        // 公开场景
        .route("/api/admin/public-scenes", get(public_scenes::list).post(public_scenes::create))
        .route("/api/admin/public-scenes/{scene_id}", put(public_scenes::update))
        .route("/api/admin/public-scenes/batch-delete", post(public_scenes::batch_delete))
        .route("/api/admin/public-scenes/batch-visibility", post(public_scenes::batch_visibility))
        .route("/api/admin/public-scenes/batch-free", post(public_scenes::batch_free))
        .route("/api/admin/public-scenes/batch-category", post(public_scenes::batch_category))
        .route("/api/admin/public-scenes/{scene_id}/republish", post(public_scenes::republish))
        // 生成场景
        .route("/api/admin/generated-scenes", get(generated_scenes::list))
        .route("/api/admin/generated-scenes/{scene_id}/publish", post(generated_scenes::publish))
        // 分类
        .route("/api/admin/scene-categories", get(categories::list).post(categories::create))
        .route("/api/admin/scene-categories/{category_id}", put(categories::update).delete(categories::delete))
        // 合集
        .route("/api/admin/scene-collections", get(collections::list).post(collections::create))
        .route("/api/admin/scene-collections/{collection_id}", put(collections::update).delete(collections::delete))
        // 存储
        .route("/api/admin/storage/overview", get(storage::overview))
        .route("/api/admin/storage/configs", get(storage::get_configs))
        .route("/api/admin/storage/configs/{backend_id}", put(storage::update_config))
        .route("/api/admin/storage/test/{backend_id}", post(storage::test_connection))
        .route("/api/admin/storage/activate/{backend_id}", post(storage::activate))
        .route("/api/admin/storage/usage", get(storage::usage))
        // 上传
        .route("/api/admin/uploads/image", post(uploads::upload_image))
}
```

---

## 5. 分期开发计划

### Phase 1: 基础框架 + 认证 + 只读视图

**目标：能登录、能看数据、不能改。预计工作量：约 20 个 API。**

| # | 任务 | 涉及文件 | 依赖 |
|---|------|----------|------|
| 1.1 | `config.rs` 加 admin 字段 | `config.rs` | 无 |
| 1.2 | `AdminUser` 中间件 | `middleware/admin_auth.rs` | 1.1 |
| 1.3 | `api/admin/mod.rs` 路由骨架 | `api/admin/mod.rs` | 无 |
| 1.4 | `api/mod.rs` 加 merge | `api/mod.rs` | 1.3 |
| 1.5 | `main.rs` 挂载 admin_web | `main.rs` | 1.1 |
| 1.6 | Admin 登录 + me | `api/admin/auth.rs` | 1.1, 1.2 |
| 1.7 | Admin 概览 | `api/admin/overview.rs`, `db/*.rs` | 1.2 |
| 1.8 | 用户列表 + 详情 | `api/admin/users.rs`, `db/users.rs`, `db/credits.rs` | 1.2 |
| 1.9 | 公开场景列表 | `api/admin/public_scenes.rs`, `db/scenes.rs` | 1.2 |
| 1.10 | 生成场景列表 | `api/admin/generated_scenes.rs`, `db/scenes.rs` | 1.2 |
| 1.11 | 任务列表 + 详情 | `api/admin/tasks.rs`, `db/tasks.rs` | 1.2 |
| 1.12 | 商品列表 | `api/admin/products.rs`, `db/products.rs` | 1.2 |
| 1.13 | SKU 列表 | `api/admin/skus.rs`, `db/products.rs` | 1.2 |
| 1.14 | 订单列表 + 详情 | `api/admin/orders.rs`, `db/orders.rs` | 1.2 |
| 1.15 | 分类列表 | `api/admin/categories.rs`, `db/scenes.rs` | 1.2 |
| 1.16 | 合集列表 | `api/admin/collections.rs`, `db/scenes.rs` | 1.2 |
| 1.17 | CDK 列表 | `api/admin/cdk.rs`, `db/cdk.rs` (新) | 1.2 |
| 1.18 | **编译验证 + cargo test** | — | 1.1-1.17 |
| 1.19 | **手动验证：浏览器打开 /admin 测试登录 + 只读页面** | — | 1.18 |

**Phase 1 完成标志**：启动 Rust 后端，`/admin` 页面能登录，所有列表页能正常显示数据。

### Phase 2: 写操作 + 批量管理

**目标：完整 CRUD。预计工作量：约 30 个 API。**

| # | 任务 | 涉及文件 |
|---|------|----------|
| 2.1 | 用户 block/unblock/grant/revoke/batch-delete | `api/admin/users.rs`, `db/users.rs` |
| 2.2 | 商品 create/update/publish/disable | `api/admin/products.rs`, `db/products.rs` |
| 2.3 | SKU create/update | `api/admin/skus.rs`, `db/products.rs` |
| 2.4 | 订单 batch-delete | `api/admin/orders.rs`, `db/orders.rs` |
| 2.5 | CDK generate/batch-delete | `api/admin/cdk.rs`, `db/cdk.rs` |
| 2.6 | 任务 retry/batch-delete/scene-generate-batch | `api/admin/tasks.rs`, `db/tasks.rs` |
| 2.7 | 公开场景 create/update/batch-delete/batch-visibility/batch-free/batch-category/republish | `api/admin/public_scenes.rs`, `db/scenes.rs` |
| 2.8 | 生成场景 publish（含 publication 记录创建） | `api/admin/generated_scenes.rs`, `db/scenes.rs` |
| 2.9 | 分类 create/update/delete | `api/admin/categories.rs`, `db/scenes.rs` |
| 2.10 | 合集 create/update/delete | `api/admin/collections.rs`, `db/scenes.rs` |
| 2.11 | Admin 图片上传 | `api/admin/uploads.rs`, `db/uploads.rs` |
| 2.12 | **全量测试：所有 CRUD 操作在浏览器上走通** | — |

**Phase 2 完成标志**：Admin 面板所有功能可用，与 Python 版本行为一致。

### Phase 3: 存储管理

**目标：可配置存储后端。预计工作量：6 个 API。**

| # | 任务 | 涉及文件 |
|---|------|----------|
| 3.1 | 存储概览 + 配置读取 | `api/admin/storage.rs`, `db/storage.rs` (新) |
| 3.2 | 存储配置更新 | `api/admin/storage.rs` |
| 3.3 | 存储连接测试 + 激活 | `api/admin/storage.rs` |
| 3.4 | 存储用量统计 | `api/admin/storage.rs` |

**Phase 3 完成标志**：存储管理页面可用，能切换后端。

### Phase 4: 切换 + 清理

**目标：Python 退役，Nginx 简化。**

| # | 任务 |
|---|------|
| 4.1 | 逐个验证 57 条 API 与 Python 版本响应格式一致 |
| 4.2 | 更新 Nginx：去掉 admin 转发到 8000，所有 `/api/` 统一走 8001 |
| 4.3 | 停止 Python 后端 |
| 4.4 | 更新 CLAUDE.md、部署文档 |

---

## 6. 关键复用清单

以下是现有代码中可以直接复用的部分，**不需要重写**：

| 模块 | 文件 | 复用内容 |
|------|------|----------|
| JWT | `services/jwt.rs` | `create_access_token()`, `decode_access_token()` — Admin 登录直接调用，传入 `role="super_admin"`, `sid="admin_console"` |
| 响应 | `response.rs` | `success()`, `fail()` — 所有 admin API 统一使用 |
| 错误 | `error.rs` | `AppError` 枚举 — 直接使用 `BadRequest`, `Unauthorized`, `NotFound`, `Internal` |
| 状态 | `state.rs` | `AppState { pool, config }` — 所有 handler 通过 State 共享 |
| DB-用户 | `db/users.rs` | `find_user_by_id()` — Admin 查用户详情复用 |
| DB-场景 | `db/scenes.rs` | `get_scene()`, `get_scenes_by_ids()` — Admin 查场景复用 |
| DB-任务 | `db/tasks.rs` | 现有函数部分可复用 |
| DB-商品 | `db/products.rs` | 现有函数部分可复用 |
| DB-订单 | `db/orders.rs` | 现有函数部分可复用 |
| Model-用户 | `models/user.rs` | `User` struct — 直接序列化给 admin 响应 |
| Model-场景 | `models/scene.rs` | `Scene`, `SceneCategory`, `SceneCollection` — 直接复用 |
| Model-商品 | `models/product.rs` | `Product`, `Sku` — 直接复用 |
| Model-订单 | `models/order.rs` | `Order` — 直接复用 |
| 上传 | `api/upload.rs` | 参考现有上传逻辑，Admin 版区别只在 ownerId |

---

## 7. 开发注意事项

### 7.1 不改现有代码

- 修改 `api/mod.rs` 只加一行 `.merge(admin::routes())`
- 修改 `config.rs` 只在 struct 和 load() 末尾追加字段
- 修改 `db/*.rs` 只追加新函数
- 修改 `models/mod.rs` 只加 `pub mod admin;`
- 修改 `middleware/mod.rs` 只加 `pub mod admin_auth;`
- **绝不修改现有函数签名或行为**

### 7.2 前端兼容

- 响应字段名必须用 **camelCase**（`#[serde(rename_all = "camelCase")]`）
- `publication` 字段：已发布的场景才有，未发布返回 `null`
- CDK 列表接口在 commerce 未启用时返回 `{ "list": [] }` 而非错误
- `coverUrl` / `backgroundUrl` 需要拼成完整 URL（`config.public_base_url + path`），而不是只返回存储路径

### 7.3 asset URL 解析

Admin 返回场景时，需要把存储路径转成完整 URL。参考 Python 的 `asset_url()` 逻辑：

```rust
fn asset_url(config: &Config, path: &str) -> String {
    if path.starts_with("http") {
        path.to_string()
    } else {
        format!("{}{}", config.public_base_url, path)
    }
}
```

### 7.4 Admin 静态文件

`admin_web/` 目前在 `backend/admin_web/`。Rust 的 `admin_web_dir` 配置需要指向这个路径。相对路径基于 Rust 的工作目录（`backend-rust/`），所以默认值应该是 `../backend/admin_web`。

---

## 8. 环境变量汇总

需要在 `backend-rust/.env`（或 `env` 文件）中新增：

```env
ADMIN_DASHBOARD_ENABLED=true
ADMIN_DASHBOARD_USERNAME=admin
ADMIN_DASHBOARD_PASSWORD=admin123456
ADMIN_WEB_DIR=../backend/admin_web
```

---

## 9. 验证方法

### Phase 1 完成后

```bash
# 1. 编译
cd backend-rust && cargo build

# 2. 启动（会同时服务用户侧 + admin）
cargo run

# 3. 测试 admin 登录
curl -X POST http://localhost:8001/api/admin/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123456"}'

# 4. 用返回的 token 测试概览
curl http://localhost:8001/api/admin/overview \
  -H 'Authorization: Bearer <token>'

# 5. 浏览器打开 http://localhost:8001/admin 验证前端加载
```

### Phase 2 完成后

在浏览器中对每个功能页面逐项测试：创建、编辑、删除、批量操作。

### Phase 4 最终验收

1. Nginx 切换：所有请求走 8001
2. Python 停止
3. Admin 面板所有功能正常
4. 小程序用户侧功能不受影响

---

## 10. 风险点

| 风险 | 影响 | 应对 |
|------|------|------|
| `admin_web/` 的 JS 硬编码了某些响应字段名 | 前端不兼容 | 严格按照 PRD 契约的 camelCase 字段名 |
| 存储配置目前持久化在 Python 的 JSON 文件中 | Rust 读取不到 | Phase 3 需要迁移到 PostgreSQL 表或 Rust 自己读 JSON |
| `scene_publications` 表的查询逻辑较复杂 | 开发周期 | 参考 Python `scene_publication.py` 的 SQL 逻辑 |
| 批量场景生成任务需要调用 AI worker | 依赖外部服务 | 复用现有 `services/scene_worker.rs` 的逻辑 |

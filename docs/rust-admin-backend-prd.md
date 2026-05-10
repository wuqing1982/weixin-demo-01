# PRD: Rust Admin Backend — 完全替代 Python Admin 面板

> 日期: 2026-05-06
> 状态: Draft
> 作者: 阿蒙

---

## 1. 目标

用纯 Rust (Axum) 实现一套独立的 Admin 后端，**完全替代当前 Python FastAPI 的 admin 模块**，实现：

- 彻底去掉对 Python 后端的依赖，运维只需维护一个 Rust 二进制
- Admin API 和用户侧 API 共用同一个 Rust 进程（`backend-rust`），通过 role 区分权限
- 与现有 `admin_web/` 前端 100% 兼容，前端零改动

## 2. 背景

当前架构：
- 用户侧 API：Rust (Axum, 端口 8001)，Nginx 转发 `/api/` 到此
- Admin 面板：Python (FastAPI, 端口 8000)，Nginx 转发 `/api/admin/` 和 `/admin/` 到此
- 两者共享 PostgreSQL 数据库 `weixin_saas_rust`

问题：需要同时维护两套后端、两个进程、两套依赖，Python 后端仅用于 admin 就得常驻运行。

目标架构：
- **单一 Rust 二进制**同时服务用户侧和 Admin API
- Nginx 所有 `/api/` 统一转发到 8001
- Admin 静态文件 (`admin_web/`) 由 Rust ServeDir 提供
- Python 后端完全退役

## 3. 通用约定

### 3.1 鉴权

所有 `/api/admin/*` 路由需要 Bearer Token 认证。Token 来自 Admin 登录接口签发的 JWT，payload 包含：

```json
{
  "sub": "admin",
  "typ": "access",
  "role": "admin",
  "sid": "admin_console",
  "iat": 1746000000,
  "exp": 1746007200
}
```

中间件校验逻辑：
1. 解析 `Authorization: Bearer <token>` 头
2. 验证 JWT 签名和过期时间
3. 验证 `role` 为 `admin` 或 `super_admin`
4. 验证 `sid` 为 `admin_console`

### 3.2 统一响应格式

```json
// 成功
{ "code": 0, "data": { ... } }

// 错误
{ "code": <int>, "message": "<string>" }
```

错误码约定：
| code | 含义 |
|------|------|
| 0 | 成功 |
| 4000 | 请求参数错误 / 业务逻辑错误 |
| 4001 | 未认证 / 认证失败 |
| 4004 | 资源不存在 |
| 4090 | 冲突（如分类下有场景引用） |
| 5000 | 服务端内部错误 |

### 3.3 分页参数

支持分页的路由统一使用 Query 参数：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `limit` | `int` | 50 | 每页条数，上限 500 |
| `offset` | `int` | 0 | 偏移量 |

### 3.4 路由前缀

所有 Admin API 路由前缀：`/api/admin/`
Admin 前端静态文件：`/admin/` → `admin_web/index.html`

---

## 4. 完整 API 契约

### 4.1 认证 — `/api/admin/auth`

#### POST `/api/admin/auth/login` — 登录

鉴权：无

请求体：
```json
{
  "username": "admin",          // string, 必填, 1-64字符
  "password": "admin123456"     // string, 必填, 1-128字符
}
```

成功响应：
```json
{
  "code": 0,
  "data": {
    "accessToken": "eyJhbGci...",
    "accessTokenExpireAt": "2026-05-06T16:29:39Z",
    "admin": {
      "username": "admin",
      "userId": "",
      "role": "super_admin",
      "loginType": "dashboard_password"
    }
  }
}
```

失败响应 (401)：
```json
{ "code": 4001, "message": "admin credential invalid" }
```

业务规则：
- 校验 `username` 和 `password` 与环境变量 `ADMIN_DASHBOARD_USERNAME` / `ADMIN_DASHBOARD_PASSWORD` 匹配
- 签发 JWT access token（有效期 2 小时），payload `role` 固定为 `super_admin`

#### GET `/api/admin/auth/me` — 获取当前管理员信息

鉴权：Bearer Token

成功响应：
```json
{
  "code": 0,
  "data": {
    "username": "admin",
    "userId": "",
    "role": "super_admin",
    "loginType": "dashboard_password"
  }
}
```

---

### 4.2 概览 — `/api/admin/overview`

#### GET `/api/admin/overview` — 系统全局统计

鉴权：Bearer Token

成功响应：
```json
{
  "code": 0,
  "data": {
    "userCount": 13,
    "publicSceneCount": 107,
    "generatedSceneCount": 107,
    "taskCount": 61,
    "queuedTaskCount": 0,
    "runningTaskCount": 0,
    "failedTaskCount": 0,
    "doneTaskCount": 0,
    "todayTaskCount": 0,
    "productCount": 5,
    "activeProductCount": 3,
    "orderCount": 54,
    "paidOrderCount": 10,
    "paidAmountTotal": "368.55",
    "todayOrderCount": 0,
    "todayPaidAmountTotal": "0.00",
    "activeMemberCount": 4
  }
}
```

`productCount` 之后的字段来自 commerce 模块，commerce 未启用时应省略或返回零值。

---

### 4.3 用户管理 — `/api/admin/users`

#### GET `/api/admin/users` — 用户列表

Query 参数：`limit` (int, 默认 50, 范围 1-200)

成功响应：
```json
{
  "code": 0,
  "data": {
    "list": [
      {
        "id": "user_xxx",
        "role": "user",
        "isAdmin": false,
        "displayName": "张三",
        "avatarUrl": "",
        "mobile": null,
        "mobileVerified": false,
        "status": "active",
        "lastLoginAt": "2026-05-01T12:00:00Z",
        "createdAt": "2026-04-01T08:00:00Z",
        "updatedAt": "2026-05-01T12:00:00Z",
        "memberSummary": { "isActive": true },
        "creditSummary": { "sceneGenerateBalance": 5 }
      }
    ]
  }
}
```

`memberSummary` 和 `creditSummary` 在 commerce 未启用时可为空对象 `{}`。

#### GET `/api/admin/users/{user_id}` — 用户详情

成功响应：基础字段同上，额外包含：
```json
{
  "code": 0,
  "data": {
    "...同用户列表字段...",
    "orders": [
      {
        "orderId": "order_xxx",
        "orderNo": "202605010001",
        "status": "paid",
        "payableAmount": "29.90",
        "createdAt": "2026-05-01T12:00:00Z"
      }
    ],
    "entitlements": [
      {
        "entitlementId": "ent_xxx",
        "entitlementCode": "membership_pro",
        "skuId": "sku_xxx",
        "status": "active",
        "expiresAt": "2026-06-01T00:00:00Z"
      }
    ],
    "generatedScenes": [
      {
        "sceneId": "scene_xxx",
        "title": "Beach Picnic",
        "createdAt": "2026-04-15T10:00:00Z"
      }
    ]
  }
}
```

#### POST `/api/admin/users/{user_id}/block` — 封禁用户

成功响应：返回更新后的用户对象（同列表项结构）

#### POST `/api/admin/users/{user_id}/unblock` — 解封用户

成功响应：返回更新后的用户对象

#### POST `/api/admin/users/{user_id}/grant-admin` — 设为管理员

业务规则：将用户 role 更新为 `admin`。
成功响应：返回更新后的用户对象

#### POST `/api/admin/users/{user_id}/revoke-admin` — 撤销管理员

业务规则：将用户 role 更新为 `user`。
成功响应：返回更新后的用户对象

#### POST `/api/admin/users/batch-delete` — 批量删除用户

请求体：
```json
{
  "userIds": ["user_001", "user_002"]   // string[], 必填, 1-200项
}
```

成功响应：
```json
{ "code": 0, "data": { "deleted": 2 } }
```

---

### 4.4 商品管理 — `/api/admin/products`

#### GET `/api/admin/products` — 商品列表

成功响应：
```json
{
  "code": 0,
  "data": {
    "list": [
      {
        "productId": "prod_001",
        "productCode": "membership_pro",
        "productType": "membership",
        "name": "Pro 会员",
        "subtitle": "解锁全部场景",
        "description": "...",
        "coverUrl": "",
        "status": "active",
        "sortOrder": 1,
        "createdAt": "2026-04-01T00:00:00Z",
        "updatedAt": "2026-04-01T00:00:00Z",
        "skus": [
          {
            "skuId": "sku_001",
            "productId": "prod_001",
            "skuCode": "pro_monthly",
            "name": "月度 Pro",
            "billingType": "one_time",
            "durationDays": 30,
            "status": "active",
            "listPrice": "39.90",
            "salePrice": "29.90",
            "currency": "CNY",
            "stockType": "unlimited",
            "stockCount": null,
            "sortOrder": 0,
            "benefits": [
              {
                "benefitType": "scene_access",
                "benefitValue": "all",
                "benefitJson": {}
              }
            ]
          }
        ]
      }
    ]
  }
}
```

#### POST `/api/admin/products` — 创建商品

请求体：
```json
{
  "productCode": "membership_pro",    // string, 必填, 1-64
  "productType": "membership",        // string, 必填, 1-32
  "name": "Pro 会员",                 // string, 必填, 1-128
  "subtitle": "解锁全部场景",          // string, 可选, 最大255
  "description": "...",               // string, 可选, 最大2000
  "coverUrl": "",                     // string, 可选, 最大1000
  "status": "draft",                  // string, 可选, 默认"draft", 最大32
  "sortOrder": 0                      // int, 可选, 默认0, 0-999999
}
```

成功响应：返回创建的商品对象（含 `productId`）

#### GET `/api/admin/products/{product_id}` — 商品详情

成功响应：同列表项结构，含 `skus` 数组

#### PUT `/api/admin/products/{product_id}` — 更新商品

请求体：同创建商品
成功响应：返回更新后的商品对象

#### POST `/api/admin/products/{product_id}/publish` — 上架

业务规则：`status` → `active`
成功响应：返回更新后的商品对象

#### POST `/api/admin/products/{product_id}/disable` — 下架

业务规则：`status` → `disabled`
成功响应：返回更新后的商品对象

---

### 4.5 SKU 管理 — `/api/admin/skus`

#### GET `/api/admin/skus` — SKU 列表

成功响应：
```json
{
  "code": 0,
  "data": {
    "list": [
      {
        "skuId": "sku_001",
        "productId": "prod_001",
        "skuCode": "pro_monthly",
        "name": "月度 Pro",
        "billingType": "one_time",
        "durationDays": 30,
        "status": "active",
        "listPrice": "39.90",
        "salePrice": "29.90",
        "currency": "CNY",
        "stockType": "unlimited",
        "stockCount": null,
        "sortOrder": 0,
        "benefits": [
          {
            "benefitType": "scene_access",
            "benefitValue": "all",
            "benefitJson": {}
          }
        ]
      }
    ]
  }
}
```

#### POST `/api/admin/skus` — 创建 SKU

请求体：
```json
{
  "productId": "prod_001",             // string, 必填, 1-128
  "skuCode": "pro_monthly",            // string, 必填, 1-64
  "name": "月度 Pro",                  // string, 必填, 1-128
  "billingType": "one_time",           // string, 可选, 默认"one_time", 最大32
  "durationDays": 30,                  // int|null, 可选, 0-3650
  "status": "draft",                   // string, 可选, 默认"draft", 最大32
  "listPrice": "39.90",               // string, 可选, 默认"0.00", 最大32
  "salePrice": "29.90",               // string, 可选, 默认"0.00", 最大32
  "currency": "CNY",                   // string, 可选, 默认"CNY", 最大8
  "stockType": "unlimited",            // string, 可选, 默认"unlimited", 最大32
  "stockCount": null,                  // int|null, 可选, 0-999999999
  "sortOrder": 0,                      // int, 可选, 默认0, 0-999999
  "benefits": [                        // array, 可选, 默认[]
    {
      "benefitType": "scene_access",   // string, 必填, 1-64
      "benefitValue": "all",           // string, 可选, 默认"", 最大128
      "benefitJson": {}                // object, 可选, 默认{}
    }
  ]
}
```

成功响应：返回创建的 SKU 对象

#### PUT `/api/admin/skus/{sku_id}` — 更新 SKU

请求体：同创建 SKU
成功响应：返回更新后的 SKU 对象

---

### 4.6 订单管理 — `/api/admin/orders`

#### GET `/api/admin/orders` — 订单列表

Query 参数：`limit` (int, 默认 50, 范围 1-200)

成功响应：
```json
{
  "code": 0,
  "data": {
    "list": [
      {
        "orderId": "order_001",
        "orderNo": "202605010001",
        "userId": "user_xxx",
        "payableAmount": "29.90",
        "paymentStatus": "paid",
        "status": "completed",
        "createdAt": "2026-05-01T12:00:00Z",
        "paidAt": "2026-05-01T12:01:00Z",
        "items": [
          {
            "productName": "Pro 会员",
            "skuName": "月度 Pro",
            "totalPrice": "29.90"
          }
        ]
      }
    ]
  }
}
```

#### GET `/api/admin/orders/{order_id}` — 订单详情

成功响应：同列表项结构

#### POST `/api/admin/orders/batch-delete` — 批量删除订单

请求体：
```json
{
  "orderIds": ["order_001", "order_002"]   // string[], 必填, 1-200项
}
```

成功响应：
```json
{ "code": 0, "data": { "deleted": 2 } }
```

---

### 4.7 CDK 兑换码管理 — `/api/admin/cdk-codes`

#### GET `/api/admin/cdk-codes` — 兑换码列表

Query 参数：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `status` | string | `""` | 按状态过滤 |
| `skuId` | string | `""` | 按 SKU 过滤 |
| `limit` | int | 200 | 1-500 |
| `offset` | int | 0 | >=0 |

成功响应：
```json
{
  "code": 0,
  "data": {
    "list": [
      {
        "cdkId": "cdk_001",
        "code": "XXXX-XXXX-XXXX",
        "skuId": "sku_001",
        "skuName": "月度 Pro",
        "status": "unused",
        "redeemedBy": null,
        "createdAt": "2026-05-01T00:00:00Z",
        "note": "test"
      }
    ]
  }
}
```

**注意**：前端对 CDK 接口做了 `.catch(() => ({ list: [] }))` 容错。Commerce 未启用时应返回空列表 `{ "list": [] }` 而非 404。

#### POST `/api/admin/cdk-codes/generate` — 批量生成兑换码

请求体：
```json
{
  "skuId": "sku_001",        // string, 必填, 1-128
  "quantity": 10,            // int, 必填, 1-500
  "note": "测试用"            // string, 可选, 默认"", 最大500
}
```

成功响应：
```json
{ "code": 0, "data": { "list": [ { "cdkId": "...", "code": "XXXX-XXXX-XXXX", ... } ] } }
```

#### POST `/api/admin/cdk-codes/batch-delete` — 批量删除兑换码

请求体：
```json
{
  "cdkIds": ["cdk_001", "cdk_002"]   // string[], 必填, 1-500项
}
```

成功响应：
```json
{ "code": 0, "data": { "deleted": 2 } }
```

---

### 4.8 任务管理 — `/api/admin/tasks`

#### GET `/api/admin/tasks` — 任务列表

Query 参数：`limit` (int, 默认 50, 范围 1-200)

成功响应：
```json
{
  "code": 0,
  "data": {
    "list": [
      {
        "taskId": "task_001",
        "ownerId": "user_xxx",
        "uploadId": "upload_001",
        "coverUrl": "https://stag.cps.vin/assets/uploads/xxx.jpg",
        "title": "Beach Picnic",
        "requestSource": "miniapp",
        "autoPublish": false,
        "categoryId": "",
        "collectionIds": [],
        "publishVisibility": "public",
        "status": "done",
        "step": "completed",
        "progress": 100,
        "sceneId": "scene_001",
        "publishedSceneId": "",
        "errorMessage": "",
        "createdAt": "2026-05-01T00:00:00Z",
        "updatedAt": "2026-05-01T00:05:00Z"
      }
    ]
  }
}
```

`coverUrl` 需要从存储路径解析为完整 URL（与用户侧 API 的 `asset_url` 逻辑一致）。

#### GET `/api/admin/tasks/{task_id}` — 任务详情

成功响应：同列表项结构

#### POST `/api/admin/tasks/{task_id}/retry` — 重试失败任务

业务规则：将 `status` 重置为 `queued`，清空 `errorMessage`，重新入队。
成功响应：返回更新后的任务对象

#### POST `/api/admin/tasks/batch-delete` — 批量删除任务

请求体：
```json
{
  "taskIds": ["task_001", "task_002"]   // string[], 必填, 1-200项
}
```

成功响应：
```json
{ "code": 0, "data": { "deleted": 2 } }
```

#### POST `/api/admin/tasks/scene-generate-batch` — 批量创建场景生成任务

请求体：
```json
{
  "items": [                           // array, 必填, 1-50项
    {
      "uploadId": "upload_001",        // string, 必填, >=1字符
      "title": "Beach Picnic"          // string, 可选, 默认"", 最大255
    }
  ],
  "includeVerbs": true,                // bool, 可选, 默认true
  "accent": "en-US",                   // string, 可选, 默认"en-US", 最大32
  "voiceGender": "female",             // string, 可选, 默认"female", 最大32
  "voiceName": "JennyNeural",          // string, 可选, 默认"JennyNeural", 最大64
  "autoPublish": false,                // bool, 可选, 默认false
  "categoryId": "",                    // string, 可选, 默认"", 最大128
  "collectionIds": [],                 // string[], 可选, 默认[], 最大50项
  "publishVisibility": "public"        // string, 可选, 默认"public", 最大32
}
```

业务规则：
- **跳过积分扣减**（Admin 操作不消耗用户积分）
- `ownerId` 使用 Admin 的 actor ID（环境变量或固定值）
- 如果 `autoPublish` 为 true，任务完成后自动发布

成功响应：
```json
{ "code": 0, "data": { "list": [ { "...task对象..." } ] } }
```

---

### 4.9 公开场景管理 — `/api/admin/public-scenes`

#### GET `/api/admin/public-scenes` — 场景列表

成功响应：
```json
{
  "code": 0,
  "data": {
    "list": [
      {
        "sceneId": "scene_001",
        "title": "Beach Picnic",
        "category": "outdoor",
        "categoryId": "cat_001",
        "collectionIds": ["col_001"],
        "visibility": "public",
        "sceneType": "public",
        "backgroundPath": "/assets/scenes/xxx/bg.jpg",
        "coverPath": "/assets/scenes/xxx/cover.jpg",
        "free": false,
        "itemCount": 8,
        "verbCount": 3,
        "items": [],
        "verbs": [],
        "meta": {},
        "publication": {
          "publicationId": "pub_001",
          "publicSceneId": "scene_001",
          "sourceGeneratedSceneId": "gen_001",
          "categoryId": "cat_001",
          "categoryName": "户外",
          "collectionIds": ["col_001"],
          "visibility": "public"
        }
      }
    ]
  }
}
```

`publication` 字段：如果该场景是通过发布生成的，包含发布来源信息；如果是手动创建的，为 `null`。

#### POST `/api/admin/public-scenes` — 创建场景

请求体：
```json
{
  "title": "Beach Picnic",             // string, 必填, 1-255
  "category": "outdoor",               // string, 可选, 默认"", 最大64
  "visibility": "public",              // string, 可选, 默认"public", 最大32
  "sceneType": "public",               // string, 可选, 默认"public", 最大32
  "backgroundPath": "/assets/xxx.jpg", // string, 可选, 默认"", 最大1000
  "coverPath": "/assets/xxx.jpg",      // string, 可选, 默认"", 最大1000
  "items": [],                         // array, 可选, 默认[]
  "verbs": [],                         // array, 可选, 默认[]
  "meta": {}                           // object, 可选, 默认{}
}
```

成功响应：返回创建的场景对象

#### PUT `/api/admin/public-scenes/{scene_id}` — 更新场景

请求体：同创建场景
成功响应：返回更新后的场景对象

#### POST `/api/admin/public-scenes/batch-delete` — 批量删除场景

请求体：
```json
{
  "sceneIds": ["scene_001", "scene_002"]   // string[], 必填, 1-200项
}
```

成功响应：
```json
{ "code": 0, "data": { "deleted": 2 } }
```

#### POST `/api/admin/public-scenes/batch-visibility` — 批量修改可见性

请求体：
```json
{
  "sceneIds": ["scene_001"],          // string[], 必填, 1-200项
  "visibility": "member"              // string, 必填, 枚举: "public" | "private" | "member"
}
```

成功响应：
```json
{ "code": 0, "data": { "patched": 1 } }
```

#### POST `/api/admin/public-scenes/batch-free` — 批量设置免费

请求体：
```json
{
  "sceneIds": ["scene_001"],          // string[], 必填, 1-200项
  "free": true                        // bool, 必填
}
```

成功响应：
```json
{ "code": 0, "data": { "patched": 1, "label": "免费可见" } }
```

`label` 值：`free=true` 时为 `"免费可见"`，`free=false` 时为 `"取消免费"`。

#### POST `/api/admin/public-scenes/batch-category` — 批量移动分类

请求体：
```json
{
  "sceneIds": ["scene_001"],          // string[], 必填, 1-200项
  "categoryId": "cat_002"             // string, 必填, 1-128
}
```

成功响应：
```json
{ "code": 0, "data": { "patched": 1 } }
```

#### POST `/api/admin/public-scenes/{scene_id}/republish` — 重新发布

业务规则：查找该场景的 publication 记录，找到源 generated scene，用源数据覆盖当前 public scene 的 `items`/`verbs`/`backgroundPath`/`coverPath`，保留 `categoryId`/`collectionIds`/`visibility` 不变。

成功响应：返回更新后的场景对象（含 `publication`）

---

### 4.10 生成场景（草稿）管理 — `/api/admin/generated-scenes`

#### GET `/api/admin/generated-scenes` — 生成场景列表

Query 参数：`limit` (int, 默认 100, 范围 1-500)

成功响应：
```json
{
  "code": 0,
  "data": {
    "list": [
      {
        "sceneId": "gen_001",
        "title": "Beach Picnic",
        "category": "outdoor",
        "visibility": "private",
        "sceneType": "private",
        "backgroundUrl": "https://stag.cps.vin/assets/scenes/xxx/bg.jpg",
        "coverUrl": "https://stag.cps.vin/assets/scenes/xxx/cover.jpg",
        "ownerId": "user_xxx",
        "itemCount": 8,
        "verbCount": 3,
        "meta": {},
        "publication": null
      }
    ]
  }
}
```

**注意**：`backgroundUrl` 和 `coverUrl` 是解析后的完整 URL（不是原始存储路径），这与 public scenes 的 `backgroundPath`/`coverPath` 不同。

#### POST `/api/admin/generated-scenes/{scene_id}/publish` — 发布草稿

请求体：
```json
{
  "title": "",                        // string, 可选, 默认"", 最大255（空则使用原标题）
  "categoryId": "cat_001",            // string, 必填, 1-128
  "collectionIds": ["col_001"],       // string[], 可选, 默认[], 最大50项
  "visibility": "public"              // string, 可选, 默认"public", 最大32
}
```

业务规则：
1. 根据 `scene_id` 找到 generated scene
2. 创建新的 public scene（复制 items/verbs/background/cover）
3. 创建 publication 记录（关联 generated scene → public scene）
4. 返回创建的 public scene 对象

成功响应：返回 public scene 对象（含 `publication`）

---

### 4.11 场景分类管理 — `/api/admin/scene-categories`

#### GET `/api/admin/scene-categories` — 分类列表

成功响应：
```json
{
  "code": 0,
  "data": {
    "list": [
      {
        "categoryId": "cat_001",
        "categoryCode": "outdoor",
        "name": "户外",
        "description": "户外场景",
        "status": "active",
        "sortOrder": 0,
        "createdAt": "2026-04-01T00:00:00Z",
        "updatedAt": "2026-04-01T00:00:00Z"
      }
    ]
  }
}
```

#### POST `/api/admin/scene-categories` — 创建分类

请求体：
```json
{
  "categoryCode": "outdoor",          // string, 必填, 1-64
  "name": "户外",                     // string, 必填, 1-128
  "description": "户外场景",          // string, 可选, 默认"", 最大2000
  "status": "active",                 // string, 可选, 默认"active", 最大32
  "sortOrder": 0                      // int, 可选, 默认0, 0-999999
}
```

#### PUT `/api/admin/scene-categories/{category_id}` — 更新分类

请求体：同创建分类

#### DELETE `/api/admin/scene-categories/{category_id}` — 删除分类

业务规则：如果分类下有场景引用，返回 409。
成功响应：
```json
{ "code": 0, "data": { "deleted": true } }
```
失败响应 (409)：
```json
{ "code": 4090, "message": "分类下存在场景，无法删除" }
```

---

### 4.12 场景合集管理 — `/api/admin/scene-collections`

#### GET `/api/admin/scene-collections` — 合集列表

成功响应：
```json
{
  "code": 0,
  "data": {
    "list": [
      {
        "collectionId": "col_001",
        "collectionCode": "daily_life",
        "name": "日常生活",
        "description": "日常生活场景集",
        "status": "active",
        "coverUrl": "",
        "sortOrder": 0,
        "createdAt": "2026-04-01T00:00:00Z",
        "updatedAt": "2026-04-01T00:00:00Z"
      }
    ]
  }
}
```

#### POST `/api/admin/scene-collections` — 创建合集

请求体：
```json
{
  "collectionCode": "daily_life",     // string, 必填, 1-64
  "name": "日常生活",                  // string, 必填, 1-128
  "description": "日常生活场景集",     // string, 可选, 默认"", 最大2000
  "status": "active",                 // string, 可选, 默认"active", 最大32
  "coverUrl": "",                     // string, 可选, 默认"", 最大1000
  "sortOrder": 0                      // int, 可选, 默认0, 0-999999
}
```

#### PUT `/api/admin/scene-collections/{collection_id}` — 更新合集

请求体：同创建合集

#### DELETE `/api/admin/scene-collections/{collection_id}` — 删除合集

业务规则：如果合集下有场景引用，返回 409。
成功响应：
```json
{ "code": 0, "data": { "deleted": true } }
```

---

### 4.13 存储管理 — `/api/admin/storage`

#### GET `/api/admin/storage/overview` — 存储概览

成功响应：
```json
{
  "code": 0,
  "data": {
    "activeBackend": "local",
    "lastActiveBackend": "local",
    "backends": {
      "local": { "name": "本地存储", "type": "local", "enabled": true },
      "cos": { "name": "腾讯COS", "type": "cos", "enabled": false },
      "r2": { "name": "Cloudflare R2", "type": "r2", "enabled": false }
    },
    "usage": {
      "totalBytes": 0,
      "usedBytes": 0,
      "fileCount": 0,
      "byType": {}
    }
  }
}
```

#### GET `/api/admin/storage/configs` — 存储配置详情

成功响应：
```json
{
  "code": 0,
  "data": {
    "activeBackend": "local",
    "backends": {
      "local": {
        "type": "local",
        "enabled": true,
        "config": { "root_dir": "/www/wwwroot/stag.cps.vin/weixin-demo-01/assets" }
      },
      "cos": {
        "type": "cos",
        "enabled": false,
        "config": {
          "secret_id": "****masked",
          "secret_key": "****masked",
          "region": "ap-guangzhou",
          "bucket": "xxx-1250000000",
          "public_url": "https://xxx-1250000000.cos.ap-guangzhou.myqcloud.com"
        }
      },
      "r2": {
        "type": "r2",
        "enabled": false,
        "config": {
          "account_id": "****masked",
          "access_key_id": "****masked",
          "secret_access_key": "****masked",
          "bucket": "xxx",
          "public_url": "https://xxx.r2.dev"
        }
      }
    }
  }
}
```

**注意**：`configs` 接口的敏感字段（secret_key 等）需要脱敏显示。

#### PUT `/api/admin/storage/configs/{backend_id}` — 更新存储配置

路径参数 `backend_id`：`local` | `cos` | `r2`

请求体：
```json
{
  "name": "本地存储",                  // string, 可选
  "enabled": true,                    // bool, 可选
  "config": {                         // object, 可选, 内容因后端类型不同
    "root_dir": "/path/to/dir"
  }
}
```

`config` 内容因类型而异：
- `local`: `{ "root_dir": string }`
- `cos`: `{ "secret_id", "secret_key", "region", "bucket", "public_url" }`
- `r2`: `{ "account_id", "access_key_id", "secret_access_key", "bucket", "public_url" }`

成功响应：返回更新后的配置

#### POST `/api/admin/storage/test/{backend_id}` — 测试存储连接

成功响应：
```json
{ "code": 0, "data": { "ok": true, "message": "连接成功" } }
```
失败响应：
```json
{ "code": 0, "data": { "ok": false, "message": "连接失败: Access Denied" } }
```

#### POST `/api/admin/storage/activate/{backend_id}` — 激活存储后端

业务规则：先测试连接，成功后才切换 `activeBackend`。
成功响应：
```json
{ "code": 0, "data": { "activeBackend": "cos", "message": "已切换活跃后端" } }
```

#### GET `/api/admin/storage/usage` — 存储用量

成功响应：
```json
{
  "code": 0,
  "data": {
    "totalBytes": 0,
    "usedBytes": 0,
    "fileCount": 0,
    "byType": {}
  }
}
```

---

### 4.14 图片上传 — `/api/admin/uploads`

#### POST `/api/admin/uploads/image` — 上传图片

Content-Type：`multipart/form-data`

表单字段：`file` (image/*)

业务规则：
- `ownerId` 使用 Admin actor ID
- 文件大小限制与用户侧上传一致

成功响应：
```json
{
  "code": 0,
  "data": {
    "uploadId": "upload_001",
    "fileUrl": "https://stag.cps.vin/assets/uploads/xxx.jpg",
    "width": null,
    "height": null
  }
}
```

---

### 4.15 Admin 页面入口 — `/admin`

#### GET `/admin` 和 GET `/admin/`

返回 `admin_web/index.html` 静态文件。同时需要配置 `admin_web/` 目录的静态文件服务（CSS/JS）。

检查逻辑：
- 如果 `ADMIN_DASHBOARD_ENABLED` 为 false，返回 503
- 如果 `admin_web/index.html` 不存在，返回 404

---

## 5. 路由总览

| 模块 | 路由数 | 路径前缀 |
|------|--------|----------|
| 认证 | 2 | `/api/admin/auth` |
| 概览 | 1 | `/api/admin/overview` |
| 用户 | 7 | `/api/admin/users` |
| 商品 | 6 | `/api/admin/products` |
| SKU | 3 | `/api/admin/skus` |
| 订单 | 3 | `/api/admin/orders` |
| CDK | 3 | `/api/admin/cdk-codes` |
| 任务 | 5 | `/api/admin/tasks` |
| 公开场景 | 8 | `/api/admin/public-scenes` |
| 生成场景 | 2 | `/api/admin/generated-scenes` |
| 分类 | 4 | `/api/admin/scene-categories` |
| 合集 | 4 | `/api/admin/scene-collections` |
| 存储 | 6 | `/api/admin/storage` |
| 上传 | 1 | `/api/admin/uploads` |
| 页面入口 | 2 | `/admin` |
| **合计** | **57** | |

---

## 6. 数据库表依赖

以下 PostgreSQL 表在 Admin API 中被读写：

| 表 | 读 | 写 | 说明 |
|----|:--:|:--:|------|
| `users` | ✅ | ✅ | 用户 CRUD、角色变更、封禁 |
| `scenes` | ✅ | ✅ | 公开场景 + 生成场景（通过 scene_type 区分） |
| `scene_categories` | ✅ | ✅ | 分类 CRUD |
| `scene_collections` | ✅ | ✅ | 合集 CRUD |
| `scene_publications` | ✅ | ✅ | 发布记录（generated → public 映射） |
| `scene_collection_items` | ✅ | ✅ | 场景-合集多对多关联 |
| `products` | ✅ | ✅ | 商品 CRUD |
| `skus` | ✅ | ✅ | SKU CRUD |
| `sku_benefits` | ✅ | ✅ | SKU 权益 |
| `orders` | ✅ | ✅ | 订单查询、删除 |
| `order_items` | ✅ | — | 订单明细 |
| `tasks` | ✅ | ✅ | 任务查询、重试、创建、删除 |
| `uploads` | ✅ | ✅ | 图片上传记录 |
| `cdk_codes` | ✅ | ✅ | CDK 生成、查询、删除 |
| `entitlements` | ✅ | — | 用户权益（用户详情中展示） |
| `credits` | ✅ | — | 用户积分余额（用户详情中展示） |
| `membership` | ✅ | — | 会员状态（用户详情中展示） |
| `storage_configs` | ✅ | ✅ | 存储后端配置（JSON 持久化） |

---

## 7. 新增环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ADMIN_DASHBOARD_ENABLED` | `true` | 是否启用 Admin 面板 |
| `ADMIN_DASHBOARD_USERNAME` | `admin` | 登录用户名 |
| `ADMIN_DASHBOARD_PASSWORD` | `admin123456` | 登录密码（**生产必须修改**） |
| `ADMIN_WEB_DIR` | `./admin_web` | Admin 前端静态文件目录 |

---

## 8. 实现分期建议

### Phase 1: 基础框架 + 认证 + 只读视图（MVP）

目标：能登录、能看数据、不能改。

- [ ] Admin 中间件（JWT 校验 + role 判断）
- [ ] `POST /api/admin/auth/login`
- [ ] `GET /api/admin/auth/me`
- [ ] `GET /api/admin/overview`
- [ ] `GET /api/admin/users`
- [ ] `GET /api/admin/users/{id}`
- [ ] `GET /api/admin/public-scenes`
- [ ] `GET /api/admin/generated-scenes`
- [ ] `GET /api/admin/tasks`
- [ ] `GET /api/admin/products`
- [ ] `GET /api/admin/skus`
- [ ] `GET /api/admin/orders`
- [ ] `GET /api/admin/scene-categories`
- [ ] `GET /api/admin/scene-collections`
- [ ] `GET /api/admin/cdk-codes`
- [ ] Admin 页面静态文件服务 (`/admin/`)

### Phase 2: 写操作 + 批量管理

目标：完整的 CRUD 和批量操作。

- [ ] 用户：block/unblock/grant-admin/revoke-admin/batch-delete
- [ ] 商品：create/update/publish/disable
- [ ] SKU：create/update
- [ ] 订单：batch-delete
- [ ] CDK：generate/batch-delete
- [ ] 任务：retry/batch-delete/scene-generate-batch
- [ ] 公开场景：create/update/batch-delete/batch-visibility/batch-free/batch-category/republish
- [ ] 生成场景：publish
- [ ] 分类：create/update/delete
- [ ] 合集：create/update/delete
- [ ] 图片上传

### Phase 3: 存储管理

目标：可配置存储后端。

- [ ] `GET /api/admin/storage/overview`
- [ ] `GET /api/admin/storage/configs`
- [ ] `PUT /api/admin/storage/configs/{id}`
- [ ] `POST /api/admin/storage/test/{id}`
- [ ] `POST /api/admin/storage/activate/{id}`
- [ ] `GET /api/admin/storage/usage`

### Phase 4: 清理 + Nginx 简化

- [ ] 验证所有 57 条路由与 Python 版本行为一致
- [ ] 更新 Nginx 配置：去掉 admin 转发到 8000 的规则，所有 `/api/` 统一走 8001
- [ ] 停止 Python 后端
- [ ] 更新 CLAUDE.md

---

## 9. Nginx 配置变更

完成后，Nginx 配置简化为：

```nginx
# 所有 /api/ 请求转发到 Rust 后端（含 admin）
location ^~ /api/ {
    proxy_pass http://127.0.0.1:8001;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    client_max_body_size 10m;
}

# Admin 面板静态文件也由 Rust 后端提供
location ^~ /admin {
    proxy_pass http://127.0.0.1:8001;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# 静态资源
location ^~ /assets/ {
    proxy_pass http://127.0.0.1:8001;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

可删除的配置：
- `location ^~ /api/admin/` → Python 8000
- `location = /admin` → Python 8000
- `location ^~ /admin/` → Python 8000

---

## 10. 验收标准

1. 现有 `admin_web/` 前端零改动，所有功能正常工作
2. 所有 57 条 API 路由行为与 Python 版本一致
3. Admin 登录、数据浏览、CRUD、批量操作、图片上传全部可用
4. Python 后端可完全停止
5. 单一 Rust 进程同时服务用户侧 API 和 Admin API
6. Nginx 配置简化，所有请求统一转发到 8001

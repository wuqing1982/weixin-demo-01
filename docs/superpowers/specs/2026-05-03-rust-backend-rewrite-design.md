# Rust 后端重写设计文档

## 目标

将当前 Python (FastAPI) 后端完整重写为 Rust (Axum)，放在 `backend-rust/` 目录下。要求：

1. **小程序无感切换** — 所有 API 路径、请求/响应格式保持一致，前端无需任何修改
2. **完整替换** — 所有 ~70 个 API 端点全部重写，Python 后端最终下线
3. **数据库不变** — 复用现有 PostgreSQL schema，不做表结构变更
4. **参考现有 Rust 代码** — 复用 `/www/wwwroot/e.cps.vin/english-loong-back/demo/backend/` 中已实现的核心模块

## 技术栈

| 组件 | 选择 | 理由 |
|------|------|------|
| Web 框架 | Axum 0.8 | 与参考代码一致，生态成熟 |
| 异步运行时 | Tokio 1 | Axum 标配 |
| 数据库 | SQLx 0.8 + PostgreSQL | async、编译时 SQL 检查 |
| HTTP 客户端 | Reqwest 0.12 | 调微信 API / 智谱 AI / TTS |
| JSON | serde + serde_json | Rust 标配 |
| JWT | hmac + sha2 + base64 手写 | 与 Python 端格式 100% 兼容 |
| 日志 | tracing + tracing-subscriber | 与参考代码一致 |
| 配置 | dotenvy + std::env | 加载 .env |
| CORS | tower-http | Axum 官方中间件 |

## 项目结构

```
backend-rust/
├── Cargo.toml
├── .env                          # 与 Python 端相同的环境变量格式
├── src/
│   ├── main.rs                   # 入口：配置加载、路由注册、worker 启动
│   ├── config.rs                 # 环境变量 → Config struct
│   ├── error.rs                  # 统一错误类型 AppError → JSON 响应
│   ├── state.rs                  # AppState（DB pool, config）
│   ├── models/                   # 数据模型
│   │   ├── mod.rs
│   │   ├── user.rs               # User, Session, Profile
│   │   ├── scene.rs              # Scene, HotspotItem, VerbItem, Rect（复用参考代码）
│   │   ├── product.rs            # Product, SKU, Benefit
│   │   ├── order.rs              # Order, Payment
│   │   ├── task.rs               # SceneGenerateTask
│   │   └── cdk.rs                # CdkCode, Redemption
│   ├── api/                      # 路由处理（按子系统分模块）
│   │   ├── mod.rs                # Router 汇总，嵌套路由
│   │   ├── auth.rs               # /api/auth/*
│   │   ├── user.rs               # /api/me/*
│   │   ├── scene.rs              # /api/scenes/*, /api/my/scenes
│   │   ├── product.rs            # /api/products/*
│   │   ├── order.rs              # /api/orders/*
│   │   ├── payment.rs            # /api/payments/*
│   │   ├── upload.rs             # /api/uploads/*
│   │   ├── task.rs               # /api/my/tasks/*
│   │   ├── cdk.rs                # /api/cdk/*
│   │   ├── video.rs              # /api/scenes/{id}/export-video, /api/video-exports/*
│   │   ├── admin.rs              # /api/admin/*
│   │   └── health.rs             # /api/health, /api/tts, /api/config
│   ├── middleware/               # Axum 中间件
│   │   ├── mod.rs
│   │   ├── auth.rs               # JWT 验证 → 注入当前用户到请求扩展
│   │   └── admin_auth.rs         # Admin Basic Auth 验证
│   ├── services/                 # 业务逻辑
│   │   ├── mod.rs
│   │   ├── jwt.rs                # JWT 创建/验证（HS256，与 Python 兼容）
│   │   ├── wechat_auth.rs        # 微信 code2session
│   │   ├── wechat_session.rs     # Session key 加解密（复现 Python XOR 流加密）
│   │   ├── zhipu.rs              # 智谱 AI 场景分析（直接复用参考代码）
│   │   ├── tts.rs                # TTS 代理（直接复用参考代码）
│   │   ├── audio_naming.rs       # 音频文件命名（直接复用参考代码）
│   │   ├── virtual_pay.rs        # 微信虚拟支付签名
│   │   ├── wechat_pay.rs         # 微信 JSAPI Pay v3 签名/加密
│   │   └── video_generator.rs    # ffmpeg 视频合成
│   ├── worker/                   # 后台任务
│   │   ├── mod.rs
│   │   └── scene_worker.rs       # 场景生成轮询 worker
│   └── db/                       # 数据库访问层（手写 SQLx 查询）
│       ├── mod.rs
│       ├── users.rs
│       ├── scenes.rs
│       ├── products.rs
│       ├── orders.rs
│       ├── tasks.rs
│       └── cdk.rs
```

## API 兼容性

### 响应格式

Python 端统一响应格式：

```json
{"code": 0, "data": <payload>, "message": "ok"}
```

Rust 端必须输出完全相同的结构。实现方式：

```rust
pub fn success<T: Serialize>(data: T) -> Json<Value> {
    Json(json!({"code": 0, "data": data, "message": "ok"}))
}

pub fn fail(code: i32, message: &str) -> (StatusCode, Json<Value>) {
    let status = match code {
        4001 | 401 => StatusCode::UNAUTHORIZED,
        404 => StatusCode::NOT_FOUND,
        _ => StatusCode::BAD_REQUEST,
    };
    (status, Json(json!({"code": code, "data": null, "message": message})))
}
```

### JWT 兼容

手写 HS256 JWT，确保 token 格式与 Python 端完全一致：

- Header: `{"alg":"HS256","typ":"JWT"}`
- Payload: `{"sub":"user_id","typ":"access","role":"user","sid":"session_id","iat":1234567890,"exp":1234568090}`
- 签名: HMAC-SHA256(secret, header_b64 + "." + payload_b64)
- Refresh token: `rt_` 前缀 + url-safe random，服务端存 SHA-256 哈希

必须做到：Python 端签发的 token，Rust 端能验证；反之亦然。

### 微信 Session Key 加解密

复现 Python 端 `security.py` 中的 XOR 流加密算法：

```
密钥流 = SHA256(secret + nonce + counter) 拼接到所需长度
密文 = 明文 XOR 密钥流
MAC = SHA256(secret + nonce + 密文)[:12]
输出 = "wsk1." + b64url(nonce) + "." + b64url(密文) + "." + b64url(mac)
```

### 数据库

直接复用 `backend/sql/` 下的所有 schema：

- `auth_postgres_schema.sql` — users, sessions, refresh_tokens
- `commerce_postgres_schema.sql` — products, skus, orders, payments, benefits, cdk_codes, redemptions
- `scene_postgres_schema.sql` — scenes, scene_categories, scene_collections, generated_scenes
- `cdk_codes_schema.sql` — CDK 兑换码

不做任何表结构变更。SQLx 手写 SQL，不做 ORM。

## 支付系统

支持 3 种支付模式，通过 `PAYMENT_MODE` 环境变量切换：

### Mock 支付
- 最简单，直接标记订单已支付
- 用于开发测试

### 微信虚拟支付（xpay）
- `paySig = HMAC-SHA256(appKey, "requestVirtualPayment&" + body)`
- `signature = HMAC-SHA256(sessionKey, body)`
- 服务端调 `/xpay/query_order` 和 `/xpay/notify_provide_goods`

### 微信 JSAPI Pay
- RSA-SHA256 签名
- 需要加载商户 .pem 私钥
- 回调通知验签 + 解密

## 场景生成 Worker

与 Python 端行为一致的内联 Worker：

1. 后台 Tokio task 每 2 秒轮询 `tasks` 表中 status=pending 的任务
2. 取到任务后：调智谱 AI 分析图片 → 生成 TTS 音频 → 保存结果
3. 一次只处理一个任务（串行排队），避免并发问题
4. Worker 启动/停止与 API server 生命周期绑定

## 视频导出

通过 `tokio::process::Command` 调用 ffmpeg 命令行：

- 输入：场景图片 + 热点数据 + TTS 音频
- 输出：720x1280 竖屏 MP4
- 流程：热点逐个高亮 + 信息面板 + TTS 音频同步 → 拼接成最终视频
- 视频保留 3 小时后自动清理（后台定时任务）

## 从参考代码复用

以下模块从 `/www/wwwroot/e.cps.vin/english-loong-back/demo/backend/src/` 直接复用：

| 源文件 | 目标 | 改动 |
|--------|------|------|
| `models/hotspot.rs` | `models/scene.rs` | 扩展 Scene 结构体适配 DB 字段 |
| `services/zhipu.rs` | `services/zhipu.rs` | 几乎原样复用，仅调整 import 路径 |
| `services/tts.rs` | `services/tts.rs` | 原样复用 |
| `services/audio_naming.rs` | `services/audio_naming.rs` | 原样复用 |
| `error.rs` | `error.rs` | 扩展 AppError 枚举，增加更多错误变体 |
| `config.rs` | `config.rs` | 扩展 Config struct，增加所有环境变量 |

## 实施阶段

### 阶段 1：骨架 + 核心 API

目标：小程序能登录、浏览场景。

- 项目骨架（Cargo.toml、main.rs、config.rs、error.rs、state.rs）
- DB 连接池（SQLx PostgreSQL）
- JWT 签发/验证
- 微信 Auth（code2session + session key 加解密）
- Auth API（login / refresh / logout）
- User API（/me /me/profile /me/membership /me/credits /me/entitlements）
- Scene API（/scenes /scenes/{id} /scene-categories /scene-collections）
- 健康检查、TTS 代理、客户端配置

验证方式：小程序真机登录 → 浏览场景 → 播放 TTS。

### 阶段 2：场景生成 + 视频

目标：小程序能上传图片、生成场景、导出视频。

- 图片上传
- 场景生成 Worker（复用 zhipu.rs + tts.rs）
- 我的场景、热点编辑
- 视频导出（ffmpeg）
- 视频清理定时任务

验证方式：小程序真机拍照 → 生成场景 → 编辑热点 → 导出视频。

### 阶段 3：商业系统

目标：小程序能购买会员、兑换 CDK。

- 产品/SKU CRUD
- 订单创建
- 支付（mock + 虚拟支付 + JSAPI）
- 支付回调
- CDK 生成/兑换
- 升级预览

验证方式：小程序真机购买会员 → 查看权益 → 兑换 CDK。

### 阶段 4：Admin 后台

目标：管理后台完全可用。

- Admin 认证（Basic Auth）
- Admin 用户管理（列表/详情/封禁/解封/管理员）
- Admin 产品/SKU 管理
- Admin 订单管理
- Admin 场景管理（公共场景/生成场景/分类/合集）
- Admin 任务管理
- Admin CDK 管理
- Admin 概览统计

验证方式：浏览器访问 /admin → CRUD 操作 → 验证小程序端数据同步。

## 部署方式

编译为单个二进制文件：

```bash
cd backend-rust
cargo build --release
# 产出 target/release/backend-rust
```

Systemd 服务：

```ini
[Service]
WorkingDirectory=/www/wwwroot/e.cps.vin/weixin-demo-01/backend-rust
ExecStart=/www/wwwroot/e.cps.vin/weixin-demo-01/backend-rust/target/release/backend-rust
Restart=always
RestartSec=3
```

Nginx 配置不变，反向代理到 127.0.0.1:8000。

## 风险与注意事项

1. **JWT 格式兼容** — 必须逐字节验证 Python 签发的 token 能被 Rust 正确验证
2. **Session key 加解密** — Python 端的自定义 XOR 流加密必须精确复现
3. **API 响应字段名** — Python 端用 camelCase（`productId`, `sceneId`），Rust serde 需要正确配置 rename
4. **微信支付签名** — HMAC-SHA256 和 RSA-SHA256 签名必须与微信文档完全一致
5. **ffmpeg 调用** — 视频导出的 ffmpeg 参数必须与 Python 端完全一致，否则产出视频会有差异
6. **数据库时区** — PostgreSQL timestamp 处理要注意 UTC 一致性
7. **文件存储** — 当前用本地文件系统（assets/ 目录），Rust 端保持一致

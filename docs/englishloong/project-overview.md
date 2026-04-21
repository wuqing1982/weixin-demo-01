# 项目概览

## 项目类型

微信小程序 + FastAPI 后端，用于**英语场景化学习**。用户通过全景图/VR 场景与热点交互，学习英语词汇和句子，配合 TTS 语音播放。

**线上域名**: `https://e.cps.vin`

---

## 目录结构

```
weixin-demo-01/
├── pages/                    # 小程序页面
├── services/                 # 小程序 API 服务封装
├── shared/scene/             # 场景共享逻辑
├── app.json                  # 小程序配置
│
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI 入口（单体大文件）
│   │   ├── settings.py       # 环境配置
│   │   ├── security.py       # JWT 认证
│   │   ├── scene_store*.py   # 场景存储（JSON / PostgreSQL）
│   │   ├── auth_store*.py    # 认证存储
│   │   ├── commerce_store*.py # 电商存储
│   │   ├── wechat_auth.py    # 微信登录
│   │   ├── wechat_pay.py     # 微信支付
│   │   ├── worker_runner.py  # AI 场景生成 worker
│   │   └── ...
│   ├── tests/                # 后端测试
│   ├── sql/                  # PostgreSQL 建表 SQL
│   ├── data/                 # JSON 存储目录
│   ├── start-api.sh         # 启动脚本
│   ├── .env                  # 环境配置（不提交）
│   └── .env.example          # 环境配置模板
│
├── docs/                     # 项目文档
└── todolist/                 # 任务清单
```

---

## 核心命令

### 后端启动

```bash
cd backend
cp .env.example .env           # 首次配置
bash start-api.sh

# 或直接运行
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 测试

```bash
# 运行所有测试
cd backend && python3 -m pytest tests/ -v

# 运行单个测试文件
cd backend && python3 -m pytest tests/test_auth_api.py -v
```

### 数据库

```bash
# 迁移 auth 到 PostgreSQL
python3 scripts/migrate_auth_to_postgres.py

# 写入 demo 商品目录
python3 scripts/seed_demo_catalog.py
```

---

## 环境配置

### 关键环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `AUTH_STORE_BACKEND` | `json` | 认证存储：`json` 或 `postgres` |
| `COMMERCE_STORE_BACKEND` | `disabled` | 电商存储：`disabled` 或 `postgres` |
| `PAYMENT_MODE` | `mock` | 支付模式：`mock` 或 `wechat_pay` |
| `AUTH_WECHAT_LOGIN_MODE` | `mock` | 微信登录：`mock`、`code2session`、`auto` |
| `DATABASE_URL` | - | PostgreSQL 连接字符串 |
| `HOTSPOT_EDITOR_ENABLED` | `true` | 是否启用热点编辑器 |

### 配置优先级

系统环境变量 > `.env` 文件 > 默认值

### 微信登录模式

- `mock`: 不调用微信接口，用于开发调试
- `code2session`: 调用微信 `code2Session` 获取真实 openid
- `auto`: 检测到 `WECHAT_MP_APP_SECRET` 后自动走真实登录，否则 fallback 到 mock

### 微信支付配置

```bash
PAYMENT_MODE=wechat_pay
WECHAT_PAY_MCH_ID=商户号
WECHAT_PAY_API_V3_KEY=APIv3密钥
WECHAT_PAY_MCH_PRIVATE_KEY_PATH=/path/to/apiclient_key.pem
WECHAT_PAY_PLATFORM_CERT_PATH=/path/to/wechatpay_platform_cert.pem
```

---

## 关键模块说明

### 认证 (`auth_store*.py`)

- JWT (HS256) 访问令牌 + 刷新令牌
- 支持 JSON 文件或 PostgreSQL 持久化
- 微信登录支持 openid / unionid 账号归并

### 场景 (`scene_store*.py`)

- 内置场景：`shared/scene/scene-registry.js`
- 用户生成场景：JSON 或 PostgreSQL 存储
- 热点编辑器支持权限控制

### 电商 (`commerce_store*.py`)

- 商品、SKU、权益模型
- 订单、支付流程
- Mock 支付用于开发测试

### AI 场景生成 (`worker_runner.py`)

- 调用智谱 AI (Core100) 分析图片
- 调用 Azure TTS 生成音频
- 结果写入 `backend/data/generated_scenes.json`

### Admin 后台

- 访问路径：`/admin`
- 独立账号密码登录
- 支持用户、商品、订单、任务管理

---

## 小程序开发

- **无需构建步骤**
- 使用微信开发者工具打开项目根目录
- ES6 转译由 DevTools 内置提供

---

## 测试注意事项

- 测试文件通过 `os.environ[]` 设置环境变量后再 import
- 使用 unittest 框架 + pytest 运行器
- 部分测试依赖 PostgreSQL（需提前配置）

---

## 相关文档

- `backend/README.md` - 后端详细说明
- `docs/current-system-architecture-*.md` - 系统架构
- `docs/e-cps-vin-ops-*.md` - 运维文档

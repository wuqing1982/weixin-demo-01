# Backend

最小 FastAPI 后端，专门用于给当前小程序模板页做第一轮联调。

## 功能

- `GET /api/health`
- `POST /api/auth/wechat/login`
- `POST /api/auth/refresh`
- `POST /api/auth/logout`
- `GET /api/me`
- `POST /api/admin/auth/login`
- `GET /api/admin/overview`
- `GET /api/admin/users`
- `GET /api/admin/products`
- `GET /api/admin/orders`
- `GET /api/admin/tasks`
- `GET /api/scenes`
- `GET /api/scenes/{sceneId}`
- `GET /api/my/scenes`
- `POST /api/uploads/image`
- `POST /api/my/tasks/scene-generate`
- `GET /api/my/tasks/{taskId}`
- `POST /api/scenes/{sceneId}/hotspots`
- 静态暴露仓库根目录下的 `assets/`
- 提供 `http://127.0.0.1:8000/admin` 网页端后台

## 启动

```bash
cd backend
cp .env.example .env
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

启动后可访问：

- `http://127.0.0.1:8000/api/health`
- `http://127.0.0.1:8000/api/scenes`
- 通过反向代理访问 `https://e.cps.vin/api/health`

## 说明

后端会自动读取 `backend/.env`。如果某个环境变量同时出现在系统环境和 `.env` 里，系统环境优先。

当前样例数据直接复用仓库里的早餐和动物园资源，目的是先把前后端闭环跑起来，不引入数据库和对象存储。

当前认证链路已经补上第一阶段的基础形态：

- 提供正式 Bearer token 接口
- 小程序可静默登录并持久化 token
- 支持 `AUTH_WECHAT_LOGIN_MODE=mock | code2session | auto`
- `mock` 模式不会真实请求微信 `code2Session`
- `code2session` 模式会调用微信登录接口获取真实 `openid`
- `auto` 模式在检测到 `WECHAT_MP_APP_SECRET` 后自动走真实登录，否则回落到 `mock`

现在已经支持第二阶段的 PostgreSQL 认证持久化：

- `backend/sql/auth_postgres_schema.sql` 提供 auth 相关建表 SQL
- `AUTH_STORE_BACKEND=postgres` 时，认证、身份、refresh token 会落 PostgreSQL
- 场景、上传、任务仍保持 JSON 文件，避免这批范围失控
- 为兼容当前 `debug_user_*` / `ownerId` 链路，auth 表主键暂时使用字符串 ID

现在已经支持下一批商品 / SKU / 权益读取底座：

- `backend/sql/commerce_postgres_schema.sql` 提供商品、SKU、权益、credits 建表 SQL
- `COMMERCE_STORE_BACKEND=postgres` 时，开放 Product API 与 `/api/me/*` 权益摘要
- 当前只做读取与摘要，不包含订单、支付、credits 扣减

现在已经支持 mock 支付订单闭环：

- `POST /api/orders`
- `GET /api/orders`
- `GET /api/orders/{orderId}`
- `POST /api/orders/{orderId}/pay`
- `POST /api/orders/{orderId}/payment-sync`
- `POST /api/orders/{orderId}/mock-pay-success`
- `POST /api/payments/wechat/notify`
- `PAYMENT_MODE=mock` 时，小程序可直接走模拟支付成功并发放权益
- `PAYMENT_MODE=wechat_pay` 时，后端会调用微信支付小程序下单接口并返回 `wx.requestPayment` 所需参数
- 真实支付模式下，小程序支付成功后会调用 `POST /api/orders/{orderId}/payment-sync` 做一次查单同步

现在已经支持 Admin 最小后台：

- 后台登录页：`/admin`
- `POST /api/admin/auth/login` 使用独立后台账号密码
- Dashboard 提供用户、商品、订单、任务概览
- 支持用户详情、封禁 / 解封
- 支持商品创建 / 编辑 / 上下架
- 支持 SKU 创建 / 编辑 / 权益 JSON 配置
- 支持订单详情查看
- 支持任务详情与失败任务重试
- 支持公共场景创建 / 编辑

当前仍保留开发兼容能力：

- `AUTH_ENABLE_DEBUG_USER_HEADER=true`
- 允许继续通过 `X-Debug-User-Id` 访问旧 JSON MVP 链路
- 方便认证切换期间联调已有功能

`PUBLIC_BASE_URL` 用于生成返回给小程序的图片和音频公网地址。反向代理部署时，这个值应设置成 `https://e.cps.vin`。

当前新增的上传与任务接口，已经接上真实生成链路：

- 图片可上传到 `assets/uploads/`
- 可创建异步生成任务
- 内置 worker 会调用 `/www/wwwroot/e.cps.vin/core100` 做图片分析
- worker 会调用 `http://127.0.0.1:5003` Azure TTS 生成音频
- 最终会把私有场景写入 `assets/generated/` 和 `backend/data/generated_scenes.json`

注意：

- 视觉分析依赖 `core100` 所需的 Python 依赖以及外部视觉模型可用
- TTS 依赖本机 `5003` 服务健康
- 可通过环境变量覆盖：
- `DATABASE_URL`
- `DATABASE_SCHEMA`
- `AUTH_STORE_BACKEND`
- `AUTH_ENABLE_DEBUG_USER_HEADER`
- `AUTH_WECHAT_LOGIN_MODE`
- `WECHAT_MP_APP_ID`
- `WECHAT_MP_APP_SECRET`
- `WECHAT_SESSION_KEY_SECRET`
- `AUTH_JWT_SECRET`
- `AUTH_ACCESS_TOKEN_TTL_SECONDS`
- `AUTH_REFRESH_TOKEN_TTL_SECONDS`
- `COMMERCE_STORE_BACKEND`
- `PAYMENT_MODE`
- `WECHAT_PAY_MCH_ID`
- `WECHAT_PAY_API_V3_KEY`
- `WECHAT_PAY_MCH_SERIAL_NO`
- `WECHAT_PAY_MCH_PRIVATE_KEY_PATH`
- `WECHAT_PAY_PLATFORM_CERT_PATH`
- `WECHAT_PAY_PLATFORM_SERIAL_NO`
- `WECHAT_PAY_NOTIFY_URL`
- `WECHAT_PAY_API_BASE`
- `WECHAT_PAY_CURRENCY`
- `WECHAT_PAY_TIMEOUT_SECONDS`
- `ADMIN_DASHBOARD_ENABLED`
- `ADMIN_DASHBOARD_USERNAME`
- `ADMIN_DASHBOARD_PASSWORD`
- `CORE100_MODEL`
  - `CORE100_TTS_URL`
  - `ZHIPUAI_API_KEY`
  - `HOTSPOT_EDITOR_ENABLED`
  - `HOTSPOT_EDITOR_ADMIN_USER_IDS`
  - `HOTSPOT_EDITOR_PUBLIC_EDITOR_IDS`
  - `HOTSPOT_EDITOR_PRIVATE_EDITOR_IDS`

热点编辑权限规则：

- public 场景默认 `HOTSPOT_EDITOR_PUBLIC_EDITOR_IDS=*`，表示当前 MVP 默认允许编辑
- private 场景默认 `HOTSPOT_EDITOR_PRIVATE_EDITOR_IDS=*`，表示当前 MVP 默认允许编辑
- `HOTSPOT_EDITOR_ADMIN_USER_IDS` 可全局覆盖
- 场景 `meta.hotspotEditors` 可做单场景白名单
- 场景 `meta.hotspotEditable=false` 可禁用普通编辑者

## 认证接口说明

### `POST /api/auth/wechat/login`

请求示例：

```json
{
  "code": "wx-login-code",
  "device": {
    "deviceId": "device_001",
    "deviceType": "wechat_mini_program",
    "appVersion": "1.0.0"
  }
}
```

返回：

- `accessToken`
- `refreshToken`
- `user`
- `me`

真实微信登录说明：

- 前端仍使用 `wx.login` 拿到 `code`
- 后端在 `code2session` 模式下调用微信 `code2Session`
- 当前用户唯一身份键使用 `openid`
- 如果微信返回了 `unionid`，后端会先按 `openid` 查找，查不到时再按 `unionid` 做账号归并
- `session_key` 不会下发给前端，只会在服务端加密后入库

启用真实微信登录：

```bash
AUTH_WECHAT_LOGIN_MODE=code2session
WECHAT_MP_APP_ID=wx8e3f9b18fc8f3241
WECHAT_MP_APP_SECRET=你的微信小程序AppSecret
WECHAT_SESSION_KEY_SECRET=建议单独配置一个高强度密钥
```

如果只想先安全上线代码，等密钥补齐后自动切换，可用：

```bash
AUTH_WECHAT_LOGIN_MODE=auto
```

### `POST /api/auth/refresh`

请求：

```json
{
  "refreshToken": "rt_xxx"
}
```

### `POST /api/auth/logout`

支持：

- 通过 Bearer token 撤销当前会话
- 通过 `refreshToken` 撤销指定 refresh token

### `GET /api/me`

返回：

- 当前用户基础资料
- 占位版 `memberSummary`
- 占位版 `creditSummary`

## PostgreSQL Auth 迁移

从现有 `backend/data/auth.json` 迁移到 PostgreSQL：

```bash
cd backend
../.venv/bin/python scripts/migrate_auth_to_postgres.py
```

切换到 PostgreSQL auth：

```bash
AUTH_STORE_BACKEND=postgres
DATABASE_SCHEMA=public
```

建议切换顺序：

1. 先执行迁移脚本
2. 确认 `users` / `user_identities` / `auth_refresh_tokens` 有数据
3. 再把 `AUTH_STORE_BACKEND` 切到 `postgres`
4. 重启 `weixin-demo-api.service`

## Demo 商品目录种子

写入第一批 demo 商品和 SKU：

```bash
cd backend
../.venv/bin/python scripts/seed_demo_catalog.py
```

启用 Product API 与权益摘要：

```bash
COMMERCE_STORE_BACKEND=postgres
```

当前提供的接口：

- `GET /api/products`
- `GET /api/products/{productId}`
- `GET /api/products/{productId}/skus`
- `GET /api/me/membership`
- `GET /api/me/credits`
- `GET /api/me/entitlements`

## 真实微信支付

当前已经支持普通商户直连模式的第一版：

- `POST /api/orders/{orderId}/pay`
  - `PAYMENT_MODE=wechat_pay` 时，后端调用微信支付 `JSAPI/小程序下单`
  - 返回小程序 `wx.requestPayment` 所需的 `timeStamp`、`nonceStr`、`package`、`signType`、`paySign`
- `POST /api/orders/{orderId}/payment-sync`
  - 小程序支付成功后调用
  - 后端按 `out_trade_no` 查单
  - 若支付成功，则更新订单、支付记录并发放权益
- `POST /api/payments/wechat/notify`
  - 用于接收微信支付回调
  - 第一版要求配置平台证书文件，以完成回调验签和资源解密

普通商户直连模式配置示例：

```bash
PAYMENT_MODE=wechat_pay
WECHAT_PAY_MCH_ID=你的商户号
WECHAT_PAY_API_V3_KEY=你的APIv3密钥
WECHAT_PAY_MCH_SERIAL_NO=商户证书序列号
WECHAT_PAY_MCH_PRIVATE_KEY_PATH=/www/wwwroot/e.cps.vin/weixin-demo-01/backend/certs/apiclient_key.pem
WECHAT_PAY_PLATFORM_CERT_PATH=/www/wwwroot/e.cps.vin/weixin-demo-01/backend/certs/wechatpay_platform_cert.pem
WECHAT_PAY_PLATFORM_SERIAL_NO=平台证书序列号
WECHAT_PAY_NOTIFY_URL=https://e.cps.vin/api/payments/wechat/notify
WECHAT_PAY_API_BASE=https://api.mch.weixin.qq.com
WECHAT_PAY_CURRENCY=CNY
WECHAT_PAY_TIMEOUT_SECONDS=10
```

说明：

- `WECHAT_MP_APP_ID` 必须与支付商户绑定的小程序 `AppID` 一致
- 小程序支付使用当前登录用户的真实 `openid`
- 未补齐支付参数时，真实支付模式会返回配置错误，不会自动降级成 mock

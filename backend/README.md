# Backend

最小 FastAPI 后端，专门用于给当前小程序模板页做第一轮联调。

## 功能

- `GET /api/health`
- `POST /api/auth/wechat/login`
- `POST /api/auth/refresh`
- `POST /api/auth/logout`
- `GET /api/me`
- `GET /api/scenes`
- `GET /api/scenes/{sceneId}`
- `GET /api/my/scenes`
- `POST /api/uploads/image`
- `POST /api/my/tasks/scene-generate`
- `GET /api/my/tasks/{taskId}`
- `POST /api/scenes/{sceneId}/hotspots`
- 静态暴露仓库根目录下的 `assets/`

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
- 默认 `AUTH_WECHAT_LOGIN_MODE=mock`
- `mock` 模式不会真实请求微信 `code2Session`
- 会基于小程序本地 `deviceId` 生成稳定的 mock 微信身份，便于当前仓库联调

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
  - `AUTH_ENABLE_DEBUG_USER_HEADER`
  - `AUTH_WECHAT_LOGIN_MODE`
  - `AUTH_JWT_SECRET`
  - `AUTH_ACCESS_TOKEN_TTL_SECONDS`
  - `AUTH_REFRESH_TOKEN_TTL_SECONDS`
  - `CORE100_ROOT`
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

当前默认 mock 模式请求示例：

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

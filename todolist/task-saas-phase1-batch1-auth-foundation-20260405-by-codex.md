# Task: SaaS 第一阶段第一批 `认证与会话底座`

## 任务来源

基于：

- `/www/wwwroot/e.cps.vin/weixin-demo-01/docs/current-project-saas-platform-prd-20260404-1831-by-codex.md`

本批次只执行 PRD 第一阶段里“当前仓库可以安全连续落地”的基础任务，不把商品、订单、支付、Admin 混进同一批次。

## 本批次目标

把当前 JSON MVP 从 `debugUserId` 临时联调模式，推进到“有正式认证入口、有平台 token、有 `/api/me`、小程序能静默登录并自动带 token”的状态，为后续商品、订单、权益和访问控制打底。

## 范围边界

本批次必须做：

- 后端认证基础配置
- token 安全工具
- JSON 存储版用户/身份/refresh token store
- `POST /api/auth/wechat/login`
- `POST /api/auth/refresh`
- `POST /api/auth/logout`
- `GET /api/me`
- 小程序端 session 持久化
- 小程序端静默登录初始化
- 请求层自动注入 `Authorization`

本批次不做：

- 真实微信 `code2Session`
- PostgreSQL 真正接入
- 商品 / SKU
- 订单 / 微信支付
- Admin 后台
- 会员权益与 credits 扣减

## 执行清单

- [x] 1. 写入本批次 todo 文档
  - 文件：
    - `todolist/task-saas-phase1-batch1-auth-foundation-20260405-by-codex.md`
  - 完成条件：
    - 任务范围、文件范围、验证方式明确
  - 验证：
    - 人工检查文档内容完整

- [x] 2. 补后端认证底座
  - 文件：
    - `backend/app/settings.py`
    - `backend/app/schemas.py`
    - `backend/app/security.py`
    - `backend/app/auth_store.py`
  - 完成条件：
    - 能生成 access token / refresh token
    - 能持久化用户、身份、refresh token
  - 验证：
    - `.venv/bin/python -m unittest backend.tests.test_auth_security -v`

- [x] 3. 实现 Auth API 与 `/api/me`
  - 文件：
    - `backend/app/main.py`
    - `backend/app/auth_store.py`
    - `backend/app/security.py`
    - `backend/app/schemas.py`
  - 完成条件：
    - 提供登录、刷新、登出、获取当前用户资料接口
    - 现有 `/api/my/*` 接口可通过 Bearer token 取用户
    - 兼容当前开发联调
  - 验证：
    - `.venv/bin/python -m unittest backend.tests.test_auth_api -v`

- [x] 4. 接入小程序端登录态与请求层
  - 文件：
    - `app.js`
    - `services/api.js`
    - `services/auth.js`
    - `services/session.js`
    - `services/upload.js`
    - 相关页面按需调整
  - 完成条件：
    - 小程序启动时自动初始化登录态
    - 请求与上传自动带 token
    - 能读取 `/api/me`
  - 验证：
    - `node -c app.js`
    - `node -c services/api.js`
    - `node -c services/auth.js`
    - `node -c services/session.js`
    - `node -c services/upload.js`

- [x] 5. 补测试与文档
  - 文件：
    - `backend/tests/test_auth_security.py`
    - `backend/tests/test_auth_api.py`
    - `backend/README.md`
  - 完成条件：
    - 覆盖核心认证链路
    - README 说明新增接口与配置
  - 验证：
    - `.venv/bin/python -m unittest backend.tests.test_auth_security backend.tests.test_auth_api -v`

## 完成定义

当下面全部成立时，本批次算完成：

- todo 文档 5 项全部打勾
- 后端新增认证接口可工作
- 小程序请求层已接入正式 token
- 现有语法检查与认证测试全部通过

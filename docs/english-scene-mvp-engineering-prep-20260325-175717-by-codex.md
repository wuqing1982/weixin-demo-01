# 英语场景学习小程序 MVP 工程准备文档

时间：2026-03-25 17:57:17  
作者：Codex

## 1. 文档目标

本文档是在前两份架构与详细设计文档基础上，进一步下沉到 MVP 可实施层，为工程启动做准备。重点覆盖：

- MVP 范围定义
- 仓库和目录组织
- 数据库 DDL 草案
- API 契约草案
- Redis job payload 设计
- Worker 状态机
- 本地磁盘目录规范
- 开发里程碑和实施顺序
- 非功能性需求

对应上游文档：

- [`docs/english-scene-miniapp-c4-architecture-20260325-150516-by_codex.md`](E:\202603\weixin-demo\docs\english-scene-miniapp-c4-architecture-20260325-150516-by_codex.md)
- [`docs/english-scene-system-detailed-design-20260325-153922-by-codex.md`](E:\202603\weixin-demo\docs\english-scene-system-detailed-design-20260325-153922-by-codex.md)

---

## 2. MVP 范围定义

MVP 目标不是一次做完最终产品，而是先跑通一条闭环：

1. 用户登录微信小程序
2. 用户上传一张图片
3. 后端创建异步任务
4. Python worker 生成场景 JSON、背景图、音频
5. 生成结果存本地磁盘
6. 小程序通过统一模板页查看生成结果
7. 会员用户可浏览预生成公开场景

MVP 暂不做：

- 完整支付链路
- 复杂运营后台
- 多租户管理
- 大规模审核流
- R2 正式切换
- 真正的实时通知
- H5 分享页

MVP 必做：

- 微信登录
- 会员状态最小实现
- 场景统一协议
- 统一运行时场景页
- 上传与任务流
- 公开场景列表
- 私人场景权限隔离

---

## 3. MVP 业务闭环

### 3.1 公开场景闭环

1. 管理员准备一批公开场景资源
2. 场景数据写入数据库
3. 资源落本地磁盘
4. API 返回公开场景列表
5. 会员在小程序中访问统一场景页

### 3.2 私人场景闭环

1. 用户拍照或上传图片
2. 前端压图
3. 文件上传到 API
4. API 写入 jobs 并推 Redis
5. Worker 异步处理
6. 处理完成后写 scenes 和 scene_items/scene_verbs
7. 用户在任务页轮询结果
8. 成功后跳转 runtime 场景页

---

## 4. 仓库与工程组织

建议最少拆成 3 个仓库，避免小程序、API、worker 混在一起。

## 4.1 小程序仓库

建议名：`english-scene-miniapp`

```text
english-scene-miniapp/
  app.js
  app.json
  app.wxss
  pages/
    home/
    library/
    scene_runtime/
    create_scene/
    task_center/
    my_scenes/
    profile/
    login/
  components/
    hotspot-layer/
    overlay-card/
    verb-strip/
    audio-toolbar/
  services/
    api.js
    auth.js
    scene.js
    task.js
    upload.js
  stores/
    user-store.js
  utils/
    image.js
    auth.js
    cache.js
```

## 4.2 API 仓库

建议名：`english-scene-api`

```text
english-scene-api/
  app/
    main.py
    settings.py
    routers/
      auth.py
      scenes.py
      uploads.py
      tasks.py
      users.py
    services/
      auth_service.py
      scene_service.py
      task_service.py
      upload_service.py
      membership_service.py
      permission_service.py
    repositories/
      user_repo.py
      scene_repo.py
      job_repo.py
      asset_repo.py
    models/
      user.py
      scene.py
      scene_item.py
      scene_verb.py
      scene_asset.py
      job.py
    schemas/
      auth.py
      scene.py
      task.py
      upload.py
    infra/
      db.py
      redis.py
      storage.py
      logger.py
  migrations/
  tests/
```

## 4.3 Worker 仓库

建议名：`english-scene-worker`

```text
english-scene-worker/
  worker/
    main.py
    settings.py
    consumers/
      redis_consumer.py
    jobs/
      generate_scene.py
      sync_to_r2.py
    services/
      image_processor.py
      vision_service.py
      prompt_builder.py
      tts_service.py
      scene_builder.py
      scene_persist_service.py
      storage_service.py
      status_reporter.py
    infra/
      db.py
      redis.py
      logger.py
  tests/
```

---

## 5. 数据库 DDL 草案

以下以 MySQL 8 为例。

## 5.1 users

```sql
CREATE TABLE users (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  openid VARCHAR(64) NOT NULL UNIQUE,
  unionid VARCHAR(64) NULL,
  nickname VARCHAR(128) NOT NULL DEFAULT '',
  avatar_url VARCHAR(512) NOT NULL DEFAULT '',
  membership_status VARCHAR(32) NOT NULL DEFAULT 'free',
  membership_expire_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

## 5.2 scenes

```sql
CREATE TABLE scenes (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  scene_uuid VARCHAR(64) NOT NULL UNIQUE,
  scene_type VARCHAR(32) NOT NULL,
  owner_user_id BIGINT NULL,
  source_type VARCHAR(32) NOT NULL,
  title VARCHAR(255) NOT NULL,
  subtitle VARCHAR(255) NULL,
  cover_image_path VARCHAR(1024) NOT NULL,
  background_image_path VARCHAR(1024) NOT NULL,
  scene_json_path VARCHAR(1024) NOT NULL,
  visibility VARCHAR(32) NOT NULL,
  status VARCHAR(32) NOT NULL,
  category VARCHAR(64) NULL,
  tags_json JSON NULL,
  version INT NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_owner_user_id (owner_user_id),
  INDEX idx_scene_type (scene_type),
  INDEX idx_visibility (visibility),
  INDEX idx_status (status)
);
```

## 5.3 scene_items

```sql
CREATE TABLE scene_items (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  scene_id BIGINT NOT NULL,
  item_id VARCHAR(64) NOT NULL,
  word VARCHAR(128) NOT NULL,
  ipa VARCHAR(128) NOT NULL DEFAULT '',
  meaning VARCHAR(255) NOT NULL DEFAULT '',
  sentence TEXT NOT NULL,
  sentence_translation TEXT NOT NULL,
  rect_l DECIMAL(6,2) NOT NULL,
  rect_t DECIMAL(6,2) NOT NULL,
  rect_w DECIMAL(6,2) NOT NULL,
  rect_h DECIMAL(6,2) NOT NULL,
  audio_path VARCHAR(1024) NULL,
  sort_order INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_scene_item (scene_id, item_id),
  INDEX idx_scene_id (scene_id)
);
```

## 5.4 scene_verbs

```sql
CREATE TABLE scene_verbs (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  scene_id BIGINT NOT NULL,
  verb_id VARCHAR(64) NOT NULL,
  word VARCHAR(128) NOT NULL,
  ipa VARCHAR(128) NOT NULL DEFAULT '',
  meaning VARCHAR(255) NOT NULL DEFAULT '',
  sentence TEXT NOT NULL,
  sentence_translation TEXT NOT NULL,
  audio_path VARCHAR(1024) NULL,
  sort_order INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_scene_verb (scene_id, verb_id),
  INDEX idx_scene_id (scene_id)
);
```

## 5.5 scene_assets

```sql
CREATE TABLE scene_assets (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  scene_id BIGINT NOT NULL,
  asset_type VARCHAR(32) NOT NULL,
  asset_key VARCHAR(255) NOT NULL,
  local_path VARCHAR(1024) NOT NULL,
  public_url VARCHAR(1024) NULL,
  cdn_status VARCHAR(32) NOT NULL DEFAULT 'local_only',
  mime_type VARCHAR(128) NOT NULL DEFAULT '',
  file_size BIGINT NOT NULL DEFAULT 0,
  checksum VARCHAR(128) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_scene_id (scene_id),
  INDEX idx_asset_type (asset_type),
  INDEX idx_cdn_status (cdn_status)
);
```

## 5.6 jobs

```sql
CREATE TABLE jobs (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  job_uuid VARCHAR(64) NOT NULL UNIQUE,
  job_type VARCHAR(32) NOT NULL,
  user_id BIGINT NULL,
  source_image_path VARCHAR(1024) NOT NULL,
  source_image_url VARCHAR(1024) NULL,
  scene_id BIGINT NULL,
  status VARCHAR(32) NOT NULL,
  progress INT NOT NULL DEFAULT 0,
  current_stage VARCHAR(64) NOT NULL DEFAULT 'queued',
  payload_json JSON NOT NULL,
  result_json JSON NULL,
  error_message TEXT NULL,
  retry_count INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  started_at DATETIME NULL,
  finished_at DATETIME NULL,
  INDEX idx_user_id (user_id),
  INDEX idx_status (status),
  INDEX idx_job_type (job_type)
);
```

## 5.7 memberships

```sql
CREATE TABLE memberships (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  membership_type VARCHAR(32) NOT NULL,
  status VARCHAR(32) NOT NULL,
  start_at DATETIME NOT NULL,
  expire_at DATETIME NOT NULL,
  source VARCHAR(32) NOT NULL DEFAULT 'manual',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_user_id (user_id),
  INDEX idx_status (status)
);
```

---

## 6. OpenAPI 草案

这里列 MVP 必需接口。

## 6.1 认证接口

### `POST /api/auth/wx-login`

作用：

- 用微信 `code` 换取 openid
- 创建或更新本地用户
- 返回 token

请求：

```json
{
  "code": "wx.login code"
}
```

响应：

```json
{
  "token": "jwt_token",
  "user": {
    "id": "u_1001",
    "nickname": "Tom",
    "avatarUrl": "https://...",
    "membershipStatus": "free"
  }
}
```

## 6.2 用户接口

### `GET /api/me`

响应：

```json
{
  "id": "u_1001",
  "nickname": "Tom",
  "avatarUrl": "https://...",
  "membershipStatus": "member",
  "membershipExpireAt": "2026-12-31 23:59:59"
}
```

## 6.3 场景接口

### `GET /api/scenes`

参数：

- `type=public`
- `category`
- `page`
- `pageSize`

响应：

```json
{
  "list": [
    {
      "sceneId": "scene_breakfast",
      "title": "营养早餐",
      "coverUrl": "https://static.example.com/public-scenes/breakfast/cover.jpg",
      "category": "food",
      "visibility": "member"
    }
  ],
  "total": 100
}
```

### `GET /api/scenes/{sceneId}`

响应直接返回统一场景 JSON 协议。

### `GET /api/my/scenes`

返回当前用户私人场景列表。

## 6.4 上传接口

### `POST /api/uploads/file`

MVP 阶段直接上传到 API，由 API 落盘。

表单字段：

- `file`

响应：

```json
{
  "storageKey": "uploads/2026/03/25/user_1001/original_xxx.jpg",
  "localPath": "/data/english-scenes/uploads/2026/03/25/user_1001/original_xxx.jpg",
  "publicUrl": "https://static.example.com/uploads/2026/03/25/user_1001/original_xxx.jpg"
}
```

## 6.5 任务接口

### `POST /api/tasks`

请求：

```json
{
  "jobType": "generate_private_scene",
  "sourceImagePath": "/data/english-scenes/uploads/2026/03/25/user_1001/original_xxx.jpg",
  "sceneTitle": null,
  "sceneHint": null
}
```

响应：

```json
{
  "jobId": "job_20260325_xxx",
  "status": "queued"
}
```

### `GET /api/tasks/{jobId}`

响应：

```json
{
  "jobId": "job_20260325_xxx",
  "status": "running",
  "progress": 70,
  "currentStage": "generate_tts",
  "result": null,
  "errorMessage": null
}
```

成功状态：

```json
{
  "jobId": "job_20260325_xxx",
  "status": "succeeded",
  "progress": 100,
  "currentStage": "done",
  "result": {
    "sceneId": "scene_20260325_abc123"
  },
  "errorMessage": null
}
```

---

## 7. Redis Job 设计

建议使用一个主队列：

- `queue:scene:generate`

后续可加：

- `queue:scene:sync:r2`

## 7.1 生成任务 payload

```json
{
  "jobId": "job_20260325_xxx",
  "jobType": "generate_private_scene",
  "userId": 1001,
  "sourceImagePath": "/data/english-scenes/uploads/2026/03/25/user_1001/original_xxx.jpg",
  "sceneTitle": null,
  "sceneHint": null,
  "ttsProvider": "azure_local_5003",
  "createdAt": "2026-03-25T18:00:00+08:00"
}
```

## 7.2 R2 同步任务 payload

```json
{
  "jobId": "job_sync_20260325_xxx",
  "jobType": "sync_to_r2",
  "sceneId": "scene_20260325_abc123",
  "assetIds": [10001, 10002, 10003]
}
```

---

## 8. Worker 状态机设计

## 8.1 任务状态

MVP 统一使用：

- `queued`
- `running`
- `succeeded`
- `failed`
- `canceled`

## 8.2 阶段状态

建议定义：

- `queued`
- `prepare_input`
- `resize_image`
- `analyze_image`
- `generate_copywriting`
- `generate_tts`
- `build_scene_json`
- `persist_scene`
- `schedule_sync`
- `done`

## 8.3 状态推进规则

1. 创建任务时：
- `status=queued`
- `current_stage=queued`
- `progress=0`

2. worker 拉取任务后：
- `status=running`
- `current_stage=prepare_input`
- `progress=5`

3. 每阶段推进：
- 进度单调递增
- 阶段写入数据库

4. 成功：
- `status=succeeded`
- `current_stage=done`
- `progress=100`

5. 失败：
- `status=failed`
- `error_message` 写清楚

---

## 9. 本地磁盘规范

## 9.1 根目录

MVP 推荐：

```text
/data/english-scenes/
```

本地开发环境可用：

```text
E:\english-scenes-data\
```

## 9.2 子目录

```text
data-root/
  uploads/
  public-scenes/
  private-scenes/
  jobs/
  temp/
  logs/
```

## 9.3 命名规则

### 私人场景目录

```text
private-scenes/user_{userId}/scene_{sceneUuid}/
```

### 公开场景目录

```text
public-scenes/{slug}/
```

### 任务目录

```text
jobs/{jobUuid}/
```

每个任务目录建议包含：

```text
jobs/job_20260325_xxx/
  input.jpg
  resized.jpg
  scene.json
  hotspots.json
  audio/
  logs/
```

---

## 10. 小程序 MVP 页面设计

## 10.1 页面清单

MVP 需要这 7 个页面：

1. `pages/home`
2. `pages/library`
3. `pages/scene_runtime`
4. `pages/create_scene`
5. `pages/task_center`
6. `pages/my_scenes`
7. `pages/profile`

## 10.2 页面职责

### `home`

- 公开场景推荐
- 上传入口
- 最近任务入口

### `library`

- 公开场景列表
- 分类和搜索

### `scene_runtime`

- 拉取单个场景详情
- 绑定当前模板

### `create_scene`

- 拍照/选图
- 前端压图
- 上传并创建任务

### `task_center`

- 展示任务列表
- 展示任务进度
- 成功跳转结果页

### `my_scenes`

- 展示当前用户自己的场景

### `profile`

- 用户信息
- 会员状态

---

## 11. 前后端契约建议

## 11.1 小程序不应关心磁盘细节

前端只关心：

- `sceneId`
- `background`
- `items`
- `verbs`
- `jobId`
- `status`

前端不应该直接拼接磁盘路径。

## 11.2 API 对前端返回 DTO，不直接暴露数据库结构

场景详情 API 应返回可直接渲染的结构。

任务详情 API 应返回可直接显示的结构。

## 11.3 Worker 只和 job payload、数据库、存储服务交互

Worker 不直接面向前端协议耦合页面逻辑。

---

## 12. 安全与权限

## 12.1 私人场景访问控制

规则：

- API 查询场景详情时校验 `owner_user_id`
- 非 owner 返回 403

## 12.2 文件上传限制

限制：

- 仅允许图片 MIME
- 限制文件大小
- 文件名去用户输入化

## 12.3 场景资源直链问题

MVP 可先使用可公开 URL，但私人场景更稳的方式是：

- 通过鉴权 API 获取场景数据
- 音频和图片短期可通过静态域名访问
- 后续再增加签名 URL 或代理读取

---

## 13. 非功能性要求

## 13.1 性能

- 私人任务期望 30-90 秒内完成
- 场景详情 API 目标 < 300ms
- 小程序打开场景首屏目标 < 2s

## 13.2 可观测性

至少记录：

- API 请求日志
- job 阶段日志
- 失败率
- 平均生成耗时

## 13.3 可恢复性

要求：

- 任务失败可重试
- 生成中间文件可保留排错
- 场景 JSON 可重建

---

## 14. 开发里程碑建议

## M1：统一运行时场景页

交付：

- 新建 `scene_runtime`
- 从 API 拉取场景 JSON
- 用现有共享模板渲染

## M2：最小 API 和数据库

交付：

- users/scenes/jobs 基础表
- `GET /api/scenes`
- `GET /api/scenes/{sceneId}`
- `POST /api/auth/wx-login`

## M3：上传与任务流

交付：

- `POST /api/uploads/file`
- `POST /api/tasks`
- `GET /api/tasks/{jobId}`
- Redis 队列

## M4：Worker 生成闭环

交付：

- 压图
- 多模态识别
- TTS
- scene JSON 写入
- 数据库回写

## M5：私人场景查看

交付：

- 我的任务页
- 我的场景页
- 权限控制

## M6：公开场景库

交付：

- 公开场景列表
- 分类
- 会员访问控制

---

## 15. 工程实施顺序建议

为了降低风险，建议严格按以下顺序推进：

1. 先定义统一 scene JSON schema
2. 再改造小程序成 runtime 场景页
3. 再做 API 只读查询
4. 再做上传接口
5. 再做 jobs + Redis
6. 再接入 worker
7. 最后补会员和后台

不要先做：

- 大量公开场景生产
- 复杂管理后台
- R2 同步
- 支付

---

## 16. 风险清单

### 风险 1：继续沿用静态源码生成

后果：

- 再次碰到 2MB 限制
- app.json 页面注册持续膨胀

### 风险 2：私人场景资源直接完全公开

后果：

- 隐私泄露

### 风险 3：前端和 worker 协议不统一

后果：

- 返工成本高

### 风险 4：上传、任务、场景 ID 不统一

后果：

- 查询和追踪困难

---

## 17. MVP 落地结论

要让这个系统尽快落地成一个可运行的 MVP，工程上最关键的是：

1. 用统一 runtime 页面替代静态场景源码页面
2. 用数据库和 scene JSON 作为内容核心
3. 用 Redis + Python worker 做异步生成
4. 用本地磁盘做第一阶段资源存储
5. 后续再把磁盘资源同步到 R2

对于当前阶段，最合理的下一步实施动作是：

1. 建库建表
2. 定 API skeleton
3. 建小程序 runtime 页面
4. 建 worker 作业链

这四步做完，MVP 的骨架就完整了。

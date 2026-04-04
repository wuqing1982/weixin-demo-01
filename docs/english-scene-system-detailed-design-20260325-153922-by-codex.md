# 英语场景学习系统详细设计

时间：2026-03-25 15:39:22  
作者：Codex

## 1. 文档目标

本文档基于当前已经实现并可运行的场景渲染页面模板，设计未来可产品化的完整系统，包括：

- 数据库设计
- 微信小程序前端设计
- 后端 API 设计
- Python worker 设计
- 本地磁盘存储设计
- 任务流设计
- 权限和会员设计
- 运维与演进建议

当前设计前提：

- 小程序的单个场景 UI 模板已经确定
- 当前页面结构以 [`pages/shared/scene-template.wxml`](E:\202603\weixin-demo\pages\shared\scene-template.wxml)、[`pages/shared/scene-page.js`](E:\202603\weixin-demo\pages\shared\scene-page.js)、[`pages/shared/scene.wxss`](E:\202603\weixin-demo\pages\shared\scene.wxss) 为基础
- 短期资源落磁盘，后续异步同步到 Cloudflare R2
- Worker 使用 Python

---

## 2. 当前模板页能力边界

当前场景页模板已经具备一套稳定的运行时 UI 模型。

### 2.1 当前模板实际包含的核心元素

- 一张背景图
- 多个热点区域
- 底部信息卡
- 一组动词 chip
- 音频播放
- 播放速度控制
- 循环播放控制
- 设备预览模式切换

### 2.2 当前模板实际依赖的数据结构

从现有模板代码可归纳出一个场景页最小协议：

```json
{
  "sceneId": "breakfast",
  "title": "营养早餐",
  "background": "/assets/images/breakfast.jpg",
  "items": [
    {
      "id": "porridge",
      "word": "porridge",
      "ipa": "/ˈpɒrɪdʒ/",
      "meaning": "粥",
      "sentence": "I eat porridge for breakfast.",
      "sentenceTranslation": "我早餐吃粥。",
      "rect": { "l": 13.5, "t": 24.5, "w": 50.2, "h": 15.0 },
      "audio": "/assets/audio/breakfast/xxx.mp3"
    }
  ],
  "verbs": [
    {
      "id": "v1",
      "word": "eat",
      "ipa": "/iːt/",
      "meaning": "吃",
      "sentence": "I eat boiled eggs.",
      "sentenceTranslation": "我吃煮鸡蛋。",
      "audio": "/assets/audio/breakfast/yyy.mp3"
    }
  ]
}
```

这意味着未来系统最重要的设计原则是：

- 不再生成大量小程序源码页面
- 只要服务端能返回这套协议，小程序就能渲染场景

---

## 3. 总体架构

系统建议拆成六层：

1. 微信小程序前端
2. API 服务
3. Redis 队列
4. Python worker
5. 磁盘资源存储
6. 数据库

整体职责分工如下：

- 小程序：负责上传、任务发起、任务查询、场景渲染
- API：负责鉴权、数据查询、任务创建、权限校验
- Redis：负责异步任务投递
- Worker：负责 AI 分析、压图、TTS、生成场景数据
- 磁盘：负责保存图片、音频、JSON
- DB：负责保存场景记录、任务记录、用户和权限关系

---

## 4. 核心设计原则

### 4.1 一套页面模板，所有场景共用

不再为每个场景写一个新的小程序页面源码目录。  
未来应收敛为一个通用场景页，例如：

- `pages/scene_runtime/scene`

这个页面只负责：

- 根据 `sceneId` 拉取场景 JSON
- 将 JSON 绑定到当前共享模板

### 4.2 服务器生成的是数据和资源，不是小程序源码

Worker 生成的产物应是：

- 背景图
- 热点数据
- 动词数据
- 音频
- 场景 JSON

而不是：

- `app.json` 修改
- `scene-data.js`
- `scene.json`
- `scene.wxml`

### 4.3 公开场景和私人场景共用一套协议

公开场景与私人场景只在权限和来源上不同，不应在前端渲染层分叉。

### 4.4 资源本地落盘，逻辑上提前抽象为存储服务

虽然短期使用磁盘存储，但代码设计上应先抽象：

- `StorageService.save_file()`
- `StorageService.get_public_url()`
- `StorageService.copy_to_cdn_queue()`

这样后续迁移到 R2 时，前端和业务代码不用大改。

---

## 5. 数据模型设计

推荐使用 MySQL 或 PostgreSQL。  
这里用关系型数据库建模。

## 5.1 users

用户表。

| 字段 | 类型 | 说明 |
|---|---|---|
| id | bigint pk | 用户主键 |
| openid | varchar(64) unique | 微信 openid |
| unionid | varchar(64) null | 微信 unionid |
| nickname | varchar(128) | 用户昵称 |
| avatar_url | varchar(512) | 头像 |
| membership_status | varchar(32) | `free` / `member` / `vip` |
| membership_expire_at | datetime null | 会员过期时间 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

## 5.2 scenes

场景主表。

| 字段 | 类型 | 说明 |
|---|---|---|
| id | bigint pk | 场景主键 |
| scene_uuid | varchar(64) unique | 对外场景 ID |
| scene_type | varchar(32) | `public` / `private` |
| owner_user_id | bigint null | 私人场景所属用户 |
| source_type | varchar(32) | `preset` / `upload` / `admin_upload` |
| title | varchar(255) | 场景标题 |
| subtitle | varchar(255) null | 可选副标题 |
| cover_image_path | varchar(1024) | 封面图路径 |
| background_image_path | varchar(1024) | 背景图路径 |
| scene_json_path | varchar(1024) | 场景 JSON 路径 |
| visibility | varchar(32) | `public` / `member` / `private` |
| status | varchar(32) | `draft` / `processing` / `ready` / `failed` / `archived` |
| category | varchar(64) null | 场景分类 |
| tags_json | json null | 标签 |
| version | int | 协议版本 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

说明：

- `scene_uuid` 是小程序和 API 对外的主键
- `scene_json_path` 指向最终可渲染的标准 JSON
- `background_image_path` 用于快速展示，不必每次都反解析 JSON

## 5.3 scene_items

热点名词表。

| 字段 | 类型 | 说明 |
|---|---|---|
| id | bigint pk | 主键 |
| scene_id | bigint | 关联 scenes.id |
| item_id | varchar(64) | 场景内对象 ID |
| word | varchar(128) | 英文单词 |
| ipa | varchar(128) | 音标 |
| meaning | varchar(255) | 中文释义 |
| sentence | text | 英文例句 |
| sentence_translation | text | 中文翻译 |
| rect_l | decimal(6,2) | 热点左边距百分比 |
| rect_t | decimal(6,2) | 热点顶部百分比 |
| rect_w | decimal(6,2) | 热点宽度百分比 |
| rect_h | decimal(6,2) | 热点高度百分比 |
| audio_path | varchar(1024) null | 音频路径 |
| sort_order | int | 排序 |
| created_at | datetime | 创建时间 |

## 5.4 scene_verbs

动词表。

| 字段 | 类型 | 说明 |
|---|---|---|
| id | bigint pk | 主键 |
| scene_id | bigint | 关联 scenes.id |
| verb_id | varchar(64) | 场景内动词 ID |
| word | varchar(128) | 动词 |
| ipa | varchar(128) | 音标 |
| meaning | varchar(255) | 中文释义 |
| sentence | text | 英文例句 |
| sentence_translation | text | 中文翻译 |
| audio_path | varchar(1024) null | 音频路径 |
| sort_order | int | 排序 |
| created_at | datetime | 创建时间 |

## 5.5 scene_assets

资源索引表。

| 字段 | 类型 | 说明 |
|---|---|---|
| id | bigint pk | 主键 |
| scene_id | bigint | 关联 scenes.id |
| asset_type | varchar(32) | `background` / `cover` / `audio_item` / `audio_verb` / `json` |
| asset_key | varchar(255) | 资源逻辑键 |
| local_path | varchar(1024) | 本地磁盘路径 |
| public_url | varchar(1024) null | 当前访问 URL |
| cdn_status | varchar(32) | `local_only` / `syncing` / `synced` / `failed` |
| mime_type | varchar(128) | MIME |
| file_size | bigint | 文件大小 |
| checksum | varchar(128) null | 文件校验 |
| created_at | datetime | 创建时间 |

## 5.6 jobs

任务表。

| 字段 | 类型 | 说明 |
|---|---|---|
| id | bigint pk | 主键 |
| job_uuid | varchar(64) unique | 对外任务 ID |
| job_type | varchar(32) | `generate_public_scene` / `generate_private_scene` / `sync_to_r2` |
| user_id | bigint null | 发起人 |
| source_image_path | varchar(1024) | 原图路径 |
| source_image_url | varchar(1024) null | 可选原图 URL |
| scene_id | bigint null | 成功后关联场景 |
| status | varchar(32) | `queued` / `running` / `succeeded` / `failed` / `canceled` |
| progress | int | 0-100 |
| current_stage | varchar(64) | 当前阶段 |
| payload_json | json | 任务请求参数 |
| result_json | json null | 结果摘要 |
| error_message | text null | 错误信息 |
| retry_count | int | 重试次数 |
| created_at | datetime | 创建时间 |
| started_at | datetime null | 开始时间 |
| finished_at | datetime null | 完成时间 |

## 5.7 memberships

会员订单或权限表，可先简化。

| 字段 | 类型 | 说明 |
|---|---|---|
| id | bigint pk | 主键 |
| user_id | bigint | 用户 ID |
| membership_type | varchar(32) | `member` / `vip` |
| status | varchar(32) | `active` / `expired` |
| start_at | datetime | 生效时间 |
| expire_at | datetime | 过期时间 |
| source | varchar(32) | 支付来源 |
| created_at | datetime | 创建时间 |

---

## 6. 场景 JSON 协议设计

这是整个系统最核心的协议。小程序前端、API、worker 都围绕它组织。

```json
{
  "sceneId": "scene_20260325_xxx",
  "title": "营养早餐",
  "background": "https://cdn.example.com/scenes/breakfast/background.jpg",
  "cover": "https://cdn.example.com/scenes/breakfast/cover.jpg",
  "items": [
    {
      "id": "porridge",
      "word": "porridge",
      "ipa": "/ˈpɒrɪdʒ/",
      "meaning": "粥",
      "sentence": "I eat porridge for breakfast.",
      "sentenceTranslation": "我早餐吃粥。",
      "rect": { "l": 13.5, "t": 24.5, "w": 50.2, "h": 15.0 },
      "audio": "https://cdn.example.com/scenes/breakfast/audio/item_porridge.mp3"
    }
  ],
  "verbs": [
    {
      "id": "v1",
      "word": "eat",
      "ipa": "/iːt/",
      "meaning": "吃",
      "sentence": "I eat porridge for breakfast.",
      "sentenceTranslation": "我早餐吃粥。",
      "audio": "https://cdn.example.com/scenes/breakfast/audio/verb_eat.mp3"
    }
  ],
  "meta": {
    "sceneType": "private",
    "ownerUserId": "u_123",
    "visibility": "private",
    "version": 1
  }
}
```

设计要求：

- 与当前前端模板兼容
- 允许资源 URL 是本地磁盘映射 URL 或 CDN URL
- 允许前端直接用 `background/items/verbs`

---

## 7. 本地磁盘存储设计

短期你计划用 Gluster 磁盘，这个方向可行。建议不要直接把业务逻辑绑死在绝对路径，而是抽象出统一目录规范。

## 7.1 根目录建议

例如：

```text
/data/english-scenes/
  uploads/
  public-scenes/
  private-scenes/
  jobs/
  temp/
  export/
```

Windows 开发环境可对应：

```text
E:\english-scenes-data\
```

## 7.2 目录约定

### 7.2.1 上传原图

```text
uploads/
  2026/
    03/
      25/
        user_1001/
          original_xxx.jpg
          compressed_xxx.jpg
```

### 7.2.2 公开场景

```text
public-scenes/
  breakfast/
    scene.json
    background.jpg
    cover.jpg
    audio/
      item_porridge.mp3
      verb_eat.mp3
```

### 7.2.3 私人场景

```text
private-scenes/
  user_1001/
    scene_20260325_abc123/
      scene.json
      background.jpg
      cover.jpg
      audio/
        item_porridge.mp3
        verb_eat.mp3
```

### 7.2.4 任务中间文件

```text
jobs/
  job_20260325_xxx/
    input.jpg
    resized.jpg
    hotspots.json
    tts/
    logs/
```

## 7.3 URL 映射建议

由 API 或 Nginx 暴露静态路径：

- `/static/public-scenes/...`
- `/static/private-scenes/...`
- `/static/uploads/...`

短期可直接读取本地盘对外提供 URL。  
后续异步同步到 R2 后，只需要替换 `public_url` 的生成逻辑。

---

## 8. 小程序前端设计

## 8.1 页面结构建议

建议前端最终页面结构：

```text
pages/
  home/
  library/
  scene_runtime/
  create_scene/
  task_center/
  my_scenes/
  profile/
```

### 8.1.1 `home`

职责：

- 首页入口
- 推荐公开场景
- 进入上传功能

### 8.1.2 `library`

职责：

- 公开场景列表
- 分类筛选
- 最近学习

### 8.1.3 `scene_runtime`

职责：

- 通用场景页
- 拉取场景 JSON
- 调用当前共享模板渲染

这个页面是未来最核心的页面。

### 8.1.4 `create_scene`

职责：

- 拍照
- 选图
- 前端压图
- 上传图片
- 创建任务

### 8.1.5 `task_center`

职责：

- 查看任务状态
- 查看失败原因
- 成功后进入场景

### 8.1.6 `my_scenes`

职责：

- 列出当前用户自己的私人场景
- 支持删除、重命名、重生成

### 8.1.7 `profile`

职责：

- 用户信息
- 会员状态
- 购买入口

## 8.2 前端服务层设计

建议新建：

```text
services/
  auth.js
  api.js
  scene.js
  task.js
  upload.js
  membership.js
```

### 8.2.1 `auth.js`

- 微信登录
- token 管理
- 当前用户读取

### 8.2.2 `scene.js`

- 获取公开场景列表
- 获取场景详情
- 获取我的场景列表

### 8.2.3 `task.js`

- 创建任务
- 获取任务状态
- 轮询任务

### 8.2.4 `upload.js`

- 前端图片压缩
- 上传文件
- 调上传签名 API

## 8.3 当前模板如何复用

当前你已有的共享模板已经非常适合作为运行时场景模板。  
建议做的不是重写 UI，而是把它改成服务端数据加载模式。

即：

- 保留当前模板 WXML/WXSS
- 把静态 `require('./scene-data')` 替换为网络请求加载

目标写法：

- 页面 `onLoad(options)` 读取 `sceneId`
- 调 `GET /api/scenes/{sceneId}`
- 将返回值 setData 到模板

## 8.4 前端上传流程

推荐流程：

1. 用户拍照或选图
2. 前端压缩到适合手机竖屏尺寸
3. 调 `POST /api/uploads/sign`
4. 小程序上传到磁盘映射目录或上传网关
5. 拿到 `sourceImagePath` 或 `sourceImageUrl`
6. 调 `POST /api/tasks`
7. 跳转 `task_center`

---

## 9. API 设计

以下为推荐 REST API。

## 9.1 认证

### `POST /api/auth/wx-login`

请求：

```json
{
  "code": "wx.login code"
}
```

响应：

```json
{
  "token": "jwt",
  "user": {
    "id": "u_1001",
    "nickname": "Tom",
    "membershipStatus": "member"
  }
}
```

## 9.2 用户信息

### `GET /api/me`

响应：

```json
{
  "id": "u_1001",
  "nickname": "Tom",
  "membershipStatus": "member",
  "membershipExpireAt": "2026-12-31 23:59:59"
}
```

## 9.3 公开场景列表

### `GET /api/scenes`

参数：

- `type=public`
- `category=...`
- `page=1`
- `pageSize=20`

响应：

```json
{
  "list": [
    {
      "sceneId": "scene_breakfast",
      "title": "营养早餐",
      "coverUrl": "https://...",
      "category": "food"
    }
  ],
  "total": 100
}
```

## 9.4 场景详情

### `GET /api/scenes/{sceneId}`

响应直接返回统一场景协议。

API 侧负责：

- 判断公开场景访问权限
- 判断私人场景 owner 权限
- 返回最终可渲染的 JSON

## 9.5 我的场景

### `GET /api/my/scenes`

返回当前用户的私人场景列表。

## 9.6 上传签名

### `POST /api/uploads/sign`

短期落磁盘时，这个接口可以返回一个业务上传地址；后续切到 R2 时再改成预签名上传。

请求：

```json
{
  "filename": "photo.jpg",
  "contentType": "image/jpeg",
  "size": 123456
}
```

响应：

```json
{
  "uploadUrl": "https://api.example.com/api/uploads/file",
  "storageKey": "uploads/2026/03/25/user_1001/original_xxx.jpg"
}
```

## 9.7 上传文件

### `POST /api/uploads/file`

职责：

- 存原图到磁盘
- 返回可追踪路径

响应：

```json
{
  "storageKey": "uploads/2026/03/25/user_1001/original_xxx.jpg",
  "localPath": "/data/english-scenes/uploads/2026/03/25/user_1001/original_xxx.jpg",
  "publicUrl": "https://static.example.com/uploads/2026/03/25/user_1001/original_xxx.jpg"
}
```

## 9.8 创建生成任务

### `POST /api/tasks`

请求：

```json
{
  "jobType": "generate_private_scene",
  "sourceImagePath": "/data/english-scenes/uploads/2026/03/25/user_1001/original_xxx.jpg",
  "sceneHint": null,
  "sceneTitle": null
}
```

响应：

```json
{
  "jobId": "job_20260325_xxx",
  "status": "queued"
}
```

## 9.9 查询任务

### `GET /api/tasks/{jobId}`

响应：

```json
{
  "jobId": "job_20260325_xxx",
  "status": "running",
  "progress": 60,
  "currentStage": "tts_generating",
  "result": null,
  "errorMessage": null
}
```

成功后：

```json
{
  "jobId": "job_20260325_xxx",
  "status": "succeeded",
  "progress": 100,
  "currentStage": "done",
  "result": {
    "sceneId": "scene_20260325_abc123"
  }
}
```

---

## 10. Worker 设计

## 10.1 Worker 输入

Redis 中的 job payload 推荐如下：

```json
{
  "jobId": "job_20260325_xxx",
  "jobType": "generate_private_scene",
  "userId": "u_1001",
  "sourceImagePath": "/data/english-scenes/uploads/2026/03/25/user_1001/original_xxx.jpg",
  "sceneHint": null,
  "sceneTitle": null,
  "ttsProvider": "azure_local_5003"
}
```

## 10.2 Worker 处理阶段

推荐拆成以下阶段：

1. `prepare_input`
2. `resize_image`
3. `analyze_image`
4. `generate_copywriting`
5. `generate_tts`
6. `build_scene_json`
7. `persist_scene`
8. `schedule_sync_to_r2`

## 10.3 每阶段职责

### `prepare_input`

- 检查原图是否存在
- 复制到 jobs 工作目录
- 建立 job 临时目录

### `resize_image`

- 缩放为手机竖屏友好尺寸
- 产出 jpg/webp
- 生成 cover

### `analyze_image`

- 调视觉模型
- 识别热点
- 产出标准化热点 JSON

### `generate_copywriting`

- 生成名词、动词、例句、中文翻译

### `generate_tts`

- 调 5003 本地 TTS
- 生成音频文件

### `build_scene_json`

- 生成最终统一协议 JSON

### `persist_scene`

- 写 `scenes`
- 写 `scene_items`
- 写 `scene_verbs`
- 写 `scene_assets`
- 保存 `scene.json` 到目标场景目录

### `schedule_sync_to_r2`

- 创建一个 `sync_to_r2` 任务
- 不阻塞主生成流程

## 10.4 Worker 错误处理

要求：

- 每个阶段更新 `jobs.current_stage`
- 每个阶段失败都写 `error_message`
- 允许重试
- 每个 job 目录保留日志

---

## 11. 公开场景与私人场景的业务设计

## 11.1 公开场景

生成方式：

- 运营在后台上传素材
- 触发 `generate_public_scene`
- worker 生成后写入 `visibility=member`

访问规则：

- 会员可读
- 非会员不可读或只看部分

## 11.2 私人场景

生成方式：

- 用户上传图片
- 触发 `generate_private_scene`
- worker 生成后写入 `visibility=private`

访问规则：

- 仅 owner 可读
- 默认不允许其他用户访问

## 11.3 未来分享设计

如果后续要支持私人场景分享，建议增加：

- `scene_share_tokens`

字段：

- `scene_id`
- `token`
- `expire_at`
- `status`

不要直接暴露私人场景真实 ID。

---

## 12. 权限设计

## 12.1 权限规则

### 公开场景

- `visibility=public`：所有登录用户可读
- `visibility=member`：仅会员可读

### 私人场景

- `visibility=private`：仅 `owner_user_id` 可读

## 12.2 API 权限校验顺序

1. 场景是否存在
2. 场景状态是否为 `ready`
3. 是否公开场景
4. 如果是会员场景，校验会员
5. 如果是私人场景，校验 `owner_user_id`

---

## 13. 资源访问设计

## 13.1 短期

短期直接用本地静态文件服务。

例如：

- `https://static.example.com/public-scenes/...`
- `https://static.example.com/private-scenes/...`

## 13.2 中期

由后台异步将本地资源同步到 R2。

同步后：

- 更新 `scene_assets.public_url`
- 更新 `scene JSON` 中对应 URL

## 13.3 建议保留本地路径和公开 URL 两套字段

原因：

- 便于回溯和修复
- R2 同步失败时仍可本地兜底

---

## 14. 日志与运维设计

## 14.1 API 日志

记录：

- 用户 ID
- 请求路径
- 状态码
- 请求耗时

## 14.2 Worker 日志

记录：

- jobId
- 当前阶段
- 调模型耗时
- TTS 成功数
- 文件生成路径
- 错误堆栈

## 14.3 任务监控

至少要有：

- 队列长度
- 处理中任务数
- 失败任务数
- 每阶段平均耗时

---

## 15. 目录组织建议

## 15.1 小程序仓库

```text
weixin-miniapp/
  app.js
  app.json
  pages/
    home/
    library/
    scene_runtime/
    create_scene/
    task_center/
    my_scenes/
    profile/
  components/
    scene-player/
    hotspot-layer/
    verb-strip/
    audio-toolbar/
  services/
    api.js
    auth.js
    scene.js
    task.js
    upload.js
```

## 15.2 API 仓库

```text
scene-api/
  app/
    main.py
    routers/
    services/
    models/
    schemas/
    infra/
```

## 15.3 Worker 仓库

```text
scene-worker/
  worker/
    main.py
    jobs/
    services/
    infra/
```

---

## 16. 推荐落地顺序

## 第一阶段：去掉静态源码生成依赖

目标：

- 先让小程序使用统一 runtime 页面
- 让场景从 API 获取

优先任务：

1. 新建 `scene_runtime`
2. 定义统一 scene JSON schema
3. API 提供 `GET /api/scenes/{sceneId}`

## 第二阶段：接入任务流

目标：

- 用户可上传图片生成私人场景

优先任务：

1. `POST /api/uploads/file`
2. `POST /api/tasks`
3. Redis + worker
4. `GET /api/tasks/{jobId}`

## 第三阶段：后台生产公开场景

目标：

- 用同一套 worker 生成公开场景

## 第四阶段：R2 同步

目标：

- 本地落盘后异步上传 R2

---

## 17. 结论

基于你当前已经确定的场景模板，未来系统最合理的设计不是继续批量生成小程序源码页面，而是：

- 小程序前端只保留固定模板和业务入口
- 服务器端生成统一场景 JSON 和资源
- 公开场景与私人场景共用同一渲染协议
- Worker 异步完成图像理解、文案、TTS、资源生成
- 短期用磁盘存储，后续无缝演进到 R2

这个设计能同时解决：

- 小程序包体限制
- 私人场景高动态扩展问题
- 资源存储迁移问题
- Python worker 的异步处理需求

如果继续往下推进，最值得先做的是：

1. 确定统一 scene JSON schema
2. 先实现 `scene_runtime` 页面
3. 设计数据库和 API
4. 把现有流水线改造成 worker 作业链，而不是小程序源码生成器

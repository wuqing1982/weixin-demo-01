# 英语场景学习小程序 C4 架构设计

时间：2026-03-25 15:05:16  
作者：Codex

## 1. 背景与目标

这个小程序的核心业务有两条：

1. 公开场景库  
预先生成很多英语学习场景，包含背景图片、热点词汇、动词、音频。所有登录会员都可以访问。

2. 私人场景生成  
用户拍照或上传图片后，系统异步生成仅本人可见的英语学习场景。

当前静态生成小程序源码页面的方式，适合早期原型验证，但不适合长期产品化。主要原因：

- 小程序主包和分包体积受限
- 每新增一个场景都要改页面文件、注册表和配置
- 图片和音频一多，预览和发布都会反复碰到包体问题
- 私人场景天然是高动态内容，不适合预生成小程序源码

因此，长期推荐架构应该转为：

- 小程序前端只保留少量固定页面和通用场景模板
- 服务器端生成场景数据和资源文件
- 小程序通过 API 拉取场景 JSON，用统一模板渲染
- 图片、音频、可选 H5 页面放在对象存储和 CDN

---

## 2. C1 Context

### 2.1 系统目标

构建一个英语场景学习平台，支持：

- 面向会员的公开场景学习
- 面向个人用户的私人场景生成
- 基于图片理解、TTS、热点标注的自动化内容生产

### 2.2 外部参与者

#### 用户

- 使用微信小程序浏览公开场景
- 上传私人照片生成个人场景
- 查看任务进度和生成结果

#### 运营/管理员

- 管理公开场景内容
- 上传素材并触发生成
- 审核失败任务、重试任务

#### 微信平台

- 提供登录态
- 提供拍照、上传、支付/会员能力
- 提供小程序运行环境

#### AI/TTS 服务

- 视觉模型：识别图片中的对象、生成热点和例句
- TTS 服务：生成英语单词和句子的音频

#### Redis

- 作为异步任务队列
- 解耦 API 服务和生成 worker

#### 对象存储/CDN

- 存放背景图、音频、缩略图
- 对资源做缓存和分发

#### 数据库

- 保存用户、场景、任务、资源索引和权限关系

---

## 3. C2 Container

系统推荐拆成以下容器。

### 3.1 微信小程序前端

职责：

- 微信登录和会员态管理
- 公开场景列表浏览
- 私人图片上传
- 任务创建和状态查询
- 使用统一模板页渲染场景

关键原则：

- 不再为每个场景生成独立小程序源码页面
- 前端保留一个通用场景页，例如 `scene_runtime`
- 场景内容完全由服务端数据驱动

### 3.2 API 服务

职责：

- 登录鉴权
- 上传签名
- 任务创建
- 任务状态查询
- 场景数据查询
- 权限控制
- 会员访问控制

建议技术：

- Python FastAPI
- REST API
- JWT 或会话 token

### 3.3 Worker 服务

职责：

- 消费 Redis 队列任务
- 下载并处理图片
- 调视觉模型生成热点数据
- 调 TTS 生成音频
- 上传资源到对象存储
- 写入数据库
- 更新任务状态

建议技术：

- Python worker
- RQ、Celery 或自定义 Redis consumer

### 3.4 Redis

职责：

- 异步任务队列
- 临时状态缓存
- 幂等 key 和限流辅助

### 3.5 数据库

职责：

- 保存用户
- 保存公开场景和私人场景
- 保存任务状态
- 保存资源 URL 和元数据
- 保存权限关系

建议：

- MySQL 或 PostgreSQL

### 3.6 对象存储 + CDN

职责：

- 存储背景图
- 存储音频
- 存储缩略图
- 可选存储 HTML 页面
- 对资源分发加速

### 3.7 可选后台管理系统

职责：

- 管理公开场景
- 查看任务失败原因
- 人工重试或重新生成
- 审核内容

---

## 4. C3 Component

下面对前端、API、Worker 三个核心容器继续拆组件。

### 4.1 小程序前端组件

#### 4.1.1 `auth`

职责：

- 微信登录
- token 持久化
- 获取用户和会员信息

#### 4.1.2 `scene-library`

职责：

- 公开场景列表
- 分类和搜索
- 最近学习记录

#### 4.1.3 `scene-runtime`

职责：

- 通用场景渲染页
- 加载 scene JSON
- 渲染背景图、热点、信息卡、音频

#### 4.1.4 `upload`

职责：

- 拍照/选图
- 前端压缩
- 获取上传签名
- 上传图片
- 创建任务

#### 4.1.5 `task-center`

职责：

- 显示任务进度
- 查看失败原因
- 成功后跳转结果页

#### 4.1.6 `cache`

职责：

- 缓存场景 JSON
- 缓存最近访问历史
- 管理图片和音频的本地使用策略

### 4.2 API 服务组件

#### 4.2.1 `auth controller`

接口职责：

- 登录
- token 刷新
- 用户身份解析

#### 4.2.2 `scene controller`

接口职责：

- 获取公开场景列表
- 获取单个场景详情
- 对私人场景做权限校验

#### 4.2.3 `upload controller`

接口职责：

- 生成上传签名
- 返回预签名 URL 或直传凭证

#### 4.2.4 `task controller`

接口职责：

- 创建任务
- 获取任务状态

#### 4.2.5 `membership controller`

接口职责：

- 会员状态查询
- 会员权限校验

#### 4.2.6 `scene service`

职责：

- 组装前端需要的统一场景 DTO
- 屏蔽底层表结构

#### 4.2.7 `task service`

职责：

- 创建任务记录
- 推送 Redis 队列
- 更新任务状态

#### 4.2.8 `permission service`

职责：

- 判断公开访问权限
- 判断私人场景 owner 权限

### 4.3 Worker 服务组件

#### 4.3.1 `job consumer`

职责：

- 消费 Redis 任务
- 幂等处理
- 失败重试

#### 4.3.2 `image processor`

职责：

- 下载原图
- 纠正方向
- 压缩
- 生成 jpg/webp 多尺寸版本

#### 4.3.3 `vision analyzer`

职责：

- 调用多模态模型
- 识别对象
- 生成热点词汇、动词、例句

#### 4.3.4 `tts generator`

职责：

- 调用 Azure TTS 或本地 TTS API
- 生成单词和句子音频

#### 4.3.5 `asset uploader`

职责：

- 上传图片、音频到对象存储
- 写回 CDN URL

#### 4.3.6 `scene builder`

职责：

- 生成统一 scene JSON
- 写入数据库

#### 4.3.7 `status reporter`

职责：

- 更新任务状态
- 写错误日志

---

## 5. C4 Code 级组织建议

推荐拆成三个仓库，而不是把所有代码混在一个目录里。

### 5.1 `miniapp`

```text
miniapp/
  app.js
  app.json
  pages/
    home/
    library/
    upload/
    tasks/
    scene_runtime/
  components/
    scene-player/
    hotspot-layer/
    audio-player/
  services/
    api.js
    auth.js
    scene.js
    task.js
    upload.js
  utils/
    cache.js
    image.js
    permission.js
```

### 5.2 `backend-api`

```text
backend-api/
  app/
    main.py
    routers/
      auth.py
      scenes.py
      tasks.py
      uploads.py
    services/
      auth_service.py
      scene_service.py
      task_service.py
      permission_service.py
    models/
      user.py
      scene.py
      job.py
    schemas/
      auth.py
      scene.py
      task.py
    infra/
      db.py
      redis.py
      storage.py
```

### 5.3 `scene-worker`

```text
scene-worker/
  worker/
    main.py
    consumers/
      redis_consumer.py
    jobs/
      generate_scene.py
    services/
      image_processor.py
      vision_service.py
      tts_service.py
      asset_service.py
      scene_builder.py
    infra/
      db.py
      redis.py
      storage.py
```

---

## 6. 统一场景协议

推荐定义统一的 `scene JSON schema`，让公开场景和私人场景都走同一套协议。

示例：

```json
{
  "id": "scene_xxx",
  "type": "public",
  "title": "营养早餐",
  "backgroundUrl": "https://cdn.xxx.com/scenes/breakfast.jpg",
  "items": [
    {
      "id": "porridge",
      "word": "porridge",
      "ipa": "/ˈpɒrɪdʒ/",
      "meaning": "粥",
      "sentence": "I eat porridge for breakfast.",
      "sentenceTranslation": "我早餐吃粥。",
      "rect": {
        "l": 13.5,
        "t": 24.5,
        "w": 50.2,
        "h": 15.0
      },
      "audioUrl": "https://cdn.xxx.com/audio/porridge.mp3"
    }
  ],
  "verbs": [],
  "visibility": "member",
  "ownerUserId": null
}
```

这个协议要满足：

- 前端只认这一套
- 公开和私人场景统一渲染
- Worker 产出结果统一入库

---

## 7. 关键业务流程

### 7.1 公开场景生成流程

1. 运营上传一张图片
2. API 创建公开场景生成任务
3. Redis 入队
4. Worker 处理图片、生成热点和音频
5. 上传资源到对象存储
6. 写入公开场景数据到数据库
7. 小程序前端可在公开库看到该场景

### 7.2 私人场景生成流程

1. 用户在小程序拍照或上传图片
2. 前端压缩图片
3. 前端上传图片到存储
4. 调 `POST /tasks` 创建任务
5. API 把任务推进 Redis
6. Worker 异步处理
7. 处理完成后写入私人场景数据
8. 前端轮询 `GET /tasks/{id}`
9. 任务完成后跳转通用场景页查看结果

### 7.3 场景浏览流程

1. 小程序进入通用场景页
2. 根据 `sceneId` 调 `GET /scenes/{id}`
3. API 判断用户权限
4. 返回场景 JSON 和资源 URL
5. 前端统一模板渲染

---

## 8. API 草案

### 8.1 登录

- `POST /api/auth/login`

### 8.2 场景

- `GET /api/scenes`
- `GET /api/scenes/{sceneId}`

### 8.3 上传

- `POST /api/uploads/sign`

### 8.4 任务

- `POST /api/tasks`
- `GET /api/tasks/{taskId}`

### 8.5 会员

- `GET /api/me`
- `GET /api/membership`

---

## 9. 数据库模型建议

### 9.1 `users`

- `id`
- `openid`
- `nickname`
- `membership_status`
- `created_at`

### 9.2 `scenes`

- `id`
- `type`，取值 `public` 或 `private`
- `owner_user_id`
- `title`
- `background_image_url`
- `cover_image_url`
- `scene_json`
- `visibility`
- `status`
- `created_at`

### 9.3 `jobs`

- `id`
- `user_id`
- `image_url`
- `status`
- `progress`
- `error_message`
- `result_scene_id`
- `created_at`

### 9.4 `scene_assets`

- `id`
- `scene_id`
- `asset_type`
- `asset_url`
- `meta_json`

---

## 10. 为什么不建议继续生成小程序源码页面

从第一性原理看，系统真正需要的是：

- 一个稳定的渲染壳
- 一份场景数据
- 一组静态资源

而不是：

- 每个场景都生成一套新的小程序源码页面

继续生成小程序源码页面会持续带来：

- 主包/分包体积问题
- `app.json` 注册问题
- 页面注册冲突
- 乱码和语法拼接问题
- 私人场景无法规模化

所以服务端真正应该生成的是：

- scene JSON
- 图片
- 音频
- 可选 HTML 页面

而不是新的小程序源码。

---

## 11. 推荐的演进路径

### 第一阶段

- 保留现有视觉效果和场景模板
- 把所有场景改为统一模板渲染
- 图片和音频先迁到服务器

### 第二阶段

- 私人场景改为真正的异步任务流
- 小程序只做上传、查任务、看结果

### 第三阶段

- 增加后台管理系统
- 支持公开内容生产、审核和批量重试

---

## 12. 结论

对于这个英语场景学习小程序，长期正确的架构不是“持续生成很多小程序页面文件”，而是：

- 小程序前端固定
- 服务端生成内容
- 内容通过统一协议下发
- 图片和音频走对象存储/CDN
- 公开场景和私人场景共用一套场景渲染引擎

这个设计同时解决了：

- 小程序包体限制
- 动态内容扩展问题
- 私人场景权限隔离问题
- Python worker 的异步处理需求

如果后续继续推进，下一步最值得先做的是：

1. 定义统一 `scene JSON schema`
2. 设计 API
3. 把现有小程序改造成单一通用场景页
4. 把 `pipeline_weixin.py` 转成真正的 worker 任务处理链

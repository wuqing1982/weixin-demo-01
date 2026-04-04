# 场景生成后端接口与目录设计

时间：2026-04-04 09:44 UTC  
作者：Codex

## 1. 文档目标

本文档用于把“用户在小程序拍照或上传图片，后端异步生成新场景”的思路收敛成一版可实施设计。

当前已知前提：

- 小程序前端已经有稳定可用的 runtime 场景页
- 当前后端已经提供：
  - `GET /api/health`
  - `GET /api/scenes`
  - `GET /api/scenes/{sceneId}`
  - `GET /api/my/scenes`
- 当前小程序 runtime 消费协议已经稳定，不应轻易改动
- 场景生成核心引擎位于：
  - `/www/wwwroot/e.cps.vin/core100`
- Azure TTS 服务位于本机：
  - `http://127.0.0.1:5003`

本文档只解决以下问题：

- 小程序如何发起上传和生成
- 后端 API 如何设计
- worker 如何调用 `core100`
- 生成结果如何落盘
- 如何把 `core100` 输出适配到当前小程序 runtime 协议

本文档暂不引入数据库，优先采用“磁盘 + JSON 索引”的方式做最小闭环。

## 2. 设计原则

### 2.1 不让前端直接消费 `core100` 原始输出

`core100` 当前更像“生成引擎”，不是直接给小程序的 API 协议层。

前端继续只认当前 runtime 协议：

```json
{
  "sceneId": "scene_xxx",
  "title": "场景标题",
  "background": "https://e.cps.vin/assets/...",
  "cover": "https://e.cps.vin/assets/...",
  "items": [],
  "verbs": [],
  "meta": {}
}
```

所以必须增加一层 adapter，把 `core100` 输出转换成当前后端协议。

### 2.2 上传与生成分离

不要让上传接口直接同步跑 AI。

推荐拆成两步：

1. 上传图片
2. 创建生成任务

这样后续切换成 worker 队列时，API 不用推翻。

### 2.3 公开场景和用户生成场景共用一套详情协议

用户生成的新场景，最终仍通过：

- `GET /api/scenes/{sceneId}`

或：

- `GET /api/my/scenes`

返回给小程序。

前端 runtime 页不需要因为“官方预置场景”和“用户生成场景”分成两套渲染逻辑。

### 2.4 先磁盘落地，后续再替换成数据库/对象存储

第一版先落磁盘和 JSON 索引，理由：

- 当前项目已经是磁盘资源方案
- 先把场景生成闭环跑通更重要
- 后续替换成 MySQL / Redis / R2 时，可保持 API 和任务模型不变

## 3. 推荐目录结构

推荐在现有仓库基础上新增以下目录：

```txt
backend/
  app/
    main.py
    settings.py
    scene_store.py
    generated_scene_store.py
    upload_store.py
    task_store.py
    scene_adapter.py
    worker_runner.py
    schemas.py
  data/
    scenes.json
    generated_scenes.json
    tasks.json

assets/
  generated/
    <sceneId>/
      background.jpg
      cover.jpg
      audio/
        item1.mp3
        item2.mp3
        ...
  uploads/
    <uploadId>/
      source.jpg
      source.png
```

说明：

- `backend/data/scenes.json`
  - 保留现有公开预置场景
- `backend/data/generated_scenes.json`
  - 保存用户生成场景索引
- `backend/data/tasks.json`
  - 保存任务状态
- `assets/uploads/<uploadId>/source.*`
  - 保存原图
- `assets/generated/<sceneId>/`
  - 保存生成后的背景图、封面图和音频

## 4. 场景生成最小流程

### 4.1 流程概览

```txt
小程序
  -> 上传图片
  -> 创建任务
API
  -> 记录 upload
  -> 创建 task
worker
  -> 读取 upload
  -> 调 core100 分析图片
  -> 调 5003 Azure TTS 生成 mp3
  -> 适配成 runtime 场景 JSON
  -> 写入 generated_scenes.json
小程序
  -> 查询 task
  -> 任务完成后进入 scene_runtime
  -> 调现有 scenes API 渲染
```

### 4.2 任务状态机

推荐任务状态：

- `queued`
- `running`
- `failed`
- `done`

推荐额外字段：

- `progress`
- `step`
- `errorMessage`

示例：

```json
{
  "taskId": "task_20260404_0001",
  "status": "running",
  "step": "generate_audio",
  "progress": 72,
  "sceneId": "",
  "errorMessage": ""
}
```

## 5. API 设计

## 5.1 上传图片

```http
POST /api/uploads/image
```

用途：

- 小程序拍照或选图后上传原图

建议返回：

```json
{
  "code": 0,
  "data": {
    "uploadId": "upload_20260404_0001",
    "fileUrl": "https://e.cps.vin/assets/uploads/upload_20260404_0001/source.jpg",
    "width": 1080,
    "height": 1920
  }
}
```

说明：

- 第一版可直接用 `wx.uploadFile`
- 后端把文件落到 `assets/uploads/<uploadId>/`
- 返回 `uploadId` 供后续创建任务使用

## 5.2 创建生成任务

```http
POST /api/my/tasks/scene-generate
```

请求体建议：

```json
{
  "uploadId": "upload_20260404_0001",
  "title": "我的厨房场景",
  "includeVerbs": true,
  "sourceLang": "zh-CN",
  "accent": "en-US",
  "voiceGender": "female",
  "voiceName": "JennyNeural"
}
```

返回：

```json
{
  "code": 0,
  "data": {
    "taskId": "task_20260404_0001",
    "status": "queued"
  }
}
```

说明：

- 第一版直接固定 `en-US + female + JennyNeural` 也可以
- 先把参数收上来，后面再决定是否真正开放给用户配置

## 5.3 查询任务详情

```http
GET /api/my/tasks/{taskId}
```

返回：

```json
{
  "code": 0,
  "data": {
    "taskId": "task_20260404_0001",
    "status": "done",
    "step": "finished",
    "progress": 100,
    "sceneId": "scene_user_20260404_0001",
    "errorMessage": ""
  }
}
```

失败示例：

```json
{
  "code": 0,
  "data": {
    "taskId": "task_20260404_0001",
    "status": "failed",
    "step": "analyze_scene",
    "progress": 36,
    "sceneId": "",
    "errorMessage": "AI scene analyze failed"
  }
}
```

## 5.4 查询我的场景列表

```http
GET /api/my/scenes
```

返回结构建议与公开场景列表一致：

```json
{
  "code": 0,
  "data": {
    "list": [
      {
        "sceneId": "scene_user_20260404_0001",
        "title": "我的厨房场景",
        "coverUrl": "https://e.cps.vin/assets/generated/scene_user_20260404_0001/cover.jpg",
        "category": "generated",
        "visibility": "private",
        "sceneType": "private"
      }
    ],
    "total": 1,
    "page": 1,
    "pageSize": 20
  }
}
```

## 5.5 查询场景详情

第一版建议保持统一入口：

```http
GET /api/scenes/{sceneId}
```

处理方式：

- 先在公开场景存储中查
- 查不到再去用户生成场景存储中查

这样当前小程序 runtime 页完全不用改详情接口。

## 6. `core100` 接入方式

## 6.1 推荐接入边界

worker 只把 `core100` 当内部库或子流程使用，不对小程序暴露其原始文件格式。

推荐调用链路：

1. `analyze_scene.py`
2. 得到 `hotspots_<scene>.json`
3. `generate_audio.py --tts-url http://127.0.0.1:5003`
4. 不使用 `generate_html.py` 作为正式产物
5. 用 adapter 转换成当前 runtime 协议

## 6.2 为什么不直接用 `pipeline.py` 输出给前端

因为 `pipeline.py` 当前默认产物包括：

- `hotspots_xxx.json`
- `scene_xxx.html`
- `voice_slide/...`

其中：

- HTML 对小程序无用
- JSON 字段名和当前 API 协议不完全一致
- 默认音频输出目录不符合当前仓库的 `assets/` 对外策略

所以推荐保留两种用法：

- `core100/pipeline.py`
  - 用作开发验证和单图测试
- `backend/app/worker_runner.py`
  - 用作正式业务生成入口

## 7. 协议适配设计

## 7.1 `core100` 原始输出特征

根据当前 `core100` README，原始 JSON 更接近：

```json
{
  "scene_id": "park",
  "scene_title": "公园",
  "hotspots": [
    {
      "id": "bench",
      "word": "bench",
      "ipa": "/.../",
      "meaning": "长椅",
      "sentence": "This is a bench.",
      "sentence_translation": "这是长椅。",
      "rect": {
        "l": 10.0,
        "t": 20.0,
        "w": 15.0,
        "h": 12.0
      }
    }
  ]
}
```

## 7.2 当前前端需要的输出

当前后端协议要求：

```json
{
  "sceneId": "scene_user_20260404_0001",
  "title": "我的厨房场景",
  "background": "https://e.cps.vin/assets/generated/scene_user_20260404_0001/background.jpg",
  "cover": "https://e.cps.vin/assets/generated/scene_user_20260404_0001/cover.jpg",
  "items": [],
  "verbs": [],
  "meta": {
    "sceneType": "private",
    "visibility": "private",
    "sourceType": "upload"
  }
}
```

## 7.3 adapter 责任

建议新增：

```txt
backend/app/scene_adapter.py
```

职责：

- `scene_id` -> `sceneId`
- `scene_title` -> `title`
- `sentence_translation` -> `sentenceTranslation`
- `hotspots` -> `items`
- 生成 `background` / `cover`
- 组装 `verbs`
- 组装 `meta`
- 把本地磁盘路径转换成 API 可返回的 `/assets/...` 路径

建议函数：

```python
def build_generated_scene_record(...)
def build_scene_detail_from_core100(...)
def build_scene_summary_from_generated(...)
```

## 8. Jenny 音色生成策略

当前本机已有 Azure TTS 服务：

- `http://127.0.0.1:5003`

建议 worker 固定使用：

- `accent = en-US`
- `gender = female`
- `voice = JennyNeural`

原因：

- 当前你的产品目标明确，就是 Jenny 音色
- 第一版不要在 API 层开放太多可选音色
- 先保证稳定生成，再考虑可配置

注意一点：

`core100/generate_audio.py` 目前参数更偏向 `accent` 和 `gender`，所以要确认内部映射是否稳定落到 Jenny。若不能强制，建议在 `core100` 或 adapter 层显式指定 voice。

## 9. worker 设计

## 9.1 第一版建议

先不要急着上 Celery / Redis。

推荐第一版：

- API 创建任务后，把任务写入 `tasks.json`
- 用后台线程、独立 Python 进程，或 systemd 定时 worker 轮询 `queued` 任务

这样先跑通闭环。

## 9.2 第二版再切异步队列

后续若任务量上来，再切到：

- Redis
- Celery / RQ / Dramatiq

但 API 和文件落盘结构不要变。

## 9.3 worker 步骤建议

worker 执行顺序：

1. 读任务
2. 校验 `uploadId`
3. 更新任务到 `running`
4. 调 `core100` 分析图片
5. 调 5003 TTS 生成音频
6. 把输出文件移动到 `assets/generated/<sceneId>/`
7. 用 adapter 生成标准 scene detail
8. 写入 `generated_scenes.json`
9. 更新任务到 `done`

任一步失败：

- 记录 `errorMessage`
- 任务状态置为 `failed`

## 10. 存储文件格式建议

## 10.1 `generated_scenes.json`

建议结构：

```json
{
  "scenes": [
    {
      "sceneId": "scene_user_20260404_0001",
      "title": "我的厨房场景",
      "category": "generated",
      "visibility": "private",
      "sceneType": "private",
      "coverPath": "/assets/generated/scene_user_20260404_0001/cover.jpg",
      "backgroundPath": "/assets/generated/scene_user_20260404_0001/background.jpg",
      "items": [],
      "verbs": [],
      "meta": {
        "sourceType": "upload",
        "uploadId": "upload_20260404_0001",
        "ownerId": "mock_user_001",
        "version": 1
      }
    }
  ]
}
```

这样它和当前 `backend/data/scenes.json` 保持接近，后端好复用。

## 10.2 `tasks.json`

建议结构：

```json
{
  "tasks": [
    {
      "taskId": "task_20260404_0001",
      "uploadId": "upload_20260404_0001",
      "sceneId": "scene_user_20260404_0001",
      "status": "queued",
      "step": "queued",
      "progress": 0,
      "errorMessage": "",
      "createdAt": "2026-04-04T09:44:00Z",
      "updatedAt": "2026-04-04T09:44:00Z"
    }
  ]
}
```

## 11. 小程序前端最小改动点

为了接入这套生成流程，小程序前端只需要新增三类页面或能力：

- 上传页
- 任务页
- 我的场景页

但 runtime 页本身不需要推翻。

建议最小交互：

1. 用户上传图片
2. 点“开始生成”
3. 进入任务详情页轮询状态
4. 完成后跳到：

```txt
/pages/scene_runtime/index?sceneId=<newSceneId>
```

## 12. 推荐实施顺序

不要一口气把上传、任务、worker、数据库、会员一起上。

推荐严格按这个顺序推进：

### 阶段 A：先打通最小生成闭环

- 新增上传接口
- 新增创建任务接口
- 新增查询任务接口
- worker 能跑一张图
- 生成一条新场景
- runtime 页能打开新场景

### 阶段 B：补小程序页面

- 上传页
- 任务页
- 我的场景页

### 阶段 C：再做真实异步化

- worker 独立进程
- 队列化
- 重试策略

### 阶段 D：再切数据库

- `generated_scenes.json` -> DB
- `tasks.json` -> DB

## 13. 第一版明确不做的事

第一版先不要做：

- 前端直接读 `core100` JSON
- 生成 HTML 给小程序用
- 一开始就接数据库
- 一开始就做对象存储
- 一开始就做复杂任务编排
- 一开始就支持多音色切换

这些都会拖慢闭环。

## 14. 推荐下一步

如果按当前项目状态继续推进，下一步最值得先做的是：

1. 在 `backend/app/` 增加 `upload_store.py`、`task_store.py`、`generated_scene_store.py`
2. 补三个 API：
   - `POST /api/uploads/image`
   - `POST /api/my/tasks/scene-generate`
   - `GET /api/my/tasks/{taskId}`
3. 加一个最小 `worker_runner.py`
4. 写一个 `scene_adapter.py`，把 `core100` 输出转换成当前 runtime 协议

做到这一步后，你的“小程序上传图片 -> 后端生成新场景 -> 小程序访问新场景”就会形成真正的第一版闭环。

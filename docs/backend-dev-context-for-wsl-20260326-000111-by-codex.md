# 后端开发上下文文档（供 WSL 开发时唤醒使用）

时间：2026-03-26 00:01:11  
作者：Codex

## 1. 这份文档的用途

这份文档用于在后续切到 WSL 目录开发后端代码时，快速给 Codex 提供上下文。  
目标是让新的开发会话一上来就知道：

- 这个系统要做什么
- 当前已经确定了哪些架构决策
- 代码应该写在哪些仓库
- 后端 API 和 worker 应该如何组织
- 第一阶段应该先做什么

---

## 2. 产品目标

这是一个英语场景学习微信小程序，核心业务有两条：

1. 公开场景库  
平台预先生成很多英语学习场景，包含：
- 背景图
- 热点名词
- 动词
- 例句和翻译
- 音频  
会员用户可以浏览学习。

2. 私人场景生成  
用户拍照或上传图片后，系统异步生成只属于该用户自己的英语学习场景。  
生成流程由后端 API + Redis + Python worker 完成。

---

## 3. 已确定的关键架构决策

### 3.1 不再继续生成大量小程序源码页面

过去原型方案是为每个场景生成一套小程序源码页面，这会导致：

- 小程序包体很快超过 2MB
- `app.json` 和页面注册持续膨胀
- 编码、拼接、资源引用容易出错

正式 MVP 方案已经明确改为：

- 小程序前端只保留固定页面和一个通用 runtime 场景页
- 服务端返回统一 `scene JSON`
- 小程序根据 `sceneId` 拉取数据并渲染

### 3.2 服务器生成的是“数据和资源”，不是小程序源码

worker 负责生成：

- 背景图
- 缩略图
- 热点数据
- 动词数据
- 音频
- `scene.json`

而不是：

- `scene-data.js`
- `app.json`
- `scene.wxml`

### 3.3 资源短期落磁盘，后续再异步同步到 R2

当前阶段资源先写本地磁盘或 Gluster 目录：

- 上传原图
- 背景图
- 音频
- scene JSON

后续再由异步任务同步到 R2。

### 3.4 后端主开发环境放在 WSL Ubuntu

建议最终分工：

- 小程序前端：Windows 本机
- API：WSL Ubuntu
- Worker：WSL Ubuntu
- VPS：测试/部署环境，不作为主开发机

---

## 4. 仓库与目录布局

建议目录结构如下：

```text
E:\202603\
  weixin-demo\                 # 旧原型，保留，只参考
  english-scene-miniapp\       # 新小程序仓库
```

WSL 内目录：

```text
/home/hqking/projects/
  english-scene-api/           # 后端 API 仓库
  english-scene-worker/        # Python worker 仓库

/home/hqking/data/
  english-scenes/              # 运行时数据目录，不进 git
```

Windows 访问路径：

```text
\\wsl$\Ubuntu\home\hqking\projects\english-scene-api
\\wsl$\Ubuntu\home\hqking\projects\english-scene-worker
\\wsl$\Ubuntu\home\hqking\data\english-scenes
```

已创建的 WSL 目录：

- `\\wsl$\Ubuntu\home\hqking\projects\english-scene-miniapp`
- `\\wsl$\Ubuntu\home\hqking\projects\english-scene-api`
- `\\wsl$\Ubuntu\home\hqking\projects\english-scene-worker`
- `\\wsl$\Ubuntu\home\hqking\data\english-scenes`

说明：

- `weixin-demo` 保留，不再作为正式 MVP 主仓库
- 新后端代码应写到 WSL 目录里的 `english-scene-api` 和 `english-scene-worker`

---

## 5. 后端系统边界

## 5.1 API 服务职责

API 仓库：`english-scene-api`

负责：

- 微信登录
- token 签发与鉴权
- 用户信息查询
- 会员状态查询
- 公开场景列表
- 单个场景详情
- 我的私人场景列表
- 图片上传
- 创建任务
- 查询任务状态
- 权限校验
- 本地静态资源映射

不负责：

- 图像分析
- TTS 生成
- 压图处理主流程

## 5.2 Worker 服务职责

Worker 仓库：`english-scene-worker`

负责：

- 消费 Redis 队列
- 原图读取
- 压图、缩放、导出 jpg/webp
- 调视觉模型分析图片
- 生成热点词汇和动词文案
- 调 TTS 服务生成音频
- 组装统一 `scene JSON`
- 入库
- 更新任务状态
- 后续异步同步 R2

---

## 6. 统一 scene JSON 协议

后端最终必须产出并返回这一类结构：

```json
{
  "sceneId": "scene_20260325_abc123",
  "title": "营养早餐",
  "background": "https://static.example.com/private-scenes/u_1001/scene_20260325_abc123/background.jpg",
  "cover": "https://static.example.com/private-scenes/u_1001/scene_20260325_abc123/cover.jpg",
  "items": [
    {
      "id": "porridge",
      "word": "porridge",
      "ipa": "/ˈpɒrɪdʒ/",
      "meaning": "粥",
      "sentence": "I eat porridge for breakfast.",
      "sentenceTranslation": "我早餐吃粥。",
      "rect": { "l": 13.5, "t": 24.5, "w": 50.2, "h": 15.0 },
      "audio": "https://static.example.com/.../item_porridge.mp3"
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
      "audio": "https://static.example.com/.../verb_eat.mp3"
    }
  ],
  "meta": {
    "sceneType": "private",
    "ownerUserId": "u_1001",
    "visibility": "private",
    "version": 1,
    "category": "food",
    "tags": ["breakfast"]
  }
}
```

API 返回的场景详情应直接兼容这个结构。  
Worker 生成的 `scene.json` 也应符合这个结构。

---

## 7. API 契约范围

MVP 后端必须至少提供以下接口：

- `POST /api/auth/wx-login`
- `GET /api/me`
- `GET /api/scenes`
- `GET /api/scenes/{sceneId}`
- `GET /api/my/scenes`
- `POST /api/uploads/file`
- `POST /api/tasks`
- `GET /api/tasks/{jobId}`
- `GET /api/membership`

响应统一结构：

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

---

## 8. 数据库范围

MVP 建议使用 MySQL 8。

最小必需表：

- `users`
- `scenes`
- `scene_items`
- `scene_verbs`
- `scene_assets`
- `jobs`
- `memberships`

如果第一阶段只想尽快打通闭环，最先必须落地的是：

- `users`
- `scenes`
- `jobs`

---

## 9. Redis 与任务状态机

主队列建议：

- `queue:scene:generate`

任务状态：

- `queued`
- `running`
- `succeeded`
- `failed`
- `canceled`

任务阶段：

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

---

## 10. 本地磁盘目录规范

WSL 内建议使用：

```text
/home/hqking/data/english-scenes/
  uploads/
  public-scenes/
  private-scenes/
  jobs/
  temp/
  logs/
```

规则：

- 上传原图放 `uploads/`
- 公开场景放 `public-scenes/`
- 私人场景放 `private-scenes/`
- worker 中间文件放 `jobs/`
- 后续由 API 或 Nginx 暴露静态 URL

---

## 11. 当前已有文档

如果后续在 WSL 目录唤醒 Codex，建议一并提供这些文档路径：

- [`docs/english-scene-miniapp-c4-architecture-20260325-150516-by_codex.md`](E:\202603\weixin-demo\docs\english-scene-miniapp-c4-architecture-20260325-150516-by_codex.md)
- [`docs/english-scene-system-detailed-design-20260325-153922-by-codex.md`](E:\202603\weixin-demo\docs\english-scene-system-detailed-design-20260325-153922-by-codex.md)
- [`docs/english-scene-mvp-engineering-prep-20260325-175717-by-codex.md`](E:\202603\weixin-demo\docs\english-scene-mvp-engineering-prep-20260325-175717-by-codex.md)
- [`docs/english-scene-openapi-and-dto-20260325-180218-by-codex.md`](E:\202603\weixin-demo\docs\english-scene-openapi-and-dto-20260325-180218-by-codex.md)
- [`docs/english-scene-sql-init-and-migration-20260325-180441-by-codex.md`](E:\202603\weixin-demo\docs\english-scene-sql-init-and-migration-20260325-180441-by-codex.md)
- [`docs/english-scene-mvp-todolist-20260325-183056-by-codex.md`](E:\202603\weixin-demo\docs\english-scene-mvp-todolist-20260325-183056-by-codex.md)
- [`docs/english-scene-repo-and-directory-layout-20260325-183719-by-codex.md`](E:\202603\weixin-demo\docs\english-scene-repo-and-directory-layout-20260325-183719-by-codex.md)

---

## 12. 后续在 WSL 开发时的第一阶段任务

建议先做 API 仓库，再做 Worker。

### 第一阶段：搭 API skeleton

目标：

- 让 `english-scene-api` 有可启动的 FastAPI 工程骨架

第一批任务：

1. 初始化 FastAPI 项目结构
2. 加环境变量配置
3. 加日志
4. 加数据库连接
5. 加 Redis 连接
6. 加 health 接口
7. 加基础路由骨架：
   - auth
   - scenes
   - uploads
   - tasks

### 第二阶段：建模与 migration

1. 建 SQLAlchemy 模型
2. 配置 Alembic
3. 落第一批 migration
4. 建好 `users/scenes/jobs`

### 第三阶段：最小 API 可用

1. `GET /api/scenes/{sceneId}`
2. `POST /api/uploads/file`
3. `POST /api/tasks`
4. `GET /api/tasks/{jobId}`

### 第四阶段：搭 Worker skeleton

1. Redis consumer
2. 任务状态推进
3. 本地文件处理
4. scene JSON 输出

---

## 13. 当你在 WSL 目录重新唤醒 Codex 时，推荐这样描述任务

可以直接给出类似这样的上下文：

```text
请在 WSL 目录 \\wsl$\Ubuntu\home\hqking\projects\english-scene-api 下继续开发。
参考文档：
1. backend-dev-context-for-wsl-20260326-000111-by-codex.md
2. english-scene-openapi-and-dto-20260325-180218-by-codex.md
3. english-scene-sql-init-and-migration-20260325-180441-by-codex.md

当前目标：
先搭 FastAPI skeleton，建立 app/main.py、settings、routers、infra/db、infra/redis、health 接口。
```

这样新会话基本就能无缝继续。

---

## 14. 结论

这套系统的后端开发，已经明确：

- 正式开发目录在 WSL
- API 与 Worker 分仓
- 小程序与后端解耦
- 资源先落本地磁盘，再异步同步到 R2
- 后端第一阶段优先做 API skeleton，再做数据库和 Worker

后续只要把这份文档和上游设计文档一起给 Codex，基本就足够恢复开发上下文。

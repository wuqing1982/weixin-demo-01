# 后端开发会话启动提示模板

时间：2026-03-26 00:12:42  
作者：Codex

## 1. 用途

这份文档用于你下次在 WSL 目录中唤醒 Codex 开发后端时，直接复制提示词，快速恢复上下文。

---

## 2. 推荐使用方式

在新的 Codex 会话里，把下面模板按实际路径稍作替换后直接发送。

---

## 3. 通用提示模板

```text
请在 WSL 目录下继续开发英语场景学习系统的后端代码。

当前工作目录：
\\wsl$\Ubuntu\home\hqking\projects\english-scene-api

请先阅读这些文档作为上下文：
1. E:\202603\weixin-demo\docs\backend-dev-context-for-wsl-20260326-000111-by-codex.md
2. E:\202603\weixin-demo\docs\english-scene-openapi-and-dto-20260325-180218-by-codex.md
3. E:\202603\weixin-demo\docs\english-scene-sql-init-and-migration-20260325-180441-by-codex.md
4. E:\202603\weixin-demo\docs\english-scene-mvp-todolist-20260325-183056-by-codex.md

背景约束：
- 这是一个英语场景学习微信小程序
- 小程序前端和后端解耦
- 后端负责 API、任务、数据库、权限
- worker 负责 AI 分析、压图、TTS、scene JSON 生成
- 资源当前先落本地磁盘，后续异步同步到 R2
- 不再继续生成小程序源码页面
- 场景统一使用 scene JSON + runtime 页面渲染

当前目标：
先搭 FastAPI skeleton，并建立最小可运行后端骨架。

本轮任务：
1. 建立 app/main.py
2. 建立 settings
3. 建立 routers
4. 建立 infra/db.py
5. 建立 infra/redis.py
6. 建立 health 接口
7. 建立基础 README 和 .gitignore

要求：
- 先检查目录现状
- 直接动手写代码
- 完成后说明创建了哪些文件
- 如果涉及后续步骤，顺手更新 todolist 中对应项
```

---

## 4. 如果要启动 Worker 开发，使用这个模板

```text
请在 WSL 目录下继续开发英语场景学习系统的 worker 代码。

当前工作目录：
\\wsl$\Ubuntu\home\hqking\projects\english-scene-worker

请先阅读这些文档作为上下文：
1. E:\202603\weixin-demo\docs\backend-dev-context-for-wsl-20260326-000111-by-codex.md
2. E:\202603\weixin-demo\docs\english-scene-system-detailed-design-20260325-153922-by-codex.md
3. E:\202603\weixin-demo\docs\english-scene-openapi-and-dto-20260325-180218-by-codex.md
4. E:\202603\weixin-demo\docs\english-scene-mvp-todolist-20260325-183056-by-codex.md

背景约束：
- Worker 是 Python 项目
- 通过 Redis 消费 job
- 输入是上传图片和 job payload
- 输出是背景图、音频、scene JSON 和数据库回写
- 资源先写本地磁盘

当前目标：
先搭 worker skeleton。

本轮任务：
1. 建立 worker/main.py
2. 建立 settings
3. 建立 Redis consumer
4. 建立 jobs/generate_scene.py
5. 建立 services/image_processor.py
6. 建立 services/scene_builder.py
7. 建立日志和基础 README

要求：
- 先检查目录现状
- 直接动手写代码
- 完成后说明创建了哪些文件
- 如果涉及后续步骤，顺手更新 todolist 中对应项
```

---

## 5. 如果要让 Codex 继续推进数据库建模，使用这个模板

```text
请继续开发英语场景学习系统后端，当前重点是数据库模型和 migration。

当前工作目录：
\\wsl$\Ubuntu\home\hqking\projects\english-scene-api

先阅读：
1. E:\202603\weixin-demo\docs\backend-dev-context-for-wsl-20260326-000111-by-codex.md
2. E:\202603\weixin-demo\docs\english-scene-sql-init-and-migration-20260325-180441-by-codex.md
3. E:\202603\weixin-demo\docs\english-scene-mvp-todolist-20260325-183056-by-codex.md

当前目标：
建立 SQLAlchemy 模型和 Alembic 基础结构。

本轮任务：
1. 建 users/scenes/jobs 模型
2. 配置 Alembic
3. 生成第一版 migration 骨架
4. 提供初始化方式

要求：
- 直接改代码
- 完成后列出文件变化
- 更新 todolist 对应项
```

---

## 6. 如果要让 Codex 继续推进 API 联调，使用这个模板

```text
请继续开发英语场景学习系统后端 API，当前重点是最小联调闭环。

当前工作目录：
\\wsl$\Ubuntu\home\hqking\projects\english-scene-api

先阅读：
1. E:\202603\weixin-demo\docs\backend-dev-context-for-wsl-20260326-000111-by-codex.md
2. E:\202603\weixin-demo\docs\english-scene-openapi-and-dto-20260325-180218-by-codex.md
3. E:\202603\weixin-demo\docs\english-scene-mvp-todolist-20260325-183056-by-codex.md

当前目标：
打通场景查询、上传、任务创建、任务查询四个接口。

本轮任务：
1. 实现 GET /api/scenes/{sceneId}
2. 实现 POST /api/uploads/file
3. 实现 POST /api/tasks
4. 实现 GET /api/tasks/{jobId}

要求：
- 能跑就跑
- 不能跑要明确阻塞点
- 更新 todolist 对应项
```

---

## 7. 建议

每次新的后端会话，至少给 Codex 提供：

1. 当前工作目录
2. 参考文档路径
3. 本轮明确目标
4. 本轮具体任务列表

这样恢复上下文最快，也最不容易偏题。

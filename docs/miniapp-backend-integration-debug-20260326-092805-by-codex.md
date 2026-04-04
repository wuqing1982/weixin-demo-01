# 新小程序前端与后端联调调试文档

时间：2026-03-26 09:28:05  
作者：Codex

## 1. 目标

本文档用于说明新的小程序前端项目如何与后端 API 联调，以及在后端尚未完成时如何使用 mock 数据继续开发和调样式。

新小程序项目目录：

[`E:\202603\english-scene-miniapp`](E:\202603\english-scene-miniapp)

---

## 2. 当前前端已完成的内容

已创建的新前端骨架包括：

- 首页
- 公开场景库
- 通用 runtime 场景页
- 图片上传页
- 任务中心
- 我的场景
- 个人资料
- 登录页
- 公共场景 runtime 模板
- 服务层 API 封装
- mock 场景数据兜底

核心目录：

- [`E:\202603\english-scene-miniapp\pages`](E:\202603\english-scene-miniapp\pages)
- [`E:\202603\english-scene-miniapp\services`](E:\202603\english-scene-miniapp\services)
- [`E:\202603\english-scene-miniapp\utils`](E:\202603\english-scene-miniapp\utils)

---

## 3. 当前前端的后端地址配置

前端默认 API 地址写在：

[`E:\202603\english-scene-miniapp\app.js`](E:\202603\english-scene-miniapp\app.js)

当前默认值：

```js
apiBaseUrl: 'http://127.0.0.1:8000/api'
staticBaseUrl: 'http://127.0.0.1:8000'
```

同时服务层通过：

[`E:\202603\english-scene-miniapp\services\config.js`](E:\202603\english-scene-miniapp\services\config.js)

读取这两个配置。

如果后端实际跑在别的地址，只要改这两个值即可。

---

## 4. 当前前端使用到的 API

## 4.1 登录

服务文件：

[`E:\202603\english-scene-miniapp\services\auth.js`](E:\202603\english-scene-miniapp\services\auth.js)

接口：

- `POST /api/auth/wx-login`
- `GET /api/me`

## 4.2 场景

服务文件：

[`E:\202603\english-scene-miniapp\services\scene.js`](E:\202603\english-scene-miniapp\services\scene.js)

接口：

- `GET /api/scenes`
- `GET /api/scenes/{sceneId}`
- `GET /api/my/scenes`

## 4.3 上传

服务文件：

[`E:\202603\english-scene-miniapp\services\upload.js`](E:\202603\english-scene-miniapp\services\upload.js)

接口：

- `POST /api/uploads/file`

## 4.4 任务

服务文件：

[`E:\202603\english-scene-miniapp\services\task.js`](E:\202603\english-scene-miniapp\services\task.js)

接口：

- `POST /api/tasks`
- `GET /api/tasks/{jobId}`

---

## 5. 当前前端的 mock 机制

为了保证后端还没接上时前端也能继续开发，当前前端已经内置了一层 mock 兜底。

mock 文件：

[`E:\202603\english-scene-miniapp\services\mock.js`](E:\202603\english-scene-miniapp\services\mock.js)

当前行为：

- `services/scene.js` 调 `GET /api/scenes` 失败时，返回 mock 场景列表
- `services/scene.js` 调 `GET /api/scenes/{sceneId}` 失败时，返回 mock 场景详情
- `services/scene.js` 调 `GET /api/my/scenes` 失败时，返回空列表而不是崩掉

这意味着：

- 首页、场景库、runtime 场景页现在就能先跑起来
- 后端还没准备好时，至少 UI 和交互可以继续调

注意：

- 上传、任务、登录目前没有完整 mock 后备
- 这几项仍然依赖后端接口存在

---

## 6. 小程序运行时调试顺序

建议按这个顺序联调。

### 第一步：先仅打开前端项目

在微信开发者工具中打开：

[`E:\202603\english-scene-miniapp`](E:\202603\english-scene-miniapp)

先验证：

- 首页能打开
- 场景库能显示 mock 列表
- 点击场景能进入 runtime 场景页

如果这里不通，先修前端，不要急着接后端。

### 第二步：启动后端只读接口

后端最先只需要提供：

- `GET /api/scenes`
- `GET /api/scenes/{sceneId}`

这样先把：

- 场景库
- runtime 场景详情

两条链路接起来。

### 第三步：启动登录接口

补：

- `POST /api/auth/wx-login`
- `GET /api/me`

这样资料页和登录页能跑通。

### 第四步：启动上传和任务接口

补：

- `POST /api/uploads/file`
- `POST /api/tasks`
- `GET /api/tasks/{jobId}`

这样上传页和任务中心能接起来。

---

## 7. 推荐的联调后端返回结构

## 7.1 场景列表

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "list": [
      {
        "sceneId": "scene_breakfast",
        "title": "营养早餐",
        "coverUrl": "http://127.0.0.1:8000/static/public-scenes/breakfast/cover.jpg",
        "category": "food",
        "visibility": "member",
        "sceneType": "public"
      }
    ],
    "total": 1,
    "page": 1,
    "pageSize": 20
  }
}
```

## 7.2 场景详情

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "sceneId": "scene_breakfast",
    "title": "营养早餐",
    "background": "http://127.0.0.1:8000/static/public-scenes/breakfast/background.jpg",
    "cover": "http://127.0.0.1:8000/static/public-scenes/breakfast/cover.jpg",
    "items": [],
    "verbs": [],
    "meta": {
      "sceneType": "public",
      "ownerUserId": null,
      "visibility": "member",
      "version": 1,
      "category": "food",
      "tags": ["breakfast"]
    }
  }
}
```

## 7.3 上传返回

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "storageKey": "uploads/2026/03/26/user_1001/original_xxx.jpg",
    "localPath": "/home/hqking/data/english-scenes/uploads/2026/03/26/user_1001/original_xxx.jpg",
    "publicUrl": "http://127.0.0.1:8000/static/uploads/2026/03/26/user_1001/original_xxx.jpg",
    "contentType": "image/jpeg",
    "size": 123456
  }
}
```

## 7.4 创建任务返回

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "jobId": "job_20260326_xxx",
    "status": "queued"
  }
}
```

## 7.5 任务详情返回

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "jobId": "job_20260326_xxx",
    "status": "running",
    "progress": 60,
    "currentStage": "generate_tts",
    "result": {
      "sceneId": null
    },
    "errorMessage": null,
    "createdAt": "2026-03-26 09:00:00",
    "startedAt": "2026-03-26 09:00:05",
    "finishedAt": null
  }
}
```

---

## 8. 本地调试建议

## 8.1 后端本地地址

当前前端默认假设后端本地地址：

```text
http://127.0.0.1:8000
```

如果你后端在 WSL 中运行，一般可以直接从 Windows 访问这个端口，只要服务监听在：

```text
0.0.0.0:8000
```

或者：

```text
127.0.0.1:8000
```

视 WSL 网络转发情况而定。

## 8.2 静态资源路径

前端中的图片和音频字段都应返回完整可访问 URL。

不要让前端拼 Linux 路径，例如：

- 不要返回 `/home/hqking/...` 给前端直接显示
- 要返回 `http://127.0.0.1:8000/static/...`

## 8.3 登录问题

在后端未实现微信真实登录前，可以先临时提供一个固定用户 token 返回，便于小程序联调。

也就是说：

- MVP 开发阶段可以先“伪登录”
- 真实微信 code 换 openid 后面再补

---

## 9. 当前前端最值得优先接入的后端能力

建议优先顺序：

1. `GET /api/scenes`
2. `GET /api/scenes/{sceneId}`
3. `GET /api/me`
4. `POST /api/uploads/file`
5. `POST /api/tasks`
6. `GET /api/tasks/{jobId}`

原因：

- 场景库和 runtime 页最容易先形成可见成果
- 上传和任务流是第二阶段闭环

---

## 10. 当前小程序关键文件说明

## 10.1 场景 runtime 页

[`E:\202603\english-scene-miniapp\pages\scene_runtime\index.js`](E:\202603\english-scene-miniapp\pages\scene_runtime\index.js)

职责：

- 根据 `sceneId` 加载场景数据
- 调用共享模板渲染

## 10.2 共享模板

[`E:\202603\english-scene-miniapp\pages\shared\scene-template.wxml`](E:\202603\english-scene-miniapp\pages\shared\scene-template.wxml)
[`E:\202603\english-scene-miniapp\pages\shared\scene-page.js`](E:\202603\english-scene-miniapp\pages\shared\scene-page.js)
[`E:\202603\english-scene-miniapp\pages\shared\scene.wxss`](E:\202603\english-scene-miniapp\pages\shared\scene.wxss)

## 10.3 上传页

[`E:\202603\english-scene-miniapp\pages\create_scene\index.js`](E:\202603\english-scene-miniapp\pages\create_scene\index.js)

职责：

- 选择图片
- 上传图片
- 创建任务

## 10.4 任务中心

[`E:\202603\english-scene-miniapp\pages\task_center\index.js`](E:\202603\english-scene-miniapp\pages\task_center\index.js)

职责：

- 查询任务状态
- 轮询结果
- 任务成功后进入场景页

---

## 11. 下一步推荐动作

如果现在继续推进，建议下一步是：

1. 在 WSL 里启动 `english-scene-api`
2. 先实现：
   - `GET /api/scenes`
   - `GET /api/scenes/{sceneId}`
3. 用微信开发者工具打开新小程序目录
4. 先验证场景库和 runtime 页联调成功

等这一步跑通，再做上传和任务中心。

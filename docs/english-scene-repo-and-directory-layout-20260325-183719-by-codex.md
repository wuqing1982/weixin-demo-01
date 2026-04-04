# 英语场景学习系统仓库与目录布局准备文档

时间：2026-03-25 18:37:19  
作者：Codex

## 1. 文档目标

本文档用于明确这个英语场景学习系统在本地开发和后续工程化阶段的目录组织、仓库边界、代码放置位置和开工顺序。

目标是解决这几个问题：

- 新代码写在哪里
- 原来的 [`weixin-demo`](E:\202603\weixin-demo) 是否继续承载正式开发
- 需要几个 git 仓库
- 运行期数据放在哪里
- 不同仓库的职责边界如何划分

---

## 2. 结论

建议最终采用：

- `3` 个 git 仓库
- `1` 个运行时数据目录
- `1` 个旧原型目录保留不动

推荐目录结构：

```text
E:\202603\
  weixin-demo\                 # 旧原型，保留不动
  english-scene-miniapp\       # 新小程序仓库
  english-scene-api\           # 后端 API 仓库
  english-scene-worker\        # Python worker 仓库
  english-scenes-data\         # 运行时数据目录，不进 git
```

---

## 3. 为什么不直接继续在 weixin-demo 上开发

[`weixin-demo`](E:\202603\weixin-demo) 当前更适合作为：

- 视觉原型参考
- 场景模板参考
- 热点和音频交互参考
- 旧数据和旧页面参考

但它不适合作为正式 MVP 主仓库，原因很具体：

1. 当前目录已经有很多历史修补痕迹  
包括：
- 静态场景页面
- 体积压缩修补
- 编码修复
- registry 反复修复

2. 当前结构是静态生成导向  
而正式产品要转向：
- 单一 runtime 页面
- 服务端 API 驱动
- Worker 生成数据和资源

3. 小程序、API、worker 的依赖完全不同  
继续混在一个仓库里会让：
- 开发环境混乱
- 发布节奏耦合
- 回滚困难

所以：

- [`weixin-demo`](E:\202603\weixin-demo) 保留
- 不覆盖
- 不作为新系统正式开发主目录

---

## 4. 建议的 3 个 git 仓库

## 4.1 `english-scene-miniapp`

位置建议：

```text
E:\202603\english-scene-miniapp
```

职责：

- 微信小程序前端
- 页面路由
- 登录态管理
- 上传图片
- 创建任务
- 查询任务状态
- 展示公开场景和私人场景
- 用统一 runtime 页面渲染场景

不负责：

- 生成场景内容
- 写数据库
- 执行 AI 任务

### 推荐目录

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
  utils/
    image.js
    cache.js
```

## 4.2 `english-scene-api`

位置建议：

```text
E:\202603\english-scene-api
```

职责：

- 用户登录
- 用户信息
- 会员权限
- 场景列表和详情查询
- 上传接口
- 任务创建接口
- 任务状态查询接口
- 本地磁盘静态资源映射
- 数据库访问

不负责：

- 耗时 AI 处理
- TTS 批量生成
- 图像分析主流程

### 推荐目录

```text
english-scene-api/
  app/
    main.py
    settings.py
    routers/
    services/
    repositories/
    models/
    schemas/
    infra/
  migrations/
  tests/
```

## 4.3 `english-scene-worker`

位置建议：

```text
E:\202603\english-scene-worker
```

职责：

- 消费 Redis 队列
- 图像缩放和压缩
- 调多模态模型生成热点数据
- 调 TTS 生成音频
- 生成 scene JSON
- 写回数据库
- 生成本地资源文件
- 后续同步到 R2

不负责：

- 前端页面逻辑
- HTTP API
- 用户登录

### 推荐目录

```text
english-scene-worker/
  worker/
    main.py
    settings.py
    consumers/
    jobs/
    services/
    infra/
  tests/
```

---

## 5. 运行时数据目录

位置建议：

```text
E:\202603\english-scenes-data
```

这个目录不进 git。

用途：

- 存上传原图
- 存公开场景资源
- 存私人场景资源
- 存任务中间文件
- 存日志

推荐结构：

```text
english-scenes-data/
  uploads/
  public-scenes/
  private-scenes/
  jobs/
  temp/
  logs/
```

后续如果迁到服务器环境，逻辑上可映射到：

```text
/data/english-scenes/
```

---

## 6. 旧原型目录的角色

[`weixin-demo`](E:\202603\weixin-demo) 建议继续保留。

它的角色不是主开发仓库，而是：

- UI 和交互参考库
- 旧模板参考库
- 已经生成的静态场景参考库
- 数据格式迁移参考库

可以从这里迁移：

- 场景页样式
- 共享模板结构
- 热点交互逻辑
- 音频播放体验

不建议继续在里面做：

- 新 API 驱动架构
- 正式 MVP 工程代码

---

## 7. 为什么建议 3 个 git 仓库

主要原因：

### 7.1 依赖隔离

小程序、API、worker 的依赖完全不同：

- 小程序：微信开发者工具、前端 JS
- API：FastAPI、SQLAlchemy、Alembic
- Worker：Pillow、Redis、AI/TTS 依赖

### 7.2 发布节奏不同

- 小程序要走开发者工具和提审发布
- API 需要独立部署
- Worker 可能单独重启和扩容

### 7.3 回滚边界清晰

一个仓库出问题，不会拖垮整个系统代码树。

### 7.4 便于后续团队协作

即使未来不是一个人维护，分仓也更合理。

---

## 8. 为什么不建议把运行数据放进 git

[`english-scenes-data`](E:\202603\english-scenes-data) 不应该进 git，原因：

- 图片和音频会快速膨胀仓库体积
- 任务中间文件是临时文件，不是源码
- 私人场景资源涉及用户隐私
- 后续要迁移到 R2，本地数据只应作为运行态资源

所以：

- git 管源码
- 磁盘目录管运行数据

---

## 9. 建议的初始化顺序

推荐按这个顺序准备工程目录。

### 第一步

创建以下目录：

```text
E:\202603\english-scene-miniapp
E:\202603\english-scene-api
E:\202603\english-scene-worker
E:\202603\english-scenes-data
```

### 第二步

初始化 3 个 git 仓库：

- `english-scene-miniapp`
- `english-scene-api`
- `english-scene-worker`

### 第三步

在 3 个仓库分别补：

- `README.md`
- `.gitignore`
- 最小目录骨架

### 第四步

先启动两个核心骨架开发：

1. `english-scene-api`
2. `english-scene-miniapp`

worker 可以稍后接入，但目录要先建好。

---

## 10. 实际开工建议

如果现在开始做，我建议写代码的位置如下：

### 小程序代码

写在：

```text
E:\202603\english-scene-miniapp
```

### API 代码

写在：

```text
E:\202603\english-scene-api
```

### Worker 代码

写在：

```text
E:\202603\english-scene-worker
```

### 资源文件

落在：

```text
E:\202603\english-scenes-data
```

### 旧代码参考

从：

[`E:\202603\weixin-demo`](E:\202603\weixin-demo)

读取和迁移

---

## 11. 第一阶段建议优先做的目录准备项

- 新建 `english-scene-miniapp`
- 新建 `english-scene-api`
- 新建 `english-scene-worker`
- 新建 `english-scenes-data`
- 为 3 个仓库分别初始化 `.gitignore`
- 为 3 个仓库分别初始化 README
- 为 API 仓库初始化基础 FastAPI 结构
- 为 worker 仓库初始化 Redis consumer 结构
- 为 miniapp 仓库初始化小程序页面骨架

---

## 12. 结论

这个系统未来的代码和目录组织，推荐明确分成：

- 旧原型参考目录：[`weixin-demo`](E:\202603\weixin-demo)
- 新小程序仓库：`english-scene-miniapp`
- 新 API 仓库：`english-scene-api`
- 新 worker 仓库：`english-scene-worker`
- 新运行数据目录：`english-scenes-data`

这是当前最稳、最清晰、最容易持续开发的布局方式。

如果继续往前推进，下一步可以直接做：

1. 新建这 4 个目录
2. 初始化 3 个 git 仓库骨架
3. 从 `english-scene-api` 开始搭第一层工程 skeleton

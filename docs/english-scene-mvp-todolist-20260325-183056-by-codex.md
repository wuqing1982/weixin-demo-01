# 英语场景学习小程序 MVP Todo List

时间：2026-03-25 18:30:56  
作者：Codex

说明：

- 这是一份可持续更新的工程任务清单
- 完成一项后，直接把 `[ ]` 改成 `[x]`
- 默认按 MVP 落地优先级排序
- 先打通闭环，再补优化项

---

## 1. 设计与协议冻结

- [x] 完成 C4 架构设计文档
- [x] 完成系统详细设计文档
- [x] 完成 MVP 工程准备文档
- [x] 完成 OpenAPI 与 DTO 定义文档
- [x] 完成 SQL 初始化与 migration 草案文档
- [ ] 冻结统一 `SceneDetailDto` 协议
- [ ] 冻结任务状态机和阶段枚举
- [ ] 冻结前后端错误码表

---

## 2. 小程序前端重构

### 2.1 页面骨架

- [x] 新建 `pages/home`
- [x] 新建 `pages/library`
- [x] 新建 `pages/scene_runtime`
- [x] 新建 `pages/create_scene`
- [x] 新建 `pages/task_center`
- [x] 新建 `pages/my_scenes`
- [x] 新建 `pages/profile`

### 2.2 统一场景 runtime

- [x] 将当前共享模板迁移到 `scene_runtime`
- [x] 去掉运行时对静态 `scene-data.js` 的依赖
- [x] 支持通过 `sceneId` 拉取场景详情接口
- [x] 场景页接入背景图远程 URL
- [x] 场景页接入热点名词渲染
- [x] 场景页接入动词渲染
- [x] 场景页接入音频播放
- [x] 场景页接入播放速度设置持久化

### 2.3 上传与任务

- [ ] 实现拍照入口
- [x] 实现相册选图入口
- [ ] 实现前端压图
- [x] 实现上传接口调用
- [x] 实现创建任务接口调用
- [x] 实现任务轮询
- [x] 任务成功后跳转场景详情页
- [x] 任务失败后展示失败原因

### 2.4 用户与会员

- [x] 接入微信登录
- [x] 存储 token
- [x] 拉取当前用户信息
- [ ] 拉取会员状态
- [ ] 对会员场景做前端访问提示

---

## 3. API 服务骨架

### 3.1 基础工程

- [ ] 创建 API 仓库骨架
- [ ] 初始化 FastAPI 项目
- [ ] 配置环境变量加载
- [ ] 配置日志系统
- [ ] 配置数据库连接
- [ ] 配置 Redis 连接
- [ ] 配置本地存储根目录

### 3.2 认证模块

- [ ] 实现 `POST /api/auth/wx-login`
- [ ] 实现 token 生成与校验
- [ ] 实现 `GET /api/me`

### 3.3 场景模块

- [ ] 实现 `GET /api/scenes`
- [ ] 实现 `GET /api/scenes/{sceneId}`
- [ ] 实现 `GET /api/my/scenes`
- [ ] 实现场景权限校验

### 3.4 上传模块

- [ ] 实现 `POST /api/uploads/file`
- [ ] 校验图片 MIME 类型
- [ ] 校验图片大小限制
- [ ] 上传文件落本地磁盘
- [ ] 返回 `UploadResultDto`

### 3.5 任务模块

- [ ] 实现 `POST /api/tasks`
- [ ] 实现 `GET /api/tasks/{jobId}`
- [ ] 创建任务记录写入数据库
- [ ] 投递 Redis 队列

---

## 4. 数据库与 Migration

### 4.1 建库建表

- [ ] 创建数据库 `english_scene`
- [ ] 创建 `users` 表
- [ ] 创建 `scenes` 表
- [ ] 创建 `scene_items` 表
- [ ] 创建 `scene_verbs` 表
- [ ] 创建 `scene_assets` 表
- [ ] 创建 `jobs` 表
- [ ] 创建 `memberships` 表

### 4.2 ORM 与迁移

- [ ] 建立 SQLAlchemy 模型
- [ ] 配置 Alembic
- [ ] 生成第一批 migration
- [ ] 验证 migration up
- [ ] 验证 migration rollback

### 4.3 初始化数据

- [ ] 插入测试用户
- [ ] 插入 1 个公开场景测试数据
- [ ] 插入 1 条会员测试数据

---

## 5. Worker 骨架

### 5.1 基础工程

- [ ] 创建 worker 仓库骨架
- [ ] 配置 Redis consumer
- [ ] 配置数据库连接
- [ ] 配置日志系统
- [ ] 配置本地存储服务

### 5.2 任务执行链

- [ ] 实现 `prepare_input`
- [ ] 实现 `resize_image`
- [ ] 实现 `analyze_image`
- [ ] 实现 `generate_copywriting`
- [ ] 实现 `generate_tts`
- [ ] 实现 `build_scene_json`
- [ ] 实现 `persist_scene`
- [ ] 实现 `schedule_sync_to_r2`

### 5.3 任务状态推进

- [ ] 实现任务状态更新
- [ ] 实现阶段进度更新
- [ ] 实现失败信息回写
- [ ] 实现重试机制

---

## 6. 本地磁盘存储

- [ ] 创建本地存储根目录规范
- [ ] 创建 `uploads/` 目录规范
- [ ] 创建 `public-scenes/` 目录规范
- [ ] 创建 `private-scenes/` 目录规范
- [ ] 创建 `jobs/` 临时目录规范
- [ ] 创建静态资源 URL 映射方案
- [ ] 验证 API 可访问本地静态资源

---

## 7. 场景数据生产

### 7.1 公开场景

- [ ] 导入现有公开场景资源
- [ ] 将现有公开场景转换为统一 scene JSON
- [ ] 将现有公开场景写入数据库
- [ ] 验证小程序可浏览公开场景

### 7.2 私人场景

- [ ] 上传图片生成任务
- [ ] worker 成功生成私人场景
- [ ] 小程序成功查看私人场景
- [ ] 验证仅 owner 可访问私人场景

---

## 8. 权限与会员

- [ ] 实现 `visibility=public` 访问控制
- [ ] 实现 `visibility=member` 访问控制
- [ ] 实现 `visibility=private` 访问控制
- [ ] 实现会员状态校验逻辑
- [ ] 非会员访问会员场景时返回正确错误码
- [ ] 非 owner 访问私人场景时返回正确错误码

---

## 9. 联调与验证

### 9.1 前后端联调

- [ ] 用 mock 数据跑通 runtime 场景页
- [ ] 接真实 `GET /api/scenes/{sceneId}`
- [ ] 接真实上传接口
- [ ] 接真实创建任务接口
- [ ] 接真实任务查询接口

### 9.2 worker 联调

- [ ] 手工插入 1 条 job 测试
- [ ] 验证 worker 消费成功
- [ ] 验证 scene JSON 文件生成成功
- [ ] 验证数据库回写成功
- [ ] 验证小程序可查看结果

### 9.3 权限验证

- [ ] 验证公开场景访问
- [ ] 验证会员场景访问
- [ ] 验证私人场景访问隔离

---

## 10. 监控与日志

- [ ] API 记录访问日志
- [ ] Worker 记录任务阶段日志
- [ ] 任务失败时保留错误详情
- [ ] 增加 jobId 贯穿日志链路
- [ ] 建立最小排障手册

---

## 11. R2 同步预留

- [ ] 抽象 `StorageService`
- [ ] 将 `local_path` 与 `public_url` 分离
- [ ] 设计 `sync_to_r2` job payload
- [ ] 预留 `scene_assets.cdn_status`
- [ ] 设计异步同步后的 URL 回写逻辑

---

## 12. 发布前检查

- [ ] 小程序主流程可用
- [ ] 公开场景可用
- [ ] 私人场景可用
- [ ] 包体控制在可接受范围
- [ ] API 基础错误处理完成
- [ ] worker 失败可重试
- [ ] 数据库 migration 可重复执行
- [ ] 本地磁盘路径配置可切环境

---

## 13. 第一阶段建议优先做的 10 项

- [ ] 搭建 API 仓库骨架
- [ ] 建库并落 `users/scenes/jobs`
- [ ] 搭建 worker 仓库骨架
- [ ] 新建小程序 `scene_runtime`
- [ ] 用 mock 数据跑通 `scene_runtime`
- [ ] 实现 `GET /api/scenes/{sceneId}`
- [ ] 实现 `POST /api/uploads/file`
- [ ] 实现 `POST /api/tasks`
- [ ] 实现 `GET /api/tasks/{jobId}`
- [ ] 实现 worker 最小闭环

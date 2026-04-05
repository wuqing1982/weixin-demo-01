# 当前项目升级为 SaaS 与虚拟数字商品平台的 PRD、数据库设计、架构设计与部署建议

更新时间：2026-04-04 18:31 UTC

本文聚焦当前项目：

- 微信小程序前端
- FastAPI 后端 API
- Worker 异步任务
- 场景生成能力

目标是把它升级为一个可收费、可运营、可持续扩展的产品平台，具备：

- 用户注册/登录
- 会员与商品体系
- 虚拟数字商品销售
- Admin 后台管理
- PostgreSQL 数据库
- 可扩展的 worker 架构
- 稳定的线上部署方式

这份文档同时包含四部分：

1. 产品 PRD
2. 数据库设计
3. 架构设计
4. 部署建议

---

## 1. 项目升级目标

当前项目已经具备：

- 小程序前端
- 场景浏览
- 图片上传
- 异步任务
- AI 生成场景
- 音频生成
- 公开场景与私人场景

但它目前仍属于“功能验证阶段”：

- 用户还是 `debugUserId`
- 没有正式账号体系
- 没有商品和会员体系
- 没有订单、支付、权益
- 没有运营后台
- 数据还是 JSON 文件

所以升级目标很明确：

**把它从一个能跑通的 AI 场景应用，升级成一个可销售的 SaaS + 虚拟数字商品平台。**

---

## 2. 产品 PRD

## 2.1 产品名称

工作名称：

**英语场景 SaaS 平台**

它不是只卖一个单点功能，而是提供三种能力：

1. 会员内容服务
2. AI 生成服务
3. 虚拟数字商品销售

---

## 2.2 产品定位

### 面向谁

第一阶段主要面向：

- 家长
- 个人学习者

后续可扩展到：

- 教师
- 培训机构
- 企业英语培训

### 核心价值

为用户提供：

- 公开场景英语学习内容
- 可持续使用的会员服务
- 自定义图片生成英语场景
- 可购买的数字内容合集
- 后续可扩展视频导出、专题内容包、记忆页产品

---

## 2.3 产品范围

第一阶段平台建议包含 4 个产品域：

### A. 账号域

- 用户注册
- 微信登录
- 手机号绑定
- 登录态管理
- 账号资料

### B. 商业域

- 商品
- SKU
- 定价
- 订单
- 支付
- 会员
- Credits
- 虚拟数字商品

### C. 业务域

- 公开场景
- 私人场景
- 图片上传
- 场景生成任务
- 历史内容

### D. 运营域

- Admin 后台
- 商品管理
- 价格管理
- 内容管理
- 用户管理
- 订单管理
- 任务监控

---

## 2.4 用户角色

建议分成以下角色：

### 1. 游客

能力：

- 浏览部分公开内容
- 查看商品页
- 引导注册/登录

### 2. 注册用户

能力：

- 登录
- 购买商品
- 查看订单
- 查看自己的场景
- 使用已开通权益

### 3. 会员用户

能力：

- 解锁公开场景库
- 使用一定 DIY credits
- 访问会员内容

### 4. Admin 管理员

能力：

- 用户管理
- 商品管理
- 价格管理
- 内容管理
- 任务监控
- 订单管理

### 5. Super Admin

能力：

- 平台级配置
- 权限配置
- 支付配置
- 系统参数配置

---

## 2.5 核心业务流程

### 流程 1：用户注册/登录

1. 用户进入小程序
2. 微信授权登录
3. 平台创建用户
4. 返回平台 access token
5. 小程序后续请求带 token

### 流程 2：用户购买会员

1. 用户进入商品页
2. 选择会员商品/SKU
3. 创建订单
4. 发起支付
5. 支付成功
6. 平台发放会员权益
7. 用户可访问对应内容

### 流程 3：用户购买 credits

1. 用户选择 credits 商品
2. 下单支付
3. 支付成功
4. 发放 credits 配额
5. 用户生成场景时扣减

### 流程 4：用户购买数字合集

1. 用户浏览专题合集
2. 一次性购买
3. 平台发放数字商品访问权
4. 用户在有效期内长期访问

### 流程 5：用户生成私人场景

1. 用户上传图片
2. 后端校验权益/credits
3. 创建任务
4. worker 执行生成
5. 保存背景图、音频、场景 JSON
6. 用户打开私人场景
7. 成功后扣减 1 次 credits

---

## 2.6 产品功能清单

## 2.6.1 小程序前台

### 用户相关

- 微信登录
- 手机号绑定
- 个人中心
- 我的会员
- 我的 credits
- 我的订单

### 内容相关

- 公开场景库
- 场景分类
- 我的生成场景
- 历史记录
- 收藏

### 商业相关

- 套餐页
- 商品详情页
- 支付页
- 订单页
- 权益页

### 生成相关

- 上传图片
- 本地压缩
- 创建任务
- 轮询状态
- 打开生成场景

## 2.6.2 Admin 后台

### 用户管理

- 用户列表
- 用户详情
- 用户状态
- 封禁/解封
- 会员信息
- credits 信息

### 商品管理

- 商品创建
- SKU 管理
- 定价管理
- 上下架
- 套餐描述

### 内容管理

- 公开场景分类
- 场景列表
- 场景编辑
- 专题合集管理

### 订单与支付

- 订单列表
- 支付状态
- 退款处理
- 对账

### 任务监控

- 任务队列
- 任务状态
- 失败任务
- 重试任务

### 系统配置

- 平台配置
- 支付配置
- AI 模型配置
- TTS 配置
- 存储配置

---

## 2.7 商品模型设计

建议平台统一支持三类商品。

### 1. 会员商品

例如：

- 内容会员
- 家庭会员
- 家庭 Plus

权益可能包括：

- 解锁场景数量
- 会员有效期
- 赠送 credits
- 导出能力

### 2. Credits 商品

例如：

- 30 次生成包
- 100 次生成包
- 300 次生成包

权益：

- 增加可用生成次数

### 3. 数字商品

例如：

- 公开场景专题合集
- 词汇记忆包
- 长期访问内容包

权益：

- 某专题可访问
- 某商品有效期 5 年

---

## 2.8 会员与权益设计

平台不应把权限写死在代码里。

建议通过“权益模型”统一表达。

例如：

- `public_scene_access_count`
- `diy_generation_credits`
- `video_export_count`
- `collection_access`
- `membership_expire_at`

权益发放来源：

- 会员商品购买
- credits 充值
- 数字商品购买
- 系统赠送

权益校验场景：

- 打开内容前
- 创建生成任务前
- 导出视频前

---

## 2.9 MVP 范围建议

第一阶段不要全做。

建议首发 MVP 只做这些：

### 必做

- 微信登录
- 用户体系
- 商品与 SKU
- 订单
- 微信支付
- 会员权益
- credits 权益
- 公开场景访问控制
- DIY 生成扣减 credits
- Admin 后台基础版
- PostgreSQL

### 暂缓

- 分销
- 优惠券
- 企业租户
- 多管理员体系
- 自动续费
- 财务复杂对账
- 视频导出正式版

---

## 3. 数据库设计（PostgreSQL）

建议将当前 JSON 文件模式升级为 PostgreSQL 结构化模型。

数据库可按 8 个模块分表。

---

## 3.1 用户与身份表

### `users`

用户主表。

字段建议：

```text
id                  uuid pk
user_no             varchar unique
status              varchar      -- active / blocked / deleted
nickname            varchar
avatar_url          text
mobile              varchar null
email               varchar null
password_hash       varchar null
last_login_at       timestamptz null
created_at          timestamptz
updated_at          timestamptz
```

### `user_identities`

用于绑定微信、手机号、邮箱等身份。

字段建议：

```text
id                  uuid pk
user_id             uuid fk -> users.id
provider            varchar      -- wechat_mp / mobile / email
provider_uid        varchar
union_id            varchar null
openid              varchar null
extra_json          jsonb
created_at          timestamptz
updated_at          timestamptz
```

索引建议：

- `(provider, provider_uid)` unique

### `user_sessions`

登录会话。

字段建议：

```text
id                  uuid pk
user_id             uuid fk -> users.id
access_token        varchar unique
refresh_token       varchar unique
expired_at          timestamptz
created_at          timestamptz
updated_at          timestamptz
```

---

## 3.2 权限与后台角色表

### `admins`

Admin 账号表。

```text
id                  uuid pk
user_id             uuid fk -> users.id
status              varchar
created_at          timestamptz
updated_at          timestamptz
```

### `roles`

```text
id                  uuid pk
code                varchar unique
name                varchar
created_at          timestamptz
updated_at          timestamptz
```

### `admin_role_relations`

```text
id                  uuid pk
admin_id            uuid fk -> admins.id
role_id             uuid fk -> roles.id
created_at          timestamptz
```

如果第一阶段想更简单，也可以先不做复杂 RBAC，只做：

- `super_admin`
- `operator`

两级。

---

## 3.3 商品与定价表

### `products`

平台商品主表。

```text
id                  uuid pk
product_code        varchar unique
product_type        varchar      -- membership / credits / digital_bundle
name                varchar
subtitle            varchar
description         text
status              varchar      -- draft / active / inactive
cover_url           text null
sort_order          int
created_at          timestamptz
updated_at          timestamptz
```

### `product_categories`

用于前台分类。

```text
id                  uuid pk
name                varchar
code                varchar unique
sort_order          int
created_at          timestamptz
updated_at          timestamptz
```

### `product_category_relations`

```text
id                  uuid pk
product_id          uuid fk -> products.id
category_id         uuid fk -> product_categories.id
```

### `product_skus`

真正售卖的具体规格。

```text
id                  uuid pk
product_id          uuid fk -> products.id
sku_code            varchar unique
name                varchar
billing_type        varchar      -- one_time / monthly / quarterly / yearly
duration_days       int null
status              varchar
list_price          numeric(10,2)
sale_price          numeric(10,2)
currency            varchar
stock_type          varchar      -- unlimited / finite
stock_count         int null
created_at          timestamptz
updated_at          timestamptz
```

### `sku_benefits`

用于表达 SKU 对应的权益。

```text
id                  uuid pk
sku_id              uuid fk -> product_skus.id
benefit_type        varchar      -- public_scene_access / credits / video_export / bundle_access
benefit_value       varchar
benefit_json        jsonb
created_at          timestamptz
updated_at          timestamptz
```

示例：

- `benefit_type = public_scene_access`
- `benefit_json = {"scene_limit":100,"category_limit":10}`

---

## 3.4 订单与支付表

### `orders`

```text
id                  uuid pk
order_no            varchar unique
user_id             uuid fk -> users.id
status              varchar      -- pending / paid / closed / refunded
total_amount        numeric(10,2)
payable_amount      numeric(10,2)
paid_amount         numeric(10,2) null
currency            varchar
payment_status      varchar
paid_at             timestamptz null
created_at          timestamptz
updated_at          timestamptz
```

### `order_items`

```text
id                  uuid pk
order_id            uuid fk -> orders.id
product_id          uuid fk -> products.id
sku_id              uuid fk -> product_skus.id
product_name        varchar
sku_name            varchar
quantity            int
unit_price          numeric(10,2)
total_price         numeric(10,2)
benefit_snapshot    jsonb
created_at          timestamptz
updated_at          timestamptz
```

### `payments`

```text
id                  uuid pk
payment_no          varchar unique
order_id            uuid fk -> orders.id
user_id             uuid fk -> users.id
channel             varchar      -- wechat_pay
status              varchar      -- pending / success / failed / refunded
amount              numeric(10,2)
channel_trade_no    varchar null
channel_payload     jsonb
paid_at             timestamptz null
created_at          timestamptz
updated_at          timestamptz
```

### `refunds`

```text
id                  uuid pk
refund_no           varchar unique
order_id            uuid fk -> orders.id
payment_id          uuid fk -> payments.id
status              varchar
amount              numeric(10,2)
reason              text null
created_at          timestamptz
updated_at          timestamptz
```

---

## 3.5 权益与配额表

### `user_entitlements`

核心表。

```text
id                  uuid pk
user_id             uuid fk -> users.id
source_type         varchar      -- order / system_grant / admin_grant
source_id           uuid null
entitlement_type    varchar      -- membership / bundle_access / feature_unlock
entitlement_code    varchar
status              varchar      -- active / expired / consumed / revoked
starts_at           timestamptz
expires_at          timestamptz null
payload_json        jsonb
created_at          timestamptz
updated_at          timestamptz
```

### `user_credit_accounts`

```text
id                  uuid pk
user_id             uuid fk -> users.id
credit_type         varchar      -- diy_scene_generation / video_export
balance             int
frozen_balance      int
created_at          timestamptz
updated_at          timestamptz
```

### `credit_ledger`

```text
id                  uuid pk
user_id             uuid fk -> users.id
credit_type         varchar
change_amount       int          -- +100 / -1
balance_after       int
reason_type         varchar      -- order_grant / task_consume / admin_adjust
reason_id           uuid null
remark              text null
created_at          timestamptz
```

### `user_bundle_access`

针对一次性数字合集。

```text
id                  uuid pk
user_id             uuid fk -> users.id
bundle_id           uuid
status              varchar
starts_at           timestamptz
expires_at          timestamptz
created_at          timestamptz
updated_at          timestamptz
```

---

## 3.6 内容与场景表

### `scene_categories`

```text
id                  uuid pk
name                varchar
code                varchar unique
sort_order          int
status              varchar
created_at          timestamptz
updated_at          timestamptz
```

### `public_scenes`

将原 `scenes.json` 拆表。

```text
id                  uuid pk
scene_code          varchar unique
title               varchar
category_id         uuid fk -> scene_categories.id
cover_url           text
background_url      text
status              varchar
scene_json          jsonb        -- items / verbs / meta
created_at          timestamptz
updated_at          timestamptz
```

### `scene_bundles`

公开场景合集商品内容包。

```text
id                  uuid pk
bundle_code         varchar unique
name                varchar
description         text
cover_url           text null
valid_days          int          -- 例如 1825 = 5 年
status              varchar
created_at          timestamptz
updated_at          timestamptz
```

### `bundle_scene_relations`

```text
id                  uuid pk
bundle_id           uuid fk -> scene_bundles.id
scene_id            uuid fk -> public_scenes.id
sort_order          int
created_at          timestamptz
```

### `generated_scenes`

私人场景表。

```text
id                  uuid pk
scene_code          varchar unique
user_id             uuid fk -> users.id
title               varchar
cover_url           text
background_url      text
status              varchar
scene_json          jsonb
created_at          timestamptz
updated_at          timestamptz
```

---

## 3.7 上传与任务表

### `uploads`

```text
id                  uuid pk
upload_code         varchar unique
user_id             uuid fk -> users.id
original_filename   varchar
content_type        varchar
storage_key         text
size_bytes          bigint
width               int null
height              int null
status              varchar
created_at          timestamptz
updated_at          timestamptz
```

### `scene_generation_tasks`

```text
id                  uuid pk
task_code           varchar unique
user_id             uuid fk -> users.id
upload_id           uuid fk -> uploads.id
status              varchar      -- queued / running / done / failed
step                varchar
progress            int
title               varchar null
include_verbs       boolean
accent              varchar
voice_gender        varchar
voice_name          varchar
result_scene_id     uuid null
error_message       text null
created_at          timestamptz
updated_at          timestamptz
```

### `task_logs`

```text
id                  uuid pk
task_id             uuid fk -> scene_generation_tasks.id
level               varchar
message             text
payload_json        jsonb
created_at          timestamptz
```

---

## 3.8 审计与配置表

### `system_configs`

```text
id                  uuid pk
config_key          varchar unique
config_value        jsonb
updated_by          uuid null
created_at          timestamptz
updated_at          timestamptz
```

### `audit_logs`

```text
id                  uuid pk
actor_type          varchar      -- user / admin / system
actor_id            uuid null
action              varchar
target_type         varchar
target_id           uuid null
payload_json        jsonb
created_at          timestamptz
```

---

## 3.9 数据库设计原则

### 原则 1

用户主键独立，不依赖微信 openid。

### 原则 2

订单、支付、权益分离。

### 原则 3

商品、价格、权益不要写死在代码里。

### 原则 4

场景 JSON 结构第一阶段可保留在 `jsonb` 里，减少重构成本。

### 原则 5

生成内容和计费逻辑要可追踪。

---

## 4. 系统架构设计

## 4.1 总体架构

建议升级后的总体结构：

```text
微信小程序前端
        │
        v
Nginx / API Gateway
        │
        v
FastAPI 应用层
├── Auth 模块
├── User 模块
├── Product 模块
├── Order/Payment 模块
├── Entitlement 模块
├── Scene 模块
├── Upload 模块
└── Admin API 模块
        │
        ├── PostgreSQL
        ├── Redis
        ├── Object Storage
        └── Worker Queue
                │
                v
            Worker 集群
            ├── 场景生成
            ├── 音频生成
            ├── 视频导出
            └── 其他异步任务
```

---

## 4.2 推荐模块划分

建议后端拆成以下模块：

### `auth`

- 微信登录
- token 发放
- session 管理

### `users`

- 用户信息
- 手机号绑定
- 用户状态

### `products`

- 商品
- SKU
- 定价
- 分类

### `orders`

- 订单创建
- 订单查询
- 订单状态

### `payments`

- 支付下单
- 回调处理
- 对账

### `entitlements`

- 会员权益
- credits
- 合集访问权

### `scenes`

- 公开场景
- 私人场景
- 场景详情
- 场景分类

### `tasks`

- 生成任务
- 任务状态
- 失败重试

### `admin`

- 后台管理 API

---

## 4.3 文件存储建议

当前是本地目录：

- `assets/uploads`
- `assets/generated`

第一阶段还能继续用，但建议尽快升级为对象存储。

建议路线：

### 第一阶段

- 本地磁盘 + Nginx/FastAPI 静态访问

### 第二阶段

- S3 兼容对象存储
- MinIO / 腾讯云 COS / 阿里云 OSS / AWS S3

对象存储目录建议：

```text
uploads/raw/<user_id>/<upload_id>.jpg
generated/scenes/<scene_id>/background.jpg
generated/scenes/<scene_id>/audio/*.mp3
exports/video/<scene_id>/<export_id>.mp4
products/covers/<product_id>.jpg
```

---

## 4.4 Worker 架构建议

当前项目使用的是进程内线程 worker。

这只能作为早期方案。

建议未来升级为：

### 推荐组合

- PostgreSQL
- Redis
- 独立 Worker

可选队列实现：

- Celery + Redis
- Dramatiq + Redis
- RQ + Redis

我更建议：

- FastAPI 负责 API
- Worker 独立部署
- Redis 做队列

Worker 类型可拆成：

- `scene_generation_worker`
- `tts_worker`
- `video_export_worker`
- `notification_worker`

---

## 4.5 Admin 后台架构建议

建议新增一个独立的 Web Admin 前端。

原因：

- Admin 不适合放在小程序里
- 权限复杂
- 操作重

建议结构：

```text
admin-web
  -> 调 admin-api
  -> 管理商品、价格、订单、内容、用户、任务
```

前端技术可以后面再定，但从架构上建议：

- Admin 前端独立项目
- 和小程序前端分开

---

## 5. API 设计建议（高层）

## 5.1 Auth API

```text
POST /api/auth/wechat/login
POST /api/auth/mobile/bind
POST /api/auth/logout
GET  /api/me
```

## 5.2 Product API

```text
GET  /api/products
GET  /api/products/{productId}
GET  /api/products/{productId}/skus
GET  /api/bundles
GET  /api/bundles/{bundleId}
```

## 5.3 Order API

```text
POST /api/orders
GET  /api/orders
GET  /api/orders/{orderId}
POST /api/orders/{orderId}/pay
```

## 5.4 Membership/Entitlement API

```text
GET /api/me/membership
GET /api/me/credits
GET /api/me/entitlements
```

## 5.5 Scene API

```text
GET  /api/scenes
GET  /api/scenes/{sceneId}
GET  /api/my/scenes
POST /api/uploads/image
POST /api/my/tasks/scene-generate
GET  /api/my/tasks/{taskId}
```

## 5.6 Admin API

```text
GET/POST /admin/products
GET/POST /admin/skus
GET/POST /admin/scenes
GET/POST /admin/bundles
GET      /admin/orders
GET      /admin/users
GET      /admin/tasks
POST     /admin/tasks/{taskId}/retry
```

---

## 6. 部署建议

## 6.1 当前阶段可行部署

如果你要在当前 VPS 上继续演进，第一阶段建议：

### 组件

- Nginx
- FastAPI API 服务
- Worker 服务
- PostgreSQL
- Redis

### 进程建议

```text
systemd
├── app-api.service
├── app-worker.service
├── postgresql.service
├── redis.service
└── nginx.service
```

### 域名建议

```text
https://e.cps.vin           小程序/API 入口
https://admin.e.cps.vin     Admin 后台
https://static.e.cps.vin    静态/对象资源（未来）
```

---

## 6.2 推荐的未来部署分层

### 第一层：入口层

- Nginx / Caddy
- TLS
- 反向代理

### 第二层：应用层

- API 服务
- Admin API
- Webhook 服务

### 第三层：异步层

- Worker
- 队列消费

### 第四层：数据层

- PostgreSQL
- Redis
- Object Storage

---

## 6.3 PostgreSQL 部署建议

如果是单机阶段：

- 先本机部署 PostgreSQL
- 开启自动备份
- 每日逻辑备份
- 每周全量快照

如果进入正式商业化阶段：

- 建议迁移到独立数据库实例
- 应用和数据库分离
- 做备份演练

建议至少配置：

- `pg_dump` 定时备份
- Binlog/WAL 归档策略
- 监控磁盘和连接数

---

## 6.4 Redis 部署建议

Redis 用于：

- 队列
- 缓存
- 限流
- 短期会话

第一阶段单机即可。

但建议：

- 持久化开启
- maxmemory 策略明确
- 不暴露公网

---

## 6.5 对象存储建议

第一阶段可继续本地磁盘。

但只要开始正式售卖，我建议尽快迁移对象存储。

原因：

- 生成文件会越来越多
- 视频导出会更大
- 本地盘管理会越来越乱
- 扩容麻烦

推荐：

- MinIO 作为过渡
- 或直接云对象存储

---

## 6.6 日志与监控建议

至少做：

- API 请求日志
- Worker 任务日志
- 支付回调日志
- 订单状态日志
- 错误报警

建议监控：

- API 响应时间
- Worker 队列长度
- 任务成功率
- PostgreSQL 连接数
- Redis 内存
- 磁盘空间

---

## 6.7 安全建议

必须考虑：

- token 鉴权
- Admin 独立权限
- 支付回调签名验证
- 上传文件校验
- 敏感内容审核
- 用户隐私保护
- 数据备份与恢复

特别注意：

- 不要让小程序直接接触支付密钥
- 不要把管理员接口混在普通用户接口里不做隔离

---

## 7. 从当前项目迁移的演进路线

## 第 1 阶段：数据层替换

目标：

- 从 JSON 文件迁移到 PostgreSQL

优先迁移：

- 用户
- 上传
- 任务
- 场景

## 第 2 阶段：账号与鉴权

目标：

- 用真实用户体系替换 `debugUserId`

## 第 3 阶段：商品与订单

目标：

- 做商品页、订单、支付、权益

## 第 4 阶段：Admin

目标：

- 后台管理能力上线

## 第 5 阶段：worker 独立

目标：

- 独立队列和 worker 服务

## 第 6 阶段：对象存储 + 视频导出

目标：

- 支持更大规模的文件型业务

---

## 8. 我建议你当前最优先做什么

如果按商业化优先级排序，我建议：

### 第一优先

- PostgreSQL 数据库
- 用户登录
- token 鉴权

### 第二优先

- 商品/SKU
- 订单
- 微信支付
- 权益模型

### 第三优先

- Admin 后台最小版
- 任务监控
- 场景管理

### 第四优先

- Redis + 独立 worker
- 视频导出
- 数字合集商品

---

## 9. 一句话总结

当前项目最合理的升级路径不是“继续在现有 demo 上零散加功能”，而是：

**把它重构成一个以 PostgreSQL 为核心、以用户/商品/订单/权益为平台底座、以小程序为用户入口、以 FastAPI 为业务 API、以独立 worker 为异步执行层、以 Admin 为运营控制台的 SaaS 与虚拟数字商品平台。**

---

## 10. 第一阶段实施拆解

下面把上面的 PRD 再往下拆到“可以直接开始研发”的程度。

这里的目标不是一次做完整个平台，而是定义：

1. 第一阶段必须落哪些表
2. 第一阶段必须开放哪些 API
3. 第一阶段 Admin 后台最小需要哪些页面

我对第一阶段的定义是：

**从当前 demo 迈入“可收费、可登录、可运营”的最小闭环。**

也就是：

- 用户可以登录
- 用户可以购买商品
- 支付成功后能拿到权益
- 系统能根据权益控制公开内容和 DIY 生成
- 管理员能在后台管理商品、用户、订单和任务

---

## 11. 第一阶段范围边界

### 第一阶段必须做

- PostgreSQL
- 用户体系
- token 鉴权
- 商品/SKU
- 订单
- 微信支付
- 权益发放
- credits 扣减
- 公开场景访问控制
- 生成任务访问控制
- Admin 最小后台

### 第一阶段不做或只预留

- 企业租户
- 优惠券
- 分销
- 自动续费
- 复杂退款流程
- 视频导出正式版
- 对象存储迁移
- 多 worker 类型拆分

这样可以把第一阶段控制在一个合理范围内。

---

## 12. 第一阶段数据库建表 SQL 草案

下面不是完整生产级 SQL，而是第一阶段的核心 DDL 草案。

目的：

- 帮你确定建表顺序
- 帮研发快速开始
- 帮后续 migration 拆分

建议优先使用：

- PostgreSQL 15+
- `uuid`
- `jsonb`
- `timestamptz`

建议先启用扩展：

```sql
create extension if not exists "pgcrypto";
```

这样可以用：

```sql
gen_random_uuid()
```

来生成主键。

### 12.1 用户与登录

```sql
create table users (
  id uuid primary key default gen_random_uuid(),
  user_no varchar(64) not null unique,
  status varchar(32) not null default 'active',
  nickname varchar(128),
  avatar_url text,
  mobile varchar(32),
  email varchar(128),
  last_login_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table user_identities (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id),
  provider varchar(32) not null,
  provider_uid varchar(128) not null,
  union_id varchar(128),
  openid varchar(128),
  extra_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (provider, provider_uid)
);

create table user_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id),
  access_token varchar(255) not null unique,
  refresh_token varchar(255) not null unique,
  expired_at timestamptz not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

### 12.2 Admin

```sql
create table admins (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id),
  admin_type varchar(32) not null default 'operator',
  status varchar(32) not null default 'active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id)
);
```

第一阶段为了提速，可以先不用完整 RBAC，只做：

- `super_admin`
- `operator`

两种类型。

### 12.3 商品、SKU、权益模板

```sql
create table products (
  id uuid primary key default gen_random_uuid(),
  product_code varchar(64) not null unique,
  product_type varchar(32) not null,
  name varchar(128) not null,
  subtitle varchar(255),
  description text,
  status varchar(32) not null default 'draft',
  cover_url text,
  sort_order int not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table product_skus (
  id uuid primary key default gen_random_uuid(),
  product_id uuid not null references products(id),
  sku_code varchar(64) not null unique,
  name varchar(128) not null,
  billing_type varchar(32) not null,
  duration_days int,
  list_price numeric(10,2) not null,
  sale_price numeric(10,2) not null,
  currency varchar(16) not null default 'CNY',
  status varchar(32) not null default 'active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table sku_benefits (
  id uuid primary key default gen_random_uuid(),
  sku_id uuid not null references product_skus(id),
  benefit_type varchar(64) not null,
  benefit_value varchar(255),
  benefit_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

第一阶段建议支持的 `product_type`：

- `membership`
- `credit_pack`
- `bundle`

第一阶段建议支持的 `benefit_type`：

- `public_scene_pack`
- `scene_generation_credits`
- `bundle_access`
- `video_export_credits`

### 12.4 订单与支付

```sql
create table orders (
  id uuid primary key default gen_random_uuid(),
  order_no varchar(64) not null unique,
  user_id uuid not null references users(id),
  status varchar(32) not null default 'pending',
  total_amount numeric(10,2) not null,
  payable_amount numeric(10,2) not null,
  paid_amount numeric(10,2),
  currency varchar(16) not null default 'CNY',
  payment_status varchar(32) not null default 'pending',
  paid_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table order_items (
  id uuid primary key default gen_random_uuid(),
  order_id uuid not null references orders(id),
  product_id uuid not null references products(id),
  sku_id uuid not null references product_skus(id),
  product_name varchar(128) not null,
  sku_name varchar(128) not null,
  quantity int not null default 1,
  unit_price numeric(10,2) not null,
  total_price numeric(10,2) not null,
  benefit_snapshot jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table payments (
  id uuid primary key default gen_random_uuid(),
  payment_no varchar(64) not null unique,
  order_id uuid not null references orders(id),
  user_id uuid not null references users(id),
  channel varchar(32) not null,
  status varchar(32) not null default 'pending',
  amount numeric(10,2) not null,
  channel_trade_no varchar(128),
  channel_payload jsonb not null default '{}'::jsonb,
  paid_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

### 12.5 权益与 credits

```sql
create table user_entitlements (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id),
  source_type varchar(32) not null,
  source_id uuid,
  entitlement_type varchar(64) not null,
  entitlement_code varchar(64) not null,
  status varchar(32) not null default 'active',
  starts_at timestamptz not null,
  expires_at timestamptz,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table user_credit_accounts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id),
  credit_type varchar(64) not null,
  balance int not null default 0,
  frozen_balance int not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, credit_type)
);

create table credit_ledger (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id),
  credit_type varchar(64) not null,
  change_amount int not null,
  balance_after int not null,
  reason_type varchar(64) not null,
  reason_id uuid,
  remark text,
  created_at timestamptz not null default now()
);
```

### 12.6 场景内容

```sql
create table scene_categories (
  id uuid primary key default gen_random_uuid(),
  code varchar(64) not null unique,
  name varchar(128) not null,
  status varchar(32) not null default 'active',
  sort_order int not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public_scenes (
  id uuid primary key default gen_random_uuid(),
  scene_code varchar(64) not null unique,
  title varchar(128) not null,
  category_id uuid references scene_categories(id),
  cover_url text,
  background_url text,
  status varchar(32) not null default 'active',
  scene_json jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table scene_bundles (
  id uuid primary key default gen_random_uuid(),
  bundle_code varchar(64) not null unique,
  name varchar(128) not null,
  description text,
  cover_url text,
  valid_days int not null default 1825,
  status varchar(32) not null default 'active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table bundle_scene_relations (
  id uuid primary key default gen_random_uuid(),
  bundle_id uuid not null references scene_bundles(id),
  scene_id uuid not null references public_scenes(id),
  sort_order int not null default 0,
  created_at timestamptz not null default now(),
  unique (bundle_id, scene_id)
);

create table generated_scenes (
  id uuid primary key default gen_random_uuid(),
  scene_code varchar(64) not null unique,
  user_id uuid not null references users(id),
  title varchar(128) not null,
  cover_url text,
  background_url text,
  status varchar(32) not null default 'active',
  scene_json jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

### 12.7 上传与任务

```sql
create table uploads (
  id uuid primary key default gen_random_uuid(),
  upload_code varchar(64) not null unique,
  user_id uuid not null references users(id),
  original_filename varchar(255) not null,
  content_type varchar(128) not null,
  storage_key text not null,
  size_bytes bigint not null,
  width int,
  height int,
  status varchar(32) not null default 'active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table scene_generation_tasks (
  id uuid primary key default gen_random_uuid(),
  task_code varchar(64) not null unique,
  user_id uuid not null references users(id),
  upload_id uuid not null references uploads(id),
  status varchar(32) not null default 'queued',
  step varchar(64) not null default 'queued',
  progress int not null default 0,
  title varchar(255),
  include_verbs boolean not null default true,
  accent varchar(32) not null default 'en-US',
  voice_gender varchar(32) not null default 'female',
  voice_name varchar(64) not null default 'JennyNeural',
  result_scene_id uuid references generated_scenes(id),
  error_message text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

### 12.8 第一阶段索引建议

建议至少补这些索引：

```sql
create index idx_orders_user_id on orders(user_id);
create index idx_orders_status on orders(status);
create index idx_payments_order_id on payments(order_id);
create index idx_user_entitlements_user_id on user_entitlements(user_id);
create index idx_user_entitlements_code on user_entitlements(entitlement_code);
create index idx_credit_ledger_user_id on credit_ledger(user_id);
create index idx_generated_scenes_user_id on generated_scenes(user_id);
create index idx_uploads_user_id on uploads(user_id);
create index idx_scene_generation_tasks_user_id on scene_generation_tasks(user_id);
create index idx_scene_generation_tasks_status on scene_generation_tasks(status);
```

---

## 13. 第一阶段 API 清单

下面的 API 清单按“第一阶段必须做”来列，保持最小可用。

### 13.1 Auth / User

#### `POST /api/auth/wechat/login`

用途：

- 小程序登录
- 用微信 code 换取平台用户和 token

请求：

```json
{
  "code": "wx_login_code"
}
```

响应：

```json
{
  "accessToken": "xxx",
  "refreshToken": "xxx",
  "user": {
    "id": "uuid",
    "nickname": "张三",
    "avatarUrl": "..."
  }
}
```

#### `GET /api/me`

用途：

- 获取当前登录用户资料

#### `POST /api/auth/logout`

用途：

- 注销当前登录会话

---

### 13.2 商品与套餐

#### `GET /api/products`

用途：

- 返回前台可售商品列表

支持筛选：

- `productType`
- `status`

#### `GET /api/products/{productId}`

用途：

- 商品详情

#### `GET /api/products/{productId}/skus`

用途：

- 商品对应 SKU 列表

#### `GET /api/bundles`

用途：

- 数字合集列表

#### `GET /api/bundles/{bundleId}`

用途：

- 数字合集详情

---

### 13.3 订单与支付

#### `POST /api/orders`

用途：

- 基于商品 SKU 创建订单

请求：

```json
{
  "skuId": "uuid",
  "quantity": 1
}
```

#### `GET /api/orders`

用途：

- 查询我的订单

#### `GET /api/orders/{orderId}`

用途：

- 订单详情

#### `POST /api/orders/{orderId}/pay`

用途：

- 生成支付参数

响应：

- 微信支付所需参数

#### `POST /api/payments/wechat/notify`

用途：

- 微信支付回调

说明：

- 这是服务端回调接口，不对前端开放

---

### 13.4 权益与账户

#### `GET /api/me/membership`

用途：

- 查看当前会员状态

#### `GET /api/me/credits`

用途：

- 查看当前 credits 余额

#### `GET /api/me/entitlements`

用途：

- 查看当前用户已拥有的权益

#### `GET /api/me/bundles`

用途：

- 查看已购买的数字合集

---

### 13.5 场景内容

#### `GET /api/scenes`

用途：

- 公开场景列表

第一阶段建议支持：

- 分类筛选
- 分页
- 会员权益过滤

#### `GET /api/scenes/{sceneId}`

用途：

- 获取公开或私人场景详情

逻辑：

- 公开场景：校验是否有访问权
- 私人场景：校验是否属于当前用户

#### `GET /api/my/scenes`

用途：

- 获取我生成的场景列表

---

### 13.6 上传与生成

#### `POST /api/uploads/image`

用途：

- 上传图片

#### `POST /api/my/tasks/scene-generate`

用途：

- 创建生成任务

新增校验：

- 当前用户是否有 DIY credits
- 当前用户是否有对应权益

#### `GET /api/my/tasks/{taskId}`

用途：

- 查询任务状态

#### `GET /api/my/tasks`

建议新增。

用途：

- 任务列表页
- 查看历史任务

---

### 13.7 Admin API

第一阶段 Admin API 只做最小集。

#### 商品管理

```text
GET    /admin/products
POST   /admin/products
GET    /admin/products/{id}
PUT    /admin/products/{id}
POST   /admin/products/{id}/publish
POST   /admin/products/{id}/disable
```

#### SKU 管理

```text
GET    /admin/skus
POST   /admin/skus
PUT    /admin/skus/{id}
```

#### 用户管理

```text
GET    /admin/users
GET    /admin/users/{id}
POST   /admin/users/{id}/block
POST   /admin/users/{id}/unblock
```

#### 订单管理

```text
GET    /admin/orders
GET    /admin/orders/{id}
```

#### 场景内容管理

```text
GET    /admin/public-scenes
POST   /admin/public-scenes
PUT    /admin/public-scenes/{id}
```

#### 数字合集管理

```text
GET    /admin/bundles
POST   /admin/bundles
PUT    /admin/bundles/{id}
POST   /admin/bundles/{id}/bind-scenes
```

#### 任务监控

```text
GET    /admin/tasks
GET    /admin/tasks/{id}
POST   /admin/tasks/{id}/retry
```

---

## 14. 第一阶段 Admin 页面清单

Admin 不求一开始做得很全，但必须把“能运营、能看数、能处理问题”这几件事做到。

### 14.1 登录页

页面名称：

- Admin 登录

核心功能：

- 管理员登录
- 进入后台首页

---

### 14.2 后台首页 / Dashboard

页面名称：

- 数据看板

核心模块：

- 今日订单数
- 今日支付金额
- 有效会员数
- 今日生成任务数
- 失败任务数

目的：

- 一进后台就知道系统是否正常

---

### 14.3 用户列表页

页面名称：

- 用户管理

核心字段：

- 用户 ID
- 昵称
- 手机号
- 注册时间
- 会员状态
- credits 余额
- 状态（正常/封禁）

操作：

- 查看详情
- 封禁
- 解封

---

### 14.4 用户详情页

页面名称：

- 用户详情

展示内容：

- 基本信息
- 登录信息
- 订单列表
- 权益列表
- credits 账户
- 生成场景列表

---

### 14.5 商品列表页

页面名称：

- 商品管理

展示内容：

- 商品名称
- 商品类型
- 状态
- SKU 数量
- 排序

操作：

- 新建商品
- 编辑商品
- 上下架

---

### 14.6 SKU 配置页

页面名称：

- SKU 管理

展示内容：

- SKU 名称
- 价格
- 计费周期
- 权益摘要
- 状态

操作：

- 新建 SKU
- 编辑 SKU
- 配置权益

---

### 14.7 订单列表页

页面名称：

- 订单管理

展示内容：

- 订单号
- 用户
- 商品
- 金额
- 支付状态
- 创建时间

操作：

- 查看详情

第一阶段可以先不做复杂退款界面。

---

### 14.8 场景管理页

页面名称：

- 公开场景管理

展示内容：

- 场景标题
- 分类
- 状态
- 更新时间

操作：

- 新增
- 编辑
- 上下架

---

### 14.9 合集管理页

页面名称：

- 数字合集管理

展示内容：

- 合集名称
- 场景数
- 有效期
- 状态

操作：

- 新建合集
- 绑定场景
- 编辑封面和文案

---

### 14.10 任务监控页

页面名称：

- 任务管理

展示内容：

- 任务 ID
- 用户
- 状态
- 进度
- 错误信息
- 创建时间

操作：

- 查看详情
- 重试失败任务

这对 AI 产品非常关键。

---

### 14.11 系统配置页

页面名称：

- 系统设置

第一阶段建议最少管理：

- 支付配置状态
- AI 模型配置
- TTS 配置
- 开关项

第一阶段可以先只读，不一定先做在线编辑。

---

## 15. 第一阶段研发顺序建议

为了减少返工，我建议按下面顺序实施。

### 第一步：数据库与 ORM 层

- 建 PostgreSQL
- 建核心表
- 落 ORM 模型
- 落 migration

### 第二步：登录与鉴权

- 微信登录
- token 中间件
- `GET /api/me`

### 第三步：商品、SKU、权益

- 商品读取接口
- SKU 读取接口
- 权益发放逻辑

### 第四步：订单与支付

- 订单创建
- 微信支付参数生成
- 支付回调
- 订单状态流转

### 第五步：将当前场景生成逻辑接入权益校验

- 创建任务前校验会员/credits
- 成功后扣减 credits

### 第六步：Admin 后台最小版

- 登录
- Dashboard
- 用户、商品、订单、任务页面

### 第七步：worker 拆分准备

- 先保留现有实现
- 但抽象任务层
- 为 Redis 队列做接口预留

---

## 16. 第一阶段交付物建议

如果要按阶段验收，我建议定义这几项交付物：

### 后端

- PostgreSQL migration
- ORM 模型
- Auth API
- Product API
- Order API
- Payment callback
- Entitlement service
- Scene access guard

### 前端小程序

- 登录流程
- 套餐页
- 订单页
- 我的权益页
- 个人中心
- 场景访问拦截与购买引导

### Admin

- 登录
- Dashboard
- 用户列表
- 商品列表
- 订单列表
- 任务列表

### 运维

- PostgreSQL 部署
- Redis 部署
- API 服务部署
- Worker 服务部署
- 备份策略

---

## 17. 我对第一阶段的建议总结

第一阶段不要追求“像一个完整商业平台一样什么都有”。

正确目标应该是：

**把当前项目升级成一个有真实用户、能卖商品、能收款、能发权益、能控制访问、能看后台数据的最小商业闭环。**

只要这个闭环打通，第二阶段再继续做：

- 更完整 Admin
- 数字合集商品
- 视频导出
- Redis 队列
- 对象存储

就会非常顺。

---

## 18. 微信小程序登录唯一性设计

这一节补充的是：当前项目如果做成正式 SaaS，微信小程序登录应该如何保证用户身份唯一，以及未来如何平滑升级到多端统一账号体系。

### 18.1 结论先说

对于当前这个项目，我建议采用下面这套原则：

- 平台内部真正的用户主键，始终是 `users.id`
- 当前小程序内的唯一微信身份，使用 `openid`
- 未来如果接公众号、H5、App，再用 `unionid` 做跨应用统一
- 手机号只作为绑定信息或辅助身份，不作为唯一主键

也就是说：

- **当前阶段：`openid` 保证“小程序内唯一”**
- **平台阶段：`unionid` 负责“跨应用统一”**
- **系统内部：`user_id` 才是平台真正主键**

### 18.2 官方依据

本节设计基于微信官方文档：

- 小程序登录：`wx.login`
  - https://developers.weixin.qq.com/miniprogram/dev/framework/open-ability/login.html
- 服务端换取登录态：`code2Session`
  - https://developers.weixin.qq.com/miniprogram/dev/OpenApiDoc/user-login/code2Session.html
- UnionID 机制说明
  - https://developers.weixin.qq.com/miniprogram/dev/framework/open-ability/union-id.html
- 获取手机号
  - https://developers.weixin.qq.com/miniprogram/dev/framework/open-ability/getPhoneNumber.html

### 18.3 为什么不能只用手机号

很多项目一开始会想：“既然微信能拿手机号，那就直接把手机号当用户唯一标识。”

这个做法不稳，原因有几个：

- 同一个人可能换手机号
- 家长可能把自己的手机号给孩子使用
- 有些场景下用户未授权手机号
- 未来如果接多种登录方式，手机号和微信身份并不是一回事

所以手机号更适合做：

- 联系方式
- 找回账号辅助信息
- 风控辅助字段
- 营销触达字段

而不应该直接取代微信身份主键。

### 18.4 `openid` 和 `unionid` 应该怎么理解

#### `openid`

`openid` 是微信给“当前小程序内某个用户”的唯一标识。

它的特点是：

- 对当前这个小程序来说，同一个用户的 `openid` 是唯一的
- 换成另一个小程序，同一个人会变成另一个 `openid`

所以如果你现在只有一个小程序：

- 直接用 `openid` 做当前登录身份唯一键，是正确的

#### `unionid`

`unionid` 是为了让同一个用户在多个微信应用体系下能够被识别成“同一个人”。

但要注意：

- `unionid` 有获取前提，不是任何时候都天然稳定拿到
- 它更适合做未来“多端统一账号”的桥梁键

所以推荐做法是：

- 现在先以 `openid` 落地
- 数据模型预留 `union_id`
- 当未来有公众号、App、多个小程序时，再把 `unionid` 用起来

### 18.5 推荐数据库设计

推荐不要把 `openid` 直接塞进 `users` 主表当唯一主键字段，而是做成“身份表”。

#### `users`

平台用户主表：

- `id`
- `status`
- `display_name`
- `avatar_url`
- `mobile`
- `mobile_verified`
- `created_at`
- `updated_at`

#### `user_identities`

第三方身份表：

- `id`
- `user_id`
- `provider`
- `provider_uid`
- `union_id`
- `session_key_encrypted`
- `meta_json`
- `created_at`
- `updated_at`

约束建议：

- `unique(provider, provider_uid)`
- `index(user_id)`
- `index(union_id)`

当前项目里：

- `provider = wechat_mp`
- `provider_uid = openid`

这意味着：

- 同一个 `openid` 在系统里只能绑定一条微信小程序身份
- 一个平台用户可以在未来绑定更多身份类型

### 18.6 推荐登录流程

推荐时序如下：

1. 小程序调用 `wx.login`
2. 前端把 `code` 发给后端 `POST /api/auth/wechat/login`
3. 后端调用微信 `code2Session`
4. 微信返回：
   - `openid`
   - `session_key`
   - 可能存在的 `unionid`
5. 后端先按 `(provider=wechat_mp, provider_uid=openid)` 查 `user_identities`
6. 如果查到，直接登录成功
7. 如果没查到，但返回了 `unionid`，则再按 `union_id` 查找是否已有历史账号
8. 如果找到旧账号，则把当前 `openid` 绑定到旧账号
9. 如果还是没找到，则创建新 `users` 记录和 `user_identities` 记录
10. 后端签发自己的 `access_token` 和 `refresh_token`
11. 小程序后续访问 API 时，只带平台自己的 token

### 18.7 一定不要这样做

以下做法不建议采用：

- 不要把 `session_key` 下发给前端
- 不要把 `session_key` 当成你自己的登录 token
- 不要只靠手机号识别用户
- 不要把 `openid` 当作整个平台内部主键
- 不要把前端传来的 `openid` 当可信身份，必须由服务端通过 `code2Session` 获取

### 18.8 推荐 API 设计

第一阶段建议补充这些认证接口：

- `POST /api/auth/wechat/login`
  - 入参：`code`
  - 出参：平台 `accessToken`、`refreshToken`、`user`
- `POST /api/auth/refresh`
  - 刷新 token
- `GET /api/me`
  - 获取当前用户资料、会员状态、credits
- `POST /api/me/bind-mobile`
  - 绑定手机号

未来如果上 Admin 和更多端，还可以增加：

- `POST /api/auth/logout`
- `POST /api/auth/admin/login`
- `POST /api/auth/wechat/unbind`

### 18.9 对当前项目的落地建议

当前项目里前端还在用一个 `debugUserId` 方案做临时隔离，这适合开发联调，但不适合正式商业化。

正式版应该升级成：

- 前端用 `wx.login`
- 后端做微信登录换取身份
- 后端签发自己的 JWT 或 session token
- 所有 `/api/my/*` 接口都基于真实 `user_id` 做访问控制

这样后续下面这些能力都会变得清晰：

- 会员权益发放
- credits 扣减
- 订单归属
- 场景归属
- 历史购买恢复
- 多设备登录

### 18.10 我对第一阶段的最终建议

如果只从第一阶段实施成本和正确性出发，我建议这样定：

- 第一阶段只支持微信小程序登录
- 以 `openid` 作为当前唯一微信身份键
- 预留 `union_id` 字段，不强依赖
- 用户系统内部始终用 `user_id`
- 手机号作为可选绑定信息，不参与主登录判定

这样设计的好处是：

- 当前可快速上线
- 后续不会推翻重做
- 未来扩公众号、App、H5、Web Admin 时也能继续沿用

---

## 19. 微信登录相关 PostgreSQL 建表 SQL 草案

这一节只补充和认证、身份、token、手机号绑定直接相关的第一阶段表。

### 19.1 `users`

```sql
create table if not exists users (
  id uuid primary key,
  status varchar(32) not null default 'active',
  display_name varchar(120),
  avatar_url text,
  mobile varchar(32),
  mobile_verified boolean not null default false,
  last_login_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_users_mobile on users(mobile);
create index if not exists idx_users_status on users(status);
```

设计说明：

- `id` 是系统内部主键
- `mobile` 可以为空，因为不是所有用户一开始都会授权手机号
- `status` 预留给封禁、注销、冻结等状态

### 19.2 `user_identities`

```sql
create table if not exists user_identities (
  id uuid primary key,
  user_id uuid not null references users(id),
  provider varchar(32) not null,
  provider_uid varchar(128) not null,
  union_id varchar(128),
  session_key_encrypted text,
  meta_json jsonb not null default '{}'::jsonb,
  last_login_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(provider, provider_uid)
);

create index if not exists idx_user_identities_user_id on user_identities(user_id);
create index if not exists idx_user_identities_union_id on user_identities(union_id);
create index if not exists idx_user_identities_provider_union_id on user_identities(provider, union_id);
```

设计说明：

- 当前小程序登录时：
  - `provider = 'wechat_mp'`
  - `provider_uid = openid`
- `union_id` 允许为空
- `session_key_encrypted` 建议加密存储，不要明文落库

### 19.3 `auth_refresh_tokens`

```sql
create table if not exists auth_refresh_tokens (
  id uuid primary key,
  user_id uuid not null references users(id),
  token_hash varchar(255) not null,
  device_type varchar(32),
  device_id varchar(128),
  app_version varchar(32),
  ip inet,
  user_agent text,
  expires_at timestamptz not null,
  revoked_at timestamptz,
  created_at timestamptz not null default now(),
  unique(token_hash)
);

create index if not exists idx_auth_refresh_tokens_user_id on auth_refresh_tokens(user_id);
create index if not exists idx_auth_refresh_tokens_expires_at on auth_refresh_tokens(expires_at);
```

设计说明：

- 建议 access token 短期有效，refresh token 落库
- 数据库存 `token_hash`，不要存明文 token
- 这样支持多设备登录和单设备踢出

### 19.4 `user_mobile_bind_logs`

```sql
create table if not exists user_mobile_bind_logs (
  id uuid primary key,
  user_id uuid not null references users(id),
  mobile varchar(32) not null,
  bind_source varchar(32) not null,
  created_at timestamptz not null default now()
);

create index if not exists idx_user_mobile_bind_logs_user_id on user_mobile_bind_logs(user_id);
create index if not exists idx_user_mobile_bind_logs_mobile on user_mobile_bind_logs(mobile);
```

设计说明：

- 用来保留手机号绑定历史
- `bind_source` 可记录：
  - `wechat_phone`
  - `manual_admin`
  - `sms_verify`

### 19.5 第一阶段是否需要 `accounts`

如果第一阶段只有个人/家长用户，不做团队和机构后台，那么：

- 可以先不引入 `accounts` / `organizations`
- 所有权益都先直接挂在 `user_id`

等第二阶段再考虑：

- 学校
- 机构
- 班级
- 多成员账号体系

---

## 20. FastAPI 认证接口定义草案

### 20.1 `POST /api/auth/wechat/login`

用途：

- 小程序使用 `wx.login` 拿到 `code` 后，调用这个接口完成平台登录

请求体示例：

```json
{
  "code": "021abcxyz",
  "device": {
    "deviceId": "wx-miniapp-device-001",
    "deviceType": "wechat_mini_program",
    "appVersion": "1.0.0"
  }
}
```

响应体示例：

```json
{
  "accessToken": "eyJhbGciOi...",
  "accessTokenExpiresIn": 7200,
  "refreshToken": "rt_xxxxx",
  "refreshTokenExpiresIn": 2592000,
  "user": {
    "id": "c56a4180-65aa-42ec-a945-5fd21dec0538",
    "displayName": "微信用户",
    "avatarUrl": "",
    "mobile": null,
    "mobileVerified": false
  }
}
```

后端动作：

1. 校验 `code` 非空
2. 调微信 `code2Session`
3. 获取 `openid`、`session_key`、可能存在的 `unionid`
4. 查找或创建用户
5. 写 `last_login_at`
6. 签发 access token / refresh token
7. 返回当前用户资料

### 20.2 `POST /api/auth/refresh`

用途：

- 用 refresh token 换新 access token

请求体示例：

```json
{
  "refreshToken": "rt_xxxxx"
}
```

响应体示例：

```json
{
  "accessToken": "eyJhbGciOi...",
  "accessTokenExpiresIn": 7200
}
```

建议规则：

- refresh token 支持轮换
- 老 token 刷新成功后立即失效
- 发现异常设备可主动 revoke

### 20.3 `POST /api/auth/logout`

用途：

- 当前设备登出

请求头：

- `Authorization: Bearer <accessToken>`

请求体示例：

```json
{
  "refreshToken": "rt_xxxxx"
}
```

后端动作：

- 将对应 refresh token 标记为 `revoked_at`

### 20.4 `GET /api/me`

用途：

- 获取当前登录用户资料
- 给小程序首页、个人中心、权益页提供基础数据

响应建议包含：

```json
{
  "id": "c56a4180-65aa-42ec-a945-5fd21dec0538",
  "displayName": "微信用户",
  "avatarUrl": "",
  "mobile": null,
  "mobileVerified": false,
  "memberSummary": {
    "isActive": true,
    "expiresAt": "2027-04-05T00:00:00Z"
  },
  "creditSummary": {
    "sceneGenerateBalance": 88
  }
}
```

### 20.5 `POST /api/me/profile`

用途：

- 修改昵称、头像等平台资料

请求体示例：

```json
{
  "displayName": "Tom",
  "avatarUrl": "https://..."
}
```

### 20.6 `POST /api/me/bind-mobile`

用途：

- 绑定手机号

第一阶段可以有两种接法：

- 方案 A：微信手机号能力
- 方案 B：短信验证码能力

如果第一阶段先图快，建议：

- 先不把它做成登录主入口
- 只做“补充资料绑定”

### 20.7 认证中间件建议

后端建议增加统一中间件或依赖注入层：

- `get_current_user()`
- `get_current_active_user()`
- `get_current_admin_user()`

这样后续下面这些接口都能统一接：

- `/api/me`
- `/api/my/scenes`
- `/api/my/tasks`
- `/api/orders`
- `/api/admin/*`

---

## 21. 小程序登录时序图

下面这张图适合研发和产品一起看，能快速理解前后端谁在做什么。

```text
+------------------+        +-------------------+        +------------------------+        +-------------------+
| 微信小程序前端   |        | FastAPI Auth API  |        | 微信 code2Session 接口 |        | PostgreSQL        |
+------------------+        +-------------------+        +------------------------+        +-------------------+
         |                            |                               |                               |
         | wx.login()                 |                               |                               |
         |--------------------------->|                               |                               |
         | 取得 code                  |                               |                               |
         |                            |                               |                               |
         | POST /api/auth/wechat/login                               |                               |
         | code                        |                               |                               |
         |--------------------------->|                               |                               |
         |                            | 调 code2Session               |                               |
         |                            |------------------------------>|                               |
         |                            |                               | 返回 openid/session_key/...   |
         |                            |<------------------------------|                               |
         |                            |                               |                               |
         |                            | 查 user_identities(openid)    |                               |
         |                            |--------------------------------------------------------------->|
         |                            |<---------------------------------------------------------------|
         |                            |                               |                               |
         |                            | 若不存在则创建 users / user_identities                         |
         |                            |--------------------------------------------------------------->|
         |                            |<---------------------------------------------------------------|
         |                            |                               |                               |
         |                            | 生成 access token / refresh token                               |
         |                            |--------------------------------------------------------------->|
         |                            |<---------------------------------------------------------------|
         |                            |                               |                               |
         | 返回 token + user          |                               |                               |
         |<---------------------------|                               |                               |
         |                            |                               |                               |
         | 后续请求带 Authorization    |                               |                               |
         |--------------------------->|                               |                               |
         |                            | 校验 token -> 得到 user_id     |                               |
         |                            |------------------------------->|                               |
         |                            |                               |                               |
```

### 21.1 对当前项目的具体改造步骤

为了从现在的 `debugUserId` 平滑切换，我建议按下面顺序改：

1. 新增 `users`、`user_identities`、`auth_refresh_tokens`
2. 新增 `POST /api/auth/wechat/login`
3. 小程序启动时增加登录态初始化
4. 把当前 `debugUserId` 请求头替换成正式 `Authorization`
5. 所有 `/api/my/*` 接口改成读取真实 `user_id`
6. 保留一个短期兼容开关，联调阶段方便排查
7. 完成后移除 `debugUserId`

### 21.2 我建议的第一阶段认证边界

第一阶段不要做得太大，先控制在下面这些范围：

- 只做微信小程序登录
- 只做用户态，不先做复杂账号中心
- 只做基础 token 刷新
- 只做个人中心资料读取
- 只做手机号可选绑定
- Admin 登录单独设计，不和小程序用户体系混在一起

这样能最快支撑：

- 会员购买
- credits 管理
- 场景访问控制
- 订单归属
- 用户画像积累

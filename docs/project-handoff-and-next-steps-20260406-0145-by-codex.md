# 当前项目开发情况说明与接手文档

更新时间：2026-04-06 01:45 UTC

关联主文档：

- `/www/wwwroot/e.cps.vin/weixin-demo-01/docs/current-project-saas-platform-prd-20260404-1831-by-codex.md`

关联执行文档：

- `/www/wwwroot/e.cps.vin/weixin-demo-01/todolist/task-saas-phase1-batch1-auth-foundation-20260405-by-codex.md`
- `/www/wwwroot/e.cps.vin/weixin-demo-01/todolist/task-saas-phase1-batch2-postgres-auth-persistence-20260405-by-codex.md`
- `/www/wwwroot/e.cps.vin/weixin-demo-01/todolist/task-saas-phase1-batch3-product-entitlement-read-model-20260405-by-codex.md`
- `/www/wwwroot/e.cps.vin/weixin-demo-01/todolist/task-saas-phase1-batch4-mock-payment-order-flow-20260405-by-codex.md`
- `/www/wwwroot/e.cps.vin/weixin-demo-01/todolist/task-saas-phase1-batch5-real-wechat-login-20260405-by-codex.md`
- `/www/wwwroot/e.cps.vin/weixin-demo-01/todolist/task-saas-phase1-batch6-admin-minimal-completion-20260405-by-codex.md`
- `/www/wwwroot/e.cps.vin/weixin-demo-01/todolist/task-saas-phase1-batch7-scene-taxonomy-and-publication-20260405-by-codex.md`
- `/www/wwwroot/e.cps.vin/weixin-demo-01/todolist/task-saas-phase1-batch8-admin-scene-generator-20260405-by-codex.md`
- `/www/wwwroot/e.cps.vin/weixin-demo-01/todolist/task-saas-phase1-batch9-library-filters-and-public-republish-20260406-by-codex.md`

---

## 1. 文档目的

本文给下一位接手工程师提供三类信息：

1. 当前项目已经完成到什么程度
2. 当前真实运行架构是什么，而不是理想架构是什么
3. 结合 PRD，后面还剩哪些任务要继续做，建议按什么顺序推进

这份文档优先反映“代码和运行状态”，不是只复述 PRD。

---

## 2. 当前项目一句话状态

项目已经从最初的 JSON MVP，推进到了“可真实微信登录、可下单 mock 支付、可发放会员/点数、可通过 web admin 运营公开场景、可批量生成和发布公开场景”的阶段。

但它还没有完成 PRD 里的完整第一阶段。当前最主要的缺口是：

- 真实微信支付
- 手机号绑定
- credits 实际扣减
- 数字合集商品化访问控制
- 更完整的 Admin 管理动作和运营能力
- worker 与存储层的进一步工程化

---

## 3. 当前已完成范围

## 3.1 小程序前端

已完成：

- 独立微信登录页
- 真实微信 `code2Session` 登录接入
- 登录后用户卡片展示
- 头像选择与昵称保存
- 首页会员中心
- 商品页
- 订单页
- 公开场景库
- 公开场景按分类/合集筛选
- 我的生成场景
- 场景运行页
- 热点编辑器
- 私有场景生成链路

当前用户侧已具备：

- 微信真实登录
- 平台 token 会话
- 商品浏览
- mock 支付下单
- 查看订单
- 浏览公开场景
- 创建私有场景
- 编辑热点

## 3.2 后端 API

已完成：

- Auth API
- `/api/me`
- 商品 / SKU 只读与后台管理
- 订单与 mock 支付闭环
- 会员 / credits 发放
- 真实微信登录
- 场景分类 / 合集 CRUD
- 草稿发布到公开库
- admin 批量场景生成
- 公开场景按分类 / 合集筛选
- 已发布公开场景覆盖发布

## 3.3 Web Admin

已完成：

- 后台登录
- Dashboard
- 用户管理
- 用户设为 Admin / 撤销 Admin
- 用户封禁 / 解封
- 商品管理
- SKU 管理
- 订单管理
- 任务管理
- 失败任务重试
- 场景分类管理
- 场景合集管理
- 草稿发布到公开库
- 公共场景管理
- 已发布公开场景覆盖发布
- admin web 多图压缩上传批量生成公开场景

## 3.4 Worker / 内容生产

已完成：

- 上传图片 -> 创建任务 -> worker 异步消费
- AI 生成场景 JSON
- 语音生成
- 生成私有草稿场景
- admin 任务自动发布公开场景
- 重试任务

当前 worker 形态：

- 不是独立消息队列服务
- 是 FastAPI 进程内启动的 inline worker
- 任务队列存储仍然是 JSON 文件

---

## 4. 当前真实架构

## 4.1 存储层现状

当前项目不是“全量 PostgreSQL”，而是混合架构：

- PostgreSQL
  - 用户
  - 身份
  - refresh token
  - 商品
  - SKU
  - 权益
  - credits
  - 订单
  - 支付
  - 场景分类
  - 场景合集
  - 场景发布关系

- JSON 文件
  - 公开场景
  - 私有生成场景
  - 上传记录
  - 任务队列

这点非常关键。下一位工程师不要误以为场景和任务已经迁到 PostgreSQL。

## 4.2 身份与权限现状

- 小程序用户通过真实微信登录进入平台
- 平台签发自己的 access token / refresh token
- web admin 目前仍以后台账号密码为入口
- 但真实微信用户已经支持 `role=admin`
- 同一个真实微信用户可以在业务侧被提升为 admin

需要注意：

- `/admin` 不是微信扫码登录
- 它目前是后台密码登录 + 用户角色管理并存的模式

## 4.3 支付现状

当前支付仍是 mock。

已经具备：

- 订单创建
- 支付意图
- mock 支付成功
- 会员权益发放
- credits 发放

还不具备：

- 微信支付下单
- `wx.requestPayment`
- 支付回调
- 查单
- 幂等支付状态更新

## 4.4 内容运营现状

admin 运营公开场景的主路径是：

1. 小程序或 admin web 上传图片
2. 创建异步生成任务
3. worker 生成私有草稿
4. admin 选择分类和合集
5. 发布到公开场景库
6. 后续可从源草稿覆盖发布

当前公开场景不是直接数据库存储，而是：

- 公开场景 JSON 作为最终内容载体
- PostgreSQL 存储分类 / 合集 / 发布关系

---

## 5. 与 PRD 对照后的完成情况

下面按 PRD 的四个域来说明。

## 5.1 账号域

已完成：

- 微信登录
- 平台 token
- 用户资料基本信息
- admin 用户角色

未完成：

- 手机号绑定
- 手机号验证
- 更完整个人中心
- 多端统一账号策略

备注：

- batch5 的 todo 仍保留“真实联调未勾选”，但实际运行环境已经配置 `WECHAT_MP_APP_SECRET` 并运行在 `code2session` 模式。建议后续顺手把该 todo 文档修正。

## 5.2 商业域

已完成：

- 商品
- SKU
- 订单
- mock 支付
- 会员权益发放
- credits 发放

未完成：

- 真实微信支付
- 退款
- 对账
- 发票
- 优惠体系
- credits 扣减
- 数字合集商品化售卖闭环

## 5.3 业务域

已完成：

- 公开场景
- 私人场景
- 图片上传
- 异步任务
- 场景生成
- 热点编辑
- 场景分类
- 场景合集
- 公开场景筛选
- admin 批量生成与自动发布

未完成：

- 私有场景生成前权益校验
- 生成成功后 credits 扣减
- 生成失败回滚 credits
- 数字合集购买后访问控制
- 公共场景更完整排序 / 推荐机制

## 5.4 运营域

已完成：

- Admin Dashboard
- 用户管理
- 商品 / SKU 管理
- 订单管理
- 任务管理
- 场景分类 / 合集管理
- 草稿发布
- 场景生成器
- 公开场景覆盖发布

未完成：

- 后台复杂筛选器
- 订单高级检索
- 任务批量操作
- 后台系统配置中心
- 支付配置管理
- 权限细粒度模型
- 操作日志 / 审计日志

---

## 6. 当前代码状态对应的批次结论

## 已完成批次

- batch1 认证与会话底座
- batch2 PostgreSQL auth 持久化
- batch3 商品、SKU、权益读取底座
- batch4 mock 支付与订单闭环
- batch6 Admin 最小版补全
- batch7 场景分类、合集与草稿发布
- batch8 Admin web 场景生成器与批量生成
- batch9 公开场景库筛选与公开场景覆盖发布

## 实际已基本完成、但文档未完全回填的批次

- batch5 真实微信登录

代码与运行层面它已经可用，但 todo 文档第 5 项没有同步勾选。

---

## 7. 当前最重要的技术债

1. 场景 / 任务 / 上传仍是 JSON 文件，不利于扩展、查询和并发。
2. worker 仍是进程内 inline 模式，扩缩容和故障隔离不足。
3. mock 支付还没有被真实微信支付替换。
4. credits 只有发放，没有实际扣减闭环。
5. admin 和用户侧权限模型仍偏轻量，缺少审计和更细粒度控制。
6. 公开场景内容和发布关系分散在 JSON 与 PostgreSQL 两层，后续要考虑统一治理策略。

---

## 8. 下一步建议开发顺序

建议不要跳着做，按下面顺序推进更稳。

## P0：必须优先完成

### 1. 真实微信支付替换 mock 支付

目标：

- 保留现有订单和权益发放模型
- 仅替换支付发起和支付确认链路

任务：

- 支付配置项整理
- 微信支付下单接口
- 小程序 `wx.requestPayment`
- 支付回调通知
- 支付查单兜底
- 幂等支付成功处理
- mock / real 支付模式切换

### 2. credits 扣减闭环

目标：

- 私有场景生成前校验 credits
- 生成成功后扣减
- 失败回滚或不扣减

任务：

- 创建任务前 credits 预校验
- 任务成功扣减
- 扣减流水表
- 幂等防重
- 失败补偿策略

### 3. 数字合集商品化

目标：

- 合集不仅可运营分类，还能作为可购买数字商品

任务：

- 设计“合集商品 / 权益”模型
- 合集购买后发放访问权
- 公开场景库按用户权益控制可见范围
- 已购合集入口与列表

## P1：第一阶段补齐

### 4. 手机号绑定

任务：

- 小程序手机号授权
- 后端绑定接口
- 手机号唯一性
- 已绑定状态展示

### 5. Admin 增强版

任务：

- 用户筛选与搜索
- 订单筛选与搜索
- 任务筛选与搜索
- 商品和 SKU 排序
- 场景发布批量操作
- 操作日志

### 6. 场景与任务数据迁移到 PostgreSQL

任务：

- 设计 scenes / generated_scenes / uploads / tasks 表
- JSON -> PostgreSQL 迁移脚本
- worker 改读数据库队列
- 历史路径兼容

### 7. Worker 工程化

任务：

- worker 独立进程化
- 心跳与消费锁
- 失败重试次数
- 死信处理
- 任务超时控制

## P2：产品增强

### 8. 用户中心完善

任务：

- 我的会员
- 我的 credits
- 我的订单增强页
- 我的已购合集
- 个人资料页

### 9. 内容运营增强

任务：

- 场景推荐位
- 分类页装修
- 合集封面与排序
- 内容上下架状态细分

### 10. 风控与审计

任务：

- 后台操作日志
- 关键支付操作日志
- 用户封禁原因
- 任务失败原因归档

---

## 9. 在 PRD 基础上建议新增的任务

这些是当前真实工程推进后，PRD 里没有写得足够具体，但下一步非常值得补上的任务。

### A. 发布内容版本化

当前已经支持“覆盖发布”，下一步建议增加：

- 发布版本号
- 发布备注
- 历史版本回滚

### B. 公开场景内容质检流程

建议增加：

- 待审核
- 已发布
- 已下架

这样 admin 批量生成后不会直接把所有内容混在公开库里。

### C. 生成链路可观测性

建议增加：

- 任务耗时统计
- 失败原因分类
- core100 调用结果摘要
- TTS 成功率统计

### D. 真实支付接入前的安全清单

建议单独开一批做：

- 回调验签
- 金额校验
- 订单幂等
- 重复通知处理
- 支付超时策略

---

## 10. 推荐下一位工程师从哪里开始

如果目标是“尽快进入可收费状态”，建议直接从下面顺序开始：

1. 真实微信支付
2. credits 扣减闭环
3. 数字合集商品化和访问控制
4. 手机号绑定
5. 场景 / 任务迁移 PostgreSQL

如果目标是“先提升工程稳定性”，建议从下面顺序开始：

1. 场景 / 上传 / 任务 PostgreSQL 化
2. worker 独立进程化
3. 任务重试和死信
4. 日志与监控
5. 再做真实支付

---

## 11. 接手时务必先确认的事项

1. 当前 `.env` 是否仍配置为真实微信登录模式。
2. 当前数据库 `weixin_saas` 是否可连接。
3. 当前 `weixin-demo-api.service` 是否正常运行。
4. 当前 `https://e.cps.vin/admin` 是否可访问。
5. 当前 mock 支付商品与 demo catalog 是否仍存在。
6. 当前 JSON 场景文件是否与 PostgreSQL 发布关系保持一致。

---

## 12. 结论

当前项目已经不再是“只有 demo 的原型”，而是一个具备：

- 真实微信登录
- 商品与订单
- mock 支付
- 会员和点数发放
- admin 运营后台
- 场景分类 / 合集
- 批量生成公开场景

的半成品 SaaS 平台。

真正阻止它进入“可正式收费运营”的核心缺口，不是前端页面数量，而是这三件事：

1. 真实微信支付
2. credits 扣减闭环
3. 场景 / 任务 / 上传的数据库化与 worker 工程化

下一阶段如果围绕这三件事推进，路线会最稳。

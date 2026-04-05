# SaaS 第一阶段第三批：商品、SKU、权益读取底座

更新时间：2026-04-05 UTC

目标：

- 建立商品、SKU、权益、credits 的 PostgreSQL 读取底座
- 提供最小 Product API 和 `/api/me` 权益摘要
- 暂不进入订单、支付、扣减逻辑

范围约束：

- 本批只做读取接口和底层数据结构
- 不做下单、支付回调
- 不做创建任务前的 credits 扣减

任务清单：

- [x] 1. 新增商品、SKU、权益、credits PostgreSQL schema 与 store
- [x] 2. 接入 Product API：`GET /api/products`、`GET /api/products/{id}`、`GET /api/products/{id}/skus`
- [x] 3. 接入 `GET /api/me/membership`、`GET /api/me/credits`、`GET /api/me/entitlements`
- [x] 4. 让 `GET /api/me` 的 `memberSummary` / `creditSummary` 读真实数据
- [x] 5. 增加 demo 商品种子、补测试并完成联调验证

兼容性说明：

- 为兼容当前 auth / scene / task 的字符串主键，本批 commerce 表继续使用字符串 ID
- 等订单、支付、业务域统一迁移时，再一起收口成 UUID

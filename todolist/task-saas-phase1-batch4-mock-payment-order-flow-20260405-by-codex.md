# SaaS 第一阶段第四批：Mock 支付与订单闭环

更新时间：2026-04-05 UTC

目标：

- 建立订单、支付、权益发放的最小闭环
- 小程序可浏览商品、创建订单、发起 mock 支付、看到订单成功
- 会员与 credits 在 mock 支付成功后自动发放

范围约束：

- 本批支付模式固定为 `mock`
- 不接真实微信支付商户证书与回调验签
- 接口形状尽量贴近后续真实微信支付替换所需结构

任务清单：

- [x] 1. 新增订单与支付 PostgreSQL schema、store 与权益发放逻辑
- [x] 2. 接入 Order API：`POST /api/orders`、`GET /api/orders`、`GET /api/orders/{id}`、`POST /api/orders/{id}/pay`
- [x] 3. 接入 mock 支付确认接口，并在支付成功后发放会员/credits
- [x] 4. 新增小程序商品页、订单页与 mock 支付交互
- [x] 5. 补测试、在线验证并勾选完成

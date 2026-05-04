# Rust Commerce API — 用户侧核心

**Date:** 2026-05-04
**Scope:** Products + Orders + Payments (virtual_pay + mock) + CDK 兑换
**Goal:** 让小程序购买流程完整跑通，切换到 Rust 后端无感知

---

## API 端点（14 个）

### Products（用户侧）
| Method | Path | 描述 |
|--------|------|------|
| GET | /api/products | 产品列表，可选 ?productType= 过滤 |
| GET | /api/products/{id} | 产品详情 |
| GET | /api/products/{id}/skus | SKU 列表含 benefits |

### Orders（用户侧）
| Method | Path | 描述 |
|--------|------|------|
| POST | /api/orders | 创建订单，限频 10/min |
| GET | /api/orders | 我的订单列表 |
| GET | /api/orders/{id} | 订单详情 |
| POST | /api/orders/{id}/pay | 发起支付（mock / virtual_pay） |
| POST | /api/orders/{id}/mock-pay-success | mock 支付完成 |
| POST | /api/orders/{id}/payment-sync | 支付状态同步 |

### Payments（回调）
| Method | Path | 描述 |
|--------|------|------|
| GET | /api/payments/virtual/notify | 微信验证 echostr |
| POST | /api/payments/virtual/notify | xpay 发货通知 |

### User（增强）
| Method | Path | 描述 |
|--------|------|------|
| GET | /api/me | 增加 memberSummary 和 creditSummary |
| GET | /api/me/upgrade-preview?skuId= | 升级预览 |

### CDK（用户侧）
| Method | Path | 描述 |
|--------|------|------|
| POST | /api/cdk/redeem | 兑换 CDK |
| GET | /api/cdk/my-redemptions | 兑换记录 |

---

## 数据库表（已存在）

products, product_skus, sku_benefits, orders, order_items, payments,
user_entitlements, user_credit_accounts, credit_ledger, cdk_codes

---

## 新增文件

| 文件 | 职责 |
|------|------|
| src/models/product.rs | Product, Sku, SkuBenefit |
| src/models/order.rs | Order, OrderItem, Payment |
| src/models/commerce.rs | Entitlement, CreditAccount, CreditLedger, CdkCode |
| src/db/products.rs | 产品/SKU 查询 |
| src/db/orders.rs | 订单/支付 CRUD |
| src/db/credits.rs | 权益/积分操作 |
| src/services/virtual_pay.rs | xpay HMAC-SHA256 签名 + 发货通知 XML 解析 |
| src/services/benefits.rs | 权益发放（membership/credits/feature） |
| src/api/product.rs | 产品 API |
| src/api/order.rs | 订单 API |
| src/api/payment.rs | 支付回调 API |

---

## 关键业务逻辑

### 1. 下单
- 根据 skuId 查 SKU + Product，校验状态和库存
- 生成 order_no: `ORD{timestamp}{4位随机}`
- 创建 order + order_item，冻结价格和 benefits 快照

### 2. 支付
- 根据 PAYMENT_MODE 分流
- mock: 直接返回 mock requestPayment 参数
- virtual_pay: 生成 wx.requestVirtualPayment 参数（paySig + signature），需要 session_key

### 3. 支付回调（virtual_pay）
- 解析 xpay_goods_deliver_notify XML
- 验证签名
- 更新 payment status → order status
- 调用 benefits 发放

### 4. 权益发放（_grant_sku_benefits）
- membership: 创建/延长 user_entitlements
- credits: 充值 user_credit_accounts + credit_ledger
- feature: 创建 feature entitlement，继承 membership 的时间

### 5. 升级预览
- 判断 fresh / renewal / upgrade / downgrade
- 计算转换天数和新到期日

### 6. CDK 兑换
- SELECT FOR UPDATE 锁行
- 验证 status=unused
- 标记 redeemed
- 调用 _grant_sku_benefits

---

## Config 新增

```
PAYMENT_MODE=virtual_pay
WX_VIRTUAL_PAY_APP_KEY=...
WX_VIRTUAL_PAY_OFFER_ID=...
WX_VIRTUAL_PAY_ENV=0
```

## 依赖新增

无额外 crate，现有依赖足够（hmac/sha2 处理签名，reqwest 处理 HTTP）

# 微信虚拟支付迁移方案

> 日期：2026-04-26
> 分支：118v3
> 状态：设计阶段

## 一、背景

微信官方要求小程序内虚拟商品（会员、积分、功能解锁等）必须接入虚拟支付（Virtual Payment），替代原有的微信支付 JSAPI 接口。

### 当前实现

- 使用微信支付 v3 JSAPI 接口（`/v3/pay/transactions/jsapi`）
- 前端调用 `wx.requestPayment` 拉起支付
- 后端使用 RSA-SHA256 签名 + AES-GCM 回调解密
- 商户证书 + 平台证书认证
- 支持三种虚拟商品：会员（pro/plus/max）、积分（credits）、功能解锁（feature）

### 迁移目标

- 完全替换为微信虚拟支付（道具直购模式）
- 前端使用 `wx.requestVirtualPayment`
- 后端使用 HMAC-SHA256 签名
- 沙箱环境开发测试，通过后切换现网

## 二、技术差异对比

| 维度 | JSAPI 支付（现有） | 虚拟支付-道具直购（目标） |
|------|-------------------|--------------------------|
| 前端 API | `wx.requestPayment` | `wx.requestVirtualPayment` |
| 后端下单 | POST `/v3/pay/transactions/jsapi` 获取 prepay_id | 后端只做签名，下单由微信客户端 SDK 内部完成 |
| 签名方式 | RSA-SHA256（商户私钥签名） | HMAC-SHA256（AppKey 签名） |
| 用户态签名 | 无 | HMAC-SHA256（session_key 签名） |
| 回调通知 | AES-256-GCM 加密 JSON | XML 消息推送（xpay_goods_deliver_notify） |
| 凭证 | 商户证书、平台证书、api_v3_key | AppKey、offerId、session_key |
| 环境控制 | 无沙箱 | env=0 现网，env=1 沙箱 |
| 订单查询 | GET `/v3/pay/transactions/out-trade-no/{no}` | POST `/xpay/query_order`（需 access_token） |
| 基础库要求 | 无特殊要求 | >= 2.19.2 |

## 三、签名算法

### 3.1 支付签名（pay_sig）

后端计算，前端传给 `wx.requestVirtualPayment` 的 `paySig` 参数。

```python
def calc_pay_sig(uri: str, post_body: str, appkey: str) -> str:
    """HMAC-SHA256 支付签名"""
    message = uri + '&' + post_body
    return hmac.new(
        key=appkey.encode('utf-8'),
        msg=message.encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()
```

- `uri`：前端固定为 `requestVirtualPayment`，服务器 API 为接口路径（如 `/xpay/query_order`）
- `post_body`：signData 的 JSON 字符串（前端），或 API POST body（服务器）
- `appkey`：对应环境的 AppKey（沙箱/现网不同）

### 3.2 用户态签名（signature）

后端计算，前端传给 `wx.requestVirtualPayment` 的 `signature` 参数。

```python
def calc_signature(post_body: str, session_key: str) -> str:
    """HMAC-SHA256 用户态签名"""
    return hmac.new(
        key=session_key.encode('utf-8'),
        msg=post_body.encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()
```

- `post_body`：signData 的 JSON 字符串（与 pay_sig 使用的相同）
- `session_key`：用户的微信 session_key（来自 wx.login → code2session）

## 四、前端 wx.requestVirtualPayment 参数

```javascript
wx.requestVirtualPayment({
  signData: JSON.stringify({
    offerId: 'xxxx',           // 虚拟支付应用 ID
    buyQuantity: 1,             // 购买数量
    env: 0,                     // 0=现网, 1=沙箱
    currencyType: 'CNY',        // 币种
    productId: 'membership_pro', // 道具 ID
    goodsPrice: 3990,           // 道具单价（分）
    outTradeNo: 'ORD_xxx',     // 业务订单号（8-32字符）
    attach: 'testdata',         // 透传数据，回调时原样返回
  }),
  mode: 'short_series_goods',   // 道具直购模式
  paySig: 'xxx',               // 后端计算的支付签名
  signature: 'xxx',            // 后端计算的用户态签名
  success(res) { /* 支付成功 */ },
  fail({ errMsg, errCode }) { /* 支付失败 */ },
})
```

## 五、后端 API 变更

### 5.1 新增文件：`backend/app/virtual_pay.py`

替代 `wechat_pay.py`，负责虚拟支付的核心逻辑。

**配置类 `VirtualPayConfig`**：
```python
@dataclass
class VirtualPayConfig:
    app_id: str           # 小程序 AppID
    offer_id: str         # 虚拟支付应用 ID（offerId）
    app_key: str          # 对应环境的 AppKey
    env: int              # 0=现网, 1=沙箱
    api_base: str         # https://api.weixin.qq.com
```

**核心方法**：
- `calc_pay_sig(uri, post_body)` — 计算支付签名
- `calc_signature(post_body, session_key)` — 计算用户态签名
- `build_payment_params(order_no, product_id, price_fen, openid, session_key)` — 构建前端调用参数
- `query_order(access_token, order_no)` — 查询订单状态（POST `/xpay/query_order`）
- `notify_provide_goods(access_token, order_no)` — 通知发货完成（POST `/xpay/notify_provide_goods`）

### 5.2 路由变更

| 路由 | 变更 | 说明 |
|------|------|------|
| `POST /api/orders/{id}/pay` | 修改 | 返回虚拟支付参数（paySig, signature, signData） |
| `POST /api/orders/{id}/payment-sync` | 修改 | 调用 `/xpay/query_order` 查询支付状态 |
| `POST /api/payments/wechat/notify` | 删除 | 不再需要 |
| `POST /api/payments/virtual/notify` | 新增 | 处理 `xpay_goods_deliver_notify` 推送 |

### 5.3 支付初始化流程（新）

```
前端                    后端                      微信
  |                       |                        |
  |--- POST /orders ----->|                        |
  |<-- order (pending) ---|                        |
  |                       |                        |
  |--- POST /orders/{id}/pay --->|                 |
  |     (携带 session_key) |                        |
  |                       |-- 获取 session_key --->|
  |                       |<-- session_key --------|
  |                       |                        |
  |                       |-- 计算 paySig ---------|
  |                       |-- 计算 signature ------|
  |<-- {signData, paySig, signature, mode} --------|
  |                       |                        |
  |-- wx.requestVirtualPayment ------------------->|
  |<-- 支付结果 ------------------------------------|
  |                       |                        |
  |--- POST /orders/{id}/payment-sync ----------->|
  |                       |-- POST /xpay/query_order -->|
  |                       |<-- 订单状态 ---------------|
  |<-- 确认结果 ----------|                        |
  |                       |                        |
  |        [异步] 微信推送 xpay_goods_deliver_notify -->|
  |                       |<-- 发货通知 -------------|
  |                       |-- 授益（会员/积分/功能） --|
```

### 5.4 回调处理

虚拟支付使用微信消息推送（XML 格式），通过现有消息推送端点或新增端点接收。

推送类型：`xpay_goods_deliver_notify`

关键数据：
```xml
<xml>
  <OpenId>用户openid</OpenId>
  <OutTradeNo>业务订单号</OutTradeNo>
  <Env>0</Env>
  <WeChatPayInfo>
    <MchOrderNo>商户单号</MchOrderNo>
    <TransactionId>交易单号</TransactionId>
    <PaidTime>支付时间戳</PaidTime>
  </WeChatPayInfo>
  <GoodsInfo>
    <ProductId>道具ID</ProductId>
    <Quantity>数量</Quantity>
    <OrigPrice>原价（分）</OrigPrice>
    <ActualPrice>实付（分）</ActualPrice>
    <Attach>透传数据</Attach>
  </GoodsInfo>
</xml>
```

响应格式：`<xml><ErrCode>0</ErrCode></xml>`

## 六、数据库变更

### 6.1 payments 表

- `channel` 字段值从 `'wechat_pay'` 改为 `'virtual_pay'`
- `channel_payload` 结构变更，存储虚拟支付相关数据

### 6.2 products 表

新增字段：
```sql
ALTER TABLE products ADD COLUMN IF NOT EXISTS virtual_product_id VARCHAR(64);
```

用于映射 `wx.requestVirtualPayment` 的 `productId` 参数。需要在微信商户管理后台配置对应的道具。

### 6.3 SKU 与道具映射

每个 SKU 需要对应一个微信虚拟支付道具。映射关系：

| SKU | virtual_product_id | 道具名称 |
|-----|-------------------|---------|
| pro 会员 | `membership_pro` | Pro 年度会员 |
| plus 会员 | `membership_plus` | Plus 年度会员 |
| max 会员 | `membership_max` | Max 年度会员 |
| 积分包 | `credits_*` | 对应积分包 |

## 七、前端变更

### 7.1 payment.js

```javascript
// 旧：wx.requestPayment
requestPaymentAsync(params)

// 新：wx.requestVirtualPayment
wx.requestVirtualPayment({
  signData: payment.signData,     // JSON 字符串
  mode: payment.mode,             // 'short_series_goods'
  paySig: payment.paySig,         // 后端计算的支付签名
  signature: payment.signature,   // 后端计算的用户态签名
  success(res) { resolve(res) },
  fail(err) { reject(err) },
})
```

### 7.2 基础库版本检测

```javascript
// 检查是否支持虚拟支付
if (wx.canIUse('requestVirtualPayment')) {
  // 使用虚拟支付
} else {
  wx.showModal({
    title: '提示',
    content: '当前微信版本不支持虚拟支付，请升级微信',
  })
}
```

### 7.3 session_key 传递

虚拟支付需要用户的 session_key 来计算用户态签名。后端在 `POST /orders/{id}/pay` 时需要获取用户的 session_key。

方案：后端通过 `auth_store` 获取用户的 WeChat identity（包含 session_key），无需前端额外传递。

## 八、环境变量变更

### 删除（清理）

```
WECHAT_PAY_MCH_ID
WECHAT_PAY_API_V3_KEY
WECHAT_PAY_MCH_SERIAL_NO
WECHAT_PAY_MCH_PRIVATE_KEY_PATH
WECHAT_PAY_PLATFORM_CERT_PATH
WECHAT_PAY_PLATFORM_SERIAL_NO
WECHAT_PAY_NOTIFY_URL
WECHAT_PAY_API_BASE
WECHAT_PAY_CURRENCY
WECHAT_PAY_TIMEOUT_SECONDS
```

### 新增

```
WX_VIRTUAL_PAY_APP_KEY=xxx          # 虚拟支付 AppKey（现网/沙箱不同）
WX_VIRTUAL_PAY_OFFER_ID=xxx         # 虚拟支付应用 ID
WX_VIRTUAL_PAY_ENV=1                # 0=现网, 1=沙箱（开发期间用沙箱）
```

### 修改

```
PAYMENT_MODE=virtual_pay             # 原值为 wechat_pay，改为 virtual_pay（mock 仍保留）
```

## 九、依赖变更

### 新增 Python 依赖

```txt
wechat-xpay>=0.2.0    # 微信虚拟支付 Python SDK（可选，也可自行实现签名）
```

### 可删除的文件

```
backend/certs/apiclient_key.pem
backend/certs/apiclient_cert.pem
backend/certs/apiclient_cert.p12
backend/certs/wechatpay_*.pem
backend/app/wechat_pay.py            # 替换为 virtual_pay.py
```

## 十、实施计划

### Phase 1：后端核心（TDD）

1. 创建 `virtual_pay.py`，实现签名算法和配置
2. 编写签名算法的单元测试
3. 修改 `settings.py`，新增虚拟支付配置
4. 修改 `POST /orders/{id}/pay` 路由
5. 编写支付初始化的集成测试
6. 修改 `POST /orders/{id}/payment-sync` 路由
7. 新增 `POST /payments/virtual/notify` 回调端点
8. 编写支付完成流程的集成测试

### Phase 2：前端适配

9. 修改 `payment.js`，替换为 `wx.requestVirtualPayment`
10. 添加基础库版本检测
11. 修改 `order.js` 的响应处理

### Phase 3：数据库与配置

12. 新增 products 表的 `virtual_product_id` 字段
13. 配置沙箱环境的 AppKey 和 offerId
14. 在微信商户管理后台配置道具

### Phase 4：清理

15. 删除 `wechat_pay.py` 和证书文件
16. 清理环境变量
17. 更新文档

## 十一、测试策略

### 单元测试

- `calc_pay_sig` 签名算法正确性（使用文档中的示例数据验证）
- `calc_signature` 用户态签名正确性
- `VirtualPayConfig` 配置验证
- `build_payment_params` 参数构建

### 集成测试

- 完整的虚拟支付订单流程（使用沙箱环境）
  1. 创建订单 → 初始化支付 → 模拟支付成功 → 验证授益
- 回调处理测试
  1. 模拟微信推送 `xpay_goods_deliver_notify`
  2. 验证订单状态更新和授益
- 订单查询测试
  1. 模拟 `/xpay/query_order` 返回

### 手工验证

1. 在微信开发者工具中调用 `wx.requestVirtualPayment`（沙箱环境）
2. 验证支付弹窗、支付成功回调
3. 验证会员/积分/功能授益正确

## 十二、风险与注意事项

1. **session_key 有效期**：session_key 可能过期，需要确保获取的是最新的。在 `POST /orders/{id}/pay` 时需要检查并可能刷新。
2. **env 配置**：沙箱（env=1）和现网（env=0）使用不同的 AppKey，不可混用。
3. **道具配置**：必须在微信商户管理后台预先配置所有道具（productId、价格等），与代码中的 virtual_product_id 一致。
4. **outTradeNo 格式**：8-32 字符，只能是数字、大小写字母、符号 -|*@，不能以下划线开头。现有 order_no 格式需要检查兼容性。
5. **回调可靠性**：微信最多推送 15 次（间隔 2,4,8,16...秒），需确保幂等处理。
6. **技术服务费**：现网环境会产生技术服务费，沙箱不收费。
7. **iOS 兼容**：iOS 端有额外开通与适配流程，需单独处理。
8. **基础库版本**：要求 >= 2.19.2，需做版本检测和降级提示。

# 微信真实支付开发日志

更新时间：2026-04-06 04:42 UTC

## 1. 背景

本次工作目标是为当前项目补齐“普通商户直连模式”的第一版微信真实支付接入能力，同时保留 `mock` 支付模式，避免在真实商户受限或联调窗口未就绪时阻塞其他功能开发。

当前项目支付策略分两层：

- `mock`：继续用于日常开发、回归测试、商品与权益链路验证
- `wechat_pay`：真实微信支付能力，代码已接入，但本次先不继续做实单联调

结论：

- 真实支付代码已经接入
- 支付参数和证书的本地准备工作已完成
- 当前开发环境已切回 `mock`
- 等商户限制解除后，再继续真实支付联调

---

## 2. 本次已经完成的内容

## 2.1 配置层

已扩展：

- `backend/.env.example`
- `backend/app/settings.py`

新增了普通商户直连模式所需的支付配置项：

- `WECHAT_PAY_MCH_ID`
- `WECHAT_PAY_API_V3_KEY`
- `WECHAT_PAY_MCH_SERIAL_NO`
- `WECHAT_PAY_MCH_PRIVATE_KEY_PATH`
- `WECHAT_PAY_PLATFORM_CERT_PATH`
- `WECHAT_PAY_PLATFORM_SERIAL_NO`
- `WECHAT_PAY_NOTIFY_URL`
- `WECHAT_PAY_API_BASE`
- `WECHAT_PAY_CURRENCY`
- `WECHAT_PAY_TIMEOUT_SECONDS`

## 2.2 后端支付能力

已新增：

- 微信支付客户端
- 商户请求签名
- 小程序 `JSAPI/小程序下单`
- `requestPayment` 参数签名生成
- 小程序支付成功后的后端查单同步
- 微信支付回调入口
- 回调验签与资源解密

主要文件：

- `/www/wwwroot/e.cps.vin/weixin-demo-01/backend/app/wechat_pay.py`
- `/www/wwwroot/e.cps.vin/weixin-demo-01/backend/app/main.py`
- `/www/wwwroot/e.cps.vin/weixin-demo-01/backend/app/commerce_store.py`

新增接口：

- `POST /api/orders/{orderId}/pay`
- `POST /api/orders/{orderId}/payment-sync`
- `POST /api/payments/wechat/notify`

## 2.3 小程序前端支付链路

已调整：

- 小程序在 `wx.requestPayment` 成功后，不再只刷新用户信息
- 会进一步调用后端 `payment-sync` 做查单同步

主要文件：

- `/www/wwwroot/e.cps.vin/weixin-demo-01/services/order.js`
- `/www/wwwroot/e.cps.vin/weixin-demo-01/services/payment.js`

## 2.4 身份与 openid 支撑

为真实支付获取 `payer.openid`，已补充：

- auth store 读取当前用户微信身份的能力

主要文件：

- `/www/wwwroot/e.cps.vin/weixin-demo-01/backend/app/auth_store.py`
- `/www/wwwroot/e.cps.vin/weixin-demo-01/backend/app/auth_store_postgres.py`

---

## 3. 本次已经验证过的内容

## 3.1 自动化验证

已通过：

- `.venv/bin/pip install -r backend/requirements.txt`
- `.venv/bin/python -m unittest backend.tests.test_auth_api backend.tests.test_order_flow backend.tests.test_admin_api backend.tests.test_commerce_store backend.tests.test_worker_runner_admin_publish -v`
- `python -m compileall backend/app`
- `node -c services/order.js`
- `node -c services/payment.js`

其中新增覆盖了：

- mock 支付不回归
- 真实支付模式下的“预下单 -> 返回 `requestPayment` 参数 -> 后端查单同步 -> 权益到账”

## 3.2 配置与证书加载验证

本地已检查并通过：

- 商户号已填
- `APIv3 Key` 已填且长度正确
- 商户证书序列号已填
- 平台证书序列号已填
- 商户私钥文件存在且可加载
- 平台证书文件存在且可加载

说明：

- 本地环境的支付参数和证书已达到“代码可加载”的状态
- 这不等于已完成真实扣款联调

---

## 4. 当前为什么先暂停真实支付联调

当前决定暂停继续调试，不是因为代码还没接入，而是因为：

- 商户侧目前仍有受限情况
- 继续强行联调，容易把问题混在“代码问题”和“商户权限问题”之间
- 当前阶段更高效的策略是：先恢复 `mock`，继续推进其他功能开发

这意味着现在的策略是：

- 代码先准备好
- 环境先准备好
- 商户限制解除后，再用真实支付做最后一轮端到端联调

---

## 5. 当前开发环境状态

当前 `backend/.env` 的开发模式已切回：

```env
PAYMENT_MODE=mock
# PAYMENT_MODE=wechat_pay
```

也就是说：

- 真实支付参数仍保留在 `.env`
- 真实支付证书仍保留在本地
- 但当前后端运行时仍按 `mock` 支付工作

这样做的好处是：

- 不影响商品、订单、会员、credits 其他链路继续开发
- 不会因为真实支付不稳定影响日常回归
- 等恢复联调时只需切换 `PAYMENT_MODE`

---

## 6. 后续恢复真实支付联调时要做什么

当商户受限解除后，按下面顺序恢复：

1. 把 `backend/.env` 中：

```env
PAYMENT_MODE=wechat_pay
```

2. 重启后端服务：

```bash
systemctl restart weixin-demo-api.service
```

3. 在小程序中走真实商品购买流程：

- 商品页下单
- 拉起 `wx.requestPayment`
- 支付成功
- 观察订单状态是否更新为 `paid`
- 观察会员 / credits 是否到账

4. 检查后端日志：

- `/api/orders/{id}/pay`
- `/api/orders/{id}/payment-sync`
- `/api/payments/wechat/notify`

5. 重点核对这几个结果：

- 是否能成功创建 `prepay_id`
- 小程序是否能正常调起支付
- 回调是否能成功验签和解密
- 订单是否只发放一次权益
- 前端支付成功后是否能及时看到支付完成状态

---

## 7. 恢复联调时最值得先查的问题

恢复真实支付时，优先排查下面几类问题：

### 1. 商户配置问题

- 小程序 `AppID` 是否与商户号绑定
- 商户产品权限是否已开通
- 回调域名是否可公网访问

### 2. 参数问题

- 商户证书序列号是否与私钥匹配
- 平台证书是否为最新可用版本
- `APIv3 Key` 是否与商户平台一致

### 3. 代码侧问题

- `openid` 是否能从当前登录用户正确取到
- 订单金额换算为分是否正确
- 查单成功后是否正确更新支付状态
- 权益发放是否具备幂等性

---

## 8. 当前建议

当前建议非常明确：

- 暂不继续真实支付调试
- 继续用 `mock` 做其他功能开发
- 后面等商户侧限制解除后，再回来做真实支付最后一轮联调

当前不会丢失的成果有：

- 真实支付代码已在仓库中
- 配置模板已补齐
- 本地证书和参数已准备
- 支付链路已有自动化回归

所以暂停并不会造成返工，只是把“最后一公里联调”延后。

---

## 9. 一句话结论

这次真实微信支付开发已经完成了“代码接入 + 配置准备 + 本地加载验证”，但还没有继续做实单联调。当前环境已切回 `mock`，后续可以继续推进其他模块，等商户限制解除后再恢复真实支付联调。

# CDK (卡密) 系统开发文档

## 功能概述

卡密系统支持运营在后台批量生成会员卡密，分发给通过小红书等非微信支付渠道购买的用户。用户在小程序内输入卡密码兑换对应会员权益。

## 数据库表结构

### `cdk_codes`

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | varchar(128) PK | `cdk_` 前缀唯一标识 |
| `code` | varchar(64) UNIQUE | 卡密码，格式 `PREFIX-GROUP1-GROUP2-GROUP3-GROUP4` |
| `sku_id` | varchar(128) FK | 关联 `product_skus.id` |
| `status` | varchar(32) | `unused` / `redeemed` / `disabled` |
| `batch_id` | varchar(128) | 同一批次生成的卡密共享此 ID |
| `redeemed_by` | varchar(128) | 兑换用户 ID |
| `redeemed_at` | timestamptz | 兑换时间 |
| `note` | text | 备注（如"小红书2026年4月批次"） |
| `created_at` | timestamptz | 创建时间 |
| `updated_at` | timestamptz | 更新时间 |

### 卡密码格式

- 格式：`PREFIX-GROUP1-GROUP2-GROUP3-GROUP4`
- 前缀由 SKU code 决定：
  - `tier_pro_*` → `PRO`
  - `tier_plus_*` → `PLUS`
  - `tier_max_*` → `MAX`
- 每组 4 位大写字母 + 数字
- 示例：`PLUS-A1B2-C3D4-E5F6-G7H8`

## API 接口

### 管理端接口（需 admin 认证）

#### 列表查询
```
GET /api/admin/cdk-codes?status=unused&skuId=xxx&limit=200&offset=0
```

#### 批量生成
```
POST /api/admin/cdk-codes/generate
Body: { "skuId": "xxx", "quantity": 10, "note": "小红书4月批次" }
```

#### 批量删除
```
POST /api/admin/cdk-codes/batch-delete
Body: { "cdkIds": ["cdk_xxx", "cdk_yyy"] }
```

### 用户端接口（需登录）

#### 兑换卡密
```
POST /api/cdk/redeem
Body: { "code": "PLUS-A1B2-C3D4-E5F6-G7H8" }
```

## 兑换流程

1. 用户获取卡密码（从小红书直播间运营处）
2. 打开小程序 → 产品页面 → 点击「卡密兑换」
3. 输入卡密码 → 确认兑换
4. 后端校验：卡密存在 → 状态 unused → 事务内更新状态 + 授予权益
5. 权益授予复用订单支付后的同一套逻辑（membership + credits + feature）
6. 兑换成功后刷新页面，显示更新后的会员状态

## 运营操作指引

1. 登录管理后台
2. 左侧导航 → 运营管理 → 卡密管理
3. 选择 SKU（年卡类型）→ 输入生成数量 → 可选备注 → 点击「生成卡密」
4. 在列表中点击「复制」按钮复制卡密码
5. 将卡密码发给用户

## 错误处理

- 卡密不存在：提示"卡密不存在"
- 卡密已使用：提示"卡密已被使用或已失效"
- 重复兑换：同上（状态已变为 redeemed）
- 无效格式：后端自动转大写并查找

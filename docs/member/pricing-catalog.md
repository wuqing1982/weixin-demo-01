# 产品目录与定价方案

> 种子数据（seed_demo_catalog）完整定义

## 产品目录（3 个产品）

### 产品 1：Pro

```python
product = {
    'id': 'product_tier_pro',
    'productCode': 'tier_pro',
    'productType': 'membership',
    'name': 'Pro',
    'subtitle': '50 积分，开启英语场景创作之旅',
    'description': '解锁全部公开场景，获得 50 次场景生成积分，有效期 365 天。',
    'status': 'active',
    'sortOrder': 10,
}
sku = {
    'id': 'sku_tier_pro',
    'productId': 'product_tier_pro',
    'skuCode': 'tier_pro_365',
    'name': 'Pro（年）',
    'billingType': 'one_time',
    'durationDays': 365,
    'status': 'active',
    'listPrice': '69.00',
    'salePrice': '39.90',
    'currency': 'CNY',
    'sortOrder': 10,
}
```

**Benefits（2 个）：**

| benefitType | benefitValue | 说明 |
|-------------|-------------|------|
| `membership` | `pro` | 会员权益，365 天 |
| `credits` | `scene_generation_credits` | 50 积分 |

---

### 产品 2：Plus

```python
product = {
    'id': 'product_tier_plus',
    'productCode': 'tier_plus',
    'productType': 'membership',
    'name': 'Plus',
    'subtitle': '150 积分 + 视频导出，记录你的学习成果',
    'description': '全部公开场景 + 150 次场景生成 + 视频导出（保留3小时），有效期 365 天。',
    'status': 'active',
    'sortOrder': 20,
}
sku = {
    'id': 'sku_tier_plus',
    'productId': 'product_tier_plus',
    'skuCode': 'tier_plus_365',
    'name': 'Plus（年）',
    'billingType': 'one_time',
    'durationDays': 365,
    'status': 'active',
    'listPrice': '168.00',
    'salePrice': '99.00',
    'currency': 'CNY',
    'sortOrder': 10,
}
```

**Benefits（3 个）：**

| benefitType | benefitValue | 说明 |
|-------------|-------------|------|
| `membership` | `plus` | 会员权益，365 天 |
| `credits` | `scene_generation_credits` | 150 积分 |
| `feature` | `video_export` | 视频导出功能 |

---

### 产品 3：Max

```python
product = {
    'id': 'product_tier_max',
    'productCode': 'tier_max',
    'productType': 'membership',
    'name': 'Max',
    'subtitle': '500 积分 + 全功能解锁，无限创作',
    'description': '全部公开场景 + 500 次场景生成 + 视频导出 + 优先生成队列，有效期 365 天。',
    'status': 'active',
    'sortOrder': 30,
}
sku = {
    'id': 'sku_tier_max',
    'productId': 'product_tier_max',
    'skuCode': 'tier_max_365',
    'name': 'Max（年）',
    'billingType': 'one_time',
    'durationDays': 365,
    'status': 'active',
    'listPrice': '328.00',
    'salePrice': '199.00',
    'currency': 'CNY',
    'sortOrder': 10,
}
```

**Benefits（4 个）：**

| benefitType | benefitValue | 说明 |
|-------------|-------------|------|
| `membership` | `max` | 会员权益，365 天 |
| `credits` | `scene_generation_credits` | 500 积分 |
| `feature` | `video_export` | 视频导出功能 |
| `feature` | `priority_queue` | 优先生成队列 |

---

## 定价策略

```
Max ¥199    ←  锚点（对比参照物）
Plus ¥99    ←  推荐（"只要一半价格就能..."）
Pro ¥39.9   ←  入门（犹豫用户的兜底选择）
```

### 价格对比

| 套餐 | 原价 | 售价 | 折扣 | 积分单价 |
|------|------|------|------|----------|
| Pro | ¥69 | ¥39.9 | 42% off | ¥0.80/次 |
| Plus | ¥168 | ¥99 | 41% off | ¥0.66/次 |
| Max | ¥328 | ¥199 | 39% off | ¥0.40/次 |

---

## 新增 benefit_type: 'feature'

当前 `_grant_benefits_for_order()` 支持 `membership` 和 `credits` 两种类型。需新增 `feature` 类型：

```python
elif benefit_type == 'feature':
    # 写入 user_entitlements 表
    # entitlement_type = 'feature'
    # entitlement_code = benefit_value (如 'video_export', 'priority_queue')
    # duration = membership 的 durationDays (与会员同步)
```

### 数据库字段映射

```
user_entitlements:
  entitlement_type = 'feature'
  entitlement_code = 'video_export'        → Plus/Max
  entitlement_code = 'priority_queue'      → 仅 Max
  starts_at = 订单支付时间
  expires_at = starts_at + 365 天
```

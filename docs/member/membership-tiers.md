# 会员套餐体系设计

> 英语场景（e.cps.vin）微信小程序会员套餐方案

## 设计原则

1. **简单明了**：只有年卡，一次性购买，无续费/升降级复杂逻辑
2. **积分核心**：付费买的是会员身份 + 积分额度，积分为消耗型虚拟商品
3. **积分与会员绑定**：积分有效期与会员期一致，会员到期积分冻结
4. **低门槛高转化**：免费用户可体验 7 个固定场景，付费解锁全部能力

---

## 套餐总览

| 套餐 | 价格 | 积分 | 场景访问 | 视频导出 | 单价 |
|------|------|------|----------|----------|------|
| **免费用户** | ¥0 | 0 | 7 个固定场景 | ❌ | — |
| **Pro** | ¥39.9 | 50 次 | 全部公开场景 | ❌ | ¥0.80/次 |
| **Plus** | ¥99 | 150 次 | 全部公开场景 | ✅（3小时） | ¥0.66/次 |
| **Max** | ¥199 | 500 次 | 全部公开场景 | ✅（3小时）+ 优先 | ¥0.40/次 |

> 心理锚定：¥199 为锚点 → ¥99 看起来划算 → ¥39.9 是犹豫用户的兜底

---

## 免费用户

| 功能 | 权限 |
|------|------|
| 场景访问 | **7 个固定场景**（由后台配置 `FREE_SCENE_IDS`） |
| 场景生成 | ❌ |
| 视频导出 | ❌ |
| 热点编辑 | ❌ |

---

## Pro（¥39.9）

| 功能 | 权限 |
|------|------|
| 有效期 | **365 天** |
| 积分额度 | **50 次**场景生成 |
| 场景访问 | 全部公开场景 |
| 视频导出 | ❌ |
| 热点编辑 | 可编辑自己场景的热点 |

---

## Plus（¥99）

| 功能 | 权限 |
|------|------|
| 有效期 | **365 天** |
| 积分额度 | **150 次**场景生成 |
| 场景访问 | 全部公开场景 |
| 视频导出 | ✅ 导出视频保留 **3 小时** |
| 热点编辑 | 可编辑自己场景的热点 |

---

## Max（¥199）

| 功能 | 权限 |
|------|------|
| 有效期 | **365 天** |
| 积分额度 | **500 次**场景生成 |
| 场景访问 | 全部公开场景 |
| 视频导出 | ✅ 导出视频保留 **3 小时** |
| 热点编辑 | 可编辑所有场景的热点 |
| 专属功能 | 优先生成队列 |

---

## 积分规则（核心）

### 积分发放

- 购买套餐时一次性发放对应额度到 `user_credit_accounts`
- `credit_type = 'scene_generation_credits'`

### 积分消耗

- 每次场景生成消耗 **1 积分**
- 生成前检查余额，余额不足则拒绝并提示

### 积分叠加

- 重复购买套餐时，新积分 **累加** 到现有余额
- 不覆盖、不重置

```
例：用户已有 30 积分，再次购买创作卡 → 余额变为 30 + 150 = 180
```

### 积分冻结与解冻

**会员到期 → 积分冻结：**

1. `get_membership_summary()` 返回 `isActive: false`
2. 积分扣减前检查会员状态，非活跃则拒绝
3. `user_credit_accounts.balance` 不变，但业务层视为不可用

**再次付费 → 积分解冻：**

1. 购买新套餐后会员重新激活
2. 原有冻结积分自动可用 + 新积分叠加
3. 无需额外的"解冻"操作

```
例：
  用户购买创作卡 → 获得 150 积分，用掉 100，剩 50
  会员到期 → 50 积分冻结
  用户再次购买体验卡 → 会员重新激活，余额 = 50(解冻) + 50(新增) = 100
```

### 积分不单独售卖

- 只有付费会员才能获得积分
- 不提供单独的积分包商品
- 积分与会员绑定，不可转让

---

## 实体关系映射

### 数据库结构

```
products (3 个产品)
├── product_tier_pro     → Pro ¥39.9
├── product_tier_plus    → Plus ¥99
└── product_tier_max     → Max ¥199

每个 product 只有 1 个 SKU（一次性购买）
每个 SKU 绑定 1~3 个 benefit

sku_benefits (权益类型)
├── benefitType = 'membership'   → 写入 user_entitlements
├── benefitType = 'credits'      → 写入 user_credit_accounts + credit_ledger
└── benefitType = 'feature'      → 写入 user_entitlements (feature 类型)
    └── entitlement_code = 'video_export'
    └── entitlement_code = 'priority_queue'
```

### benefit_json 结构

**Pro SKU benefits：**
```json
[
  {
    "benefitType": "membership",
    "benefitValue": "pro",
    "benefitJson": { "durationDays": 365, "tier": "pro", "sceneAccess": "all_public" }
  },
  {
    "benefitType": "credits",
    "benefitValue": "scene_generation_credits",
    "benefitJson": { "creditType": "scene_generation_credits", "amount": 50 }
  }
]
```

**Plus SKU benefits：**
```json
[
  {
    "benefitType": "membership",
    "benefitValue": "plus",
    "benefitJson": { "durationDays": 365, "tier": "plus", "sceneAccess": "all_public" }
  },
  {
    "benefitType": "credits",
    "benefitValue": "scene_generation_credits",
    "benefitJson": { "creditType": "scene_generation_credits", "amount": 150 }
  },
  {
    "benefitType": "feature",
    "benefitValue": "video_export",
    "benefitJson": { "retentionHours": 3 }
  }
]
```

**Max SKU benefits：**
```json
[
  {
    "benefitType": "membership",
    "benefitValue": "max",
    "benefitJson": { "durationDays": 365, "tier": "max", "sceneAccess": "all_public", "priorityQueue": true }
  },
  {
    "benefitType": "credits",
    "benefitValue": "scene_generation_credits",
    "benefitJson": { "creditType": "scene_generation_credits", "amount": 500 }
  },
  {
    "benefitType": "feature",
    "benefitValue": "video_export",
    "benefitJson": { "retentionHours": 3 }
  },
  {
    "benefitType": "feature",
    "benefitValue": "priority_queue",
    "benefitJson": {}
  }
]
```

---

## 7 个免费场景

免费场景 ID 列表通过环境变量 `FREE_SCENE_IDS` 配置（逗号分隔），默认值：

```
FREE_SCENE_IDS=scene_breakfast,scene_zoo
```

随着公开场景增加，后台可随时调整此列表扩充到 7 个。无需代码变更。

---

## 前端展示建议

### 产品页布局

```
┌────────────────────────────────────┐
│  当前状态：会员/积分余额           │
├────────────────────────────────────┤
│  ┌──────────┐                      │
│  │ 体验卡   │  ¥39.9              │
│  │ 50积分   │  全部公开场景        │
│  │          │  [购买]              │
│  └──────────┘                      │
│  ┌──────────┐                      │
│  │ 创作卡   │  ¥99  ← 推荐       │
│  │ 150积分  │  全部场景 + 视频导出 │
│  │          │  [购买]              │
│  └──────────┘                      │
│  ┌──────────┐                      │
│  │ 大师卡   │  ¥199               │
│  │ 500积分  │  全部场景 + 视频 + 优先│
│  │          │  [购买]              │
│  └──────────┘                      │
├────────────────────────────────────┤
│  权益对比表                        │
└────────────────────────────────────┘
```

### 状态提示

| 场景 | 提示 |
|------|------|
| 免费用户访问付费场景 | "升级会员解锁全部场景" |
| 积分不足时生成场景 | "积分不足，购买套餐获取更多积分" |
| 积分冻结状态 | "会员已过期，积分已冻结，请续费解锁" |
| 视频导出无权限 | "升级 Plus 或 Max 解锁视频导出功能" |

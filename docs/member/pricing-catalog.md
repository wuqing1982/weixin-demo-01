# 产品目录与定价方案

> 种子数据（seed_demo_catalog）扩展方案

## 完整产品目录

### 产品 1：基础会员

```python
product = {
    'id': 'product_membership_basic',
    'productCode': 'membership_basic',
    'productType': 'membership',
    'name': '基础会员',
    'subtitle': '无限场景学习，开启英语全景之旅',
    'description': '解锁全部公开场景的无限学习权限，每月赠送 5 次场景生成点数。',
    'status': 'active',
    'sortOrder': 10,
}
```

**SKU 列表：**

| SKU ID | 名称 | 周期 | 原价 | 售价 | 排序 |
|--------|------|------|------|------|------|
| `sku_basic_monthly` | 月卡 | 30 天 | ¥39.00 | ¥19.90 | 10 |
| `sku_basic_annual` | 年卡 | 365 天 | ¥238.80 | ¥128.00 | 20 |

**月卡 benefits：**
```json
[{
    "benefitType": "membership",
    "benefitValue": "membership_basic",
    "benefitJson": {
        "durationDays": 30,
        "tier": "basic",
        "monthlyCredits": 5,
        "sceneAccess": "all_public",
        "ttsVoices": ["standard", "enhanced_female", "enhanced_male"],
        "maxFavorites": 10,
        "maxPrivateScenes": 20,
        "historyDays": 30,
        "priorityQueue": false
    }
}]
```

**年卡 benefits：**
```json
[{
    "benefitType": "membership",
    "benefitValue": "membership_basic",
    "benefitJson": {
        "durationDays": 365,
        "tier": "basic",
        "monthlyCredits": 5,
        "sceneAccess": "all_public",
        "ttsVoices": ["standard", "enhanced_female", "enhanced_male"],
        "maxFavorites": 10,
        "maxPrivateScenes": 20,
        "historyDays": 30,
        "priorityQueue": false
    }
}]
```

---

### 产品 2：高级会员

```python
product = {
    'id': 'product_membership_pro',
    'productCode': 'membership_pro',
    'productType': 'membership',
    'name': '高级会员',
    'subtitle': '全功能解锁，创作与学习无界限',
    'description': '包含基础会员全部权益，外加每月 20 次生成点数、全部 TTS 音色、永久学习记录、优先生成队列。',
    'status': 'active',
    'sortOrder': 20,
}
```

**SKU 列表：**

| SKU ID | 名称 | 周期 | 原价 | 售价 | 排序 |
|--------|------|------|------|------|------|
| `sku_pro_monthly` | 月卡 | 30 天 | ¥69.00 | ¥39.90 | 10 |
| `sku_pro_annual` | 年卡 | 365 天 | ¥478.80 | ¥258.00 | 20 |

**月卡 benefits：**
```json
[{
    "benefitType": "membership",
    "benefitValue": "membership_pro",
    "benefitJson": {
        "durationDays": 30,
        "tier": "pro",
        "monthlyCredits": 20,
        "sceneAccess": "all_public",
        "ttsVoices": ["standard", "enhanced_female", "enhanced_male", "premium_child", "premium_narrator"],
        "maxFavorites": -1,
        "maxPrivateScenes": -1,
        "historyDays": -1,
        "priorityQueue": true
    }
}]
```

**年卡 benefits（附赠 50 次点数）：**
```json
[
    {
        "benefitType": "membership",
        "benefitValue": "membership_pro",
        "benefitJson": {
            "durationDays": 365,
            "tier": "pro",
            "monthlyCredits": 20,
            "sceneAccess": "all_public",
            "ttsVoices": ["standard", "enhanced_female", "enhanced_male", "premium_child", "premium_narrator"],
            "maxFavorites": -1,
            "maxPrivateScenes": -1,
            "historyDays": -1,
            "priorityQueue": true
        }
    },
    {
        "benefitType": "credits",
        "benefitValue": "scene_generation_credits",
        "benefitJson": {
            "creditType": "scene_generation_credits",
            "amount": 50
        }
    }
]
```

> 年卡附赠 50 次点数是标准搭赠策略，提升年卡吸引力。

---

### 产品 3：场景生成点数包

```python
product = {
    'id': 'product_credit_scene',
    'productCode': 'credit_scene',
    'productType': 'credit_pack',
    'name': '场景生成点数',
    'subtitle': '按需购买，灵活创作',
    'description': '用于 AI 场景生成的虚拟点数，永不过期。',
    'status': 'active',
    'sortOrder': 30,
}
```

**SKU 列表：**

| SKU ID | 名称 | 次数 | 原价 | 售价 | 单价 | 排序 |
|--------|------|------|------|------|------|------|
| `sku_credit_5` | 体验包 | 5 | ¥9.90 | ¥4.90 | ¥0.98 | 10 |
| `sku_credit_20` | 标准包 | 20 | ¥29.90 | ¥9.90 | ¥0.50 | 20 |
| `sku_credit_50` | 超值包 | 50 | ¥49.90 | ¥19.90 | ¥0.40 | 30 |
| `sku_credit_100` | 大师包 | 100 | ¥99.90 | ¥29.90 | ¥0.30 | 40 |

**各 SKU benefits 格式统一：**
```json
[{
    "benefitType": "credits",
    "benefitValue": "scene_generation_credits",
    "benefitJson": {
        "creditType": "scene_generation_credits",
        "amount": <对应次数>
    }
}]
```

---

## 前端展示建议

### 产品页布局

```
┌──────────────────────────────────┐
│  当前会员状态（层级/到期日/点数） │
├──────────────────────────────────┤
│  ┌──────┐  ┌──────┐             │
│  │基础月卡│  │基础年卡│ ← 基础   │
│  │¥19.90 │  │¥128  │             │
│  │/月    │  │/年   │             │
│  └──────┘  └──────┘             │
│  ┌──────┐  ┌──────┐             │
│  │高级月卡│  │高级年卡│ ← 高级   │
│  │¥39.90 │  │¥258  │  推荐 ✓    │
│  │/月    │  │/年   │             │
│  └──────┘  └──────┘             │
├──────────────────────────────────┤
│  点数包                          │
│  [5次¥4.90] [20次¥9.90]          │
│  [50次¥19.90] [100次¥29.90]      │
├──────────────────────────────────┤
│  权益对比表                      │
│  功能      │免费│基础│高级│       │
│  每日学习   │ 3  │无限│无限│      │
│  月赠点数   │ 0  │ 5  │ 20 │     │
│  ...       │    │    │    │      │
└──────────────────────────────────┘
```

### 价格展示技巧

- 高级年卡标记 **"推荐"** 或 **"最受欢迎"**
- 显示年付节省金额，如 "年卡省 ¥220.80"
- 原价划线 + 现价突出
- 点数包显示单价对比，突出量大优惠

---

## 数据库种子脚本更新

需要更新的文件：
- `backend/scripts/seed_demo_catalog.py` — 按 Phase 2 完整产品目录重写

Phase 1 保持现有种子数据不变（基础月卡 + 20 次点数包），仅更新 benefit_json 结构加入 `tier` 字段。

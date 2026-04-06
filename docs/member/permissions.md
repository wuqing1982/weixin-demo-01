# 权限矩阵

> 会员层级对应的详细功能权限对照表

## 场景访问权限

| 功能 | 免费 | 基础会员 | 高级会员 | 判断逻辑 |
|------|------|----------|----------|----------|
| 浏览公开场景列表 | ✅ | ✅ | ✅ | 所有用户可见 |
| 每日可学习场景数 | 3 个/天 | 无限 | 无限 | `entitlement_code` + 每日计数 |
| 查看场景详情（全景 + 热点） | ✅（受限） | ✅ | ✅ | 同上 |
| 查看私有场景（自己创建的） | ✅ | ✅ | ✅ | `ownerId == userId` |
| 查看私有场景（他人创建的） | ❌ | ❌ | ❌ | 始终禁止 |

## TTS 语音权限

| 功能 | 免费 | 基础会员 | 高级会员 | 判断逻辑 |
|------|------|----------|----------|----------|
| 标准音色 | ✅ | ✅ | ✅ | 默认可用 |
| 高级音色（增强女声/男声） | ❌ | ✅（2 种） | ✅（全部） | `ttsVoices` 列表 |
| 精品音色（童声/特色） | ❌ | ❌ | ✅ | `tier == 'pro'` |
| 语速调节 | ❌ | ✅ | ✅ | `tier != 'free'` |

## 场景生成权限

| 功能 | 免费 | 基础会员 | 高级会员 | 判断逻辑 |
|------|------|----------|----------|----------|
| 注册赠送点数 | 1 次 | — | — | 注册时自动发放 |
| 每月赠送点数 | — | 5 次 | 20 次 | `monthlyCredits` 按月发放 |
| 购买点数包 | ✅ | ✅ | ✅ | 所有人可购买 |
| 单次生成消耗 | 1 点 | 1 点 | 1 点 | 统一消耗 |
| 生成队列优先级 | 普通 | 普通 | 优先 | `tier == 'pro'` |
| 点数过期规则 | 永不过期 | 月赠月末清零，购买永不过期 | 同左 | `credit_source` 区分 |

## 热点交互权限

| 功能 | 免费 | 基础会员 | 高级会员 | 判断逻辑 |
|------|------|----------|----------|----------|
| 点击热点查看单词/句子 | ✅ | ✅ | ✅ | 学习功能始终开放 |
| 编辑自己场景的热点 | ❌ | ✅ | ✅ | `tier != 'free'` |
| 编辑公开场景热点 | ❌ | ❌ | ✅（需权限） | `tier == 'pro'` + admin 配置 |
| 添加/删除热点 | ❌ | ✅（自己的） | ✅ | 同编辑权限 |

## 个人数据权限

| 功能 | 免费 | 基础会员 | 高级会员 | 判断逻辑 |
|------|------|----------|----------|----------|
| 学习记录保留 | 不保留 | 30 天 | 永久 | `historyDays` 配置 |
| 场景收藏数量 | 0 | 10 个 | 无限 | `maxFavorites` 配置 |
| 单词本功能 | ❌ | ✅ | ✅ | `tier != 'free'` |
| 单词本导出 | ❌ | ❌ | ✅ | `tier == 'pro'` |
| 学习统计报告 | ❌ | ❌ | ✅ | `tier == 'pro'` |
| 个人场景数量上限 | 5 个 | 20 个 | 无限 | `maxPrivateScenes` 配置 |

---

## 权限检查伪代码

### 场景学习次数检查

```python
def can_learn_scene(user_id: str, date: str) -> tuple[bool, int]:
    """返回 (是否允许, 剩余次数)"""
    membership = get_active_membership(user_id)

    if membership and membership['tier'] in ('basic', 'pro'):
        return True, -1  # 无限

    # 免费用户：检查每日计数
    daily_count = get_daily_scene_view_count(user_id, date)
    remaining = max(0, FREE_DAILY_LIMIT - daily_count)
    return remaining > 0, remaining
```

### 场景生成点数检查

```python
def can_generate_scene(user_id: str) -> tuple[bool, int]:
    """返回 (是否允许, 剩余点数)"""
    balance = get_credit_balance(user_id, 'scene_generation_credits')
    return balance > 0, balance

def consume_generation_credit(user_id: str, task_id: str):
    """生成成功后扣减点数"""
    deduct_credit(
        user_id=user_id,
        credit_type='scene_generation_credits',
        amount=1,
        reason_type='scene_generation',
        reason_id=task_id
    )
```

### 会员层级判断

```python
def get_effective_tier(user_id: str) -> str:
    """获取用户当前有效会员层级"""
    entitlements = get_active_entitlements(
        user_id=user_id,
        entitlement_type='membership',
        status='active'
    )
    if not entitlements:
        return 'free'

    # 如果有多个会员权益（如升级场景），取最高层级
    tier_priority = {'pro': 2, 'basic': 1, 'free': 0}
    best = 'free'
    for e in entitlements:
        tier = e.get('payload_json', {}).get('tier', 'free')
        if tier_priority.get(tier, 0) > tier_priority.get(best, 0):
            best = tier
    return best
```

---

## 现有系统映射

### benefit_json 字段扩展

当前种子数据中的 benefit_json：
```json
{"durationDays": 30, "sceneAccess": "public"}
```

扩展为：
```json
{
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
```

高级会员 benefit_json：
```json
{
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
```

> `-1` 表示无限制。

### entitlement_code 命名规范

| entitlement_code | 含义 |
|------------------|------|
| `membership_basic` | 基础会员权益 |
| `membership_pro` | 高级会员权益 |
| `scene_generation_credits` | 场景生成点数（通过 credit_accounts 管理） |

### 免费用户默认值

无需在 user_entitlements 表中创建记录，权限检查时无记录即视为 `free` 层级。注册赠送的 1 次点数通过 `grant_credits` 写入 `user_credit_accounts`。

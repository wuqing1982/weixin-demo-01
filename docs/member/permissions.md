# 权限矩阵

> 会员套餐对应的功能权限对照表

## 功能权限总览

| 功能 | 免费 | Pro ¥39.9 | Plus ¥99 | Max ¥199 |
|------|------|-----------|----------|----------|
| 访问免费场景（7个） | ✅ | ✅ | ✅ | ✅ |
| 访问全部公开场景 | ❌ | ✅ | ✅ | ✅ |
| 场景生成（消耗积分） | ❌ | ✅ | ✅ | ✅ |
| 积分余额 | 0 | 50 | 150 | 500 |
| 导出视频 | ❌ | ❌ | ✅（3小时） | ✅（3小时） |
| 编辑自己场景热点 | ❌ | ✅ | ✅ | ✅ |
| 编辑公开场景热点 | ❌ | ❌ | ❌ | ✅ |
| 优先生成队列 | ❌ | ❌ | ❌ | ✅ |

---

## 场景访问权限

### 检查逻辑

```python
def check_scene_access(scene_id, user_id, commerce_store, free_scene_ids):
    # 1. 免费场景 -> 所有人可访问
    if scene_id in free_scene_ids:
        return True

    # 2. 未配置商业系统 -> 放行
    if not commerce_store:
        return True

    # 3. 自己的私有场景 -> 可访问
    # (在调用前已通过 ownerId 检查)

    # 4. 检查会员状态
    membership = commerce_store.get_membership_summary(user_id)
    if membership.get('isActive'):
        return True

    # 5. 非会员 -> 拒绝
    raise HTTPException(403, "此场景需要付费会员")
```

### 场景列表过滤

```python
# GET /api/scenes 场景列表
if not membership.get('isActive'):
    # 免费用户只看到免费场景
    scenes = [s for s in scenes if s['sceneId'] in free_scene_ids]
```

---

## 积分消耗权限

### 检查逻辑

```python
def check_and_deduct_credit(user_id, commerce_store):
    # 1. 未配置商业系统 -> 放行
    if not commerce_store:
        return

    # 2. 检查会员是否活跃
    membership = commerce_store.get_membership_summary(user_id)
    if not membership.get('isActive'):
        raise HTTPException(403, "会员已过期，积分已冻结")

    # 3. 检查积分余额
    balance = commerce_store.get_credit_balance(user_id, 'scene_generation_credits')
    if balance <= 0:
        raise HTTPException(403, "积分不足，请购买套餐")

    # 4. 扣减积分
    commerce_store.deduct_credit(
        user_id=user_id,
        credit_type='scene_generation_credits',
        amount=1,
        reason_type='scene_generate'
    )
```

### 积分冻结流程

```
正常状态：
  会员活跃 → 积分可用 → 生成场景 → 扣减积分 → 余额减少

冻结状态：
  会员到期 → 积分冻结 → 尝试生成 → 被拒绝（"会员已过期"）

解冻流程：
  再次购买 → 会员激活 → 原积分解冻 + 新积分叠加 → 正常使用
```

---

## 视频导出权限

### 检查逻辑

```python
def check_video_export_permission(user_id, commerce_store):
    if not commerce_store:
        return

    # 查询用户是否有 video_export feature 权益
    entitlements = commerce_store.list_user_entitlements(
        user_id=user_id,
        entitlement_type='feature',
        entitlement_code='video_export',
        status='active'
    )
    if not entitlements:
        raise HTTPException(403, "视频导出需要 Plus 或 Max 会员")
```

### 视频保留策略

- 创作卡/大师卡导出的视频保留 **3 小时**
- 后台线程每 5 分钟扫描一次，删除超过 3 小时的视频文件
- 过期视频在列表中显示 `isExpired: true`，前端展示"已过期"

---

## 权限检查调用点

| API 路由 | 检查类型 | 检查位置 |
|----------|----------|----------|
| `GET /api/scenes` | 场景列表过滤 | 列表返回前过滤 |
| `GET /api/scenes/{id}` | 场景访问检查 | 返回场景详情前 |
| `POST /api/my/tasks/scene-generate` | 积分扣减 | 创建任务前 |
| `POST /api/scenes/{id}/export-video` | 视频导出权限 | 启动导出前 |
| `GET /api/me/video-exports` | 过期标记 | 返回列表时 |

---

## entitlement_code 命名规范

| entitlement_code | 类型 | 含义 |
|------------------|------|------|
| `pro` | membership | Pro 会员 |
| `plus` | membership | Plus 会员 |
| `max` | membership | Max 会员 |
| `video_export` | feature | 视频导出功能 |
| `priority_queue` | feature | 优先生成队列 |
| `scene_generation_credits` | credits | 场景生成积分（通过 credit_accounts 管理） |

---

## 免费场景管理

免费场景 ID 通过环境变量配置：

```bash
# backend/.env
FREE_SCENE_IDS=scene_breakfast,scene_zoo,scene_20260405212610_c2829a
```

后台调整此值即可增减免费场景数量，无需修改代码或数据库。

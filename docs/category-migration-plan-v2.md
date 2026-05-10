# 场景分类迁移方案：8 类 → 6 类（方案 A）

## 1. 背景

现有 8 个分类混合了"地点"和"主题"两个分类轴，导致交叉和不 MECE 的问题。
方案 A 采用单一「场所」轴，6 个分类覆盖儿童 3-8 岁可接触的全部场景。

## 2. 新旧分类对照表

### 新分类定义

| 新 ID | 新 code | 新名称 | sort_order |
|-------|---------|--------|------------|
| `cat_home` | home | 居家生活 | 1 |
| `cat_school` | school | 校园学习 | 2 |
| `cat_city` | city | 城市社区 | 3 |
| `cat_nature` | nature | 自然探索 | 4 |
| `cat_transport` | transport | 交通出行 | 5 |
| `cat_sports` | sports | 运动娱乐 | 6 |

### 新 ← 旧映射规则

以「场景发生的地点」为判定标准，逐场景人工审核：

| 旧分类 | 旧场景 | 迁移到新分类 | 判定依据 |
|--------|--------|-------------|---------|
| 饮食 (food) | 厨房 | **居家生活** | 家庭厨房 |
| 饮食 (food) | 餐桌 | **居家生活** | 家中餐桌 |
| 饮食 (food) | 咖啡店 ×5 | **城市社区** | 城市商业场所 |
| 饮食 (food) | 面包店 ×3 | **城市社区** | 城市商业场所 |
| 饮食 (food) | 无分类-超市中的蔬菜区 | **城市社区** | 超市属于城市商业 |
| 饮食 (food) | 无分类-营养早餐 | **居家生活** | 早餐场景默认居家 |
| 自然户外 (nature) | 山湖风景 | **自然探索** | 自然环境 |
| 自然户外 (nature) | 河边野餐 | **自然探索** | 自然环境 |
| 自然户外 (nature) | 海滨步道 | **自然探索** | 自然环境 |
| 自然户外 (nature) | 海滩 | **自然探索** | 自然环境 |
| 自然户外 (nature) | 露台 | **居家生活** | 家庭露台 |
| 自然户外 (nature) | 咖啡店 | **城市社区** | 实际是商业咖啡店 |
| 动物/动物世界 | 动物园 ×3 | **自然探索** | 动物园归入自然探索 |
| 动物/动物世界 | 农场 | **自然探索** | 农场归入自然探索 |
| 动物/动物世界 | 办公室 | **城市社区** | 办公场所（旧分类有误） |
| 交通出行 (transport) | 全部 7 个 | **交通出行** | 不变 |
| 校园学习 (school) | 图书馆 | **校园学习** | 不变 |
| 校园学习 (school) | 运动场 | **运动娱乐** | 校园运动场→运动类 |
| 家庭生活 (home) | 0 场景 | N/A | 空分类，不迁移 |
| 社区职业 (community) | 0 场景 | N/A | 空分类，不迁移 |
| 运动娱乐 (sports) | 0 场景 | N/A | 空分类，不迁移 |

## 3. 迁移后预期分布

| 新分类 | 场景数 | 来源 |
|--------|--------|------|
| 居家生活 | 4 | 厨房、餐桌、露台、营养早餐 |
| 校园学习 | 1 | 图书馆 |
| 城市社区 | 9 | 咖啡店×5、面包店×3（含1个cat=自然户外）、办公室、超市 |
| 自然探索 | 7 | 山湖、河边、海滨、海滩、动物园×3、农场 |
| 交通出行 | 7 | 不变 |
| 运动娱乐 | 1 | 运动场 |
| **合计** | **29** | 另有4个需确认（见下文） |

## 4. 需人工确认的场景

| scene_id | title | 旧分类 | 建议新分类 | 说明 |
|----------|-------|--------|-----------|------|
| `scene_20260422111418_79d0ae` | 咖啡店 | 自然户外 | 城市社区 | 旧分类明显有误 |
| `scene_20260405212610_c2829a` | 办公室 | 动物 | 城市社区 | 旧分类明显有误 |
| `scene_zoo` | 动物园 | 动物世界 | 自然探索 | 无 catId，需补 |
| `scene_breakfast` | 营养早餐 | 饮食 | 居家生活 | 无 catId，需补 |

## 5. 执行步骤

### Phase 1：创建新分类（不影响现有数据）

```sql
INSERT INTO scene_categories (id, category_code, name, status, sort_order) VALUES
  ('cat_home',      'home',      '居家生活', 'active', 1),
  ('cat_school',    'school',    '校园学习', 'active', 2),
  ('cat_city',      'city',      '城市社区', 'active', 3),
  ('cat_nature',    'nature',    '自然探索', 'active', 4),
  ('cat_transport', 'transport', '交通出行', 'active', 5),
  ('cat_sports',    'sports',    '运动娱乐', 'active', 6);
```

### Phase 2：迁移场景的 categoryId

```sql
-- 饮食 → 城市社区（咖啡店、面包店）
UPDATE scenes SET meta_json = jsonb_set(meta_json, '{categoryId}', '"cat_city"')
WHERE scene_type = 'public'
  AND meta_json->>'categoryId' = 'scene_category_food'
  AND title IN ('咖啡店','面包店');

-- 饮食 → 居家生活（厨房、餐桌）
UPDATE scenes SET meta_json = jsonb_set(meta_json, '{categoryId}', '"cat_home"')
WHERE scene_type = 'public'
  AND meta_json->>'categoryId' = 'scene_category_food'
  AND title IN ('厨房','餐桌');

-- 自然户外 → 自然探索
UPDATE scenes SET meta_json = jsonb_set(meta_json, '{categoryId}', '"cat_nature"')
WHERE scene_type = 'public'
  AND meta_json->>'categoryId' = 'scene_category_nature'
  AND title NOT IN ('露台','咖啡店');

-- 自然户外 → 居家生活（露台）
UPDATE scenes SET meta_json = jsonb_set(meta_json, '{categoryId}', '"cat_home"')
WHERE scene_type = 'public'
  AND meta_json->>'categoryId' = 'scene_category_nature'
  AND title = '露台';

-- 动物/动物世界 → 自然探索
UPDATE scenes SET meta_json = jsonb_set(
    COALESCE(meta_json, '{}'::jsonb), '{categoryId}', '"cat_nature"')
WHERE scene_type = 'public'
  AND meta_json->>'categoryId' IN ('scene_category_animals','scene_category_001')
  AND title IN ('动物园','农场');

-- 动物 → 城市社区（办公室 - 旧分类有误）
UPDATE scenes SET meta_json = jsonb_set(
    COALESCE(meta_json, '{}'::jsonb), '{categoryId}', '"cat_city"')
WHERE scene_type = 'public'
  AND scene_id = 'scene_20260405212610_c2829a';

-- 交通出行 → 交通出行（仅改 ID）
UPDATE scenes SET meta_json = jsonb_set(meta_json, '{categoryId}', '"cat_transport"')
WHERE scene_type = 'public'
  AND meta_json->>'categoryId' = 'scene_category_transport';

-- 校园学习 → 校园学习（仅改 ID）
UPDATE scenes SET meta_json = jsonb_set(meta_json, '{categoryId}', '"cat_school"')
WHERE scene_type = 'public'
  AND meta_json->>'categoryId' = 'scene_category_school'
  AND title = '图书馆';

-- 校园学习 → 运动娱乐（运动场）
UPDATE scenes SET meta_json = jsonb_set(meta_json, '{categoryId}', '"cat_sports"')
WHERE scene_type = 'public'
  AND meta_json->>'categoryId' = 'scene_category_school'
  AND title = '运动场';

-- 无分类的场景补充分类
UPDATE scenes SET meta_json = jsonb_set(
    COALESCE(meta_json, '{}'::jsonb), '{categoryId}', '"cat_nature"')
WHERE scene_id = 'scene_zoo';

UPDATE scenes SET meta_json = jsonb_set(
    COALESCE(meta_json, '{}'::jsonb), '{categoryId}', '"cat_home"')
WHERE scene_id = 'scene_breakfast';

UPDATE scenes SET meta_json = jsonb_set(
    COALESCE(meta_json, '{}'::jsonb), '{categoryId}', '"cat_city"')
WHERE scene_id = 'scene_6452f0ce-4b79-4933-8c1e-32feb5b62417';
```

### Phase 3：同步 publication 表

```sql
UPDATE scene_publications sp
SET category_id = s.meta_json->>'categoryId'
FROM scenes s
WHERE sp.public_scene_id = s.scene_id
  AND s.scene_type = 'public';
```

### Phase 4：验证

```sql
-- 检查是否还有指向旧分类的场景
SELECT count(*) FROM scenes
WHERE meta_json->>'categoryId' LIKE 'scene_category_%'
  AND meta_json->>'categoryId' NOT LIKE 'cat_%';

-- 检查新分类分布
SELECT meta_json->>'categoryId' as new_cat, count(*)
FROM scenes WHERE scene_type = 'public'
GROUP BY 1 ORDER BY 1;

-- 检查 publication 是否同步
SELECT sp.category_id, count(*)
FROM scene_publications sp
GROUP BY 1 ORDER BY 1;
```

### Phase 5：确认无误后，清理旧分类

```sql
-- 旧分类设为 inactive（先不删，观察一段时间）
UPDATE scene_categories SET status = 'inactive'
WHERE id LIKE 'scene_category_%';
```

## 6. 前端/后端影响

### 需要同步更新的地方

| 位置 | 改动 |
|------|------|
| 小程序 `library` 页面 | 分类筛选使用新 ID，显示新名称 |
| Admin 后台分类管理 | 新分类可管理，旧分类 inactive |
| Scene worker prompt | `recommendedCategory` 的映射表更新 |
| Admin 批量分类 | 使用新分类 ID |

### 场景生成 prompt 调整

当前 prompt 输出 `recommendedCategory` 自由文本，需要在 prompt 中明确指定 6 个可选值：

```
recommended_category 只能是以下之一：
home, school, city, nature, transport, sports
```

## 7. 回滚方案

如果迁移后发现问题：

```sql
-- 所有改动都有旧 categoryId 在 publication 表中可追溯
-- 或从备份恢复
```

建议在执行前备份数据库：

```bash
su - postgres -c "/www/server/pgsql/bin/pg_dump weixin_saas_rust" > backup_before_category_migration.sql
```

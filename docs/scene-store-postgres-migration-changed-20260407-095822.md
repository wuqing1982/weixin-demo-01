# Scene 存储迁移：JSON 文件 -> PostgreSQL

> 文档版本：2026-04-07 09:58
> 变更范围：Scene 模块存储层
> 影响文件：2 个修改 + 6 个新建
> 向后兼容：是（通过 `SCENE_STORE_BACKEND` 环境变量切换）

---

## 一、背景

### 1.1 迁移前架构

Scene 模块是项目中最后一个仍使用 JSON 文件存储数据的模块。当前场景数据分布在两个 JSON 文件中：

| 文件 | 内容 | 记录数 | 文件大小 |
|------|------|--------|----------|
| `data/scenes.json` | 公开场景 | 5 条 | ~24KB |
| `data/generated_scenes.json` | 用户生成场景 | 17 条 | ~89KB |

对应的两个 Python 类：

- `app/scene_store.py` — `SceneStore`：管理公开场景，`list_scenes(scene_type)` 按 `sceneType` 过滤
- `app/generated_scene_store.py` — `GeneratedSceneStore`：管理用户场景，`list_scenes(owner_id)` 按 `meta.ownerId` 过滤

两个类均使用 `threading.Lock` + `read_json_file` / `write_json_file` 实现并发安全的全量读写。

### 1.2 已迁移模块

| 模块 | 存储后端 | 环境变量 | 迁移时间 |
|------|----------|----------|----------|
| Auth | PostgreSQL | `AUTH_STORE_BACKEND` | 2026-04 |
| Commerce | PostgreSQL | `COMMERCE_STORE_BACKEND` | 2026-04 |
| **Scene** | **PostgreSQL（本次）** | `SCENE_STORE_BACKEND` | 2026-04-07 |

---

## 二、迁移动机

### 2.1 JSON 文件的局限

| 问题 | 说明 |
|------|------|
| **全量读写** | 每次操作（读/写一条记录）都要序列化/反序列化整个文件 |
| **并发瓶颈** | `threading.Lock` 串行化所有操作（包括读操作），高并发下性能退化 |
| **查询能力弱** | 无法按字段索引、过滤、排序，排序必须在 Python 内存中完成 |
| **无事务** | 发布流程涉及 generated_store -> public_store -> commerce_store，无法保证跨 store 一致性 |
| **扩展性差** | 数据量增长后性能线性下降 |

### 2.2 PostgreSQL 的优势

| 优势 | 说明 |
|------|------|
| **行级锁** | 并发读写互不阻塞 |
| **索引查询** | `owner_id`、`scene_type`、`category` 等字段走索引 |
| **原生排序** | `ORDER BY created_at DESC` 替代 Python 内存排序 |
| **事务保证** | 发布流程可在单个事务中完成 |
| **架构统一** | 与 Auth、Commerce 模块保持一致 |
| **可扩展** | 数据量从几十到几万无性能变化 |

---

## 三、设计决策

### 3.1 单表存储所有场景

公开场景和用户生成场景的数据结构完全一致（sceneId, title, category, items, verbs, meta...），仅 `scene_type` 和 `owner_id` 不同。采用单表 + 索引方案区分，避免不必要的表拆分。

### 3.2 `items` 和 `verbs` 使用 jsonb 列

这两个字段始终作为整体读写，从不单独查询某一条 item 或 verb。jsonb 避免了拆分出子表的额外开销。

### 3.3 `meta` 使用 jsonb 列

`meta` 字段在不同场景间差异大（ownerId, uploadId, publishedAt, tags 等），jsonb 灵活存储，同时支持未来用 `jsonb` 操作符按需查询。

### 3.4 提取 `owner_id` 为独立列

`GeneratedSceneStore.list_scenes(owner_id)` 是高频查询（"我的生成场景"页面），独立列 + 索引优于 jsonb 查询。

### 3.5 保持相同的 Python 接口

四个核心方法签名不变：`list_scenes`、`get_scene`、`upsert_scene`、`update_hotspots`。`main.py` 中的 25+ 调用点无需修改。

### 3.6 工厂模式选择后端

新增 `SCENE_STORE_BACKEND` 环境变量，与 `AUTH_STORE_BACKEND` 模式一致。JSON 和 PG 模式可随时切换，实现零停机回滚。

---

## 四、数据库 Schema

```sql
CREATE TABLE IF NOT EXISTS scenes (
  scene_id       varchar(128) PRIMARY KEY,
  title          varchar(255) NOT NULL DEFAULT '',
  category       varchar(64)  NOT NULL DEFAULT '',
  visibility     varchar(32)  NOT NULL DEFAULT 'public',
  scene_type     varchar(32)  NOT NULL DEFAULT 'public',
  cover_path     text         NOT NULL DEFAULT '',
  background_path text        NOT NULL DEFAULT '',
  items          jsonb        NOT NULL DEFAULT '[]'::jsonb,
  verbs          jsonb        NOT NULL DEFAULT '[]'::jsonb,
  meta_json      jsonb        NOT NULL DEFAULT '{}'::jsonb,
  owner_id       varchar(128),
  created_at     timestamptz  NOT NULL DEFAULT now(),
  updated_at     timestamptz  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_scenes_scene_type  ON scenes(scene_type);
CREATE INDEX IF NOT EXISTS idx_scenes_owner_id    ON scenes(owner_id) WHERE owner_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_scenes_category    ON scenes(category);
CREATE INDEX IF NOT EXISTS idx_scenes_created_at  ON scenes(created_at DESC);
```

### 字段映射关系

| JSON 场景字段 | PG 列名 | 类型 | 说明 |
|---------------|---------|------|------|
| `sceneId` | `scene_id` | varchar(128) PK | 场景唯一标识 |
| `title` | `title` | varchar(255) | 场景标题 |
| `category` | `category` | varchar(64) | 分类（food, animals, existing 等） |
| `visibility` | `visibility` | varchar(32) | 可见性（public, private, member） |
| `sceneType` | `scene_type` | varchar(32) | 场景类型（public, private） |
| `coverPath` | `cover_path` | text | 封面图路径 |
| `backgroundPath` | `background_path` | text | 背景图路径 |
| `items` | `items` | jsonb | 热点物品数组（含 word, ipa, meaning, sentence, rect 等） |
| `verbs` | `verbs` | jsonb | 动词数组 |
| `meta` | `meta_json` | jsonb | 元数据（ownerId, uploadId, version, tags 等） |
| `meta.ownerId` | `owner_id` | varchar(128) | 从 meta 提取的 owner_id，带索引 |
| — | `created_at` | timestamptz | 创建时间，PG 自动生成 |
| — | `updated_at` | timestamptz | 更新时间，PG 自动更新 |

### 索引说明

| 索引 | 用途 |
|------|------|
| `idx_scenes_scene_type` | 按场景类型过滤（公开/私有），替代 `SceneStore.list_scenes(scene_type)` |
| `idx_scenes_owner_id` | 按 owner 过滤（部分索引，仅非 NULL 行），替代 `GeneratedSceneStore.list_scenes(owner_id)` |
| `idx_scenes_category` | 按分类过滤（未来分类浏览页） |
| `idx_scenes_created_at` | 按创建时间降序排序，实现"最新优先" |

---

## 五、文件变更清单

### 5.1 新建文件

| 文件 | 行数 | 说明 |
|------|------|------|
| `app/scene_postgres_schema.py` | 27 | DDL 语句 + `ensure_scene_postgres_schema(connection)` 函数 |
| `app/scene_store_postgres.py` | 146 | `PostgresSceneStore` 核心类 |
| `app/scene_store_factory.py` | 30 | 工厂函数 `create_public_scene_store()` 和 `create_generated_scene_store()` |
| `scripts/migrate_scenes_to_postgres.py` | 42 | 数据迁移脚本 |
| `sql/scene_postgres_schema.sql` | 27 | SQL 参考文件 |
| `tests/test_scene_store_postgres.py` | 250 | 14 个单元测试 |

### 5.2 修改文件

| 文件 | 改动量 | 说明 |
|------|--------|------|
| `app/settings.py` | +1 行 | 新增 `SCENE_STORE_BACKEND` 配置 |
| `app/main.py` | ~4 行 | 替换 import 和实例化 |

### 5.3 未修改文件

| 文件 | 说明 |
|------|------|
| `app/scene_store.py` | JSON 模式仍需使用 |
| `app/generated_scene_store.py` | JSON 模式仍需使用 |
| `app/scene_adapter.py` | PG store 复用 `apply_hotspot_updates()` |
| `app/scene_publication.py` | 接口不变 |

---

## 六、代码详解

### 6.1 `app/scene_postgres_schema.py`

```python
SCENE_POSTGRES_SCHEMA_SQL = """
create table if not exists scenes (...);
create index if not exists idx_scenes_scene_type on scenes(scene_type);
create index if not exists idx_scenes_owner_id on scenes(owner_id) where owner_id is not null;
create index if not exists idx_scenes_category on scenes(category);
create index if not exists idx_scenes_created_at on scenes(created_at desc);
"""

def ensure_scene_postgres_schema(connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute(SCENE_POSTGRES_SCHEMA_SQL)
```

遵循 `auth_postgres_schema.py` 的模式：DDL 字符串 + `ensure_*` 函数。首次连接时自动建表建索引，幂等执行。

### 6.2 `app/scene_store_postgres.py`

#### 序列化层

```python
def _scene_to_row(scene: dict) -> dict:
    """Python dict -> PG row (jsonb 字段序列化为字符串)"""
    # 从 scene 和 meta 中提取字段
    # items/verbs/meta_json 序列化为 JSON 字符串
    # owner_id 从 meta.ownerId 提取

def _row_to_scene(row: dict | None) -> dict | None:
    """PG row (psycopg 自动解析 jsonb) -> Python dict"""
    # 反向映射：snake_case -> camelCase
    # jsonb 列已被 psycopg 自动解析为 Python 对象
```

#### 核心方法

**`list_scenes(filter_param)`** — 智能过滤分发：

| filter_param 值 | 过滤方式 | SQL |
|-----------------|----------|-----|
| `None` / 空字符串 | 无过滤，返回全部 | `SELECT * FROM scenes ORDER BY created_at DESC` |
| `'public'` / `'private'` / `'member'` | 按 scene_type | `WHERE scene_type = %s` |
| `'scene_*'` 开头 | 按 scene_type | `WHERE scene_type = %s` |
| 其他（如 `'user_abc123'`） | 按 owner_id | `WHERE owner_id = %s` |

**`get_scene(scene_id)`** — 主键查询：

```sql
SELECT * FROM scenes WHERE scene_id = %s LIMIT 1
```

**`upsert_scene(scene)`** — 插入或更新：

```sql
INSERT INTO scenes (...) VALUES (...)
ON CONFLICT (scene_id) DO UPDATE SET
  title = excluded.title,
  category = excluded.category,
  ...
RETURNING *
```

幂等操作，可重复执行（迁移脚本依赖此特性）。

**`update_hotspots(scene_id, items, operator_id)`** — 热点更新：

```sql
SELECT * FROM scenes WHERE scene_id = %s FOR UPDATE  -- 行级锁
```

在事务内读取 -> 调用 `apply_hotspot_updates()`（复用现有逻辑）-> 写回 items 和 meta_json。

### 6.3 `app/scene_store_factory.py`

```python
_pg_instance: PostgresSceneStore | None = None

def _get_pg_instance() -> PostgresSceneStore:
    """单例模式，public 和 generated 共享同一个 PG 实例"""
    global _pg_instance
    if _pg_instance is None:
        _pg_instance = PostgresSceneStore(DATABASE_URL, DATABASE_SCHEMA)
    return _pg_instance

def create_public_scene_store():
    if SCENE_STORE_BACKEND == 'postgres':
        return _get_pg_instance()   # 单表共享
    return SceneStore(PUBLIC_SCENES_FILE)

def create_generated_scene_store():
    if SCENE_STORE_BACKEND == 'postgres':
        return _get_pg_instance()   # 同一个实例
    return GeneratedSceneStore(GENERATED_SCENES_FILE)
```

关键设计：PG 模式下，public_store 和 generated_store 是**同一个对象**。这是因为单表存储所有场景，不需要两个独立的存储实例。`list_scenes` 的 filter_param 参数自动区分查询类型。

### 6.4 `app/main.py` 改动

```diff
- from .generated_scene_store import GeneratedSceneStore
+ from .generated_scene_store import GeneratedSceneStore
+ from .scene_store_factory import create_generated_scene_store, create_public_scene_store

- from .scene_store import SceneStore
  # （SceneStore 仍被保留，因为 factory 内部使用）

- public_store = SceneStore(PUBLIC_SCENES_FILE)
- generated_store = GeneratedSceneStore(GENERATED_SCENES_FILE)
+ public_store = create_public_scene_store()
+ generated_store = create_generated_scene_store()
```

其余 25+ 个调用点（`public_store.list_scenes()`、`generated_store.get_scene()` 等）**完全不变**，因为接口签名一致。

### 6.5 `app/settings.py` 改动

```diff
  COMMERCE_STORE_BACKEND = (os.getenv('COMMERCE_STORE_BACKEND', 'disabled') or 'disabled').strip().lower()
+ SCENE_STORE_BACKEND = (os.getenv('SCENE_STORE_BACKEND', 'json') or 'json').strip().lower()
```

默认值为 `'json'`，不影响现有部署。设置为 `'postgres'` 后切换到 PG 后端。

---

## 七、迁移脚本

### `scripts/migrate_scenes_to_postgres.py`

```bash
cd backend && python3 scripts/migrate_scenes_to_postgres.py
```

脚本行为：
1. 检查 `DATABASE_URL` 环境变量是否存在
2. 读取 `data/scenes.json`，逐条调用 `upsert_scene` 写入 PG
3. 读取 `data/generated_scenes.json`，逐条调用 `upsert_scene` 写入 PG
4. 打印迁移统计

**幂等性**：脚本使用 `ON CONFLICT DO UPDATE`，可重复运行。每次运行会覆盖 PG 中的数据为 JSON 文件的最新内容。

---

## 八、测试

### 8.1 测试文件

`tests/test_scene_store_postgres.py` — 14 个单元测试

### 8.2 测试覆盖

| 测试类 | 测试数 | 覆盖内容 |
|--------|--------|----------|
| `TestSceneToRow` | 3 | 公开场景序列化、生成场景序列化、缺失字段默认值 |
| `TestRowToScene` | 3 | None 输入、公开场景往返、生成场景完整往返 |
| `TestPostgresSceneStoreListScenesFilter` | 5 | 无过滤、按 scene_type 过滤、按 owner_id 过滤、scene_ 前缀值处理 |
| `TestPostgresSceneStoreGetScene` | 2 | 存在的场景、不存在的场景 |
| `TestPostgresSceneStoreUpsert` | 1 | upsert 返回正确结果 |

### 8.3 运行测试

```bash
cd backend && python3 -m pytest tests/test_scene_store_postgres.py -v
```

---

## 九、部署步骤

### 9.1 迁移流程（按顺序执行）

```
1. 部署代码
   └── SCENE_STORE_BACKEND=json（保持不变，JSON 模式继续工作）

2. 运行迁移脚本
   └── cd backend && python3 scripts/migrate_scenes_to_postgres.py

3. 验证 PG 数据
   └── 检查 scenes 表中的记录数是否与 JSON 文件一致
   └── 抽查几条记录的字段完整性

4. 切换后端
   └── 修改 .env: SCENE_STORE_BACKEND=postgres

5. 重启服务
   └── 服务启动时 PostgresSceneStore.__init__ 自动执行 ensure_schema

6. 功能验证
   └── 小程序端测试：浏览公开场景、查看"我的场景"、编辑热点
```

### 9.2 回滚方案

将 `.env` 改回 `SCENE_STORE_BACKEND=json` 并重启服务即可。JSON 文件在 PG 模式期间**不会被修改**（PG 后端完全不读写 JSON 文件）。

```
回滚步骤：
1. 修改 .env: SCENE_STORE_BACKEND=json
2. 重启服务
3. 服务恢复为 JSON 文件读写模式
```

### 9.3 注意事项

- 迁移脚本和 PG 后端都要求 `DATABASE_URL` 环境变量已配置
- 迁移脚本应只运行一次（幂等，但不要反复运行覆盖 PG 中更新的数据）
- 切换到 PG 后端前，确保迁移脚本输出与预期记录数一致
- 公开场景 5 条 + 生成场景 17 条 = 总计 22 条

---

## 十、依赖复用

| 已有模块 | 复用点 |
|----------|--------|
| `postgres.py` | `connect_postgres()` — 连接管理、schema 设置 |
| `scene_adapter.py` | `apply_hotspot_updates()` — 热点更新逻辑（PG store 直接复用） |
| `store_utils.py` | `utcnow_iso()` — 时间戳生成 |
| `auth_postgres_schema.py` | 代码风格和 DDL 组织方式作为参考 |
| `auth_store_postgres.py` | upsert 模式、连接管理、序列化层设计作为参考 |
| `auth_store_factory.py` | 工厂模式设计作为参考 |

---

## 十一、与 JSON 模式的接口对比

| 操作 | JSON 模式 (SceneStore) | JSON 模式 (GeneratedSceneStore) | PG 模式 (PostgresSceneStore) |
|------|----------------------|-------------------------------|------------------------------|
| 列出公开场景 | `list_scenes('public')` | — | `list_scenes('public')` |
| 列出用户场景 | — | `list_scenes(owner_id)` | `list_scenes(owner_id)` |
| 列出全部场景 | `list_scenes('')` | `list_scenes()` | `list_scenes()` |
| 获取单个场景 | `get_scene(id)` | `get_scene(id)` | `get_scene(id)` |
| 创建/更新场景 | `upsert_scene(scene)` | `upsert_scene(scene)` | `upsert_scene(scene)` |
| 更新热点 | `update_hotspots(id, items, operator_id=)` | `update_hotspots(id, items, operator_id=)` | `update_hotspots(id, items, operator_id=)` |

所有方法签名保持一致，`main.py` 的调用代码无需修改。

# 英语场景学习系统 SQL 初始化脚本与 Migration 草案

时间：2026-03-25 18:04:41  
作者：Codex

## 1. 文档目标

本文档用于为 MVP 阶段提供数据库初始化和迁移设计，目标是：

- 给出 MySQL 8 可执行的初始化 SQL 草案
- 说明各张表的关系与索引原则
- 给出第一批 migration 的拆分建议
- 给出初始化数据建议

上游文档：

- [`docs/english-scene-system-detailed-design-20260325-153922-by-codex.md`](E:\202603\weixin-demo\docs\english-scene-system-detailed-design-20260325-153922-by-codex.md)
- [`docs/english-scene-mvp-engineering-prep-20260325-175717-by-codex.md`](E:\202603\weixin-demo\docs\english-scene-mvp-engineering-prep-20260325-175717-by-codex.md)
- [`docs/english-scene-openapi-and-dto-20260325-180218-by-codex.md`](E:\202603\weixin-demo\docs\english-scene-openapi-and-dto-20260325-180218-by-codex.md)

---

## 2. 数据库选型建议

MVP 建议：

- MySQL 8
- `utf8mb4`
- `InnoDB`

原因：

- 与 Python/FastAPI/SQLAlchemy 生态兼容稳定
- JSON 字段可用
- 运维成本低

建议数据库名：

```sql
english_scene
```

---

## 3. 初始化 SQL

## 3.1 创建数据库

```sql
CREATE DATABASE IF NOT EXISTS english_scene
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE english_scene;
```

## 3.2 users

```sql
CREATE TABLE users (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  openid VARCHAR(64) NOT NULL UNIQUE,
  unionid VARCHAR(64) NULL,
  nickname VARCHAR(128) NOT NULL DEFAULT '',
  avatar_url VARCHAR(512) NOT NULL DEFAULT '',
  membership_status VARCHAR(32) NOT NULL DEFAULT 'free',
  membership_expire_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

## 3.3 scenes

```sql
CREATE TABLE scenes (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  scene_uuid VARCHAR(64) NOT NULL UNIQUE,
  scene_type VARCHAR(32) NOT NULL,
  owner_user_id BIGINT NULL,
  source_type VARCHAR(32) NOT NULL,
  title VARCHAR(255) NOT NULL,
  subtitle VARCHAR(255) NULL,
  cover_image_path VARCHAR(1024) NOT NULL,
  background_image_path VARCHAR(1024) NOT NULL,
  scene_json_path VARCHAR(1024) NOT NULL,
  visibility VARCHAR(32) NOT NULL,
  status VARCHAR(32) NOT NULL,
  category VARCHAR(64) NULL,
  tags_json JSON NULL,
  version INT NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_scenes_owner_user
    FOREIGN KEY (owner_user_id) REFERENCES users(id),
  INDEX idx_scenes_owner_user_id (owner_user_id),
  INDEX idx_scenes_scene_type (scene_type),
  INDEX idx_scenes_visibility (visibility),
  INDEX idx_scenes_status (status),
  INDEX idx_scenes_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

## 3.4 scene_items

```sql
CREATE TABLE scene_items (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  scene_id BIGINT NOT NULL,
  item_id VARCHAR(64) NOT NULL,
  word VARCHAR(128) NOT NULL,
  ipa VARCHAR(128) NOT NULL DEFAULT '',
  meaning VARCHAR(255) NOT NULL DEFAULT '',
  sentence TEXT NOT NULL,
  sentence_translation TEXT NOT NULL,
  rect_l DECIMAL(6,2) NOT NULL,
  rect_t DECIMAL(6,2) NOT NULL,
  rect_w DECIMAL(6,2) NOT NULL,
  rect_h DECIMAL(6,2) NOT NULL,
  audio_path VARCHAR(1024) NULL,
  sort_order INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_scene_items_scene
    FOREIGN KEY (scene_id) REFERENCES scenes(id) ON DELETE CASCADE,
  UNIQUE KEY uk_scene_items_scene_item (scene_id, item_id),
  INDEX idx_scene_items_scene_id (scene_id),
  INDEX idx_scene_items_sort_order (scene_id, sort_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

## 3.5 scene_verbs

```sql
CREATE TABLE scene_verbs (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  scene_id BIGINT NOT NULL,
  verb_id VARCHAR(64) NOT NULL,
  word VARCHAR(128) NOT NULL,
  ipa VARCHAR(128) NOT NULL DEFAULT '',
  meaning VARCHAR(255) NOT NULL DEFAULT '',
  sentence TEXT NOT NULL,
  sentence_translation TEXT NOT NULL,
  audio_path VARCHAR(1024) NULL,
  sort_order INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_scene_verbs_scene
    FOREIGN KEY (scene_id) REFERENCES scenes(id) ON DELETE CASCADE,
  UNIQUE KEY uk_scene_verbs_scene_verb (scene_id, verb_id),
  INDEX idx_scene_verbs_scene_id (scene_id),
  INDEX idx_scene_verbs_sort_order (scene_id, sort_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

## 3.6 scene_assets

```sql
CREATE TABLE scene_assets (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  scene_id BIGINT NOT NULL,
  asset_type VARCHAR(32) NOT NULL,
  asset_key VARCHAR(255) NOT NULL,
  local_path VARCHAR(1024) NOT NULL,
  public_url VARCHAR(1024) NULL,
  cdn_status VARCHAR(32) NOT NULL DEFAULT 'local_only',
  mime_type VARCHAR(128) NOT NULL DEFAULT '',
  file_size BIGINT NOT NULL DEFAULT 0,
  checksum VARCHAR(128) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_scene_assets_scene
    FOREIGN KEY (scene_id) REFERENCES scenes(id) ON DELETE CASCADE,
  INDEX idx_scene_assets_scene_id (scene_id),
  INDEX idx_scene_assets_asset_type (asset_type),
  INDEX idx_scene_assets_cdn_status (cdn_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

## 3.7 jobs

```sql
CREATE TABLE jobs (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  job_uuid VARCHAR(64) NOT NULL UNIQUE,
  job_type VARCHAR(32) NOT NULL,
  user_id BIGINT NULL,
  source_image_path VARCHAR(1024) NOT NULL,
  source_image_url VARCHAR(1024) NULL,
  scene_id BIGINT NULL,
  status VARCHAR(32) NOT NULL,
  progress INT NOT NULL DEFAULT 0,
  current_stage VARCHAR(64) NOT NULL DEFAULT 'queued',
  payload_json JSON NOT NULL,
  result_json JSON NULL,
  error_message TEXT NULL,
  retry_count INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  started_at DATETIME NULL,
  finished_at DATETIME NULL,
  CONSTRAINT fk_jobs_user
    FOREIGN KEY (user_id) REFERENCES users(id),
  CONSTRAINT fk_jobs_scene
    FOREIGN KEY (scene_id) REFERENCES scenes(id),
  INDEX idx_jobs_user_id (user_id),
  INDEX idx_jobs_status (status),
  INDEX idx_jobs_job_type (job_type),
  INDEX idx_jobs_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

## 3.8 memberships

```sql
CREATE TABLE memberships (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  membership_type VARCHAR(32) NOT NULL,
  status VARCHAR(32) NOT NULL,
  start_at DATETIME NOT NULL,
  expire_at DATETIME NOT NULL,
  source VARCHAR(32) NOT NULL DEFAULT 'manual',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_memberships_user
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_memberships_user_id (user_id),
  INDEX idx_memberships_status (status),
  INDEX idx_memberships_expire_at (expire_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## 4. 表关系说明

## 4.1 主关系

- `users` 1:N `scenes`
- `users` 1:N `jobs`
- `users` 1:N `memberships`
- `scenes` 1:N `scene_items`
- `scenes` 1:N `scene_verbs`
- `scenes` 1:N `scene_assets`
- `scenes` 1:N `jobs`

## 4.2 级联策略

建议：

- 删除场景时，`scene_items`、`scene_verbs`、`scene_assets` 走 `ON DELETE CASCADE`
- 删除用户时，不建议级联删除 `scenes` 和 `jobs`
- 用户删除属于高风险操作，建议走业务层软删除，不直接物理删

---

## 5. 索引策略

MVP 阶段索引遵循一个原则：

- 先保证查询路径稳定
- 不为了“可能的未来查询”过早加太多索引

推荐重点查询路径：

### 5.1 场景列表

查询条件：

- `scene_type`
- `visibility`
- `status`
- `category`

因此 `scenes` 上保留这些索引。

### 5.2 我的场景

查询条件：

- `owner_user_id`
- `status`

### 5.3 任务列表

查询条件：

- `user_id`
- `status`
- `created_at`

### 5.4 任务详情

查询条件：

- `job_uuid`

### 5.5 场景详情

查询条件：

- `scene_uuid`

---

## 6. 建议的软删除策略

MVP 可先不做通用软删除字段。  
但对于 `scenes`，后续高概率会需要：

- `deleted_at`

原因：

- 私人场景删除通常不建议直接物理删
- 未来可能需要恢复功能

如果 MVP 想保持简单，可以先只使用：

- `status = archived`

作为业务删除态。

---

## 7. 初始化数据建议

MVP 建库后建议初始化以下内容。

## 7.1 初始化管理员公开场景

如果一开始没有后台系统，可以先手工插入若干公开场景。

例如：

```sql
INSERT INTO scenes (
  scene_uuid,
  scene_type,
  owner_user_id,
  source_type,
  title,
  subtitle,
  cover_image_path,
  background_image_path,
  scene_json_path,
  visibility,
  status,
  category,
  tags_json,
  version
) VALUES (
  'scene_breakfast',
  'public',
  NULL,
  'preset',
  '营养早餐',
  NULL,
  '/data/english-scenes/public-scenes/breakfast/cover.jpg',
  '/data/english-scenes/public-scenes/breakfast/background.jpg',
  '/data/english-scenes/public-scenes/breakfast/scene.json',
  'member',
  'ready',
  'food',
  JSON_ARRAY('breakfast', 'food'),
  1
);
```

## 7.2 初始化测试用户

开发环境可插一个测试用户：

```sql
INSERT INTO users (
  openid,
  nickname,
  avatar_url,
  membership_status
) VALUES (
  'test_openid_001',
  'Test User',
  '',
  'member'
);
```

---

## 8. Migration 设计原则

推荐使用：

- Alembic

每次 migration 只做一类事情，不要一个 migration 同时做：

- 改表结构
- 回填业务数据
- 修复线上脏数据

要拆开。

---

## 9. MVP 第一批 Migration 草案

建议按以下顺序。

## 9.1 `001_create_users`

创建：

- `users`

## 9.2 `002_create_scenes`

创建：

- `scenes`

## 9.3 `003_create_scene_items_and_verbs`

创建：

- `scene_items`
- `scene_verbs`

## 9.4 `004_create_scene_assets`

创建：

- `scene_assets`

## 9.5 `005_create_jobs`

创建：

- `jobs`

## 9.6 `006_create_memberships`

创建：

- `memberships`

## 9.7 `007_seed_public_scenes`

写入：

- 初始公开场景

## 9.8 `008_seed_test_user`

写入：

- 测试用户

---

## 10. Alembic 目录建议

```text
migrations/
  env.py
  script.py.mako
  versions/
    001_create_users.py
    002_create_scenes.py
    003_create_scene_items_and_verbs.py
    004_create_scene_assets.py
    005_create_jobs.py
    006_create_memberships.py
    007_seed_public_scenes.py
    008_seed_test_user.py
```

---

## 11. SQLAlchemy 模型建议

建议每张表一个模型文件。

例如：

```text
models/
  user.py
  scene.py
  scene_item.py
  scene_verb.py
  scene_asset.py
  job.py
  membership.py
```

模型层建议：

- `scene_uuid`
- `job_uuid`

都由服务层生成，不依赖数据库自增 ID 作为外部接口主键。

---

## 12. 后续高概率追加的 Migration

这些不建议进 MVP 第一版，但提前预判。

### 12.1 `scene_share_tokens`

用于私人场景分享。

### 12.2 `job_events`

用于更细粒度的任务阶段日志。

### 12.3 `scene_favorites`

用于用户收藏公开场景。

### 12.4 `scene_study_records`

用于学习行为记录和推荐。

### 12.5 `billing_orders`

用于会员支付。

---

## 13. 回滚原则

MVP 阶段建议：

- 结构 migration 可回滚
- seed migration 尽量幂等

例如：

- 插入公开场景时先按 `scene_uuid` 判重
- 插入测试用户时先按 `openid` 判重

不要把生产数据修复和 schema migration 混在一起。

---

## 14. 初始化脚本执行顺序

如果先不用 Alembic，也可以按 SQL 文件顺序执行：

1. `00_create_database.sql`
2. `01_users.sql`
3. `02_scenes.sql`
4. `03_scene_items.sql`
5. `04_scene_verbs.sql`
6. `05_scene_assets.sql`
7. `06_jobs.sql`
8. `07_memberships.sql`
9. `90_seed_public_scenes.sql`
10. `91_seed_test_user.sql`

---

## 15. 建议的初始 SQL 文件组织

```text
sql/
  init/
    00_create_database.sql
    01_users.sql
    02_scenes.sql
    03_scene_items.sql
    04_scene_verbs.sql
    05_scene_assets.sql
    06_jobs.sql
    07_memberships.sql
  seed/
    90_seed_public_scenes.sql
    91_seed_test_user.sql
```

---

## 16. MVP 数据库落地建议

为了加快落地，推荐实际操作顺序：

1. 先建 `users`
2. 再建 `scenes`
3. 再建 `scene_items` / `scene_verbs`
4. 再建 `jobs`
5. 再建 `scene_assets`
6. 最后建 `memberships`

其中真正最先必须打通的是：

- `users`
- `scenes`
- `jobs`

因为这三张表足以支撑登录、任务、结果页闭环。

---

## 17. 结论

MVP 数据库设计要尽量满足两个目标：

1. 结构足够稳定，能支撑前后端和 worker 并行开发
2. 不过度设计，不把分享、支付、运营审计一次塞进第一版

如果马上进入开发，建议下一步动作是：

1. 先把本文里的 SQL 转成真实 `.sql` 文件
2. 在 API 仓库里建立 SQLAlchemy 模型
3. 配好 Alembic
4. 先落前三张关键表：`users`、`scenes`、`jobs`

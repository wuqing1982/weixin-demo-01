# 存储管理功能设计文档

**日期**: 2026-04-22
**状态**: 待实现
**方案**: B — 抽象存储层 + 统一接口

---

## 1. 目标

在 Admin 后台新增「存储管理」菜单，支持：
- 集中管理多种存储后端的连接配置（本地文件系统、Cloudflare R2、腾讯云 COS）
- 切换活跃存储后端
- 监控存储用量（已用空间、文件数、按类型分类统计）
- 测试各后端连接是否可用

## 2. 架构

### 2.1 存储抽象层

新增 `backend/app/storage/` 模块：

```
backend/app/storage/
├── __init__.py           # 导出工厂函数
├── base.py               # StorageBackend Protocol
├── local.py              # LocalStorage 实现
├── r2.py                 # CloudflareR2Storage 实现
├── cos.py                # TencentCOSStorage 实现
├── config_store.py       # 存储配置 JSON 读写（线程安全）
└── factory.py            # get_active_storage() 工厂（带缓存）
```

### 2.2 StorageBackend Protocol

定义统一接口：

| 方法 | 签名 | 说明 |
|------|------|------|
| upload | `upload(path: str, content: bytes, content_type: str) -> str` | 上传文件，返回公开 URL |
| download | `download(path: str) -> bytes` | 下载文件内容 |
| delete | `delete(path: str) -> bool` | 删除文件 |
| get_usage | `get_usage() -> StorageUsage` | 返回用量统计（带缓存，5分钟 TTL） |
| test_connection | `test_connection() -> ConnectionTestResult` | 测试连接 |
| list_files | `list_files(prefix: str, limit: int) -> list[FileInfo]` | 列举文件（Phase 2 使用，当前不暴露给前端） |

数据类：
- `StorageUsage(total_bytes: int, used_bytes: int, file_count: int, by_type: dict[str, int])`
  - 本地存储的 `total_bytes` = 磁盘分区可用空间
  - `by_type` 按文件扩展名分类统计（如 `.jpg`、`.mp3`）
- `ConnectionTestResult(ok: bool, message: str)`
- `FileInfo(path: str, size_bytes: int, last_modified: str | None)`

### 2.3 配置存储

配置文件：`backend/data/storage_config.json`

**密钥存储策略**：敏感字段（secret_key、secret_access_key、secret_id）存放在 JSON 文件中，但：
1. 文件创建时强制 `chmod 600`
2. 文件路径加入 `.gitignore`
3. `GET` API 返回时脱敏（只显示后4位）
4. 与现有 `.env` 模式并行，不破坏现有密钥管理

```json
{
  "activeBackend": "local",
  "lastActiveBackend": "local",
  "backends": {
    "local": {
      "type": "local",
      "name": "本地存储",
      "enabled": true,
      "config": {
        "root_dir": "assets"
      }
    },
    "r2": {
      "type": "r2",
      "name": "Cloudflare R2",
      "enabled": false,
      "config": {
        "account_id": "",
        "access_key_id": "",
        "secret_access_key": "",
        "bucket": "",
        "public_url": ""
      }
    },
    "cos": {
      "type": "cos",
      "name": "腾讯云 COS",
      "enabled": false,
      "config": {
        "secret_id": "",
        "secret_key": "",
        "region": "",
        "bucket": "",
        "public_url": ""
      }
    }
  }
}
```

**backend_id 说明**：`"local"`、`"r2"`、`"cos"` 为固定 ID，与 `type` 字段一一对应。Phase 1 不支持自定义后端或多实例。

### 2.4 工厂函数

`factory.py` 职责：
- `get_active_storage() -> StorageBackend` — 根据配置实例化当前活跃后端
- `get_all_backends() -> dict` — 返回所有后端配置摘要（密钥脱敏）
- 切换活跃后端时更新配置文件，下次调用自动使用新后端

**缓存策略**：
- 按 backend type 缓存单例实例（`_instances: dict[str, StorageBackend]`）
- `activate` 切换时清除旧实例缓存，强制下次重新创建
- 配置文件每次调用时读取（JSON 解析开销极小，~1μs）
- 已激活的后端在实例化失败时自动回退到 `lastActiveBackend`

**config_store.py 线程安全**：
- 使用 `threading.Lock` 保护 JSON 文件读写（与现有 `UploadStore`、`SceneStore` 一致）

### 2.5 阶段说明

**Phase 1（本次）**：`StorageBackend.upload()` / `download()` / `delete()` 已定义但**不被任何调用者使用**。只有 `get_usage()`、`test_connection()` 和配置管理被接入。实际文件操作将在 Phase 2（`UploadStore` 改造）中接入。

## 3. Admin API

### 3.1 路由模块

为避免 `main.py` 进一步膨胀，新增独立路由文件 `backend/app/routes/storage_admin.py`，在 `main.py` 中通过 `include_router` 挂载。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/admin/storage/overview` | 综合概览（活跃后端 + 各后端启用状态 + 总用量） |
| GET | `/api/admin/storage/configs` | 获取所有后端配置（密钥脱敏） |
| PUT | `/api/admin/storage/configs/{backend_id}` | 更新指定后端配置 |
| POST | `/api/admin/storage/test/{backend_id}` | 测试指定后端连接 |
| POST | `/api/admin/storage/activate/{backend_id}` | 切换活跃后端 |
| GET | `/api/admin/storage/usage` | 获取当前活跃后端用量 |

### 3.2 输入验证

新增 Pydantic v2 模型：

```python
class StorageConfigUpdateRequest(BaseModel):
    name: str | None = None
    enabled: bool | None = None
    config: dict[str, str] | None = None
```

`backend_id` 路径参数验证：仅允许 `"local"` / `"r2"` / `"cos"`，否则返回 400。

### 3.3 密钥脱敏

- `secret_key` / `secret_access_key` / `secret_id` 等敏感字段 → 只返回 `****xxxx`（后4位）
- PUT 更新时：如果字段值以 `****` 开头则不更新该字段（保留原值）
- **所有存储管理 API 要求 HTTPS**（生产环境必须启用 TLS）

### 3.4 切换活跃后端流程

1. 调用目标后端的 `test_connection()` 验证可用性
2. 验证失败 → 返回错误，不切换
3. 验证通过 → 保存 `lastActiveBackend = 当前活跃后端`，然后更新 `activeBackend`
4. 清除工厂缓存
5. 无需重启服务

**回退机制**：
- `config.json` 记录 `lastActiveBackend`（切换前的活跃后端）
- 如果新后端在后续操作中失败，管理员可一键切回 `lastActiveBackend`
- 本地存储始终作为兜底（不可禁用）

### 3.5 get_usage() 性能

- 本地存储：使用 `os.scandir()` 遍历，结果缓存 5 分钟（`_usage_cache` + `time.monotonic()`）
- R2/COS：调用 SDK 的统计 API 或遍历列举，同样缓存 5 分钟
- 超时保护：遍历超过 10 秒则返回部分结果 + 超时标记

## 4. Admin 前端

### 4.1 侧边栏

新增导航组「系统配置」，位于「运营管理」之后：

```html
<div class="nav-group">
  <div class="nav-group-title">系统配置</div>
  <button class="nav-item" data-view="storage">存储管理</button>
</div>
```

### 4.2 页面布局

#### 存储概览（顶部）

4 个 metric 卡片：
- 已用空间
- 总容量
- 剩余空间
- 文件数量

加上当前活跃后端名称和状态标签。

#### 存储配置（中部）

3 张后端卡片并排：本地存储 / Cloudflare R2 / 腾讯云 COS

每张卡片包含：
- 名称 + 启用状态标签
- 最后测试结果
- 操作按钮：「配置」（弹出 modal 编辑）、「测试连接」、「设为默认」

Modal 编辑表单根据后端类型动态显示字段：

| 后端 | 配置字段 |
|------|---------|
| 本地存储 | 根目录路径（只读显示） |
| R2 | Account ID, Access Key ID, Secret Access Key, Bucket, Public URL |
| COS | Secret ID, Secret Key, Region, Bucket, Public URL |

#### 使用量分类（底部）

按文件类型统计：图片 / 音频 / 其他，用横向条形图或数字标签展示。

### 4.3 前端状态

新增 state 字段：
- `storageConfigs` — 所有后端配置
- `storageUsage` — 当前用量
- `editingBackend` — 正在编辑的后端 ID

### 4.4 加载与错误状态

- 页面切换到 storage 视图时调用 `loadStorageData()` 获取 overview + configs
- API 失败时显示错误提示（toast），metric 卡片显示 `-` 占位
- 初始状态（无配置文件）自动创建默认配置
- 测试连接按钮显示 loading spinner，完成后显示成功/失败标签

## 5. 依赖

新增 Python 依赖：
- `boto3` — Cloudflare R2 兼容 S3 API
- `cos-python-sdk-v5` — 腾讯云 COS SDK

**系统级依赖**（安装 COS SDK 可能需要）：
```bash
sudo apt install python3-dev build-essential
```

如果 `crcmod` 编译失败，COS 的 HMAC 签名功能会降级为纯 Python 实现（性能略差但功能正常）。

## 6. 文件变更清单

### 新增文件

```
backend/app/storage/__init__.py
backend/app/storage/base.py         # StorageBackend Protocol + 数据类
backend/app/storage/local.py        # LocalStorage 实现
backend/app/storage/r2.py           # CloudflareR2Storage 实现
backend/app/storage/cos.py          # TencentCOSStorage 实现
backend/app/storage/config_store.py # 配置 JSON 读写（线程安全）
backend/app/storage/factory.py      # 工厂函数（带缓存 + 回退）
backend/app/routes/storage_admin.py # Admin API 路由
backend/data/storage_config.json    # 自动生成（首次运行时）
```

### 修改文件

```
backend/admin_web/index.html        # 侧边栏加「系统配置」导航组
backend/admin_web/admin.js          # 新增 storage 视图 + state + renderStorage() + API 调用
                                     # 更新 VIEW_TITLES 和 renderCurrentView()
backend/admin_web/admin.css         # 存储卡片 + 配置 modal 样式
backend/app/main.py                 # include_router 挂载 storage_admin 路由
backend/requirements.txt            # 新增 boto3, cos-python-sdk-v5
.gitignore                          # 新增 backend/data/storage_config.json
```

### 不改的文件

- 现有 `UploadStore` 暂不改造（本次只做配置管理 + 监控面板）
- `settings.py` 不动
- 不影响小程序前端

## 7. 风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| `qcloud-cos-sdk` 安装需编译环境 | 提前安装 `python3-dev build-essential`；编译失败时降级为纯 Python |
| 密钥明文存储在 JSON 中 | `chmod 600` + `.gitignore` 排除 + API 脱敏返回 |
| R2/COS `get_usage()` 遍历性能 | 5 分钟缓存 + 10 秒超时保护 |
| 切换后端后新后端不可用 | `lastActiveBackend` 回退 + 本地存储兜底 |
| `main.py` 已 2337 行 | 路由拆分到独立文件 `routes/storage_admin.py` |

## 8. 后续扩展（不在本次范围）

- `UploadStore` 改造为使用 `StorageBackend` 抽象层进行实际上传/下载
- 文件浏览管理器（上传/下载/删除文件）
- 存储迁移工具（本地 → R2/COS）
- 支持多后端实例（如多个 R2 bucket）
- `list_files()` 分页与前端文件浏览器集成

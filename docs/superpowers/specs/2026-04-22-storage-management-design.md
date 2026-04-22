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
├── config_store.py       # 存储配置 JSON 读写
└── factory.py            # get_active_storage() 工厂
```

### 2.2 StorageBackend Protocol

定义统一接口：

| 方法 | 签名 | 说明 |
|------|------|------|
| upload | `upload(path: str, content: bytes, content_type: str) -> str` | 上传文件，返回公开 URL |
| download | `download(path: str) -> bytes` | 下载文件内容 |
| delete | `delete(path: str) -> bool` | 删除文件 |
| get_usage | `get_usage() -> StorageUsage` | 返回用量统计 |
| test_connection | `test_connection() -> ConnectionTestResult` | 测试连接 |
| list_files | `list_files(prefix: str, limit: int) -> list[FileInfo]` | 列举文件 |

数据类：
- `StorageUsage(total_bytes: int, used_bytes: int, file_count: int)`
- `ConnectionTestResult(ok: bool, message: str)`
- `FileInfo(path: str, size_bytes: int, last_modified: str | None)`

### 2.3 配置存储

配置文件：`backend/data/storage_config.json`

```json
{
  "activeBackend": "local",
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

### 2.4 工厂函数

`factory.py` 职责：
- `get_active_storage() -> StorageBackend` — 根据配置实例化当前活跃后端
- `get_all_backends() -> dict` — 返回所有后端配置摘要（密钥脱敏）
- 切换活跃后端时更新配置文件，下次调用自动使用新后端

## 3. Admin API

在 `backend/app/main.py` 新增路由组 `/api/admin/storage/*`：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/admin/storage/overview` | 综合概览（活跃后端 + 各后端启用状态 + 总用量） |
| GET | `/api/admin/storage/configs` | 获取所有后端配置（密钥脱敏） |
| PUT | `/api/admin/storage/configs/{backend_id}` | 更新指定后端配置 |
| POST | `/api/admin/storage/test/{backend_id}` | 测试指定后端连接 |
| POST | `/api/admin/storage/activate/{backend_id}` | 切换活跃后端 |
| GET | `/api/admin/storage/usage` | 获取当前活跃后端用量 |

### 3.1 密钥脱敏

- `secret_key` / `secret_access_key` / `secret_id` 等敏感字段 → 只返回 `****xxxx`（后4位）
- PUT 更新时：如果字段值以 `****` 开头则不更新该字段（保留原值）

### 3.2 切换活跃后端流程

1. 调用目标后端的 `test_connection()` 验证可用性
2. 验证通过 → 更新 `storage_config.json` 的 `activeBackend`
3. 下次 `get_active_storage()` 调用自动使用新后端
4. 无需重启服务

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

## 5. 依赖

新增 Python 依赖：
- `boto3` — Cloudflare R2 兼容 S3 API
- `qcloud-cos-sdk` (即 `cos-python-sdk-v5`) — 腾讯云 COS SDK

## 6. 文件变更清单

### 新增文件

```
backend/app/storage/__init__.py
backend/app/storage/base.py
backend/app/storage/local.py
backend/app/storage/r2.py
backend/app/storage/cos.py
backend/app/storage/config_store.py
backend/app/storage/factory.py
backend/data/storage_config.json
```

### 修改文件

```
backend/admin_web/index.html       # 侧边栏加导航组
backend/admin_web/admin.js         # 新增 storage 视图渲染 + API 调用
backend/admin_web/admin.css        # 存储卡片样式
backend/app/main.py                # 新增 /api/admin/storage/* 路由
backend/requirements.txt           # 新增 boto3, qcloud-cos-sdk
```

### 不改的文件

- 现有 `UploadStore` 暂不改造（本次只做配置管理 + 监控面板）
- `settings.py` 不动
- 不影响小程序前端

## 7. 风险

- `qcloud-cos-sdk` 依赖 `crcmod`，可能需要系统级编译环境
- 密钥明文存储在 JSON 文件中，需配合文件权限保护（`chmod 600`）
- R2/COS 的 `get_usage()` 可能需要遍历文件统计，大量文件时有性能问题

## 8. 后续扩展（不在本次范围）

- `UploadStore` 改造为使用 `StorageBackend` 抽象层进行实际上传/下载
- 文件浏览管理器（上传/下载/删除文件）
- 存储迁移工具（本地 → R2/COS）

# 场景生成 Worker 内化 core100 模块 — 变更文档

**日期:** 2026-04-07 04:33
**分支:** 118v3
**变更范围:** 场景生成 Worker 从动态加载外部 core100 目录迁移到标准 Python 包内化导入

---

## 1. 变更背景

### 1.1 旧架构

场景生成 Worker（`InlineSceneWorker`）依赖仓库外部的 core100 工具集目录：

```
/www/wwwroot/e.cps.vin/core100/          ← 仓库外，不在 Git 管控中
├── analyze_scene.py                      ← GLM-4V 图像分析
├── generate_audio.py                     ← TTS 音频生成
├── scene_assets.py                       ← 共享工具函数
├── json_repair.py                        ← JSON 修复
└── tts-service/                          ← Edge TTS 服务
```

`worker_runner.py` 通过 `importlib.import_module()` + `sys.path` 操纵在运行时动态加载这三个模块：

```python
# 旧代码
import importlib, sys

class InlineSceneWorker:
    def __init__(self, ..., core100_root: Path, ...):
        self.core100_root = core100_root
        self.module_cache: dict[str, object] = {}

    def _load_core100_module(self, module_name: str):
        # 将 core100_compat/ 和 core100_root 加入 sys.path
        sys.path.insert(0, compat_root)
        sys.path.insert(1, str(self.core100_root))
        module = importlib.import_module(module_name)
        self.module_cache[module_name] = module
        return module

    def _get_core100_symbol(self, module_name, symbol_name):
        return getattr(self._load_core100_module(module_name), symbol_name)
```

### 1.2 旧架构的问题

1. **部署脆弱**：core100 目录不存在时 worker 直接崩溃（`RuntimeError: core100 root not found`）
2. **版本不同步**：两个仓库的代码需要手动保持一致，容易出现不一致
3. **调试困难**：调用链跨越两个目录，IDE 无法正确跳转和补全
4. **配置耦合**：需要在 `.env` 中配置 `CORE100_ROOT` 路径，且硬编码了默认值 `../core100`

---

## 2. 新架构

### 2.1 内化后的结构

所有核心模块迁移到项目内的 `backend/app/scene_worker/` 包中：

```
backend/app/scene_worker/                 ← 新包，在 Git 管控中
├── __init__.py                           ← 导出 3 个公共函数
├── analyze_scene.py                      ← GLM-4V 图像分析（从 core100 迁入）
├── generate_audio.py                     ← TTS 音频生成（从 core100 迁入）
├── scene_assets.py                       ← 共享工具函数（从 core100 迁入）
└── json_repair.py                        ← JSON 修复（从 core100_compat 迁入）
```

### 2.2 导入方式变更

```python
# 新代码 — 标准 Python 相对导入，无需 importlib / sys.path
from .scene_worker.analyze_scene import analyze_scene_with_glm4v
from .scene_worker.generate_audio import generate_scene_audio
from .scene_worker.scene_assets import build_audio_filename
```

不再有 `import importlib`、`import sys`、`sys.path.insert()`、`module_cache`。

---

## 3. 逐文件变更清单

### 3.1 新建文件

| 文件路径 | 来源 | 变更说明 |
|---------|------|---------|
| `backend/app/scene_worker/__init__.py` | 新建 | 包入口，导出 `analyze_scene_with_glm4v`、`generate_scene_audio`、`build_audio_filename` |
| `backend/app/scene_worker/scene_assets.py` | 从 `core100/scene_assets.py` 复制 | 无改动，该模块没有跨模块 import |
| `backend/app/scene_worker/analyze_scene.py` | 从 `core100/analyze_scene.py` 复制 | ① `from json_repair import ...` → `from .json_repair import ...` ② 移除硬编码的 API Key 回退值 `"c016be5f55f64d62..."` ③ 移除 `main()` 函数和 `if __name__` 块 |
| `backend/app/scene_worker/generate_audio.py` | 从 `core100/generate_audio.py` 复制 | ① `from scene_assets import ...` → `from .scene_assets import ...` ② 移除 `main()` 函数和 `if __name__` 块 |
| `backend/app/scene_worker/json_repair.py` | 从 `backend/app/core100_compat/json_repair.py` 移入 | 无改动，仅移动位置 |

### 3.2 修改文件

#### `backend/app/worker_runner.py`

**移除的代码（约 30 行）：**

- 移除 `import importlib` 和 `import sys`
- 移除 `core100_root: Path` 构造参数
- 移除 `self.core100_root`、`self.module_cache` 实例变量
- 移除 `_get_core100_symbol()` 方法
- 移除 `_load_core100_module()` 方法（含 `sys.path.insert`、`importlib.import_module`）

**新增的代码（3 行）：**

```python
from .scene_worker.analyze_scene import analyze_scene_with_glm4v
from .scene_worker.generate_audio import generate_scene_audio
from .scene_worker.scene_assets import build_audio_filename
```

**简化的方法调用：**

| 方法 | 旧写法 | 新写法 |
|-----|-------|-------|
| `_analyze_scene` | `self._get_core100_symbol('analyze_scene', 'analyze_scene_with_glm4v')` | 直接使用模块级 `analyze_scene_with_glm4v` |
| `_generate_audio` | `self._get_core100_symbol('generate_audio', 'generate_scene_audio')` | 直接使用模块级 `generate_scene_audio` |
| `_attach_audio_paths` | `self._get_core100_symbol('scene_assets', 'build_audio_filename')` | 直接使用模块级 `build_audio_filename` |

**错误消息更新：**

- `'core100 analyze_scene returned invalid payload'` → `'scene analysis returned invalid payload'`
- `'core100 analyze_scene returned empty hotspots'` → `'scene analysis returned empty hotspots'`

#### `backend/app/main.py`

```diff
 from .settings import (
     ...
-    CORE100_ROOT,
     CORE100_TTS_URL,
     ...
 )

 scene_worker = InlineSceneWorker(
     ...
-    core100_root=CORE100_ROOT,
     tts_url=CORE100_TTS_URL,
     ...
 )
```

#### `backend/app/settings.py`

```diff
-CORE100_ROOT = Path(os.getenv('CORE100_ROOT', str(REPO_ROOT.parent / 'core100')))
```

仅移除 `CORE100_ROOT` 这一行。`CORE100_MODEL`、`CORE100_TTS_URL`、`ZHIPUAI_API_KEY` 等配置保留不变。

#### `backend/requirements.txt`

新增 4 个之前通过 core100 隐式依赖的包：

```
zhipuai>=2.0.0          # 智谱 AI SDK，用于 GLM-4V 图像分析
pillow>=9.0.0           # 图片处理，用于获取图片尺寸和坐标转换
pydub>=0.25.0           # 音频拼接，用于合并单词+静音+例句
audioop-lts>=0.2.1;python_version>="3.13"   # Python 3.13+ 下 pydub 的依赖
```

#### `backend/.env.example`

```diff
-# core100 / TTS
-CORE100_ROOT=/www/wwwroot/e.cps.vin/core100
+# Scene Worker / TTS
 CORE100_MODEL=glm-4v-flash
 CORE100_TTS_URL=http://127.0.0.1:5003
```

#### `backend/README.md`

从环境变量列表中移除 `CORE100_ROOT`。

#### `backend/tests/test_core100_json_repair.py`

```diff
-from backend.app.core100_compat.json_repair import repair_truncated_json
+from backend.app.scene_worker.json_repair import repair_truncated_json
```

#### `backend/tests/test_worker_runner_admin_publish.py`

```diff
 self.worker = InlineSceneWorker(
     ...
-    core100_root=root,
     tts_url='http://127.0.0.1:5003',
     ...
 )
```

#### `docs/worker/scene-generation.md`

全面重写：
- 移除 "外部依赖：core100 目录" 章节
- 移除 "动态加载机制" 章节
- 移除 "关于 core100 目录的总结" 章节
- 新增 scene_worker 包的文档
- 新增标准 import 说明
- 更新目录结构图（`core100_compat/` → `scene_worker/`）

### 3.3 删除文件

| 文件路径 | 原因 |
|---------|------|
| `backend/app/core100_compat/json_repair.py` | 已迁移到 `scene_worker/json_repair.py` |
| `backend/app/core100_compat/__init__.py` | 目录整体移除 |

---

## 4. 与 core100 的差异

内化后的模块与 core100 原版存在以下有意的差异：

### 4.1 `analyze_scene.py`

| 差异点 | core100 原版 | 内化版 |
|--------|-------------|-------|
| json_repair import | `from json_repair import ...` | `from .json_repair import ...` |
| API Key 回退 | 硬编码 `"c016be5f55f64d62a2f5b7074ec1c8d0.w7sxKyHb7zP7mTzg"` | 仅读环境变量，不硬编码 |
| CLI 入口 | `main()` + `argparse` + `if __name__` | 已移除（服务端不需要） |

### 4.2 `generate_audio.py`

| 差异点 | core100 原版 | 内化版 |
|--------|-------------|-------|
| scene_assets import | `from scene_assets import ...` | `from .scene_assets import ...` |
| CLI 入口 | `main()` + `argparse` + `if __name__` | 已移除（服务端不需要） |

### 4.3 `scene_assets.py`

完全一致，无任何改动。

### 4.4 `json_repair.py`

从 `core100_compat/` 移入，代码本身无变化。与 core100 目录中的 `json_repair.py` 可能存在差异（项目内的版本增加了尾逗号修复等增强），以项目内版本为准。

---

## 5. 升级/部署注意事项

### 5.1 部署不再需要 core100 目录

迁移完成后，部署时**不再需要** `/www/wwwroot/e.cps.vin/core100/` 目录存在即可启动场景生成功能。

### 5.2 环境变量变更

| 变量 | 变更 | 说明 |
|------|------|------|
| `CORE100_ROOT` | **已移除** | 不再需要配置，可从 `.env` 中删除 |
| `CORE100_MODEL` | 保留 | 智谱 AI 模型名称 |
| `CORE100_TTS_URL` | 保留 | TTS 服务地址 |
| `ZHIPUAI_API_KEY` | 保留 | API 密钥 |

### 5.3 新增 Python 依赖

部署前需要安装新增的依赖：

```bash
cd backend
pip install -r requirements.txt
```

新增包：`zhipuai`、`pillow`、`pydub`、`audioop-lts`（Python 3.13+）。

### 5.4 TTS 服务仍然是外部依赖

Edge TTS 服务（`core100/tts-service/`）作为独立进程运行，没有内化。这是设计决定——TTS 服务是独立部署的 HTTP 服务，与语言/框架无关。

### 5.5 向后兼容

- `CORE100_ROOT` 如果在 `.env` 中保留，会被 `settings.py` 忽略（该配置项已移除）
- 旧版 core100 目录如果仍然存在，不会影响新代码运行（不再被引用）

---

## 6. 测试验证

### 6.1 验证导入

```bash
cd backend
python3 -c "
from app.scene_worker import analyze_scene_with_glm4v, generate_scene_audio, build_audio_filename
print('imports OK')
"
```

### 6.2 运行相关测试

```bash
cd /www/wwwroot/e.cps.vin/weixin-demo-01
python3 -m pytest \
  backend/tests/test_core100_json_repair.py \
  backend/tests/test_worker_runner_titles.py \
  backend/tests/test_worker_runner_admin_publish.py \
  -v
```

预期结果：5 tests passed。

### 6.3 启动 API 验证

```bash
cd backend
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

验证：服务正常启动，Worker 线程正常创建，日志中无 `core100 root not found` 错误。

---

## 7. 文件路径速查

### 新文件

```
backend/app/scene_worker/__init__.py          # 251 bytes
backend/app/scene_worker/analyze_scene.py     # ~18 KB
backend/app/scene_worker/generate_audio.py    # ~8 KB
backend/app/scene_worker/scene_assets.py      # ~3 KB
backend/app/scene_worker/json_repair.py       # ~5 KB
```

### 修改文件

```
backend/app/worker_runner.py                  # -30 行动态加载 → +3 行标准导入
backend/app/main.py                           # -2 行（移除 CORE100_ROOT 引用）
backend/app/settings.py                       # -1 行（移除 CORE100_ROOT 设置）
backend/requirements.txt                      # +4 行（新增依赖）
backend/.env.example                          # 重命名注释 + 移除 CORE100_ROOT
backend/README.md                             # 移除 CORE100_ROOT 列表项
backend/tests/test_core100_json_repair.py     # 更新 import 路径
backend/tests/test_worker_runner_admin_publish.py  # 移除 core100_root 参数
docs/worker/scene-generation.md               # 全面重写
```

### 删除文件

```
backend/app/core100_compat/json_repair.py     # 已迁移到 scene_worker/
backend/app/core100_compat/__init__.py         # 目录整体移除
```

---

## 8. 回滚方案

如果需要回滚到动态加载 core100 的旧版本：

1. `git revert` 本次变更的 commit
2. 确保 `/www/wwwroot/e.cps.vin/core100/` 目录存在
3. 恢复 `.env` 中的 `CORE100_ROOT` 配置
4. 恢复 `requirements.txt`（移除 `zhipuai`、`pillow`、`pydub` 等）

---

## 9. 后续优化建议

1. **重命名环境变量前缀**：`CORE100_MODEL` 和 `CORE100_TTS_URL` 可以考虑改为 `SCENE_MODEL` 和 `TTS_URL`，与 core100 脱钩
2. **scene_worker 目录重命名**：`scene_worker` 在项目中已存在同名目录（worker 线程相关），未来可考虑合并或更明确地区分
3. **core100 目录清理**：确认不再需要后，可以从服务器上删除 `/www/wwwroot/e.cps.vin/core100/` 目录（注意保留 `tts-service/`）

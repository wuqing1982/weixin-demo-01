# 场景生成系统技术文档

## 概述

场景生成系统是本项目的核心功能之一。用户上传一张全景/场景图片后，系统自动识别图中的物体（名词）和动作（动词），生成对应的英语学习内容，包括：单词、音标、释义、例句、中文翻译和 TTS 语音。

整个过程由后端的 **InlineSceneWorker** 后台线程完成，依赖智谱 AI (ZhipuAI) 的 GLM-4V 视觉模型进行图像分析，以及本地 Edge TTS 服务生成语音。

---

## 整体流程

```
用户上传图片
    │
    ▼
POST /api/uploads/image        ── 图片保存到 assets/uploads/
    │
    ▼
POST /api/my/tasks/scene-generate  ── 创建生成任务（status: queued）
    │
    ▼
InlineSceneWorker 轮询任务队列（每 2 秒）
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ _process_task() 六步流水线：                                   │
│                                                             │
│  1. load_upload (15%)     ── 加载上传记录                     │
│  2. prepare_assets (45%)  ── 复制图片到 assets/generated/     │
│  3. analyze_scene (55%)   ── 调用智谱AI GLM-4V 分析图片       │
│  4. generate_audio (75%)  ── 调用本地 TTS 服务生成 MP3         │
│  5. write_scene (90%)     ── 转换数据格式并存储                │
│  6. publish_scene (95%)   ── [可选] 发布到公共场景库            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
GET /api/my/tasks/{taskId}     ── 前端轮询任务进度
    │
    ▼
生成完成 (100%)，用户可在"我的场景"中查看
```

---

## 代码结构

### 项目内的所有相关文件

所有场景生成相关的代码都在 `backend/app/` 目录下，不依赖任何外部目录：

| 文件 | 作用 |
|------|------|
| `worker_runner.py` | 后台工作线程，编排整个生成流程的六步流水线 |
| `scene_adapter.py` | 数据转换层：将 AI 输出转为小程序使用的场景格式 |
| `scene_publication.py` | 场景发布：将用户私有的生成场景发布到公共场景目录 |
| `task_store.py` | 任务队列管理：创建、认领、更新、重试任务 |
| `upload_store.py` | 上传文件管理：图片元数据和磁盘路径映射 |
| `generated_scene_store.py` | 生成场景存储：JSON 文件存储生成的场景数据 |
| `schemas.py` | Pydantic 请求模型：`SceneGenerateRequest` 等 |
| `settings.py` | 配置项：`CORE100_MODEL`、`CORE100_TTS_URL` 等 |

### scene_worker 包

`backend/app/scene_worker/` 包含从 core100 迁移过来的核心逻辑，使用标准 Python import：

| 文件 | 作用 |
|------|------|
| `__init__.py` | 包入口，导出三个公共函数 |
| `analyze_scene.py` | 智谱 AI GLM-4V 图像分析：识别物体、生成 bounding box、音标、释义、例句 |
| `generate_audio.py` | TTS 音频生成：调用本地 Edge TTS 服务生成 MP3 文件 |
| `scene_assets.py` | 共享工具：音频文件名构建、场景数据辅助函数 |
| `json_repair.py` | JSON 修复工具：处理 AI 模型截断/格式错误的输出 |

---

## 部署依赖关系

### 部署不依赖外部 core100 目录

场景生成的所有代码已经内化到项目内的 `scene_worker/` 包中，通过标准 Python import 加载。部署时只需要：

1. **TTS 服务**：需要作为独立服务运行（默认 `http://127.0.0.1:5003`），否则音频生成步骤会失败。
2. **智谱 AI API Key**：`ZHIPUAI_API_KEY` 环境变量必须设置。
3. **Python 依赖**：`requirements.txt` 中的 `zhipuai`、`pillow`、`pydub` 等包。

### 配置项

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `CORE100_MODEL` | `glm-4v-flash` | 智谱 AI 模型名称 |
| `CORE100_TTS_URL` | `http://127.0.0.1:5003` | 本地 TTS 服务地址 |
| `ZHIPUAI_API_KEY` | 空 | 智谱 AI 的 API 密钥 |
| `ENABLE_INLINE_SCENE_WORKER` | `true` | 是否启用后台生成 worker |
| `WORKER_POLL_INTERVAL` | `2` | 任务轮询间隔（秒） |

---

## 导入方式

`worker_runner.py` 通过标准 Python 相对 import 加载 scene_worker 包中的函数：

```python
from .scene_worker.analyze_scene import analyze_scene_with_glm4v
from .scene_worker.generate_audio import generate_scene_audio
from .scene_worker.scene_assets import build_audio_filename
```

不再使用 `importlib` 动态加载，也不再需要 `sys.path` 操作。

---

## AI 图像分析详情

### 模型选择

支持以下智谱 AI 视觉模型：

| 模型 ID | 说明 |
|---------|------|
| `glm-4v-flash` | 默认，快速且免费 |
| `glm-4.5v` | 更精准 |
| `glm-4.6v` | 最新、能力最强 |
| `glm-4.6v-flash` | 最新免费版 |

### 分析过程

`analyze_scene_with_glm4v()` 函数（位于 `scene_worker/analyze_scene.py`）的工作流程：

1. 将图片编码为 base64
2. 调用 `ZhipuAI.chat.completions.create()` 发送图片和提示词
3. 提示词要求模型识别：
   - 5 个名词（物体/hotspot），包含 bounding box 坐标、音标、中文释义、英文例句
   - 可选的 3 个动词（verb），关联到识别出的物体
4. AI 返回 JSON，通过 `repair_truncated_json()` 修复可能的格式问题
5. 如果动词缺失或不完整，调用 `generate_verbs_fallback()` 进行兜底生成

### 输出数据格式

AI 分析完成后返回如下结构：

```json
{
  "scene_title": "Living Room",
  "hotspots": [
    {
      "id": "sofa",
      "word": "sofa",
      "ipa": "/ˈsoʊfə/",
      "meaning": "沙发",
      "rect": {"l": 10.5, "t": 30.2, "w": 25.0, "h": 20.0},
      "sentence": "Sit on the sofa.",
      "sentence_translation": "坐在沙发上。"
    }
  ],
  "verbs": [
    {
      "id": "sit",
      "word": "sit",
      "ipa": "/sɪt/",
      "meaning": "坐",
      "related_item": "sofa",
      "sentence": "I sit on the sofa.",
      "sentence_translation": "我坐在沙发上。"
    }
  ],
  "recommended_category": "living_room",
  "recommended_tags": ["furniture", "home"]
}
```

---

## TTS 语音生成详情

### 语音配置

支持 4 种语音组合：

| 口音 | 性别 | 语音名称 |
|------|------|---------|
| `en-US` (美式) | female | JennyNeural |
| `en-US` (美式) | male | ChristopherNeural |
| `en-GB` (英式) | female | LibbyNeural |
| `en-GB` (英式) | male | RyanNeural |

### 音频文件生成

`generate_scene_audio()` 函数（位于 `scene_worker/generate_audio.py`）为每个名词和动词生成一个 MP3 文件：

- 格式：单词朗读 + 0.1 秒静音 + 例句朗读
- 文件名格式：`{scene_id}_{accent}-{voiceName}_{region}_{gender}_{entryId}_{sentence}.mp3`
- 保存位置：`assets/generated/{scene_id}/`

### TTS 服务

本地 Edge TTS 服务（独立进程），基于 Microsoft Azure Cognitive Services 的 Edge TTS 实现，默认监听 `http://127.0.0.1:5003`。

---

## 数据转换层

### scene_adapter.py 的作用

AI 返回的数据格式和小程序前端使用的格式不同。`scene_adapter.py` 负责这个转换：

- `build_generated_scene_from_core_result()` — 将 AI 的原始输出转为小程序场景对象
- `build_runtime_entry()` — 标准化单个 hotspot/verb 条目
- `apply_hotspot_updates()` — 处理用户手动调整 hotspot 位置
- `normalize_hotspot_rect()` / `clamp_percent()` — 确保坐标在 0-100% 范围内，最小尺寸 4%

### scene_publication.py 的作用

可选的发布流程：将用户私有的生成场景发布到公共场景目录。

- 由 `autoPublish=true` 的任务自动触发，或通过管理后台手动触发
- 发布时会创建公共场景记录和发布记录
- 支持指定分类和合集

---

## 任务队列

任务存储在 `backend/data/tasks.json` 中（JSON 文件存储），支持：

- 创建任务（`status: queued`）
- 认领任务（`status: running`，原子操作防止并发重复处理）
- 更新进度（step + progress 百分比）
- 标记完成（`status: done`）或失败（`status: failed`）
- 崩溃恢复：启动时自动将 `running` 状态的任务重新入队

### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/uploads/image` | 上传源图片 |
| POST | `/api/my/tasks/scene-generate` | 创建场景生成任务 |
| GET | `/api/my/tasks/{task_id}` | 轮询任务进度 |
| GET | `/api/my/scenes` | 获取用户的生成场景列表 |
| POST | `/api/admin/tasks/scene-generate-batch` | 管理员批量生成（最多 50 个） |
| POST | `/api/admin/tasks/{task_id}/retry` | 重试失败的任务 |
| POST | `/api/admin/generated-scenes/{scene_id}/publish` | 发布到公共目录 |

---

## 目录结构（生成后的文件）

```
assets/
├── uploads/                          # 用户上传的原始图片
│   └── {upload_id}/
│       └── source.jpg
└── generated/                        # 生成的场景资源
    └── {scene_id}/
        ├── background.jpg            # 场景背景图（从 uploads 复制）
        ├── {scene_id}_en-US-JennyNeural_US_female_sofa_sit_on_the_sofa.mp3
        └── ...                       # 每个词汇对应的 MP3 文件

backend/
├── data/
│   ├── tasks.json                    # 任务队列
│   ├── uploads.json                  # 上传记录
│   └── generated_scenes.json         # 生成的场景数据
└── app/
    ├── worker_runner.py              # Worker 线程（编排器）
    ├── scene_adapter.py              # 数据转换
    ├── scene_publication.py          # 场景发布
    ├── task_store.py                 # 任务存储
    ├── upload_store.py               # 上传存储
    ├── generated_scene_store.py      # 生成场景存储
    ├── settings.py                   # 配置
    └── scene_worker/                 # 场景生成核心逻辑包
        ├── __init__.py               # 导出三个公共函数
        ├── analyze_scene.py          # AI 图像分析
        ├── generate_audio.py         # TTS 音频生成
        ├── scene_assets.py           # 共享工具函数
        └── json_repair.py            # JSON 修复工具
```

---

## 关于 core100 的历史说明

core100 最初是作为独立工具开发的（有自己的 `pipeline.py` CLI 和 `README.md`），可以直接在命令行执行场景分析。早期版本通过 `importlib` 动态 import 的方式复用 core100 中的核心逻辑。

现已将核心模块（`analyze_scene.py`、`generate_audio.py`、`scene_assets.py`、`json_repair.py`）迁移到项目内的 `backend/app/scene_worker/` 包中，使用标准 Python import，不再依赖外部 core100 目录。

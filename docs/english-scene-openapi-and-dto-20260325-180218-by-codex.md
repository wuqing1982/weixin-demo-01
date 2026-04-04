# 英语场景学习系统 OpenAPI 与 DTO 定义

时间：2026-03-25 18:02:18  
作者：Codex

## 1. 文档目标

本文档用于定义 MVP 阶段前后端联调所需的接口契约和数据传输对象。

目标：

- 为 API 服务提供清晰的 OpenAPI 草案
- 为小程序前端提供稳定 DTO
- 为 worker 输出 scene JSON 提供统一协议
- 减少后续实现阶段的字段漂移

上游文档：

- [`docs/english-scene-system-detailed-design-20260325-153922-by-codex.md`](E:\202603\weixin-demo\docs\english-scene-system-detailed-design-20260325-153922-by-codex.md)
- [`docs/english-scene-mvp-engineering-prep-20260325-175717-by-codex.md`](E:\202603\weixin-demo\docs\english-scene-mvp-engineering-prep-20260325-175717-by-codex.md)

---

## 2. 统一约定

## 2.1 API 基础路径

```text
/api
```

## 2.2 鉴权方式

HTTP Header：

```text
Authorization: Bearer <token>
```

## 2.3 时间格式

统一使用：

```text
YYYY-MM-DD HH:mm:ss
```

如：

```text
2026-03-25 18:00:00
```

## 2.4 通用响应包装

建议统一返回：

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

说明：

- `code=0` 表示成功
- 非 0 表示业务错误
- HTTP 状态码表达技术层错误

---

## 3. 通用错误码

| code | 含义 |
|---|---|
| 0 | 成功 |
| 40001 | 参数错误 |
| 40002 | 未登录 |
| 40003 | token 无效 |
| 40004 | 无权限 |
| 40005 | 文件类型不支持 |
| 40006 | 文件过大 |
| 40007 | 场景不存在 |
| 40008 | 任务不存在 |
| 40009 | 任务状态非法 |
| 40010 | 会员权限不足 |
| 50001 | 服务内部错误 |
| 50002 | 任务创建失败 |
| 50003 | 任务执行失败 |
| 50004 | 存储写入失败 |

---

## 4. 核心 DTO 定义

## 4.1 UserDto

```json
{
  "id": "u_1001",
  "nickname": "Tom",
  "avatarUrl": "https://example.com/avatar.jpg",
  "membershipStatus": "free",
  "membershipExpireAt": "2026-12-31 23:59:59"
}
```

字段说明：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | string | 是 | 用户对外 ID |
| nickname | string | 是 | 昵称 |
| avatarUrl | string | 否 | 头像 |
| membershipStatus | string | 是 | `free/member/vip` |
| membershipExpireAt | string/null | 否 | 会员过期时间 |

## 4.2 SceneListItemDto

```json
{
  "sceneId": "scene_breakfast",
  "title": "营养早餐",
  "coverUrl": "https://static.example.com/public-scenes/breakfast/cover.jpg",
  "category": "food",
  "visibility": "member",
  "sceneType": "public"
}
```

## 4.3 RectDto

```json
{
  "l": 13.5,
  "t": 24.5,
  "w": 50.2,
  "h": 15.0
}
```

## 4.4 SceneItemDto

```json
{
  "id": "porridge",
  "word": "porridge",
  "ipa": "/ˈpɒrɪdʒ/",
  "meaning": "粥",
  "sentence": "I eat porridge for breakfast.",
  "sentenceTranslation": "我早餐吃粥。",
  "rect": {
    "l": 13.5,
    "t": 24.5,
    "w": 50.2,
    "h": 15.0
  },
  "audio": "https://static.example.com/public-scenes/breakfast/audio/item_porridge.mp3"
}
```

## 4.5 SceneVerbDto

```json
{
  "id": "v1",
  "word": "eat",
  "ipa": "/iːt/",
  "meaning": "吃",
  "sentence": "I eat porridge for breakfast.",
  "sentenceTranslation": "我早餐吃粥。",
  "audio": "https://static.example.com/public-scenes/breakfast/audio/verb_eat.mp3"
}
```

## 4.6 SceneMetaDto

```json
{
  "sceneType": "private",
  "ownerUserId": "u_1001",
  "visibility": "private",
  "version": 1,
  "category": "food",
  "tags": ["breakfast", "food"]
}
```

## 4.7 SceneDetailDto

这是最重要的 DTO。

```json
{
  "sceneId": "scene_20260325_abc123",
  "title": "营养早餐",
  "background": "https://static.example.com/private-scenes/u_1001/scene_20260325_abc123/background.jpg",
  "cover": "https://static.example.com/private-scenes/u_1001/scene_20260325_abc123/cover.jpg",
  "items": [],
  "verbs": [],
  "meta": {
    "sceneType": "private",
    "ownerUserId": "u_1001",
    "visibility": "private",
    "version": 1,
    "category": "food",
    "tags": ["breakfast"]
  }
}
```

## 4.8 UploadResultDto

```json
{
  "storageKey": "uploads/2026/03/25/user_1001/original_xxx.jpg",
  "localPath": "/data/english-scenes/uploads/2026/03/25/user_1001/original_xxx.jpg",
  "publicUrl": "https://static.example.com/uploads/2026/03/25/user_1001/original_xxx.jpg",
  "contentType": "image/jpeg",
  "size": 123456
}
```

## 4.9 TaskCreateRequestDto

```json
{
  "jobType": "generate_private_scene",
  "sourceImagePath": "/data/english-scenes/uploads/2026/03/25/user_1001/original_xxx.jpg",
  "sceneTitle": null,
  "sceneHint": null
}
```

## 4.10 TaskCreateResponseDto

```json
{
  "jobId": "job_20260325_xxx",
  "status": "queued"
}
```

## 4.11 TaskDetailDto

```json
{
  "jobId": "job_20260325_xxx",
  "status": "running",
  "progress": 70,
  "currentStage": "generate_tts",
  "result": {
    "sceneId": null
  },
  "errorMessage": null,
  "createdAt": "2026-03-25 18:00:00",
  "startedAt": "2026-03-25 18:00:05",
  "finishedAt": null
}
```

## 4.12 MembershipDto

```json
{
  "membershipStatus": "member",
  "membershipExpireAt": "2026-12-31 23:59:59"
}
```

---

## 5. OpenAPI 草案

下面用接近 OpenAPI 的方式描述接口。

## 5.1 `POST /api/auth/wx-login`

### 请求体

```json
{
  "code": "wx_login_code"
}
```

### 成功响应

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "token": "jwt_token",
    "user": {
      "id": "u_1001",
      "nickname": "Tom",
      "avatarUrl": "",
      "membershipStatus": "free",
      "membershipExpireAt": null
    }
  }
}
```

### DTO

- 请求：`WxLoginRequestDto`
- 响应：`AuthLoginResponseDto`

## 5.2 `GET /api/me`

### 成功响应

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "u_1001",
    "nickname": "Tom",
    "avatarUrl": "",
    "membershipStatus": "member",
    "membershipExpireAt": "2026-12-31 23:59:59"
  }
}
```

## 5.3 `GET /api/scenes`

### 查询参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| type | string | 否 | 默认 `public` |
| category | string | 否 | 分类 |
| page | int | 否 | 默认 1 |
| pageSize | int | 否 | 默认 20 |

### 成功响应

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "list": [
      {
        "sceneId": "scene_breakfast",
        "title": "营养早餐",
        "coverUrl": "https://static.example.com/public-scenes/breakfast/cover.jpg",
        "category": "food",
        "visibility": "member",
        "sceneType": "public"
      }
    ],
    "total": 1,
    "page": 1,
    "pageSize": 20
  }
}
```

## 5.4 `GET /api/scenes/{sceneId}`

### 路径参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| sceneId | string | 是 | 场景对外 ID |

### 成功响应

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "sceneId": "scene_20260325_abc123",
    "title": "营养早餐",
    "background": "https://static.example.com/private-scenes/u_1001/scene_20260325_abc123/background.jpg",
    "cover": "https://static.example.com/private-scenes/u_1001/scene_20260325_abc123/cover.jpg",
    "items": [],
    "verbs": [],
    "meta": {
      "sceneType": "private",
      "ownerUserId": "u_1001",
      "visibility": "private",
      "version": 1,
      "category": "food",
      "tags": ["breakfast"]
    }
  }
}
```

## 5.5 `GET /api/my/scenes`

### 查询参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| page | int | 否 | 默认 1 |
| pageSize | int | 否 | 默认 20 |

### 成功响应

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "list": [
      {
        "sceneId": "scene_20260325_abc123",
        "title": "营养早餐",
        "coverUrl": "https://static.example.com/private-scenes/u_1001/scene_20260325_abc123/cover.jpg",
        "category": "food",
        "visibility": "private",
        "sceneType": "private"
      }
    ],
    "total": 1,
    "page": 1,
    "pageSize": 20
  }
}
```

## 5.6 `POST /api/uploads/file`

### Content-Type

```text
multipart/form-data
```

### 表单字段

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| file | binary | 是 | 图片文件 |

### 成功响应

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "storageKey": "uploads/2026/03/25/user_1001/original_xxx.jpg",
    "localPath": "/data/english-scenes/uploads/2026/03/25/user_1001/original_xxx.jpg",
    "publicUrl": "https://static.example.com/uploads/2026/03/25/user_1001/original_xxx.jpg",
    "contentType": "image/jpeg",
    "size": 123456
  }
}
```

## 5.7 `POST /api/tasks`

### 请求体

```json
{
  "jobType": "generate_private_scene",
  "sourceImagePath": "/data/english-scenes/uploads/2026/03/25/user_1001/original_xxx.jpg",
  "sceneTitle": null,
  "sceneHint": null
}
```

### 成功响应

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "jobId": "job_20260325_xxx",
    "status": "queued"
  }
}
```

## 5.8 `GET /api/tasks/{jobId}`

### 成功响应

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "jobId": "job_20260325_xxx",
    "status": "running",
    "progress": 70,
    "currentStage": "generate_tts",
    "result": {
      "sceneId": null
    },
    "errorMessage": null,
    "createdAt": "2026-03-25 18:00:00",
    "startedAt": "2026-03-25 18:00:05",
    "finishedAt": null
  }
}
```

## 5.9 `GET /api/membership`

### 成功响应

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "membershipStatus": "member",
    "membershipExpireAt": "2026-12-31 23:59:59"
  }
}
```

---

## 6. DTO 字段约束

## 6.1 SceneDetailDto 字段要求

| 字段 | 类型 | 约束 |
|---|---|---|
| sceneId | string | 必填，唯一 |
| title | string | 必填，1-255 |
| background | string | 必填，可直接访问 |
| cover | string | 可选 |
| items | array | 必填，可为空 |
| verbs | array | 必填，可为空 |
| meta | object | 必填 |

## 6.2 SceneItemDto 字段要求

| 字段 | 类型 | 约束 |
|---|---|---|
| id | string | 必填，场景内唯一 |
| word | string | 必填 |
| ipa | string | 可空字符串 |
| meaning | string | 可空字符串 |
| sentence | string | 必填 |
| sentenceTranslation | string | 必填 |
| rect | object | 必填 |
| audio | string/null | 可空 |

## 6.3 TaskDetailDto 字段要求

| 字段 | 类型 | 约束 |
|---|---|---|
| jobId | string | 必填 |
| status | string | `queued/running/succeeded/failed/canceled` |
| progress | int | 0-100 |
| currentStage | string | 必填 |
| result.sceneId | string/null | 成功后必填 |
| errorMessage | string/null | 失败时建议必填 |

---

## 7. 前端 TypeScript 风格 DTO 参考

即便小程序当前不使用 TypeScript，也建议按这个对象结构实现。

```ts
type MembershipStatus = 'free' | 'member' | 'vip';
type SceneType = 'public' | 'private';
type Visibility = 'public' | 'member' | 'private';
type JobStatus = 'queued' | 'running' | 'succeeded' | 'failed' | 'canceled';

interface UserDto {
  id: string;
  nickname: string;
  avatarUrl?: string;
  membershipStatus: MembershipStatus;
  membershipExpireAt?: string | null;
}

interface RectDto {
  l: number;
  t: number;
  w: number;
  h: number;
}

interface SceneItemDto {
  id: string;
  word: string;
  ipa: string;
  meaning: string;
  sentence: string;
  sentenceTranslation: string;
  rect: RectDto;
  audio?: string | null;
}

interface SceneVerbDto {
  id: string;
  word: string;
  ipa: string;
  meaning: string;
  sentence: string;
  sentenceTranslation: string;
  audio?: string | null;
}

interface SceneMetaDto {
  sceneType: SceneType;
  ownerUserId?: string | null;
  visibility: Visibility;
  version: number;
  category?: string | null;
  tags?: string[];
}

interface SceneDetailDto {
  sceneId: string;
  title: string;
  background: string;
  cover?: string | null;
  items: SceneItemDto[];
  verbs: SceneVerbDto[];
  meta: SceneMetaDto;
}

interface UploadResultDto {
  storageKey: string;
  localPath: string;
  publicUrl: string;
  contentType: string;
  size: number;
}

interface TaskDetailDto {
  jobId: string;
  status: JobStatus;
  progress: number;
  currentStage: string;
  result: {
    sceneId: string | null;
  };
  errorMessage?: string | null;
  createdAt: string;
  startedAt?: string | null;
  finishedAt?: string | null;
}
```

---

## 8. Worker 输出契约

Worker 最终输出必须能落成 `SceneDetailDto`。

建议 worker 最终生成文件：

```json
{
  "sceneId": "scene_20260325_abc123",
  "title": "营养早餐",
  "background": "/static/private-scenes/u_1001/scene_20260325_abc123/background.jpg",
  "cover": "/static/private-scenes/u_1001/scene_20260325_abc123/cover.jpg",
  "items": [],
  "verbs": [],
  "meta": {
    "sceneType": "private",
    "ownerUserId": "u_1001",
    "visibility": "private",
    "version": 1,
    "category": "food",
    "tags": []
  }
}
```

API 再决定是否转换为完整域名 URL。

---

## 9. FastAPI Pydantic 模型草案

```python
from pydantic import BaseModel
from typing import List, Optional

class RectDto(BaseModel):
    l: float
    t: float
    w: float
    h: float

class SceneItemDto(BaseModel):
    id: str
    word: str
    ipa: str = ""
    meaning: str = ""
    sentence: str
    sentenceTranslation: str
    rect: RectDto
    audio: Optional[str] = None

class SceneVerbDto(BaseModel):
    id: str
    word: str
    ipa: str = ""
    meaning: str = ""
    sentence: str
    sentenceTranslation: str
    audio: Optional[str] = None

class SceneMetaDto(BaseModel):
    sceneType: str
    ownerUserId: Optional[str] = None
    visibility: str
    version: int
    category: Optional[str] = None
    tags: List[str] = []

class SceneDetailDto(BaseModel):
    sceneId: str
    title: str
    background: str
    cover: Optional[str] = None
    items: List[SceneItemDto]
    verbs: List[SceneVerbDto]
    meta: SceneMetaDto
```

---

## 10. 联调建议

MVP 实施阶段建议按这个顺序联调：

1. 先 mock `GET /api/scenes/{sceneId}`
2. 小程序 runtime 页面先接 mock 数据
3. 再联调真实场景详情接口
4. 再联调上传接口
5. 再联调创建任务和查任务
6. 最后接 worker 真正产出的 scene JSON

这样能最小化前后端互相阻塞。

---

## 11. 结论

MVP 阶段真正要锁死的不是数据库细节，而是：

- `SceneDetailDto`
- `TaskDetailDto`
- 上传返回 DTO
- 统一错误结构

只要这几份 DTO 先稳定，前端、小程序 runtime 页、API、worker 都能并行开发。

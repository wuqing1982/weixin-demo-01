# Server API

这份文档不再讨论大方向，直接约束当前第一版联调协议。

目标只有一个：

小程序前端模板页 -> 调后端接口 -> 返回场景 JSON -> 展示图片 -> 点击热点播放 mp3

## 当前联调基准

后端字段必须对齐这套前端代码：

- [miniapp_scaffold/services/scene.js](E:/202603/weixin-demo-01/miniapp_scaffold/services/scene.js)
- [miniapp_scaffold/pages/library/index.js](E:/202603/weixin-demo-01/miniapp_scaffold/pages/library/index.js)
- [miniapp_scaffold/pages/scene_runtime/index.js](E:/202603/weixin-demo-01/miniapp_scaffold/pages/scene_runtime/index.js)
- [miniapp_scaffold/pages/shared/scene-page.js](E:/202603/weixin-demo-01/miniapp_scaffold/pages/shared/scene-page.js)

也就是说，第一版不要返回另一套 `id/imageUrl/hotspots/audioUrl` 协议；直接返回当前 runtime 页已经能消费的结构。

## 响应约定

所有成功响应统一返回：

```json
{
  "code": 0,
  "data": {}
}
```

失败响应统一返回：

```json
{
  "code": 4004,
  "message": "scene not found"
}
```

## 接口 1：场景列表

```http
GET /api/scenes
```

支持查询参数：

- `type`: 默认 `public`
- `page`: 默认 `1`
- `pageSize`: 默认 `20`

响应：

```json
{
  "code": 0,
  "data": {
    "list": [
      {
        "sceneId": "scene_breakfast",
        "title": "营养早餐",
        "coverUrl": "https://e.cps.vin/assets/images/breakfast.jpg",
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

说明：

- 前端列表页读的是 `data.list`
- 列表项字段必须包含 `sceneId` 和 `coverUrl`
- `category`、`visibility`、`sceneType` 当前也会直接显示或透传

## 接口 2：场景详情

```http
GET /api/scenes/{sceneId}
```

响应：

```json
{
  "code": 0,
  "data": {
    "sceneId": "scene_breakfast",
    "title": "营养早餐",
    "background": "https://e.cps.vin/assets/images/breakfast.jpg",
    "cover": "https://e.cps.vin/assets/images/breakfast.jpg",
    "items": [
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
        "audio": "https://e.cps.vin/assets/audio/breakfast/breakfast_en-US-JennyNeural_US_female_porridge_i_eat_porridge_for_breakfast.mp3"
      }
    ],
    "verbs": [
      {
        "id": "v1",
        "word": "eat",
        "ipa": "/iːt/",
        "meaning": "吃",
        "sentence": "I eat boiled eggs.",
        "sentenceTranslation": "我吃煮鸡蛋。",
        "audio": "https://e.cps.vin/assets/audio/breakfast/breakfast_en-US-JennyNeural_US_female_v1_i_eat_boiled_eggs.mp3"
      }
    ],
    "meta": {
      "sceneType": "public",
      "visibility": "member",
      "category": "food",
      "version": 1,
      "tags": ["breakfast", "food"]
    }
  }
}
```

说明：

- 页面背景图字段是 `background`，不是 `imageUrl`
- 热点字段是 `items`，不是 `hotspots`
- 热点位置字段是 `rect.l/t/w/h` 百分比，不是绝对像素 `x/y`
- 音频字段是 `audio`，不是 `audioUrl`
- 句子中文字段优先用 `sentenceTranslation`，兼容 `sentence_translation`

## 接口 3：我的场景

```http
GET /api/my/scenes
```

第一版可以先返回空列表，目的是让页面联调时不报错。

```json
{
  "code": 0,
  "data": {
    "list": [],
    "total": 0,
    "page": 1,
    "pageSize": 20
  }
}
```

## 接口 4：健康检查

```http
GET /api/health
```

响应：

```json
{
  "code": 0,
  "data": {
    "status": "ok"
  }
}
```

## 资源策略

第一版直接复用仓库里的本地资源目录，由后端统一对外暴露：

- `/assets/images/*.jpg`
- `/assets/audio/**/*`

这样可以先把 API 联调跑通，不需要先上对象存储。

## 本地运行

后端目录：

```txt
backend/
  app/
  data/
  requirements.txt
```

启动方式：

```bash
cd backend
PUBLIC_BASE_URL=https://e.cps.vin python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## 当前约束

- 小程序前端默认请求 `https://e.cps.vin/api`
- 后端进程本身可以只监听 `127.0.0.1:8000`，再由 Nginx 反向代理到 `https://e.cps.vin`
- 返回给前端的图片和音频地址依赖 `PUBLIC_BASE_URL`
- 要做微信预览和真机联调，需要把 `https://e.cps.vin` 配进小程序后台合法域名

## 第一版范围

这一版只做下面 4 件事：

- 场景列表可拉取
- 场景详情可拉取
- 图片可显示
- mp3 可播放

先不要把登录、上传、任务队列、AI 生成一起塞进来。

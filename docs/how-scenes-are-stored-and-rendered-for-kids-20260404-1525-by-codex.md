# 场景图片和音频是怎么保存的，以及小程序怎么把它们显示成页面

更新时间：2026-04-04 15:25 UTC

这篇文档用“给 12 岁孩子讲编程课”的方式来解释一件事：

**一张图片和一堆 mp3，是怎么一步一步变成一个可以点、可以听的场景页面的。**

我们会讲四个问题：

1. 这些图片和 mp3 保存在服务器哪里
2. 后端 API 怎么把它们找出来
3. 小程序怎么把它们画成页面
4. 这些功能在代码里分别写在哪些文件

---

## 1. 先把整个系统想成一个“玩具工厂”

你可以把这个项目想成一个玩具工厂。

工厂里有三种东西：

- 原材料
  - 比如用户刚上传的图片
- 半成品
  - 比如后端正在处理的任务
- 成品
  - 比如已经做好的场景页、背景图、音频

这三种东西都要有地方放。

所以系统里其实有好几个“仓库”。

---

## 2. 图片和音频到底保存在什么目录

### 2.1 公开场景的资源放在哪里

公开场景就是系统一开始就准备好的内容。

比如：

- 早餐
- 动物园

它们的文件放在这里：

```text
/www/wwwroot/e.cps.vin/weixin-demo-01/assets/images/
/www/wwwroot/e.cps.vin/weixin-demo-01/assets/audio/
/www/wwwroot/e.cps.vin/weixin-demo-01/backend/data/scenes.json
```

意思是：

- `assets/images/`
  - 放背景图
- `assets/audio/`
  - 放公开场景的 mp3
- `backend/data/scenes.json`
  - 放“这个场景有哪些热点、哪些动词、每条音频地址是什么”

你可以把它想成：

```text
图片仓库 + 音频仓库 + 说明书
```

---

### 2.2 用户自己上传的新场景放在哪里

当你在小程序里拍照上传时，系统会产生三类新文件。

#### 第一类：上传原图

放在这里：

```text
/www/wwwroot/e.cps.vin/weixin-demo-01/assets/uploads/<uploadId>/source.jpg
```

比如你最新那次成功上传，原图就在这里：

- [source.jpg](/www/wwwroot/e.cps.vin/weixin-demo-01/assets/uploads/upload_20260404144235_933a52/source.jpg)

这就像：

```text
快递刚送到仓库，还没开始加工
```

#### 第二类：生成后的背景图和 mp3

放在这里：

```text
/www/wwwroot/e.cps.vin/weixin-demo-01/assets/generated/<sceneId>/
```

比如你最新生成成功的那个场景，它的目录是：

- [scene_user_20260404144237_88b7f9](/www/wwwroot/e.cps.vin/weixin-demo-01/assets/generated/scene_user_20260404144237_88b7f9)

里面有：

- 背景图：
  - [background.jpg](/www/wwwroot/e.cps.vin/weixin-demo-01/assets/generated/scene_user_20260404144237_88b7f9/background.jpg)
- 一堆 mp3：
  - 例如 `shower_head...mp3`
  - `window...mp3`
  - `trash_can...mp3`

这就像：

```text
场景已经做好了，成品都放进成品库
```

#### 第三类：记录这些场景的“账本”

放在这里：

```text
/www/wwwroot/e.cps.vin/weixin-demo-01/backend/data/uploads.json
/www/wwwroot/e.cps.vin/weixin-demo-01/backend/data/tasks.json
/www/wwwroot/e.cps.vin/weixin-demo-01/backend/data/generated_scenes.json
```

它们分别记录：

- `uploads.json`
  - 谁上传了什么图
- `tasks.json`
  - 任务是不是做完了
- `generated_scenes.json`
  - 这个新场景有哪些热点、动词、背景图和音频

所以你可以把它们理解为：

```text
仓库清单 + 任务本 + 成品目录
```

---

## 3. 用一张简图看懂“磁盘目录 -> 后端 API -> 小程序页面”

这是最重要的一张图。

```text
┌──────────────────────────────────────────────┐
│                服务器磁盘目录                 │
├──────────────────────────────────────────────┤
│ assets/images/            公开背景图          │
│ assets/audio/             公开音频            │
│ assets/uploads/           用户上传原图        │
│ assets/generated/         生成后的背景图/mp3  │
│ backend/data/scenes.json  公开场景说明书      │
│ backend/data/uploads.json 上传记录本          │
│ backend/data/tasks.json   任务记录本          │
│ backend/data/generated_scenes.json 私人场景本 │
└──────────────────────┬───────────────────────┘
                       │
                       │ 读取文件、组织数据
                       v
┌──────────────────────────────────────────────┐
│                 后端 FastAPI                  │
├──────────────────────────────────────────────┤
│ GET  /api/scenes                             │
│ GET  /api/scenes/{sceneId}                   │
│ GET  /api/my/scenes                          │
│ POST /api/uploads/image                      │
│ POST /api/my/tasks/scene-generate            │
│ GET  /api/my/tasks/{taskId}                  │
└──────────────────────┬───────────────────────┘
                       │
                       │ 返回 JSON 数据
                       │ 和图片/音频地址
                       v
┌──────────────────────────────────────────────┐
│                微信小程序前端                 │
├──────────────────────────────────────────────┤
│ pages/library          场景列表页             │
│ pages/create_scene     上传和创建任务页       │
│ pages/my_scenes        我的私人场景页         │
│ pages/scene_runtime    统一场景显示页         │
└──────────────────────────────────────────────┘
```

这张图的意思是：

- 磁盘目录里真的有图片和 mp3
- 后端 API 去读这些文件和 JSON
- 小程序不是直接翻服务器目录
- 小程序是先问 API，再拿 API 给它的答案去显示页面

---

## 4. 给 12 岁孩子讲：场景页为什么不是“凭空变出来的”

假设你在小程序里看到一个浴室场景页。

页面里有：

- 背景图
- 淋浴喷头热点
- 窗户热点
- 垃圾桶热点
- 点击后还能播放英语音频

这不是“页面自己会变出来”的。

实际上它是这样来的：

### 第一步：服务器上先有图片和 mp3

背景图文件就躺在这里：

- [background.jpg](/www/wwwroot/e.cps.vin/weixin-demo-01/assets/generated/scene_user_20260404144237_88b7f9/background.jpg)

音频文件也躺在同一目录里。

### 第二步：服务器上还有一份“场景说明书”

说明书在：

- [generated_scenes.json](/www/wwwroot/e.cps.vin/weixin-demo-01/backend/data/generated_scenes.json)

这份说明书里会告诉后端：

- 这个场景叫啥
- 背景图在哪里
- 哪些地方有热点
- 每个热点的英文是什么
- 每个热点的句子是什么
- 每条音频在哪里

所以，场景页本质上就是：

```text
背景图 + 热点坐标 + 文字 + 音频地址
```

### 第三步：小程序向后端要这份说明书

小程序会请求：

```text
GET /api/scenes/{sceneId}
```

比如：

```text
GET /api/scenes/scene_user_20260404144237_88b7f9
```

后端把说明书读出来，再变成前端更容易用的格式，发回小程序。

### 第四步：小程序把说明书画成页面

统一场景页会做这几件事：

1. 把背景图放到页面上
2. 按 `rect.l/t/w/h` 在图片上画热点框
3. 把动词芯片画出来
4. 点击热点时显示文字
5. 再用音频地址去播放 mp3

于是你看到的就是一个“会说话的场景页面”。

---

## 5. 小程序里的代码是怎么做这件事的

### 5.1 入口页面在哪里

这个项目里，小程序页面主要在：

```text
/www/wwwroot/e.cps.vin/weixin-demo-01/pages/
```

你可以把这个目录理解为“小程序里的教室走廊”。

每个文件夹是一间教室：

- `home/`
  - 首页
- `library/`
  - 场景库页
- `create_scene/`
  - 上传图片和创建任务页
- `my_scenes/`
  - 我的私人场景页
- `scene_runtime/`
  - 统一场景详情页
- `shared/`
  - 公共模板和公共逻辑

---

### 5.2 小程序怎么拿场景数据

代码文件：

- [scene.js](/www/wwwroot/e.cps.vin/weixin-demo-01/services/scene.js)
- [api.js](/www/wwwroot/e.cps.vin/weixin-demo-01/services/api.js)

这里的想法很简单：

- `services/scene.js`
  - 专门负责“打电话问场景”
- `services/api.js`
  - 专门负责“真正拨电话”

比如：

- `getSceneList()`
  - 问公开场景列表
- `getSceneDetail(sceneId)`
  - 问某个场景详情
- `getMyScenes()`
  - 问我的私人场景列表

这样页面本身不用知道太多网络细节。

---

### 5.3 场景列表页怎么工作

代码文件：

- [index.js](/www/wwwroot/e.cps.vin/weixin-demo-01/pages/library/index.js)
- [index.wxml](/www/wwwroot/e.cps.vin/weixin-demo-01/pages/library/index.wxml)

它会做两件事：

1. 请求公开场景
2. 请求我的私人场景

拿到结果后，把每个场景渲染成卡片：

- 场景封面图
- 场景标题
- 场景分类

点一下卡片，就跳去统一场景页。

---

### 5.4 创建场景页怎么工作

代码文件：

- [index.js](/www/wwwroot/e.cps.vin/weixin-demo-01/pages/create_scene/index.js)
- [upload.js](/www/wwwroot/e.cps.vin/weixin-demo-01/services/upload.js)
- [task.js](/www/wwwroot/e.cps.vin/weixin-demo-01/services/task.js)

这是整个“生成场景”功能里最重要的前端页面。

它的工作流程像这样：

```text
选图片
-> 本地压缩成 JPG
-> 上传图片
-> 创建任务
-> 每 2 秒问一次任务状态
-> 任务完成
-> 打开新场景
```

#### 选图片

它用的是：

- `wx.chooseMedia`

#### 本地压缩

它会：

- 先读原图信息
- 如果长边太大就缩到 `1600`
- 用隐藏 canvas 重新导出成 JPG

这一步的目的是：

- 减少上传流量
- 减少后端处理负担

#### 上传图片

它调用：

- `POST /api/uploads/image`

后端会返回一个：

- `uploadId`

#### 创建任务

它再调用：

- `POST /api/my/tasks/scene-generate`

后端会返回一个：

- `taskId`

#### 轮询任务

它每 2 秒调用：

- `GET /api/my/tasks/{taskId}`

如果任务完成，就能拿到：

- `sceneId`

然后小程序跳去统一场景页。

---

### 5.5 我的场景页怎么工作

代码文件：

- [index.js](/www/wwwroot/e.cps.vin/weixin-demo-01/pages/my_scenes/index.js)

这个页面很像“我的作品集”。

它负责：

- 请求 `GET /api/my/scenes`
- 把属于当前调试用户的私人场景列出来

所以你生成成功的新场景，之后就会在这里出现。

---

### 5.6 统一场景页怎么把数据画出来

代码文件：

- [index.js](/www/wwwroot/e.cps.vin/weixin-demo-01/pages/scene_runtime/index.js)
- [scene-page.js](/www/wwwroot/e.cps.vin/weixin-demo-01/pages/shared/scene-page.js)
- [scene-template.wxml](/www/wwwroot/e.cps.vin/weixin-demo-01/pages/shared/scene-template.wxml)
- [scene.wxss](/www/wwwroot/e.cps.vin/weixin-demo-01/pages/shared/scene.wxss)

这个页面非常重要，因为：

**不管是公开场景还是用户生成场景，最后都由它来显示。**

它做的事是：

1. 通过 `sceneId` 请求后端详情
2. 拿到：
   - `background`
   - `items`
   - `verbs`
3. 把 `background` 当成背景图显示
4. 用每个 item 的 `rect` 在图片上定位热点
5. 点击热点后显示：
   - 单词
   - 音标
   - 中文
   - 例句
6. 再播放这个热点的音频

所以统一场景页其实像一个“通用播放器”。

它不在乎场景内容来自哪里，它只在乎：

```text
你给我的数据长得对不对
```

---

## 6. 后端代码是怎么找这些文件的

后端主要在：

```text
/www/wwwroot/e.cps.vin/weixin-demo-01/backend/app/
```

你可以把这个目录想成“后厨办公室”。

里面每个文件都有分工。

---

### 6.1 `main.py` 是总经理

文件：

- [main.py](/www/wwwroot/e.cps.vin/weixin-demo-01/backend/app/main.py)

它的工作是：

- 定义所有 API
- 告诉系统该读哪个仓库
- 把内部数据整理成前端能用的格式

比如：

- `GET /api/scenes`
  - 从公开场景账本里找
- `GET /api/my/scenes`
  - 从私人场景账本里找
- `GET /api/scenes/{sceneId}`
  - 找某一个具体场景
- `POST /api/uploads/image`
  - 收图片
- `POST /api/my/tasks/scene-generate`
  - 建任务
- `GET /api/my/tasks/{taskId}`
  - 查进度

---

### 6.2 `upload_store.py` 是“收件员”

文件：

- [upload_store.py](/www/wwwroot/e.cps.vin/weixin-demo-01/backend/app/upload_store.py)

它负责：

- 收到图片
- 决定保存路径
- 把图片写到硬盘
- 在 `uploads.json` 里记一笔账

所以当你上传成功时，它就会做出像这样的目录：

```text
assets/uploads/upload_xxx/source.jpg
```

---

### 6.3 `task_store.py` 是“排队管理员”

文件：

- [task_store.py](/www/wwwroot/e.cps.vin/weixin-demo-01/backend/app/task_store.py)

它负责：

- 新建任务
- 把任务状态改成 `queued`
- 工人开始做时改成 `running`
- 做完后改成 `done`
- 出错时改成 `failed`

这就像甜品店门口的排号机。

---

### 6.4 `generated_scene_store.py` 是“成品管理员”

文件：

- [generated_scene_store.py](/www/wwwroot/e.cps.vin/weixin-demo-01/backend/app/generated_scene_store.py)

它负责：

- 保存生成好的新场景
- 读取某个场景
- 按用户列出私人场景

所以当场景生成成功后，它就把成品写进：

- [generated_scenes.json](/www/wwwroot/e.cps.vin/weixin-demo-01/backend/data/generated_scenes.json)

---

### 6.5 `worker_runner.py` 是真正干活的工人

文件：

- [worker_runner.py](/www/wwwroot/e.cps.vin/weixin-demo-01/backend/app/worker_runner.py)

它会不停做这件事：

```text
看看有没有新的任务排队
```

如果有，它就开始工作：

1. 找到上传图
2. 复制一份作为背景图
3. 调 `core100` 识别图片
4. 得到热点和动词
5. 调 TTS 生成 mp3
6. 把这些结果整理成场景结构
7. 保存成品

这就是为什么用户不用一直盯着后端，系统可以在后台慢慢做。

---

### 6.6 `scene_adapter.py` 是翻译官

文件：

- [scene_adapter.py](/www/wwwroot/e.cps.vin/weixin-demo-01/backend/app/scene_adapter.py)

它很重要。

因为：

- `core100` 返回的结构不一定正好是前端需要的
- 前端统一场景页只认固定格式

所以这个文件负责把：

```text
AI 识别结果
```

翻译成：

```text
小程序 runtime 页能直接渲染的场景结构
```

比如它会整理：

- 热点坐标
- 句子翻译
- 音频路径
- 场景 meta 信息

---

## 7. 一次完整流程，像故事一样讲

假设你拍了一张浴室照片。

整个系统会这样工作：

### 第一步：你在小程序里选图

创建场景页收到图片后：

- 先在手机端压缩成 JPG
- 再上传

### 第二步：后端把原图存起来

原图会存到：

```text
assets/uploads/upload_xxx/source.jpg
```

### 第三步：后端记一条任务

任务会写到：

```text
backend/data/tasks.json
```

### 第四步：worker 接单开始做

它会：

- 看图
- 找物体
- 写英语
- 生成音频

### 第五步：背景图和 mp3 被放到成品目录

比如：

```text
assets/generated/scene_user_xxx/background.jpg
assets/generated/scene_user_xxx/*.mp3
```

### 第六步：场景说明书写进 `generated_scenes.json`

这样后端就能知道：

- 这个场景叫什么
- 有哪些热点
- 音频在哪里

### 第七步：小程序打开统一场景页

统一场景页拿到后端返回的数据后：

- 显示背景图
- 画热点
- 点热点时弹出英文信息
- 再播放 mp3

最后你看到的，就是一个完整的场景学习页面。

---

## 8. 一张更像上课黑板的流程图

```text
你拍了一张图片
        │
        v
小程序 create_scene 页面
        │
        │ 先本地压缩成 JPG
        v
POST /api/uploads/image
        │
        v
assets/uploads/<uploadId>/source.jpg
        │
        v
POST /api/my/tasks/scene-generate
        │
        v
backend/data/tasks.json
        │
        v
worker_runner.py 后台工人开始干活
        │
        ├── 调 core100 看图识别
        │
        ├── 调 TTS 生成 mp3
        │
        └── 复制背景图
        v
assets/generated/<sceneId>/
        │
        ├── background.jpg
        └── *.mp3
        │
        v
backend/data/generated_scenes.json
        │
        v
GET /api/scenes/{sceneId}
        │
        v
pages/scene_runtime 统一场景页
        │
        ├── 显示背景图
        ├── 画热点
        ├── 显示单词/句子
        └── 播放 mp3
```

---

## 9. 这套代码设计里最聪明的地方是什么

如果给 12 岁孩子讲，我会特别强调这一点：

### 不是每个场景写一个页面

而是：

- 做一个通用页面
- 再把不同的场景数据喂进去

这就是为什么：

- 早餐场景能显示
- 动物园场景能显示
- 你自己拍的浴室场景也能显示

因为它们本质上都是：

```text
一张背景图 + 一些热点 + 一些音频
```

页面代码只写一次，但能显示很多内容。

这就叫：

```text
数据驱动页面
```

这是这个项目最值得学的编程思想之一。

---

## 10. 一句话总结给孩子听

这个项目就是：

**“先把图片和 mp3 存在服务器上，再让后端 API 把它们整理成一份场景说明书，最后让小程序用同一个通用页面，把说明书画成一个可以点击、可以听英语的场景页面。”**

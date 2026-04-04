# VPS 对接文档

本文档用于把当前 `weixin-demo-01` 项目交接到远程 VPS 继续开发和联调。

适用对象：

- 在远程 VPS 上继续接手开发
- 需要快速理解当前代码状态、已完成内容、阻塞点和下一步动作

日期：

- 2026-04-04

## 一句话概述

当前项目已经从“纯本地静态场景页”推进到“前端 runtime 模板 + 最小 FastAPI 后端 + `https://e.cps.vin` 域名方案”的状态。

目前最关键的未完成事项不是业务代码，而是服务器部署链路：

- GitHub 仓库建立并推送代码
- VPS 拉代码
- FastAPI 在 VPS 本机跑起来
- Nginx 把 `https://e.cps.vin/api` 和 `https://e.cps.vin/assets` 反代到 `127.0.0.1:8000`
- 微信小程序后台配置 `https://e.cps.vin` 为合法域名

## 当前目标

第一阶段只追求最小闭环：

- 小程序首页进入场景库
- 场景库从后端拉取场景列表
- 点击场景进入统一 runtime 场景页
- runtime 页从后端拉取场景详情
- 显示背景图
- 点击热点播放 mp3

先不做：

- 登录
- 上传
- 任务队列
- AI 生成
- 数据库

## 当前代码结构

### 前端根目录小程序

当前实际要联调的是仓库根目录这套小程序，不是 `miniapp_scaffold`。

关键入口：

- [app.json](E:/202603/weixin-demo-01/app.json)
- [app.js](E:/202603/weixin-demo-01/app.js)
- [runtime.js](E:/202603/weixin-demo-01/config/runtime.js)

当前首页与联调页面：

- [index.js](E:/202603/weixin-demo-01/pages/home/index.js)
- [index.js](E:/202603/weixin-demo-01/pages/library/index.js)
- [index.js](E:/202603/weixin-demo-01/pages/scene_runtime/index.js)

统一 runtime 模板：

- [scene-page.js](E:/202603/weixin-demo-01/pages/shared/scene-page.js)
- [scene-template.wxml](E:/202603/weixin-demo-01/pages/shared/scene-template.wxml)
- [scene.wxss](E:/202603/weixin-demo-01/pages/shared/scene.wxss)

前端 API 服务层：

- [api.js](E:/202603/weixin-demo-01/services/api.js)
- [scene.js](E:/202603/weixin-demo-01/services/scene.js)
- [config.js](E:/202603/weixin-demo-01/services/config.js)

### 后端

最小 FastAPI 后端已经建立：

- [main.py](E:/202603/weixin-demo-01/backend/app/main.py)
- [scene_store.py](E:/202603/weixin-demo-01/backend/app/scene_store.py)
- [settings.py](E:/202603/weixin-demo-01/backend/app/settings.py)
- [scenes.json](E:/202603/weixin-demo-01/backend/data/scenes.json)

启动脚本：

- [start-local-api.ps1](E:/202603/weixin-demo-01/backend/start-local-api.ps1)
- [start-api.sh](E:/202603/weixin-demo-01/backend/start-api.sh)

## 已完成内容

### 1. 清理了问题场景

“城市景观”页面和对应音频资源已删除，不再参与当前联调链路。

### 2. 前端从静态展示扩展为 API 驱动

已新增：

- 首页
- 场景库页
- 统一 runtime 场景页
- API 请求封装

前端不再只依赖本地 `scene-data.js`，而是可以直接请求后端：

- `GET /api/scenes`
- `GET /api/scenes/{sceneId}`

### 3. FastAPI 最小接口已完成

已实现：

- `GET /api/health`
- `GET /api/scenes`
- `GET /api/scenes/{sceneId}`
- `GET /api/my/scenes`

并且后端会把仓库根目录下的 `assets/` 作为静态资源暴露。

### 4. 当前已内置两套样例场景

在 [scenes.json](E:/202603/weixin-demo-01/backend/data/scenes.json) 中已经配置：

- `scene_breakfast`
- `scene_zoo`

它们直接复用现有仓库资源：

- `assets/images/breakfast.jpg`
- `assets/images/zoo.jpg`
- `assets/audio/breakfast/*`
- `assets/audio/zoo/*`

### 5. 域名方案已切到 e.cps.vin

前端默认：

- `apiBaseUrl = https://e.cps.vin/api`
- `staticBaseUrl = https://e.cps.vin`

后端默认：

- `PUBLIC_BASE_URL = https://e.cps.vin`

也就是说，只要 VPS 上反代配置完成，前端无需再改域名。

## 当前接口协议

接口协议已经固定在：

- [server-api.md](E:/202603/weixin-demo-01/docs/server-api.md)

注意这里不是另一套抽象协议，而是严格按当前前端消费格式来定：

- 列表项字段是 `sceneId`、`title`、`coverUrl`
- 场景详情字段是 `sceneId`、`background`、`items`、`verbs`
- 热点坐标字段是 `rect.l/t/w/h`
- 音频字段是 `audio`

不要改成：

- `id`
- `imageUrl`
- `hotspots`
- `audioUrl`

否则前端要重新适配。

## 当前最关键的阻塞点

现在卡的不是代码逻辑，而是部署链路尚未完成。

具体表现：

- 小程序现在默认请求 `https://e.cps.vin/api`
- 如果 VPS 上没有把 `e.cps.vin` 反代到 FastAPI，前端就一定失败
- 如果微信后台没有把 `https://e.cps.vin` 配成合法域名，前端也一定失败

## VPS 推荐目录

用户当前计划的服务器站点根目录是：

```txt
/www/wwwroot/e.cps.vin
```

建议代码仓库放在下面这个子目录，而不是直接占满站点根：

```txt
/www/wwwroot/e.cps.vin/weixin-demo-01
```

推荐原因：

- 站点根和代码目录分开，部署更清晰
- 以后加 Nginx 配置、日志、备份文件不会和 Git 仓库混在一起
- `git pull`、回滚、切分支更稳

## VPS 接手步骤

### 1. 拉代码

如果 GitHub 仓库已经建立：

```bash
cd /www/wwwroot/e.cps.vin
git clone <repo-url> weixin-demo-01
cd /www/wwwroot/e.cps.vin/weixin-demo-01
```

后续更新：

```bash
cd /www/wwwroot/e.cps.vin/weixin-demo-01
git pull
```

### 2. 创建 Python 环境

```bash
cd /www/wwwroot/e.cps.vin/weixin-demo-01
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### 3. 先在服务器本机跑 FastAPI

```bash
cd /www/wwwroot/e.cps.vin/weixin-demo-01/backend
PUBLIC_BASE_URL=https://e.cps.vin ../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

或：

```bash
cd /www/wwwroot/e.cps.vin/weixin-demo-01/backend
PUBLIC_BASE_URL=https://e.cps.vin bash start-api.sh
```

### 4. 验证本机接口

在 VPS 上执行：

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/scenes
```

预期：

- `health` 返回 `code = 0`
- `scenes` 返回 `scene_breakfast` 和 `scene_zoo`

### 5. 再配置 Nginx 反向代理

目标：

- `https://e.cps.vin/api/*` -> `http://127.0.0.1:8000/api/*`
- `https://e.cps.vin/assets/*` -> `http://127.0.0.1:8000/assets/*`

这一步的细节见：

- [e-cps-vin-dev-debug.md](E:/202603/weixin-demo-01/docs/e-cps-vin-dev-debug.md)

### 6. 最后做小程序联调

外网浏览器先验证：

- `https://e.cps.vin/api/health`
- `https://e.cps.vin/api/scenes`
- `https://e.cps.vin/assets/images/breakfast.jpg`

这三项都通了，再去开微信开发者工具和真机调试。

## 建议的下一阶段计划

接手后建议严格按这个顺序往下做：

### 阶段 A：先把服务器链路打通

- GitHub 推送
- VPS 拉代码
- FastAPI 本机可用
- Nginx 反代可用
- `e.cps.vin` 外网可访问

### 阶段 B：完成小程序前后端联调验收

验收点：

- 首页可打开
- 场景库可显示 `scene_breakfast`、`scene_zoo`
- 进入详情页可显示背景图
- 点击热点可显示卡片
- 点击热点可播放 mp3

### 阶段 C：把后端运行方式固化

建议接下来补：

- `systemd` 服务
- Nginx 正式站点配置
- 部署更新流程
- 日志查看命令

### 阶段 D：再扩功能

等闭环稳定后再考虑：

- 登录
- 上传图片
- 任务中心
- AI 生成场景
- 数据库存储

## 不要在接手时做的事

接手 VPS 的第一轮不要同时做下面这些：

- 改接口字段协议
- 重构前端页面结构
- 接数据库
- 接上传
- 接 AI
- 改成另一套域名

否则你会失去当前“最小闭环”这个基准面，排错会变慢。

## 对接时优先看的文档

建议阅读顺序：

1. [vps-handoff-20260404.md](E:/202603/weixin-demo-01/docs/vps-handoff-20260404.md)
2. [e-cps-vin-dev-debug.md](E:/202603/weixin-demo-01/docs/e-cps-vin-dev-debug.md)
3. [server-api.md](E:/202603/weixin-demo-01/docs/server-api.md)

## 当前状态结论

代码层面：

- 前端联调页面已完成
- 后端最小接口已完成
- 域名方案已写入代码

部署层面：

- 仍待 VPS 上真正跑通

换句话说，当前项目已经完成了“可部署的第一版代码准备”，下一步应该从“写代码”切到“服务器部署 + 域名联调”。

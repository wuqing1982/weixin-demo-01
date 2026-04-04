# e.cps.vin 开发调试文档

这份文档约束当前这套仓库如何接到 `https://e.cps.vin/`。

目标：

- 小程序前端固定请求 `https://e.cps.vin/api`
- FastAPI 在服务器本机监听 `127.0.0.1:8000`
- Nginx 把 `https://e.cps.vin/api` 和 `https://e.cps.vin/assets` 反向代理到 FastAPI

## 代码里的当前默认值

前端默认域名已经写入：

- [runtime.js](E:/202603/weixin-demo-01/config/runtime.js)
- [app.js](E:/202603/weixin-demo-01/app.js)
- [config.js](E:/202603/weixin-demo-01/services/config.js)

后端默认公网资源基地址已经写入：

- [settings.py](E:/202603/weixin-demo-01/backend/app/settings.py)

默认值都是：

```txt
https://e.cps.vin
```

## 建仓建议

GitHub 仓库名直接用：

```txt
weixin-demo-01
```

服务器目录也建议保持一致，例如：

```txt
/srv/weixin-demo-01
```

这样本地、GitHub、服务器三处名字一致，后面排错最省事。

## 服务器部署步骤

### 1. 拉代码

```bash
cd /srv
git clone <your-github-repo-url> weixin-demo-01
cd weixin-demo-01
```

后续更新：

```bash
cd /srv/weixin-demo-01
git pull
```

### 2. 安装 Python 依赖

```bash
cd /srv/weixin-demo-01
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### 3. 手工启动 FastAPI

```bash
cd /srv/weixin-demo-01/backend
PUBLIC_BASE_URL=https://e.cps.vin ../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

也可以直接用脚本：

```bash
cd /srv/weixin-demo-01/backend
PUBLIC_BASE_URL=https://e.cps.vin bash start-api.sh
```

### 4. 验证本机接口

在服务器上执行：

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/scenes
```

预期：

- `health` 返回 `{"code":0,"data":{"status":"ok"}}`
- `scenes` 返回 `scene_breakfast` 和 `scene_zoo`

## Nginx 反向代理示例

假设 TLS 已经由你自己的 Nginx 站点配置接管，只展示核心 location：

```nginx
server {
    listen 443 ssl http2;
    server_name e.cps.vin;

    ssl_certificate     /path/to/fullchain.pem;
    ssl_certificate_key /path/to/privkey.pem;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /assets/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

注意：

- `proxy_pass` 这里不要把 `/api/` 再拼一遍，否则路径会错
- `/assets/` 也要代理出去，否则接口返回的图片和音频地址会 404
- `PUBLIC_BASE_URL` 必须和外网访问域名一致，这里就是 `https://e.cps.vin`

## 小程序后台配置

至少把下面这个域名配进去：

```txt
https://e.cps.vin
```

建议先加到这几类里：

- `request` 合法域名
- `downloadFile` 合法域名
- 后面如果接上传，再加 `uploadFile` 合法域名

## 联调检查顺序

### 1. 先检查公网

在电脑浏览器里打开：

```txt
https://e.cps.vin/api/health
https://e.cps.vin/api/scenes
https://e.cps.vin/assets/images/breakfast.jpg
```

只要这三项有任何一项失败，先别开微信开发者工具。

### 2. 再检查小程序首页

当前首页入口是：

- [app.json](E:/202603/weixin-demo-01/app.json)
- [home/index.js](E:/202603/weixin-demo-01/pages/home/index.js)

首页应先进入：

```txt
公开场景库
```

### 3. 再检查场景详情页

当前 runtime 页是：

- [index.js](E:/202603/weixin-demo-01/pages/scene_runtime/index.js)

它会先拉：

- `GET /api/scenes`
- `GET /api/scenes/{sceneId}`

再渲染背景图、热点和音频。

## 常见问题

### 1. `request:fail url not in domain list`

原因：

- 小程序后台还没把 `https://e.cps.vin` 配进合法域名
- 或者开发者工具缓存了旧配置

处理：

- 去微信公众平台补合法域名
- 开发者工具里重新编译，必要时清缓存

### 2. `502 Bad Gateway`

原因：

- Nginx 能到域名，但后端 `127.0.0.1:8000` 没起来
- 或 `proxy_pass` 路径写错

处理：

- 先 `curl http://127.0.0.1:8000/api/health`
- 再查 Nginx error log

### 3. 接口通了，但图片或音频 404

原因：

- `/assets/` 没做代理
- 返回给前端的资源地址不是 `https://e.cps.vin`
- `PUBLIC_BASE_URL` 没设置对

处理：

- 查 `https://e.cps.vin/api/scenes/scene_breakfast` 返回 JSON
- 确认 `background`、`coverUrl`、`audio` 都是 `https://e.cps.vin/assets/...`

### 4. 接口是对的，但前端还是旧地址

原因：

- 小程序还在跑旧代码包
- 或你服务器 `git pull` 后没重新拉起 FastAPI

处理：

- 确认 [runtime.js](E:/202603/weixin-demo-01/config/runtime.js) 已经是 `https://e.cps.vin`
- 重新编译小程序
- 重启后端服务

## 当前建议

最稳的顺序是：

1. 先把 GitHub 仓库建好并推代码。
2. 在服务器 `git pull` 并跑通 `127.0.0.1:8000/api/health`。
3. 再让 Nginx 跑通 `https://e.cps.vin/api/health`。
4. 最后再开微信开发者工具做前后端联调。

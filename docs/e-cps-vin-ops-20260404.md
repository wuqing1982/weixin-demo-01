# e.cps.vin 运维说明

日期：

- 2026-04-04

适用范围：

- VPS 上的 `weixin-demo-01` 小程序联调后端
- 域名 `https://e.cps.vin`

## 当前线上结构

代码目录：

```txt
/www/wwwroot/e.cps.vin/weixin-demo-01
```

站点根目录：

```txt
/www/wwwroot/e.cps.vin
```

后端监听：

```txt
127.0.0.1:8000
```

公网入口：

```txt
https://e.cps.vin/api
https://e.cps.vin/assets
```

## 当前已落地配置

### 1. FastAPI systemd 服务

服务名：

```txt
weixin-demo-api.service
```

systemd 单元文件：

- [/etc/systemd/system/weixin-demo-api.service](/etc/systemd/system/weixin-demo-api.service)

启动脚本：

- [start-api.sh](/www/wwwroot/e.cps.vin/weixin-demo-01/backend/start-api.sh)

服务的实际启动方式是：

```bash
cd /www/wwwroot/e.cps.vin/weixin-demo-01/backend
PUBLIC_BASE_URL=https://e.cps.vin bash start-api.sh
```

其中 `start-api.sh` 会优先使用：

```txt
/www/wwwroot/e.cps.vin/weixin-demo-01/.venv/bin/python
```

### 2. Nginx 反向代理

当前站点配置文件：

- [/www/server/panel/vhost/nginx/e.cps.vin.conf](/www/server/panel/vhost/nginx/e.cps.vin.conf)

当前关键规则：

- `^~ /api/` 反代到 `http://127.0.0.1:8000`
- `^~ /assets/` 反代到 `http://127.0.0.1:8000`

这里使用 `^~` 是为了避免被图片静态资源的正则 `location` 抢走，导致 `/assets/images/*.jpg` 返回 404。

## 常用命令

### 查看服务状态

```bash
systemctl status weixin-demo-api.service --no-pager -l
```

### 启动服务

```bash
systemctl start weixin-demo-api.service
```

### 停止服务

```bash
systemctl stop weixin-demo-api.service
```

### 重启服务

```bash
systemctl restart weixin-demo-api.service
```

### 开机自启

```bash
systemctl enable weixin-demo-api.service
```

### 查看最近日志

```bash
journalctl -u weixin-demo-api.service -n 100 --no-pager
```

### 持续追日志

```bash
journalctl -u weixin-demo-api.service -f
```

### 重载 Nginx

```bash
systemctl reload nginx
```

### 检查 Nginx 配置

```bash
nginx -t
```

## 发布更新流程

### 1. 拉代码

```bash
cd /www/wwwroot/e.cps.vin/weixin-demo-01
git pull
```

### 2. 如依赖变化，更新虚拟环境

```bash
cd /www/wwwroot/e.cps.vin/weixin-demo-01
.venv/bin/pip install -r backend/requirements.txt
```

### 3. 重启后端

```bash
systemctl restart weixin-demo-api.service
```

### 4. 验证本机接口

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/scenes
```

### 5. 验证公网接口

```bash
curl https://e.cps.vin/api/health
curl https://e.cps.vin/api/scenes
curl -I https://e.cps.vin/assets/images/breakfast.jpg
```

## 联调验收清单

公网至少要过这三项：

- `https://e.cps.vin/api/health`
- `https://e.cps.vin/api/scenes`
- `https://e.cps.vin/assets/images/breakfast.jpg`

小程序真机至少要过这几项：

- 首页进入“公开场景库”
- 能看到 `scene_breakfast` 和 `scene_zoo`
- 进入详情后背景图正常
- 点击热点可以播放 mp3

## 故障排查

### 1. 真机报 `request:fail url not in domain list`

先确认：

- 当前小程序 `appid` 是否正确
- 微信公众平台是否已把 `https://e.cps.vin` 配到 `request` 和 `downloadFile`
- 手机微信和开发者工具是否用了旧缓存

如果手机预览正常，但真机调试异常，优先怀疑微信侧缓存，不要先改后端。

### 2. 公网报 `502 Bad Gateway`

先查服务：

```bash
systemctl status weixin-demo-api.service --no-pager -l
journalctl -u weixin-demo-api.service -n 100 --no-pager
```

再查本机接口：

```bash
curl http://127.0.0.1:8000/api/health
```

最后查 Nginx：

```bash
tail -n 100 /www/wwwlogs/e.cps.vin.error.log
```

### 3. 接口 200，但图片或音频 404

优先检查两项：

- `e.cps.vin.conf` 里 `/assets/` 是否仍是 `^~ /assets/`
- `PUBLIC_BASE_URL` 是否仍是 `https://e.cps.vin`

再查详情接口返回：

```bash
curl https://e.cps.vin/api/scenes/scene_breakfast
```

确认 `background`、`cover`、`audio` 都是 `https://e.cps.vin/assets/...`

## 当前结论

到 2026-04-04 为止，这个项目已经不是“手工起一个临时 uvicorn”的状态，而是：

- systemd 管理 FastAPI
- Nginx 反代 `/api` 和 `/assets`
- 微信小程序可做真机联调

后续如果还有扩展，优先在这个基准面上增量修改，不要先推翻运行链路。

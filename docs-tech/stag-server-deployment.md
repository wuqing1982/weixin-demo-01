# stag.cps.vin 国内服务器部署记录

## 服务器信息

| 项目 | 值 |
|------|-----|
| IP | 118.24.42.187 |
| 系统 | Ubuntu 24.04 LTS |
| 内存 | 7.5G |
| 磁盘 | 59G（已用 38G） |
| 面板 | 宝塔 |
| Nginx | /www/server/nginx/ |
| PostgreSQL | /www/server/pgsql/ (v18.0) |

## 目录结构

```
/www/wwwroot/stag.cps.vin/          # 对应本机的 /www/wwwroot/e.cps.vin/
  weixin-demo-01/                   # 小程序 + 后端代码（从 GitHub 拉取）
    backend-rust/                   # Rust 后端
      .env                          # 环境配置（注意：代码里是 env 文件，需 cp env .env）
      target/release/backend-rust   # 编译好的二进制
    config/runtime.js               # 小程序环境切换（CURRENT_ENV）
```

## 架构

```
微信小程序 → https://stag.cps.vin (Nginx 443/SSL)
                  ↓ 反向代理
            127.0.0.1:8001 (Rust 后端)
                  ↓
            127.0.0.1:5432 (PostgreSQL weixin_saas_rust)
```

## Nginx 反向代理配置

配置文件：`/www/server/panel/vhost/nginx/stag.cps.vin.conf`

关键部分（已直接写入配置文件，不是通过宝塔面板的"反向代理"功能）：

```nginx
# 所有用户侧 /api/ 请求转发到 Rust 后端
location ^~ /api/ {
    proxy_pass http://127.0.0.1:8001;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    client_max_body_size 10m;
}

# 静态资源 → Rust后端(ServeDir)
location ^~ /assets/ {
    proxy_pass http://127.0.0.1:8001;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

修改后重载：`/www/server/nginx/sbin/nginx -t && /www/server/nginx/sbin/nginx -s reload`

## 数据库

- 连接：`postgresql://postgres@localhost:5432/weixin_saas_rust`（本地 trust 认证，无需密码）
- 管理：`su - postgres -c "/www/server/pgsql/bin/psql -d weixin_saas_rust"`
- 备份：`su - postgres -c "/www/server/pgsql/bin/pg_dump weixin_saas_rust" > backup.sql`
- 恢复：`su - postgres -c "/www/server/pgsql/bin/psql -d weixin_saas_rust" < backup.sql`

## Rust 后端

### 启动

```bash
cd /www/wwwroot/stag.cps.vin/weixin-demo-01/backend-rust
nohup ./target/release/backend-rust > /tmp/rust-backend.log 2>&1 &
```

### 查看日志

```bash
cat /tmp/rust-backend.log
tail -f /tmp/rust-backend.log
```

### 停止

```bash
kill $(pgrep -f 'target/release/backend-rust')
```

### 更新部署

本机编译后传二进制：

```bash
# 本机执行
cd /www/wwwroot/e.cps.vin/weixin-demo-01/backend-rust
cargo build --release
sshpass -p 'hq425771' scp target/release/backend-rust root@118.24.42.187:/www/wwwroot/stag.cps.vin/weixin-demo-01/backend-rust/target/release/backend-rust

# 远程重启
sshpass -p 'hq425771' ssh root@118.24.42.187 'kill $(pgrep -f "target/release/backend-rust"); sleep 1; cd /www/wwwroot/stag.cps.vin/weixin-demo-01/backend-rust && nohup ./target/release/backend-rust > /tmp/rust-backend.log 2>&1 &'
```

或者从 GitHub 拉取后在远程编译（需要安装 Rust 工具链）。

## .env 关键配置

```env
DATABASE_URL=postgresql://postgres@localhost:5432/weixin_saas_rust
PUBLIC_BASE_URL=https://stag.cps.vin
CORS_ALLOWED_ORIGINS=https://stag.cps.vin
SERVER_PORT=8001
```

注意：Git 仓库里文件名是 `env`，Rust 的 dotenvy 库读 `.env`。首次部署需 `cp env .env`。

## 小程序端切换环境

文件：`config/runtime.js`

```js
const CURRENT_ENV = 'staging';   // 国内测试
const CURRENT_ENV = 'production'; // 海外生产
```

## 微信后台域名白名单

request 合法域名：
```
https://e.cps.vin
https://stag.cps.vin
```

## 注意事项

1. 宝塔面板上的站点设置不要随意修改，反向代理是直接写在 Nginx 配置文件里的
2. SSL 证书通过宝塔管理，自动续期
3. Rust 后端目前没有 systemd 管理，重启后需手动启动
4. 数据库同步需手动操作（本机 dump → 传到远程 → import）

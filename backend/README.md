# Backend

最小 FastAPI 后端，专门用于给当前小程序模板页做第一轮联调。

## 功能

- `GET /api/health`
- `GET /api/scenes`
- `GET /api/scenes/{sceneId}`
- `GET /api/my/scenes`
- 静态暴露仓库根目录下的 `assets/`

## 启动

```bash
cd backend
PUBLIC_BASE_URL=https://e.cps.vin python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

启动后可访问：

- `http://127.0.0.1:8000/api/health`
- `http://127.0.0.1:8000/api/scenes`
- 通过反向代理访问 `https://e.cps.vin/api/health`

## 说明

当前样例数据直接复用仓库里的早餐和动物园资源，目的是先把前后端闭环跑起来，不引入数据库和对象存储。

`PUBLIC_BASE_URL` 用于生成返回给小程序的图片和音频公网地址。反向代理部署时，这个值应设置成 `https://e.cps.vin`。

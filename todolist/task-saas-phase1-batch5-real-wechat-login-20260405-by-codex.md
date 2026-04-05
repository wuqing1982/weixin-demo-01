# SaaS 第一阶段第五批：真实微信登录

更新时间：2026-04-05 UTC

目标：

- 接入微信 `code2Session`
- 用真实 `openid` / `unionid` 建立平台用户身份
- 保持现有小程序静默登录与平台 token 机制不变

范围约束：

- 本批只做真实微信登录
- 不做手机号绑定
- 不做公众号 / H5 / App 多端统一

任务清单：

- [x] 1. 新增微信 `code2Session` 客户端与 `session_key` 加密能力
- [x] 2. 接入真实登录模式到 `/api/auth/wechat/login`
- [x] 3. 按 `openid -> unionid` 顺序实现账号归并
- [x] 4. 补测试、配置说明与模式切换
- [ ] 5. 在具备 `WECHAT_MP_APP_SECRET` 后完成真实联调

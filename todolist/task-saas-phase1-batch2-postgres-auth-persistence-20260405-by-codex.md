# SaaS 第一阶段第二批：PostgreSQL 认证持久化

更新时间：2026-04-05 UTC

目标：

- 把认证、身份、refresh token 从 JSON 文件迁到 PostgreSQL
- 保持现有小程序登录、`/api/me`、refresh、logout 行为不变
- 先兼容当前字符串 `userId` / `sessionId`，不在这一批强切 UUID

范围约束：

- 本批只迁 auth 数据
- 场景、上传、任务仍保持 JSON 文件
- 微信登录仍保持 `mock` 模式，不在本批接真实 `code2Session`

任务清单：

- [x] 1. 新增 PostgreSQL auth 建表 SQL 和数据库访问层
- [x] 2. 实现 `PostgresAuthStore` 并接入运行时 store 工厂
- [x] 3. 增加 JSON `auth.json` -> PostgreSQL 的迁移脚本
- [x] 4. 补齐 PostgreSQL store / API 回归测试，并通过
- [x] 5. 执行迁移、切换后端到 PostgreSQL auth、完成联调验证

兼容性说明：

- 为避免打断当前 `debug_user_*`、`ownerId`、历史 token/session 链路，本批 PostgreSQL auth 表主键先使用 `varchar/text`
- 等后续业务表也迁入 PostgreSQL 后，再统一做 UUID 主键升级更稳妥

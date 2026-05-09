# 支付后引导绑定手机号 + 视频导出强制绑定

**日期**: 2026-05-10
**状态**: 已确认

## 背景

用户购买会员后，需要引导绑定手机号以获取全部权益（尤其是视频导出功能）。如果用户忽略引导，在导出视频时强制要求绑定。三层防护确保手机号绑定的覆盖率。

## 方案：可复用组件 + 前后端双检查

### 1. 新组件 `components/phone-bind-modal/`

4 个文件：`index.js`、`index.wxml`、`index.wxss`、`index.json`

**组件接口**：
- Properties: `visible` (Boolean), `title` (String, default 「绑定手机号，获取全部权益」), `description` (String, default 「绑定手机号后即可使用视频导出等全部会员功能」)
- Events: `bindsuccess` (携带 `{ maskedMobile }`), `close`

**内部逻辑**：
- `<button open-type="getPhoneNumber" bindgetphonenumber="onGetPhoneNumber">` 内嵌按钮
- 调用已有 `services/user.js` 的 `bindPhone(code)`
- 成功后更新 `getApp().globalData.currentUser` 的 `mobile` 和 `mobileVerified`
- 触发 `bindsuccess` 事件
- 提供关闭按钮触发 `close`

### 2. Products 页面（`pages/products/`）

**`index.json`**：注册 `phone-bind-modal` 组件

**`index.wxml`**：页面底部添加 `<phone-bind-modal visible="{{showPhoneBindModal}}" bind:bindsuccess="onPhoneBindSuccess" bind:close="onPhoneBindClose" />`

**`index.js`**：
- `data` 增加 `showPhoneBindModal: false`
- `onBuySku` 支付成功后（`wx.showToast` 之后）：若 `me.mobileVerified` 为 false → `setData({ showPhoneBindModal: true })`
- 新增 `onPhoneBindSuccess(e)`：关闭弹窗，更新 `me.mobileVerified = true`, `me.mobile = e.detail.maskedMobile`
- 新增 `onPhoneBindClose()`：`setData({ showPhoneBindModal: false })`（用户可忽略）

### 3. Scene Runtime 页面

**`pages/scene_runtime/index.json`**：注册 `phone-bind-modal` 组件

**`pages/scene_runtime/index.wxml`**：添加 `<phone-bind-modal>` 标签，文案为「绑定手机号后即可导出视频」/「为了保障您的账号安全，导出视频前需要绑定手机号」

**`shared/scene/scene-page.js`**：
- `data` 增加 `showPhoneBindModal: false`
- `onExportVideo` 在编辑模式检查之后、确认弹窗之前：检查 `getApp().globalData.currentUser.mobileVerified`，若 false → `setData({ showPhoneBindModal: true })` 并 return
- 新增 `onPhoneBindSuccess()`：关闭弹窗，自动继续调用 `_doExportVideo(sceneId)`
- 新增 `onPhoneBindClose()`：关闭弹窗（导出被阻止，不继续）

### 4. 后端（Rust）

**`backend-rust/src/api/video.rs`** `export_video` handler：
- 在现有 owner/admin 权限检查之后
- 调用 `db::users::find_user_by_id` 获取用户
- 若 `mobile_verified == false` → 返回 `AppError::Forbidden("请先绑定手机号后再导出视频")`

### 5. 不改动的部分

- 用户模型已有 `mobile` / `mobile_verified` 字段，不改
- `POST /api/me/bind-phone` 已完整实现，不改
- `services/user.js` 已有 `bindPhone()`，不改
- 数据库 schema 不改
- 首页已有绑定按钮保留

## 文件变更清单

| 文件 | 操作 |
|------|------|
| `components/phone-bind-modal/index.js` | 新建 |
| `components/phone-bind-modal/index.wxml` | 新建 |
| `components/phone-bind-modal/index.wxss` | 新建 |
| `components/phone-bind-modal/index.json` | 新建 |
| `pages/products/index.json` | 修改：注册组件 |
| `pages/products/index.wxml` | 修改：添加组件标签 |
| `pages/products/index.js` | 修改：支付后弹窗逻辑 |
| `pages/scene_runtime/index.json` | 修改：注册组件 |
| `pages/scene_runtime/index.wxml` | 修改：添加组件标签 |
| `shared/scene/scene-page.js` | 修改：导出前手机号检查 |
| `backend-rust/src/api/video.rs` | 修改：添加 mobile_verified 检查 |

## 验证步骤

1. Mock 模式购买 → 支付成功后弹出绑定手机号引导
2. 弹窗中点击绑定 → 微信授权 → 成功 → 弹窗关闭
3. 关闭弹窗不绑定 → 导出视频 → 弹出必须绑定的提示
4. 绑定后导出 → 正常流程
5. 已绑定用户购买 → 不弹窗
6. 后端：未绑定用户调 `/api/scenes/{id}/export-video` → 403

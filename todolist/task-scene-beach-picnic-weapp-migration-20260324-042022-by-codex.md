# Task: 迁移 `scene_beach_picnic.html` 为微信小程序原生页面

## 任务目标

请把 `https://e.cps.vin/core100/scene_beach_picnic.html` 迁移成微信小程序原生页面，不允许使用 `web-view`。优先复刻“背景图 + 热点点击 + 播放音频”的核心交互。

## 输入来源

- 网页地址: `https://e.cps.vin/core100/scene_beach_picnic.html`
- 源文件: `/www/wwwroot/e.cps.vin/core100/scene_beach_picnic.html`
- 参考方案: `/www/wwwroot/e.cps.vin/weixin/docs/scene-beach-picnic-weapp-migration-plan-20260324-042022-by-codex.md`

## 必做事项

- 先分析原网页资源与数据结构
- 直接输出以下完整可运行代码:
  - `pages/scene/scene.wxml`
  - `pages/scene/scene.wxss`
  - `pages/scene/scene.js`
  - `pages/scene/scene.json`
- 说明 `app.json` 注册方式
- 说明运行步骤

## 实现约束

- 不允许使用 `web-view`
- 优先保证“背景图 + 热点点击 + 播放音频”跑通
- 遇到无法直接迁移的 DOM/JS 逻辑时，必须改写成小程序原生实现
- 不要停留在方案层面
- 不能只给伪代码或结构草稿

## 资源与数据要求

- 使用原场景背景图 `assets/beach_picnic.png`
- 使用原页面 4 个热点数据:
  - `wine_glass`
  - `kombucha_bottle`
  - `cake`
  - `basket`
- 优先接入现成 MP3 资源
- 热点坐标继续使用百分比定位

## 建议技术实现

- 背景图: 小程序 `<image>`
- 热点层: 绝对定位 `<view>`
- 选中状态: `activeId`
- 浮层信息: `activeItem`
- 音频播放: `wx.createInnerAudioContext()`
- 页面卸载时销毁音频对象

## 非首版范围

- 浏览器 `speechSynthesis`
- 键盘快捷键
- 网页编辑器权限逻辑
- 外部 `window.PREV_SCENE/NEXT_SCENE`
- 数据库驱动的热点显示模式

## 完成定义

- 能在微信开发者工具中直接运行
- 背景图正常显示
- 4 个热点可点
- 点击后展示正确词卡
- 点击后播放正确音频
- 提供完整文件代码与接入说明

# `scene_beach_picnic.html` 迁移到微信小程序原生页面方案

## 基本信息

- 来源页面: `https://e.cps.vin/core100/scene_beach_picnic.html`
- 来源文件: `/www/wwwroot/e.cps.vin/core100/scene_beach_picnic.html`
- 迁移目标: 微信小程序原生页面
- 明确约束: 不允许使用 `web-view`
- 优先级: 先复刻“背景图 + 热点点击 + 播放音频”核心交互，再补充非核心能力

## 原网页资源与数据结构分析

### 1. 主背景图

- 背景图来源字段: `CONFIG.image`
- 当前值: `assets/beach_picnic.png`
- 实际文件: `/www/wwwroot/e.cps.vin/core100/assets/beach_picnic.png`
- 图片尺寸: `1440 x 1920`
- 页面渲染方式: `<img id="bg">` 全屏铺满，容器纵横比固定为 `9:16`

### 2. 热点数据结构

当前页面把场景数据内嵌在 `const CONFIG = { ... }` 中，核心字段为:

```js
{
  scene_id,
  scene_title,
  recommended_category,
  recommended_tags,
  image,
  items: [
    {
      id,
      word,
      ipa,
      meaning,
      sentence,
      sentence_translation,
      rect: { l, t, w, h },
      hidden,
      locked
    }
  ]
}
```

当前有效热点共 4 个:

1. `wine_glass`
2. `kombucha_bottle`
3. `cake`
4. `basket`

`rect` 采用百分比坐标，含义是相对于背景图容器的 `left/top/width/height` 百分比。该结构非常适合直接迁移到小程序页面 `data`，或抽成独立 `scene-data.js`。

### 3. 音频资源

页面使用三层音频策略:

1. 优先尝试本地 MP3
2. MP3 不存在时调用 Edge-TTS API
3. 再失败时回退浏览器 `speechSynthesis`

其中小程序可直接复用的是第 1 层，需改写的是第 2、3 层。

当前页面的音频映射为:

```js
{
  wine_glass: "wine_glass_look_at_the_wine_glasses_on",
  kombucha_bottle: "kombucha_bottle_there_are_two_kombucha_bottles_next",
  cake: "cake_the_cake_is_shaped_like_a",
  basket: "basket_the_basket_is_filled_with_flowers"
}
```

当前磁盘上已存在并且与本页 4 个热点对应的 MP3 资源只有一套:

- `voice_slide/beach_picnic/beach_picnic_en-US-JennyNeural_US_female_wine_glass_look_at_the_wine_glasses_on.mp3`
- `voice_slide/beach_picnic/beach_picnic_en-US-JennyNeural_US_female_kombucha_bottle_there_are_two_kombucha_bottles_next.mp3`
- `voice_slide/beach_picnic/beach_picnic_en-US-JennyNeural_US_female_cake_the_cake_is_shaped_like_a.mp3`
- `voice_slide/beach_picnic/beach_picnic_en-US-JennyNeural_US_female_basket_the_basket_is_filled_with_flowers.mp3`

这意味着第一阶段迁移应优先使用这 4 个现成 MP3，避免依赖浏览器能力。

### 4. 页面核心交互

原网页的核心交互链路如下:

1. 渲染背景图
2. 计算热点区域并绝对定位
3. 点击热点后高亮
4. 打开底部信息浮层
5. 展示单词、音标、中文、例句、翻译
6. 播放该热点对应的音频

这套交互可以 1:1 转写为小程序原生能力:

- 背景图: `<image>`
- 热点层: `<view wx:for>`
- 浮层: `<view>`
- 播放音频: `wx.createInnerAudioContext()`

## 迁移范围与优先级

### 第一阶段: 必须完成

- 原生渲染背景图
- 原生渲染热点
- 点击热点显示词卡信息
- 点击热点播放音频
- 同步热点激活态
- 输出 `pages/scene/scene.wxml`
- 输出 `pages/scene/scene.wxss`
- 输出 `pages/scene/scene.js`
- 输出 `pages/scene/scene.json`
- 说明 `app.json` 注册方式
- 说明本地运行步骤

### 第二阶段: 可降级或后补

- 语速滑块
- 口音切换
- 男女声音切换
- 浏览器 `speechSynthesis` 逻辑
- 桌面/平板/手机预览切换
- 键盘快捷键
- 页面级场景导航
- 编辑器权限和后台接口
- 数据库驱动的热点显示模式

## 小程序数据设计

建议把场景数据与页面逻辑拆开，新增独立数据模块，例如:

- `pages/scene/scene-data.js`

建议结构:

```js
module.exports = {
  sceneId: "beach_picnic",
  title: "海滩野餐",
  background: "/assets/beach_picnic.png",
  items: [
    {
      id: "wine_glass",
      word: "wine glass",
      ipa: "/waɪn ɡlæs/",
      meaning: "红酒杯",
      sentence: "Look at the wine glasses on the table.",
      sentenceTranslation: "看桌子上的酒杯。",
      rect: { l: 20, t: 40, w: 10, h: 10 },
      audio: "/assets/audio/beach_picnic/...mp3"
    }
  ]
}
```

与原网页相比，建议做两处简化:

- 将 `sentence_translation` 改成小程序风格字段 `sentenceTranslation`
- 将 `ID_TO_AUDIO_MAP` 合并进每个 item 的 `audio` 字段，减少运行时拼接逻辑

## 原网页逻辑到小程序原生实现的映射

### 可直接迁移

- `CONFIG.items` -> `Page.data.items`
- 百分比热点定位 -> `style="left:{{...}}%;top:{{...}}%;width:{{...}}%;height:{{...}}%"`
- `applyOverlay(item)` -> `setData({ activeItem: item })`
- `zone.active` -> `activeId === item.id`

### 需要改写

- `new Audio()` -> `wx.createInnerAudioContext()`
- 浏览器 `speechSynthesis` -> 删除或改为“无本地音频时不播放/提示缺失”
- DOM 查询与事件绑定 -> 小程序声明式绑定
- `localStorage` -> 如有需要用 `wx.setStorageSync`
- `window` 全局变量依赖 -> 页面 `data` 或本地常量

### 不纳入首版迁移

- `window.PREV_SCENE`
- `window.NEXT_SCENE`
- `window.DEFAULT_HOTSPOT_DISPLAY_MODE`
- `window.HAS_EDITOR_PERMISSION`
- `/membership/api/editor_state.php`

这些都依赖网页环境或后台系统，不应阻塞首版小程序页面交付。

## 输出要求

执行迁移时，最终结果不能停留在分析或伪代码，必须直接给出以下文件的完整可运行代码:

- `pages/scene/scene.wxml`
- `pages/scene/scene.wxss`
- `pages/scene/scene.js`
- `pages/scene/scene.json`

并额外说明:

- `app.json` 中如何注册页面
- 背景图与 MP3 应该放到小程序项目的哪个目录
- 微信开发者工具里的运行步骤

## 实施步骤

1. 先从原网页中抽出场景静态数据: 背景图、热点列表、音频路径。
2. 把现有背景图和 4 个热点 MP3 放入小程序可访问的静态资源目录。
3. 编写小程序页面结构，使用同一张背景图作为底图。
4. 用百分比绝对定位方式渲染热点层。
5. 点击热点时设置当前选中项，并展示底部信息卡。
6. 使用 `wx.createInnerAudioContext()` 播放该热点的 MP3。
7. 在页面卸载时销毁音频上下文，避免泄漏。
8. 在回答中直接输出完整代码，不再停留在方案描述。

## 验收标准

- 页面无需 `web-view`
- 背景图正常显示
- 4 个热点都可点击
- 点击后有明显激活态
- 底部词卡内容正确
- 对应 MP3 可播放
- 页面代码可直接粘贴进小程序项目运行
- `app.json` 注册方式清晰
- 运行步骤清晰

## 风险与处理

### 风险 1: 小程序静态资源路径不一致

处理方式:

- 在输出代码时使用项目内相对/绝对路径，并明确资源应复制到的目录。

### 风险 2: 原网页多音色逻辑在小程序中不可直接复用

处理方式:

- 首版只接入已存在的 `en-US + JennyNeural + female` MP3，保证可运行。

### 风险 3: 浏览器专属 API 不可用

处理方式:

- 统一改写为小程序原生 API，不保留 `window`、DOM、`speechSynthesis` 依赖。

## 结论

这个迁移任务的可行路径很明确。首版不追求把网页所有外围能力全部搬过去，而是优先落地“背景图 + 热点点击 + 播放音频”这条主链路。执行任务时应直接产出小程序页面完整代码，而不是继续停留在方案层。

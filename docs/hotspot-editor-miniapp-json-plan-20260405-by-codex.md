# 小程序热点编辑方案（JSON 第一阶段）

更新时间：2026-04-05 UTC

## 1. 目标

在当前微信小程序的场景详情页上增加“热点编辑”能力，先满足这几个要求：

- 在现有场景页面里直接进入编辑态，不新开一套 H5/PHP 编辑器
- 先用 JSON 文件作为唯一数据源
- 只编辑 `items[*].rect`，不改动单词、音频、句子生成链路
- 为后续迁移数据库保留稳定的数据结构和 API 形状

这个方案基于当前项目实际结构，而不是直接照搬 [HOTSPOT_EDITOR_DESIGN.md](/www/wwwroot/e.cps.vin/weixin-demo-01/docs/HOTSPOT_EDITOR_DESIGN.md) 里的 PHP/iframe 架构。

当前真实落点是：

- 前端统一场景页：[pages/scene_runtime/index.js](/www/wwwroot/e.cps.vin/weixin-demo-01/pages/scene_runtime/index.js)
- 场景模板：[pages/shared/scene-template.wxml](/www/wwwroot/e.cps.vin/weixin-demo-01/pages/shared/scene-template.wxml)
- 场景样式：[pages/shared/scene.wxss](/www/wwwroot/e.cps.vin/weixin-demo-01/pages/shared/scene.wxss)
- 场景接口：[services/scene.js](/www/wwwroot/e.cps.vin/weixin-demo-01/services/scene.js)
- 公开场景 JSON：[backend/data/scenes.json](/www/wwwroot/e.cps.vin/weixin-demo-01/backend/data/scenes.json)
- 私有场景 JSON：[backend/data/generated_scenes.json](/www/wwwroot/e.cps.vin/weixin-demo-01/backend/data/generated_scenes.json)
- 后端入口：[backend/app/main.py](/www/wwwroot/e.cps.vin/weixin-demo-01/backend/app/main.py)

---

## 2. 现状判断

当前系统已经具备热点编辑的最关键前提：

- 热点坐标已经存在，字段就是 `items[*].rect`
- 坐标已经是百分比，天然适合多端缩放
- 小程序页面已经把热点渲染为绝对定位区域
- 后端已经是文件型 JSON 存储，不需要先上数据库

也有几个现实约束：

- 当前没有成熟的角色权限体系，只有 `X-Debug-User-Id` 这一层调试身份
- 公开场景读取使用了 [backend/app/scene_store.py](/www/wwwroot/e.cps.vin/weixin-demo-01/backend/app/scene_store.py) 的缓存读法，还没有写入能力
- 当前场景页是“浏览页”，没有编辑模式、选中态管理、拖拽手势和保存接口

结论：第一阶段不该做“全新编辑系统”，而应该做“场景页内嵌编辑模式 + 后端 JSON 写回”。

---

## 3. 可选方案

### 方案 A：在 `scene_runtime` 页面里直接加入编辑模式

做法：

- 浏览态和编辑态共用同一张场景页
- 顶部工具栏增加“编辑开关”
- 编辑态下直接拖拽/缩放热点
- 保存时调用后端接口写回 JSON

优点：

- 复用现有渲染链路最多
- 编辑结果和最终浏览效果完全一致
- 最适合先用 JSON 快速落地

缺点：

- `scene_runtime` 页面状态会变复杂
- 要处理编辑态和浏览态的交互隔离

### 方案 B：新建一个独立的 `scene_editor` 页面

做法：

- 浏览页保持不动
- 新页面专门用于编辑热点

优点：

- 浏览逻辑和编辑逻辑隔离更干净
- 后续加更多编辑工具更容易

缺点：

- 需要重复维护一套场景渲染结构
- 未来容易出现“浏览页和编辑页显示不一致”

### 方案 C：先做服务端后台或 H5 编辑器，再同步回小程序

优点：

- PC 端编辑体验好

缺点：

- 不符合“给当前小程序前端页面加上这个功能”的目标
- 会引入第二套前端

### 推荐

第一阶段推荐 **方案 A**。

理由：

- 改动面最小
- 与当前架构最贴合
- 最容易保证“看到什么，保存什么”
- 将来迁移数据库时，前端基本不用重写

---

## 4. 第一阶段范围

### 做什么

- 在场景页内增加编辑模式
- 支持选择热点
- 支持拖动热点位置
- 支持缩放热点大小
- 支持保存到 JSON
- 支持重新进入页面后看到最新结果

### 暂时不做什么

- 不做数据库存储
- 不做多人并发编辑
- 不做自动保存到每一步
- 不编辑 `verbs`
- 不编辑热点文案、音频、图片资源
- 不做复杂权限后台

---

## 5. 交互设计

### 5.1 入口

在顶部工具栏增加一个仅对可编辑用户显示的按钮：

- 浏览态：`编辑`
- 编辑态：`完成`

同时保留一个显式保存按钮：

- 有改动时显示 `保存`
- 保存成功后提示 `已保存`

不建议第一阶段使用“每次拖动都自动保存”。

原因：

- 小程序触摸事件频繁，自动保存会带来很多无意义请求
- JSON 文件写入不是事务数据库，频繁落盘没有必要
- 显式保存更容易控制脏状态和失败重试

### 5.2 编辑态表现

编辑态下：

- 热点区域显示半透明边框
- 当前选中热点高亮
- 热点中心点继续保留，方便看命中位置
- 页面底部 overlay 默认隐藏，避免挡住编辑区域
- 左右切场景和点词播放能力禁用或弱化，避免误触

### 5.3 选中与调整方式

第一阶段建议采用“拖拽 + 四角手柄 + 微调按钮”的组合，而不是一次性做完整 8 向手柄。

具体规则：

- 点击热点：选中
- 拖动热点主体：移动整个矩形
- 拖动四角手柄：等比或非等比调整大小
- 底部增加微调工具：
  - 上下左右移动 1%
  - 宽高增减 1%

原因：

- 小程序触控面积有限，8 个手柄在手机上容易误触
- 四角手柄已经覆盖大多数场景
- 微调按钮可以补足精度

如果你坚持和设计文档完全一致，第二版再补 8 向手柄即可，数据结构不需要变化。

---

## 6. 数据结构方案

第一阶段继续沿用当前 `items[*].rect`：

```json
{
  "id": "corn",
  "word": "corn",
  "rect": {
    "l": 70.8,
    "t": 45.8,
    "w": 30.2,
    "h": 25.0
  }
}
```

建议补充少量元信息，但不改动现有渲染字段：

```json
{
  "meta": {
    "version": 2,
    "hotspotEditable": true,
    "hotspotUpdatedAt": "2026-04-05T12:00:00Z",
    "hotspotUpdatedBy": "debug_user_xxx"
  }
}
```

说明：

- `rect` 继续作为运行时唯一坐标源
- `meta.hotspotUpdatedAt`、`meta.hotspotUpdatedBy` 用于追踪最后一次编辑
- `meta.version` 可以继续沿用场景版本号，保存一次就加一

### 坐标标准

继续使用当前百分比坐标：

- `l`：左边距，0 到 100
- `t`：上边距，0 到 100
- `w`：宽度百分比
- `h`：高度百分比

保存前统一做约束：

- `l >= 0`
- `t >= 0`
- `w >= 最小宽度`
- `h >= 最小高度`
- `l + w <= 100`
- `t + h <= 100`

建议最小值：

- `w >= 4`
- `h >= 4`

---

## 7. 前端实现方案

### 7.1 状态设计

在场景页新增这些状态：

- `canEditHotspots`
- `editorMode`
- `editingItemId`
- `draftItems`
- `isDirty`
- `isSaving`
- `stageRect`

含义：

- `canEditHotspots`：当前用户能否看到编辑入口
- `editorMode`：是否处于编辑态
- `editingItemId`：当前选中的热点
- `draftItems`：编辑中的热点副本，不直接覆盖原始 `items`
- `isDirty`：是否有未保存改动
- `isSaving`：是否正在保存
- `stageRect`：场景舞台的尺寸信息，用于像素位移换算为百分比

### 7.2 页面结构调整

在 [pages/shared/scene-template.wxml](/www/wwwroot/e.cps.vin/weixin-demo-01/pages/shared/scene-template.wxml) 中：

- 顶部工具栏增加编辑按钮
- `scene-hotspots` 中根据 `editorMode` 切换渲染数据源
- 选中热点时渲染编辑边框和手柄
- 底部增加保存栏和微调控件

### 7.3 手势实现

推荐做法：

1. 页面渲染后通过 `SelectorQuery` 获取 `.scene-content` 的宽高
2. 记录 touchstart 的起点坐标和当前热点原始 `rect`
3. touchmove 时把像素位移换算成百分比增量
4. 实时更新 `draftItems`
5. touchend 时只更新内存，不自动提交

### 7.4 为什么要用 `draftItems`

不能直接改 `items`，原因有两个：

- 保存失败时难以回滚
- 浏览态和编辑态会相互污染

正确做法：

- 进入编辑态时：`draftItems = deepCopy(items)`
- 编辑中只改 `draftItems`
- 保存成功后：再把 `items` 替换成服务端返回值
- 取消编辑时：直接丢弃 `draftItems`

### 7.5 兼容当前浏览功能

浏览态保持现有逻辑不动：

- 点击热点仍然弹出 overlay
- 点击动词仍然播放音频

编辑态下改为：

- 点击热点只做选中
- 不弹 overlay
- 不播放音频
- 不响应左右切场景手势

这样用户意图更单一，误触更少。

---

## 8. 后端实现方案

### 8.1 接口设计

新增一个保存接口即可：

`POST /api/scenes/{sceneId}/hotspots`

请求体：

```json
{
  "items": [
    {
      "id": "corn",
      "rect": {
        "l": 69.5,
        "t": 47.2,
        "w": 28.0,
        "h": 22.5
      }
    }
  ]
}
```

返回：

```json
{
  "sceneId": "scene_breakfast",
  "items": [
    {
      "id": "corn",
      "rect": {
        "l": 69.5,
        "t": 47.2,
        "w": 28.0,
        "h": 22.5
      }
    }
  ],
  "meta": {
    "version": 2,
    "hotspotUpdatedAt": "2026-04-05T12:00:00Z",
    "hotspotUpdatedBy": "debug_user_xxx"
  }
}
```

说明：

- 第一阶段只更新 `items[*].rect`
- 服务端按 `id` 合并，不允许新增未知热点
- 保存成功后返回最新场景详情或至少返回最新 `items` + `meta`

### 8.2 存储抽象

建议新增一个统一的热点写入服务层，而不是让路由直接操作 JSON 文件。

可以增加一层概念：

- `SceneRepository`
- `update_scene_hotspots(scene_id, items, operator)`

第一阶段实现：

- public scene -> 写 [backend/data/scenes.json](/www/wwwroot/e.cps.vin/weixin-demo-01/backend/data/scenes.json)
- private scene -> 写 [backend/data/generated_scenes.json](/www/wwwroot/e.cps.vin/weixin-demo-01/backend/data/generated_scenes.json)

第二阶段迁移数据库时：

- 保持路由不变
- 把 repository 的底层实现从 JSON 切到 DB

这一步很关键，能避免未来前后端一起重写。

### 8.3 对现有存储类的调整

[backend/app/generated_scene_store.py](/www/wwwroot/e.cps.vin/weixin-demo-01/backend/app/generated_scene_store.py) 已经支持加锁写入，可以复用。

[backend/app/scene_store.py](/www/wwwroot/e.cps.vin/weixin-demo-01/backend/app/scene_store.py) 当前只有缓存读取，没有写入能力。第一阶段至少要补这两点：

- 加锁
- 更新后清理缓存，或者改成和 `GeneratedSceneStore` 类似的读写模式

否则 public scene 保存后，接口可能继续读到旧缓存。

### 8.4 权限规则

当前项目没有完整会员/角色系统，所以第一阶段建议用“最小可行权限”：

- 私有场景：只有 `ownerId` 对应用户可编辑
- 公开场景：仅允许服务端配置白名单用户编辑

不要在第一阶段把“VIP3”硬编码进小程序前端。

原因：

- 当前并没有稳定的会员等级来源
- 权限判断应该以服务端为准

可以在服务端加一个简单配置，例如：

- `HOTSPOT_EDITOR_PUBLIC_EDITORS=debug_user_a,debug_user_b`

前端只读取接口返回的 `canEditHotspots`。

---

## 9. 接口返回建议

建议扩展现有 `GET /api/scenes/{sceneId}` 返回值，在 `meta` 外再补一个前端可直接使用的字段：

```json
{
  "sceneId": "scene_breakfast",
  "title": "营养早餐",
  "background": "...",
  "items": [],
  "verbs": [],
  "meta": {},
  "capabilities": {
    "canEditHotspots": true
  }
}
```

这样前端无需自己猜权限。

如果想少改现有返回，也可以把权限放进 `meta`，但 `capabilities` 语义更清晰。

---

## 10. 数据库迁移预留

未来改数据库时，建议把 JSON 结构一比一映射到表，不改前端字段名。

推荐思路：

- `scenes` 表保存场景基础信息
- `scene_items` 表保存单词信息
- `scene_item_hotspots` 表保存 `rect`

示意：

```text
scene_item_hotspots
- scene_id
- item_id
- left_pct
- top_pct
- width_pct
- height_pct
- version
- updated_at
- updated_by
```

前端和 API 仍然继续收发：

```json
{
  "id": "corn",
  "rect": {
    "l": 69.5,
    "t": 47.2,
    "w": 28.0,
    "h": 22.5
  }
}
```

也就是：

- API 契约不变
- 前端编辑逻辑不变
- 只替换持久化实现

---

## 11. 实施步骤

### 第一批

- 扩展后端场景详情接口，返回 `canEditHotspots`
- 增加热点保存接口
- 补齐 public/private scene 的统一写入逻辑

### 第二批

- 场景页增加编辑态入口
- 引入 `draftItems`
- 加入选中态、高亮态、保存栏

### 第三批

- 实现拖拽移动
- 实现四角缩放
- 实现边界约束和最小尺寸约束

### 第四批

- 加入保存、失败回滚、脏状态提示
- 加入微调按钮
- 验证 public scene 和 private scene 都能保存

### 第五批

- 补测试
- 补使用说明文档
- 评估是否要继续做 8 向手柄

---

## 12. 测试策略

至少覆盖这些场景：

- 公开场景进入编辑态后拖动并保存
- 私有场景进入编辑态后拖动并保存
- 无权限用户看不到编辑入口
- 保存失败时本地编辑态不丢失
- 退出编辑态不保存时，刷新后仍是旧坐标
- 热点拖动到边缘时不会超出 0 到 100
- 不同设备模式下显示位置一致

需要特别注意一个风险：

当前背景图使用的是 `aspectFill`。如果未来某些背景图比例和场景容器不一致，裁切可能影响“热点和真实图像内容的视觉对应关系”。

所以第一阶段建议：

- 编辑态和浏览态严格复用同一套容器和同一套背景显示规则

不要一边编辑用 `aspectFit`，一边浏览用 `aspectFill`。否则保存出来的坐标会漂移。

---

## 13. 最终建议

这件事最稳的做法不是“重新做一个编辑器系统”，而是：

1. 在现有场景页里增加编辑模式
2. 前端只维护 `draftItems[*].rect`
3. 后端增加一个“按 sceneId 保存热点”的接口
4. 继续把 JSON 当第一阶段唯一真相源
5. 用 repository/adapter 方式把未来数据库迁移隔离在后端内部

这样可以最小成本上线第一版，同时不给第二阶段挖坑。

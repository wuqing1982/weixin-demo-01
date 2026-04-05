# 热点编辑器设计与实现文档

> 英语龙场景热点编辑系统 - 完整技术文档
> 版本: 2.0
> 更新日期: 2026-04-05

---

## 目录

1. [系统概述](#一系统概述)
2. [架构设计](#二架构设计)
3. [前端实现](#三前端实现)
4. [后端API](#四后端api)
5. [数据库设计](#五数据库设计)
6. [交互流程](#六交互流程)
7. [核心算法](#七核心算法)
8. [安全机制](#八安全机制)

---

## 一、系统概述

### 1.1 功能简介

热点编辑器是"英语龙"学习平台的核心功能，允许有权限的用户（管理员/VIP3）在场景图片上：

- **可视化编辑**热点位置（8方向调整大小）
- **拖拽移动**热点位置
- **实时保存**到数据库和场景文件
- **切换编辑/浏览模式**（红/绿圆点按钮）

### 1.2 用户界面

```
┌─────────────────────────────────────────────────────────────┐
│  [绿色圆点●] [红色圆点●]    场景导航 [←] [→]   [家]        │ ← 顶部控制栏
├─────────────────────────────────────────────────────────────┤
│                                                             │
│    ┌─────────────────────────────────────────┐              │
│    │                                         │              │
│    │    ┌─────┐      ┌───────────┐         │              │
│    │    │ palm├──┐   │  street   │         │              │
│    │    │tree │  │   │   lamp    │         │              │
│    │    └──┬──┘  │   └─────┬─────┘         │              │
│    │       │  ◆  │         │               │              │
│    │       └──●──┘         ◆               │              │ ← 场景图片
│    │     热点区域       可调整大小          │              │   (9:16比例)
│    │                                         │              │
│    │         ┌──────────────────┐            │              │
│    │         │    building      │            │              │
│    │         └────────●─────────┘            │              │
│    │                                         │              │
│    └─────────────────────────────────────────┘              │
│                                                             │
│  [💾 保存] [拖动条]                                          │ ← 浮动保存按钮
└─────────────────────────────────────────────────────────────┘
```

### 1.3 文件结构

```
/www/wwwroot/english.cps.vin/
├── v6/pages/hotspot-editor.php          # 编辑器控制面板
├── assets/hotspot-editor.js             # 核心编辑器逻辑
├── membership/api/
│   ├── editor_state.php                 # 编辑器状态API
│   └── save_hotspots.php               # 保存热点位置API
├── scenes/
│   ├── private/scene_demo_xxx.php      # 私有场景页面
│   └── public/scene_demo_xxx.php       # 公开场景页面
└── docs/HOTSPOT_EDITOR_DESIGN.md       # 本文档
```

---

## 二、架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                        用户浏览器                            │
│  ┌──────────────────┐    ┌──────────────────────────────┐  │
│  │ 热点控制面板     │    │ 场景页面                     │  │
│  │ (hotspot-editor)│    │ (scene_demo_xxx.php)         │  │
│  │                  │    │                              │  │
│  │ ┌──────────────┐ │    │ ┌────────────────────────┐   │  │
│  │ │ 启用/关闭按钮│ │    │ │ 场景图片 + 热点区域    │   │  │
│  │ │ 预览iframe   │ │    │ │ 绿/红圆点切换按钮      │   │  │
│  │ └──────────────┘ │    │ │ 可移动保存按钮         │   │  │
│  └──────────────────┘    │ └────────────────────────┘   │  │
│                          └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      JavaScript 层                          │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              hotspot-editor.js                         │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │ │
│  │  │ 八向调整手柄 │  │ 拖拽移动逻辑 │  │ 保存到服务器 │ │ │
│  │  │ (8 handles)  │  │ (startDrag)  │  │ (saveChanges)│ │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘ │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       API 层                                │
│  ┌──────────────────┐      ┌──────────────────────────────┐ │
│  │ editor_state.php │      │ save_hotspots.php            │ │
│  │ (GET/SET状态)    │      │ (保存热点坐标)               │ │
│  └──────────────────┘      └──────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      数据存储层                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ MySQL        │  │ 场景PHP文件  │  │ JSON备份文件     │  │
│  │ user_editor_ │  │ CONFIG.items │  │ hotspots_xxx.json│  │
│  │ _state 表    │  │ rect字段     │  │                  │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 核心组件关系

```
                    ┌──────────────────┐
                    │   用户点击       │
                    │  绿/红圆点按钮   │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ editor_state.php │
                    │  (更新数据库)    │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
        ┌─────────┐   ┌──────────┐   ┌──────────┐
        │  页面   │   │ 热点编辑 │   │  控制    │
        │  刷新   │   │   器JS   │   │  面板    │
        └────┬────┘   └────┬─────┘   └────┬─────┘
             │             │              │
             └─────────────┴──────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │  isHotspotEditorEnabled│
              │  (检查编辑器是否启用)  │
              └───────────┬────────────┘
                          │
            ┌─────────────┼─────────────┐
            ▼             ▼             ▼
      ┌──────────┐  ┌──────────┐  ┌──────────┐
      │  显示    │  │  隐藏    │  │  渲染    │
      │编辑手柄  │  │编辑手柄  │  │ 热点区域 │
      └──────────┘  └──────────┘  └──────────┘
```

---

## 三、前端实现

### 3.1 场景页面结构 (scene_demo_xxx.php)

#### HTML结构

```html
<body>
  <!-- 视图切换栏（左上角） -->
  <div class="view-switch" id="viewSwitch">
    <!-- 设备视图切换 -->
    <button data-view="mobile">手机</button>
    <button data-view="tablet">平板</button>
    <button data-view="desktop">桌面</button>
    
    <!-- 编辑器开关（仅管理员/VIP3可见） -->
    <span class="editor-toggle" id="editorToggle" style="display: none;">
      <button class="editor-btn" id="enableEditorBtn"></button>  <!-- 绿色圆点 -->
      <button class="editor-btn" id="disableEditorBtn"></button> <!-- 红色圆点 -->
    </span>
  </div>

  <!-- 场景导航（右上角） -->
  <div class="scene-nav">
    <a href="/membership" id="homeBtn">⌂</a>
    <button id="prevSceneBtn">←</button>
    <button id="nextSceneBtn">→</button>
  </div>

  <!-- 场景舞台 -->
  <div class="stage">
    <div class="frame" id="frame">
      <img class="bg" id="bg" src="xxx.webp" />
      
      <!-- 热点区域（动态生成） -->
      <div class="zone" data-id="0" style="left:...;top:...;width:...;height:...;"></div>
      
      <!-- 浮动控制栏 -->
      <div class="floating-controls">
        <!-- 语速控制、重音选择等 -->
      </div>
      
      <!-- 底部覆盖层（单词详情） -->
      <div class="overlay" id="overlay">
        <div class="word">palm tree</div>
        <div class="ipa">/pɑːm triː/</div>
        <div class="meaning">棕榈树</div>
        <div class="sentence">There is a palm tree in the park.</div>
      </div>
    </div>
  </div>
</body>
```

#### CSS关键样式

```css
/* ========== 编辑器开关按钮样式 ========== */
.view-switch .editor-toggle {
    display: flex;
    gap: 8px;
}

.view-switch .editor-btn {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    border: none;
    cursor: pointer;
    transition: all 0.2s;
}

/* 绿色圆点 - 启用编辑器 */
#enableEditorBtn {
    background: #4CAF50;
}

/* 红色圆点 - 关闭编辑器 */
#disableEditorBtn {
    background: #f44336;
}

/* 激活状态：添加白色边框 */
.editor-btn.active {
    box-shadow: 0 0 0 2px rgba(255,255,255,0.8);
}

/* 未激活状态：半透明 */
.editor-btn.inactive {
    opacity: 0.4;
}

/* ========== 编辑模式下隐藏控制栏 ========== */
body.hotspot-edit-mode .floating-controls {
    display: none !important;
}

/* ========== 热点基础样式 ========== */
.zone {
    position: absolute;
    border-radius: 14px;
    border: 2px solid rgba(255,255,255,0);
    background: rgba(255,255,255,0);
    cursor: pointer;
}

.zone:hover {
    border-color: rgba(255,255,255,.55);
    background: rgba(255,255,255,.10);
}

.zone.active {
    border-color: rgba(255,255,255,.95);
    background: rgba(255,255,255,.18);
    box-shadow: 0 0 0 2px rgba(255,255,255,.25);
}
```

### 3.2 热点编辑器核心逻辑 (hotspot-editor.js)

#### 3.2.1 八向调整手柄实现

```javascript
// 创建热点DOM结构
function createHotspotDom(index, data) {
    const zones = document.querySelectorAll('.zone');
    const el = zones[index];
    
    el.dataset.id = index.toString();
    el.classList.add('hotspot-editing');

    // 1. 添加标签（显示单词名称）
    const label = document.createElement('div');
    label.className = 'label';
    label.textContent = data.word || data.id;
    el.appendChild(label);

    // 2. 添加中心拖拽点（用于移动整个热点）
    const center = document.createElement('div');
    center.className = 'center-handle';
    center.dataset.handle = 'center';
    el.appendChild(center);

    // 3. 添加8个方向调整手柄
    // 位置：nw(西北/左上), n(北/上), ne(东北/右上)
    //       w(西/左),           e(东/右)
    //       sw(西南/左下), s(南/下), se(东南/右下)
    const positions = ['nw', 'n', 'ne', 'e', 'se', 's', 'sw', 'w'];
    positions.forEach(pos => {
        const h = document.createElement('div');
        h.className = `handle ${pos}`;
        h.dataset.handle = pos;
        el.appendChild(h);
    });

    hotspotEls.set(index.toString(), el);
    applyHotspotToDom(index.toString(), data);
    bindHotspotEvents(el);
}
```

#### 3.2.2 八向手柄CSS定位

```css
/* 手柄基础样式 */
.zone .handle {
    position: absolute;
    --size: 14px;
    width: var(--size);
    height: var(--size);
    border-radius: 999px;
    background: rgba(255,255,255,.92);
    border: 2px solid rgba(0,0,0,.35);
    box-shadow: 0 6px 18px rgba(0,0,0,.25);
    z-index: 20;
    opacity: 0;  /* 默认隐藏 */
}

/* 仅在编辑模式下显示 */
body.hotspot-edit-mode .zone.selected .handle {
    opacity: 1;
}

/* 8个方向的具体定位 */
.zone .handle.nw { 
    left: calc(var(--size) / -2); 
    top: calc(var(--size) / -2); 
    cursor: nwse-resize;  /* 双向箭头 */
}
.zone .handle.n { 
    left: 50%; 
    top: calc(var(--size) / -2); 
    transform: translateX(-50%); 
    cursor: ns-resize;
}
.zone .handle.ne { 
    right: calc(var(--size) / -2); 
    top: calc(var(--size) / -2); 
    cursor: nesw-resize;
}
.zone .handle.e { 
    right: calc(var(--size) / -2); 
    top: 50%; 
    transform: translateY(-50%); 
    cursor: ew-resize;
}
.zone .handle.se { 
    right: calc(var(--size) / -2); 
    bottom: calc(var(--size) / -2); 
    cursor: nwse-resize;
}
.zone .handle.s { 
    left: 50%; 
    bottom: calc(var(--size) / -2); 
    transform: translateX(-50%); 
    cursor: ns-resize;
}
.zone .handle.sw { 
    left: calc(var(--size) / -2); 
    bottom: calc(var(--size) / -2); 
    cursor: nesw-resize;
}
.zone .handle.w { 
    left: calc(var(--size) / -2); 
    top: 50%; 
    transform: translateY(-50%); 
    cursor: ew-resize;
}

/* 中心拖拽点样式 */
.zone .center-handle {
    position: absolute;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
    width: 20px;
    height: 20px;
    border-radius: 999px;
    background: rgba(255,255,255,.85);
    border: 2px solid rgba(0,0,0,.35);
    opacity: 0;
    z-index: 19;
}

/* 十字图标 */
.zone .center-handle::before,
.zone .center-handle::after {
    content: "";
    position: absolute;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
    background: rgba(0,0,0,.65);
}
.zone .center-handle::before { width: 12px; height: 2px; }
.zone .center-handle::after { width: 2px; height: 12px; }
```

#### 3.2.3 拖拽移动实现

```javascript
function startDragMove(e, el) {
    e.preventDefault();
    el.setPointerCapture(e.pointerId);
    
    // 记录初始位置
    const start = {
        px: e.clientX,
        py: e.clientY,
        rect: getHotspotRectPx(el)  // 获取当前像素坐标
    };
    
    const { w: bw, h: bh } = getBox();  // 容器宽高

    function onMove(ev) {
        // 计算移动距离
        const dx = ev.clientX - start.px;
        const dy = ev.clientY - start.py;
        
        // 计算新位置
        let nx = start.rect.x + dx;
        let ny = start.rect.y + dy;
        
        // 限制在容器边界内
        nx = clamp(nx, 0, bw - start.rect.w);
        ny = clamp(ny, 0, bh - start.rect.h);
        
        // 应用到DOM
        el.style.left = `${nx}px`;
        el.style.top = `${ny}px`;
        
        // 同步到数据模型
        syncDomToModel(el);
    }

    function onUp() {
        el.releasePointerCapture(e.pointerId);
        window.removeEventListener('pointermove', onMove);
        window.removeEventListener('pointerup', onUp);
    }

    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
}
```

#### 3.2.4 八向调整大小实现

```javascript
function startResize(e, el, handlePos) {
    e.preventDefault();
    el.setPointerCapture(e.pointerId);

    const start = {
        px: e.clientX,
        py: e.clientY,
        rect: getHotspotRectPx(el)
    };
    const { w: bw, h: bh } = getBox();
    const minW = 30, minH = 30;  // 最小尺寸限制

    function onMove(ev) {
        const dx = ev.clientX - start.px;
        const dy = ev.clientY - start.py;
        let { x, y, w, h } = start.rect;

        // 根据手柄位置判断调整方向
        const hasN = ['n', 'nw', 'ne'].includes(handlePos);  // 北（上）
        const hasS = ['s', 'sw', 'se'].includes(handlePos);  // 南（下）
        const hasW = ['w', 'nw', 'sw'].includes(handlePos);  // 西（左）
        const hasE = ['e', 'ne', 'se'].includes(handlePos);  // 东（右）

        // 调整位置和大小的核心逻辑
        if (hasW) { 
            x = start.rect.x + dx;       // 向左移动左边框
            w = start.rect.w - dx;       // 宽度减小
        }
        if (hasE) { 
            w = start.rect.w + dx;       // 向右扩展
        }
        if (hasN) { 
            y = start.rect.y + dy;       // 向上移动上边框
            h = start.rect.h - dy;       // 高度减小
        }
        if (hasS) { 
            h = start.rect.h + dy;       // 向下扩展
        }

        // 应用最小尺寸限制
        if (w < minW) { 
            if (hasW) x -= (minW - w);   // 如果左边调整，需要移动位置
            w = minW; 
        }
        if (h < minH) { 
            if (hasN) y -= (minH - h);   // 如果上边调整，需要移动位置
            h = minH; 
        }

        // 限制在容器内
        x = clamp(x, 0, bw - minW);
        y = clamp(y, 0, bh - minH);
        w = clamp(w, minW, bw - x);
        h = clamp(h, minH, bh - y);

        // 应用到DOM
        el.style.left = `${x}px`;
        el.style.top = `${y}px`;
        el.style.width = `${w}px`;
        el.style.height = `${h}px`;
        
        syncDomToModel(el);
    }

    function onUp() {
        el.releasePointerCapture(e.pointerId);
        window.removeEventListener('pointermove', onMove);
        window.removeEventListener('pointerup', onUp);
    }

    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
}
```

### 3.3 可移动保存按钮实现

```javascript
function addEditorControls() {
    // 创建浮动控制面板容器
    editorControls = document.createElement('div');
    editorControls.id = 'hotspot-editor-controls';
    editorControls.style.cssText = `
        position: fixed;
        top: 80px;
        left: 10px;
        z-index: 10000;
        display: none;
        user-select: none;
        touch-action: none;
    `;

    // 按钮容器
    const btnContainer = document.createElement('div');
    btnContainer.style.cssText = `
        position: relative;
        background: rgba(0, 0, 0, 0.85);
        backdrop-filter: blur(10px);
        border: 2px solid #4cd964;
        border-radius: 12px;
        padding: 10px 15px;
        padding-right: 50px;  /* 留出拖动条空间 */
        box-shadow: 0 5px 20px rgba(0,0,0,0.5);
    `;

    // 保存按钮
    const btnSave = document.createElement('button');
    btnSave.innerHTML = '💾 保存';
    btnSave.style.cssText = `
        background: linear-gradient(135deg, #4cd964 0%, #5ac55f 100%);
        color: white;
        border: none;
        padding: 10px 15px;
        border-radius: 8px;
        cursor: pointer;
        font-weight: bold;
        font-size: 14px;
        min-height: 44px;
        min-width: 80px;
    `;
    btnSave.onclick = saveChanges;
    btnContainer.appendChild(btnSave);

    // 拖动句柄（右侧竖条）
    const dragHandle = document.createElement('div');
    dragHandle.className = 'editor-drag-handle';
    dragHandle.style.cssText = `
        position: absolute;
        right: 12px;
        top: 50%;
        transform: translateY(-50%);
        width: 8px;
        height: 50px;
        border-radius: 4px;
        background: rgba(255, 255, 255, 0.6);
        border: 2px solid rgba(255, 255, 255, 0.8);
        cursor: grab;
    `;
    btnContainer.appendChild(dragHandle);
    editorControls.appendChild(btnContainer);

    // 拖动功能实现
    let isDragging = false;
    let dragOffset = { x: 0, y: 0 };

    function startDrag(e) {
        e.preventDefault();
        isDragging = true;
        
        const clientX = e.touches ? e.touches[0].clientX : e.clientX;
        const clientY = e.touches ? e.touches[0].clientY : e.clientY;
        
        const rect = editorControls.getBoundingClientRect();
        dragOffset.x = clientX - rect.left;
        dragOffset.y = clientY - rect.top;
        
        dragHandle.style.cursor = 'grabbing';
    }

    function onDrag(e) {
        if (!isDragging) return;
        e.preventDefault();
        
        const clientX = e.touches ? e.touches[0].clientX : e.clientX;
        const clientY = e.touches ? e.touches[0].clientY : e.clientY;
        
        const x = clientX - dragOffset.x;
        const y = clientY - dragOffset.y;
        
        // 限制在视口内
        const maxX = window.innerWidth - editorControls.offsetWidth;
        const maxY = window.innerHeight - editorControls.offsetHeight;
        
        editorControls.style.left = Math.max(0, Math.min(x, maxX)) + 'px';
        editorControls.style.top = Math.max(0, Math.min(y, maxY)) + 'px';
    }

    function endDrag() {
        isDragging = false;
        dragHandle.style.cursor = 'grab';
    }

    // 绑定鼠标和触摸事件
    dragHandle.addEventListener('mousedown', startDrag);
    document.addEventListener('mousemove', onDrag);
    document.addEventListener('mouseup', endDrag);
    
    dragHandle.addEventListener('touchstart', startDrag, { passive: false });
    dragHandle.addEventListener('touchmove', onDrag, { passive: false });
    dragHandle.addEventListener('touchend', endDrag);

    document.body.appendChild(editorControls);
}
```

---

## 四、后端API

### 4.1 编辑器状态管理 API (editor_state.php)

```php
<?php
/**
 * API端点: /membership/api/editor_state.php
 * 方法: GET/POST
 * 
 * 功能:
 * - GET ?action=get    获取当前用户的编辑器状态
 * - POST ?action=set   设置编辑器状态 (enabled=1/0)
 * - GET ?action=toggle 切换编辑器状态
 */

// 数据库表结构
/*
CREATE TABLE user_editor_state (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    editor_enabled TINYINT(1) DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
*/

switch ($action) {
    case 'get':
        $stmt = $pdo->prepare("SELECT editor_enabled FROM user_editor_state WHERE user_id = ?");
        $stmt->execute([$user_id]);
        $result = $stmt->fetch();
        
        echo json_encode([
            'success' => true,
            'enabled' => $result ? (bool)$result['editor_enabled'] : false
        ]);
        break;

    case 'set':
        $enabled = $_POST['enabled'] === '1' ? 1 : 0;
        
        // UPSERT操作（存在则更新，不存在则插入）
        $stmt = $pdo->prepare("SELECT id FROM user_editor_state WHERE user_id = ?");
        $stmt->execute([$user_id]);
        
        if ($stmt->fetch()) {
            $stmt = $pdo->prepare("UPDATE user_editor_state SET editor_enabled = ? WHERE user_id = ?");
        } else {
            $stmt = $pdo->prepare("INSERT INTO user_editor_state (user_id, editor_enabled) VALUES (?, ?)");
        }
        $stmt->execute([$enabled, $user_id]);
        
        echo json_encode(['success' => true, 'enabled' => (bool)$enabled]);
        break;
}
?>
```

### 4.2 保存热点位置 API (save_hotspots.php)

```php
<?php
/**
 * API端点: /membership/api/save_hotspots.php
 * 方法: POST
 * 
 * 参数:
 * - scene_slug: 场景标识
 * - hotspots: JSON格式的热点数组 [{id, rect}, ...]
 * - csrf_token: CSRF防护令牌
 * 
 * 流程:
 * 1. 验证CSRF令牌
 * 2. 检查用户登录和权限（管理员或场景创建者）
 * 3. 解析热点数据
 * 4. 更新场景PHP文件中的CONFIG
 * 5. 备份原文件
 * 6. 同步更新JSON文件和数据库
 */

// 接收数据
$scene_slug = $_POST['scene_slug'] ?? '';
$hotspots = json_decode($_POST['hotspots'] ?? '[]', true);

// 权限检查
$can_save = false;
if ($user['role'] === 'admin') {
    $can_save = true;
} else {
    // 检查是否是场景创建者
    $stmt = $pdo->prepare("
        SELECT u.username as creator_username 
        FROM scenes s
        LEFT JOIN users u ON s.created_by = u.id
        WHERE s.slug = ?
    ");
    $stmt->execute([$scene_slug]);
    $scene = $stmt->fetch();
    
    if ($scene && $scene['creator_username'] === $user['username']) {
        $can_save = true;
    }
}

// 查找场景文件
$scene_file = null;
$possible_paths = [
    __DIR__ . '/../../scenes/private/' . $scene_slug . '.php',
    __DIR__ . '/../../scenes/public/' . $scene_slug . '.php',
];
foreach ($possible_paths as $path) {
    if (file_exists($path)) {
        $scene_file = $path;
        break;
    }
}

// 读取文件内容
$content = file_get_contents($scene_file);

// 使用正则替换更新每个热点的rect
foreach ($hotspots as $hotspot) {
    $id = $hotspot['id'];
    $rect = $hotspot['rect'];
    
    // 匹配特定id的rect字段
    $rect_pattern = '/("id"\s*:\s*"' . preg_quote($id, '/') . '"[^}]*"rect"\s*:\s*)\{[^}]+\}/s';
    
    $content = preg_replace_callback($rect_pattern, function($matches) use ($rect) {
        $new_rect = sprintf('{"l": %.2f, "t": %.2f, "w": %.2f, "h": %.2f}',
            $rect['l'], $rect['t'], $rect['w'], $rect['h']);
        return $matches[1] . $new_rect;
    }, $content, -1, $count);
}

// 备份原文件
$backup_file = $backup_dir . '/' . $scene_slug . '_backup_' . date('YmdHis') . '.php';
copy($scene_file, $backup_file);

// 原子写入新内容
$temp_file = $scene_file . '.tmp.' . getmypid();
file_put_contents($temp_file, $content);
rename($temp_file, $scene_file);

// 清除OPcache
if (function_exists('opcache_invalidate')) {
    opcache_invalidate($scene_file, true);
}

// 同步更新数据库
$stmt = $pdo->prepare("
    UPDATE scenes 
    SET hotspots_data = ?, hotspots_updated_at = NOW() 
    WHERE slug = ?
");
$stmt->execute([json_encode($hotspots), $scene_slug]);

echo json_encode([
    'success' => true,
    'message' => "成功保存 {$updated_count} 个热点的位置"
]);
?>
```

---

## 五、数据库设计

### 5.1 用户编辑器状态表

```sql
CREATE TABLE user_editor_state (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增ID',
    user_id INT NOT NULL COMMENT '用户ID',
    editor_enabled TINYINT(1) DEFAULT 0 COMMENT '编辑器是否启用',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    UNIQUE KEY uk_user_id (user_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户热点编辑器状态表';
```

### 5.2 场景热点数据表

```sql
CREATE TABLE scenes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    slug VARCHAR(100) NOT NULL UNIQUE COMMENT '场景标识',
    title VARCHAR(200) COMMENT '场景标题',
    
    -- 热点相关字段
    hotspots_data JSON COMMENT '热点位置数据(JSON格式)',
    hotspots_updated_at TIMESTAMP NULL COMMENT '热点数据更新时间',
    hotspot_display_mode VARCHAR(20) DEFAULT 'dot' COMMENT '热点显示模式',
    
    -- 创建信息
    created_by INT COMMENT '创建者ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (created_by) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='场景表';
```

### 5.3 数据示例

```json
// CONFIG.items 结构（场景PHP文件内）
{
  "items": [
    {
      "id": "palm_tree",
      "word": "palm tree",
      "ipa": "/pɑːm triː/",
      "meaning": "棕榈树",
      "sentence": "There is a palm tree in the park.",
      "rect": {"l": 50.84, "t": 38.42, "w": 21.81, "h": 15.42},
      "hidden": false,
      "locked": false
    }
  ]
}

// hotspots_data 数据库字段存储格式
[
  {
    "id": "palm_tree",
    "rect": {"l": 50.84, "t": 38.42, "w": 21.81, "h": 15.42}
  }
]
```

---

## 六、交互流程

### 6.1 启用编辑器的完整流程

```
┌─────────┐     点击绿色圆点      ┌──────────────────┐
│  用户   │ ──────────────────▶ │ enableEditorBtn  │
└─────────┘                     └────────┬─────────┘
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │ 调用 setHotspotEditor│
                              │   Enabled(true)      │
                              └──────────┬───────────┘
                                         │
              ┌──────────────────────────┼──────────────────────────┐
              │                          │                          │
              ▼                          ▼                          ▼
    ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
    │ POST /api/       │    │ 更新按钮视觉状态 │    │ 延迟500ms        │
    │ editor_state.php │    │ (绿点激活)       │    │ 刷新页面         │
    │ enabled=1        │    │                  │    │                  │
    └────────┬─────────┘    └──────────────────┘    └──────────────────┘
             │
             ▼
    ┌──────────────────┐
    │  数据库存储状态   │
    │ user_editor_state│
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │  触发 CustomEvent│
    │ hotspotEditorToggle
    └──────────────────┘
             │
             ▼
页面刷新后 ------------------------------------------------------
             │
             ▼
    ┌──────────────────┐
    │  isHotspotEditor │
    │  Enabled() 检查  │
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │  加载hotspot-    │
    │  editor.js       │
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │ enableEditor()   │
    │ - 添加编辑样式   │
    │ - 显示8向手柄    │
    │ - 显示保存按钮   │
    └──────────────────┘
```

### 6.2 保存热点的完整流程

```
┌─────────┐     点击保存按钮      ┌──────────────────┐
│  用户   │ ──────────────────▶ │   btnSave.onclick │
└─────────┘                     └────────┬─────────┘
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │    saveChanges()     │
                              └──────────┬───────────┘
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │  1. 收集所有热点数据  │
                              │  遍历所有.zone元素    │
                              │  获取rect像素坐标     │
                              └──────────┬───────────┘
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │  2. 转换为百分比坐标  │
                              │  pxToPctRect()       │
                              │  {l, t, w, h} / 容器 │
                              └──────────┬───────────┘
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │  3. 发送到服务器      │
                              │  POST /api/          │
                              │  save_hotspots.php   │
                              └──────────┬───────────┘
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │  服务器处理           │
                              │  - 验证CSRF          │
                              │  - 检查权限          │
                              │  - 更新PHP文件       │
                              │  - 备份原文件        │
                              │  - 更新数据库        │
                              └──────────┬───────────┘
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │  返回JSON响应         │
                              │  {success, message}  │
                              └──────────┬───────────┘
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │  显示成功/失败提示    │
                              │  alert('✅ 保存成功')│
                              └──────────────────────┘
```

---

## 七、核心算法

### 7.1 像素与百分比坐标转换

```javascript
// 像素转百分比（用于保存到服务器）
function pxToPctRect(rectPx) {
    const { w, h } = getBox();  // 获取容器宽高
    return {
        l: round2(clamp((rectPx.x / w) * 100, 0, 100)),      // left
        t: round2(clamp((rectPx.y / h) * 100, 0, 100)),      // top
        w: round2(clamp((rectPx.w / w) * 100, 0.1, 100)),    // width (最小0.1%)
        h: round2(clamp((rectPx.h / h) * 100, 0.1, 100))     // height (最小0.1%)
    };
}

// 百分比转像素（用于渲染到DOM）
function pctToPxRect(rectPct) {
    const { w, h } = getBox();
    return {
        x: (rectPct.l / 100) * w,
        y: (rectPct.t / 100) * h,
        w: (rectPct.w / 100) * w,
        h: (rectPct.h / 100) * h
    };
}

// 辅助函数
function clamp(n, min, max) {
    return Math.max(min, Math.min(max, n));
}

function round2(n) {
    return Math.round(n * 100) / 100;  // 保留2位小数
}
```

### 7.2 边界限制算法

```javascript
// 确保热点不会超出容器边界
function constrainToBounds(x, y, w, h, containerW, containerH) {
    // 限制位置
    x = Math.max(0, Math.min(x, containerW - w));
    y = Math.max(0, Math.min(y, containerH - h));
    
    // 限制大小
    w = Math.max(minW, Math.min(w, containerW - x));
    h = Math.max(minH, Math.min(h, containerH - y));
    
    return { x, y, w, h };
}
```

### 7.3 窗口大小变化适配

```javascript
// 监听窗口大小变化，重新计算热点位置
window.addEventListener('resize', () => {
    for (const [id, el] of hotspotEls.entries()) {
        const index = parseInt(id);
        const item = CONFIG.items?.[index];
        if (item) {
            // 使用百分比坐标重新计算像素位置
            applyHotspotToDom(id, item);
        }
    }
});
```

---

## 八、安全机制

### 8.1 CSRF防护

```php
// 1. 生成CSRF令牌（页面加载时）
function generateCSRFToken() {
    if (!isset($_SESSION['csrf_token'])) {
        $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
    }
    return $_SESSION['csrf_token'];
}

// 2. 在HTML中注入令牌
function csrfScript() {
    $token = generateCSRFToken();
    return "<script>window.CSRF_TOKEN = '{$token}';</script>";
}

// 3. API验证令牌
$csrf_token = $_POST['csrf_token'] ?? $_SERVER['HTTP_X_CSRF_TOKEN'] ?? '';
if (!validateCSRFToken($csrf_token)) {
    echo json_encode(['success' => false, 'message' => '安全验证失败']);
    exit;
}
```

### 8.2 权限检查

```javascript
// 前端权限检查
window.HAS_EDITOR_PERMISSION = true;  // 用户是否有权限（管理员/VIP3）
window.CAN_USE_EDITOR = true;         // 编辑器当前是否启用

function isHotspotEditorEnabled() {
    // 两层检查：权限 + 开关状态
    return window.CAN_USE_EDITOR === true && cachedEditorEnabled === true;
}
```

```php
// 后端权限检查
$can_save = false;

if ($user['role'] === 'admin') {
    $can_save = true;
} else {
    // 检查是否是场景创建者（使用username支持跨环境）
    $stmt = $pdo->prepare("
        SELECT u.username as creator_username 
        FROM scenes s
        LEFT JOIN users u ON s.created_by = u.id
        WHERE s.slug = ?
    ");
    $stmt->execute([$scene_slug]);
    $scene = $stmt->fetch();
    
    if ($scene && $scene['creator_username'] === $user['username']) {
        $can_save = true;
    }
}
```

### 8.3 数据验证

```php
// 验证热点数据格式
$hotspots_data = json_decode($hotspots, true);
if (json_last_error() !== JSON_ERROR_NONE) {
    echo json_encode(['success' => false, 'message' => '数据格式错误']);
    exit;
}

// 验证每个热点
foreach ($hotspots_data as $hotspot) {
    if (!isset($hotspot['id']) || !isset($hotspot['rect'])) {
        continue;
    }
    
    $rect = $hotspot['rect'];
    // 验证坐标范围
    if ($rect['l'] < 0 || $rect['l'] > 100 ||
        $rect['t'] < 0 || $rect['t'] > 100 ||
        $rect['w'] <= 0 || $rect['w'] > 100 ||
        $rect['h'] <= 0 || $rect['h'] > 100) {
        continue;
    }
}
```

### 8.4 文件备份机制

```php
// 保存前自动备份
$backup_dir = __DIR__ . '/../../bakfiles/hotspots';
if (!is_dir($backup_dir)) {
    mkdir($backup_dir, 0755, true);
}

$backup_file = $backup_dir . '/' . $scene_slug . '_backup_' . date('YmdHis') . '.php';
copy($scene_file, $backup_file);

// 原子写入（使用临时文件+重命名）
$temp_file = $scene_file . '.tmp.' . getmypid();
file_put_contents($temp_file, $content);
rename($temp_file, $scene_file);
```

---

## 九、扩展功能

### 9.1 热点显示模式

系统支持9种热点显示模式，通过CSS类控制：

```css
/* 1. dot - 圆点标记（默认） */
.hotspot-mode-dot .zone::before { /* 白色圆点 */ }

/* 2. glow - 边缘发光 */
.hotspot-mode-glow .zone { box-shadow: 0 0 8px 2px rgba(102,126,234,0.3); }

/* 3. border - 虚线边框 */
.hotspot-mode-border .zone { border: 2px dashed rgba(102,126,234,0.4); }

/* 4. overlay - 半透明遮罩 */
.hotspot-mode-overlay .zone { background: rgba(102,126,234,0.15); }

/* 5. pulse - 脉冲动画 */
.hotspot-mode-pulse .zone { animation: hotspot-pulse 2s ease-in-out infinite; }

/* 6. hidden - 完全隐藏 */
.hotspot-mode-hidden .zone { background: transparent; border: none; }

/* 7. numbered-purple - 数字+紫色框 */
.hotspot-mode-numbered-purple .zone::before { /* 显示序号 */ }

/* 8. neon-glow - 霓虹灯效果 */
.hotspot-mode-neon-glow .zone { border: 2px solid #ff00ff; animation: neonPulse 2s infinite; }

/* 9. emoji-face - 表情符号 */
.hotspot-mode-emoji-face .zone::before { content: attr(data-emoji); }
```

---

## 十、总结

### 10.1 核心特性

1. **可视化编辑**: 8向手柄精确调整热点大小
2. **拖拽移动**: 支持鼠标和触摸设备
3. **实时保存**: 百分比坐标存储，自适应不同屏幕
4. **权限控制**: 管理员+VIP3专属功能
5. **跨设备适配**: 百分比坐标+响应式布局
6. **安全机制**: CSRF防护+权限验证+数据备份

### 10.2 技术亮点

- **Pointer Events API**: 统一鼠标和触摸事件处理
- **CSS Clip Path**: 编辑模式下保持圆角效果
- **原子文件写入**: 防止保存过程中断导致数据损坏
- **OPcache清除**: 确保PHP文件修改立即生效

### 10.3 文件清单

| 文件 | 说明 |
|------|------|
| `v6/pages/hotspot-editor.php` | 编辑器控制面板页面 |
| `assets/hotspot-editor.js` | 核心编辑器逻辑（819行） |
| `membership/api/editor_state.php` | 编辑器状态API |
| `membership/api/save_hotspots.php` | 保存热点位置API（428行） |

---

*文档生成时间: 2026-04-05 by Kimi*

# 视频导出视觉升级 — 设计文档

**日期**: 2026-05-09
**状态**: Draft → Approved

## 目标

将 Python 脚本迭代出的视频导出视觉方案（v7）移植到 Rust 后端，替换现有的旧版滤镜逻辑。

### 改动前后对比

| 项目 | 旧版（当前 Rust） | 新版（本次改造） |
|------|-------------------|-------------------|
| 分辨率 | 720×1280 (9:16) | 720×960 (3:4) |
| 编码 | H.264 / 25fps / 192k 立体声 | HEVC / 24fps / 64k 单声道 |
| 面板 | drawbox 黑色遮罩（有闪烁） | 圆角半透明 PNG overlay |
| 热点高亮 | 多层白色光晕 | 简洁白色 2px 实线框 |
| 字体 | DroidSans + DejaVu | Poppins Bold + Noto Sans CJK + DejaVu IPA |
| 词性标签 | 有（名词/动词） | 无 |
| 过渡片段 | 有（0.3s 淡入淡出，造成闪烁） | 无 |
| 文字阴影 | 无 | 有（black@0.55, 2px 偏移） |
| 封面帧 | 无（微信黑屏） | 有（0.3s 纯背景图） |
| 画面边框 | 无 | 8px white@0.12 四边窄框 |

## 改动范围

### 只改一个文件

- `backend-rust/src/services/video_export.rs` — 全部重写滤镜/面板/分段逻辑

### 新增依赖

- `Cargo.toml` 加 `image = "0.25"` — 用于生成圆角 PNG overlay

### 新增静态资源

- `backend-rust/fonts/Poppins-Bold.ttf`
- `backend-rust/fonts/Poppins-Regular.ttf`
- `backend-rust/fonts/DejaVuSans.ttf`

字体从项目相对路径加载（`env!("CARGO_MANIFEST_DIR")/fonts/`），不依赖系统字体安装。

### 不改的文件

- `src/api/video.rs` — API 路由不变
- `src/db/videos.rs` — 数据库操作不变
- `src/services/video_cleanup.rs` — 清理逻辑不变
- `src/models/video.rs` — 数据模型不变
- `src/main.rs` — 路由注册不变
- 存储层 — 不变

## 详细设计

### 1. 常量更新

```rust
const VIDEO_W: i32 = 720;
const VIDEO_H: i32 = 960;
const FPS: i32 = 24;
const PANEL_RADIUS: i32 = 16;
const PANEL_FILL_ALPHA: f32 = 0.51;   // 130/255
const PANEL_BORDER_ALPHA: f32 = 0.18;  // 45/255
const PANEL_BORDER_W: i32 = 1;
const FRAME_BORDER_W: i32 = 8;
const FRAME_BORDER_ALPHA: f32 = 0.12;
```

字体路径：
```rust
const CHINESE_FONT: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/fonts/NotoSansCJK-Medium.ttc");
const ENGLISH_FONT: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/fonts/Poppins-Bold.ttf");
const ENGLISH_FONT_BODY: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/fonts/Poppins-Regular.ttf");
const IPA_FONT: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/fonts/DejaVuSans.ttf");
```

### 2. 圆角面板 PNG 生成

新增函数 `generate_rounded_panel_png(path, w, h, radius)`:

用 `image` crate 创建 `RgbaImage`：
- 每个像素计算 SDF（Signed Distance Field）
- `d = sqrt(max(qx,0)² + max(qy,0)²) + min(max(qx,qy), 0) - radius`
- 外边缘 1.5px 抗锯齿过渡
- 边框区域 vs 填充区域通过 `d > -border_w` 判断

保存为 PNG 到 tmp 文件，供 FFmpeg overlay 使用。

### 3. 滤镜架构改造

`generate_display_segment` 从 `-vf` 单链改为 `-filter_complex` 三输入：

```
ffmpeg -loop 1 -i bg.jpg -i audio.mp3 -i panel.png \
  -filter_complex "
    [0:v]scale=720:960:...,crop=720:960[bg];
    [bg]drawbox=...highlight...[hl];
    [hl][2:v]overlay=x=PX:y=PY[wp];
    [wp]drawtext=...,drawbox=...border...[final]
  " \
  -map "[final]" -map 1:a \
  -c:v libx265 -r 24 -preset fast \
  -c:a aac -b:a 64k -ar 44100 -ac 1 \
  -pix_fmt yuv420p -t DURATION output.mp4
```

层序：背景缩放 → 热点高亮 → 圆角面板 overlay → 文字 → 边框

### 4. 面板文字布局

去掉词性标签（名词/动词），字号体系：

| 元素 | 字体 | 字号 (720基准) |
|------|------|----------------|
| 英文单词 | Poppins Bold | 40 |
| 音标 | DejaVu Sans | 22 |
| 中文释义 | Noto Sans CJK Medium | 26 |
| 英文例句 | Poppins Regular | 24 |
| 中文翻译 | Noto Sans CJK Medium | 22 |

所有文字带阴影：`drawtext` 先画一层 `black@0.55` 偏移 +2px，再画正文。

进度指示器保留，右上角 "1 / 7"，Poppins Regular。

### 5. 热点高亮

简化为两层 drawbox：
```rust
"drawbox=x=X:y=Y:w=W:h=H:color=white@0.10:t=fill,
 drawbox=x=X:y=Y:w=W:h=H:color=white@0.85:t=2"
```

### 6. 分段结构

```
封面帧 (0.3s, 纯背景图 + 边框, 无淡入淡出)
→ 开场标题卡 (1.5s, 无淡入, 有淡出)
→ 展示片段1 (音频时长, 无淡入, 无过渡)
→ 展示片段2
→ ...
→ 展示片段N
```

关键：去掉所有过渡片段和 fade=in，消除闪烁。

### 7. 编码参数

```rust
// 视频段
"-c:v", "libx265", "-r", "24", "-preset", "fast"
// 音频段
"-c:a", "aac", "-b:a", "64k", "-ar", "44100", "-ac", "1"
// 合并段
"-c", "copy", "-movflags", "+faststart"
```

### 8. 面板高度计算

```
pad_v (3.5%)
+ line_spacing_word (44)
+ ipa_height? (26×1.2)
+ meaning_height? (26×1.3)
+ sentence_lines × line_spacing (31)
+ translation_lines × line_spacing (31)
+ pad_v (3.5%)
```

面板 y 坐标 = VIDEO_H - total_height - bottom_margin(2.5%)

## 不做的事情

- 不加并发控制（tokio::spawn 当前够用）
- 不加重试机制
- 不改存储路径模式（仍为 `generated/videos/{job_id}.mp4`）
- 不做视频模板配置化（YAGNI）
- 不改 API 接口和数据模型

## 验证方式

1. `cargo build` 编译通过
2. 通过小程序触发视频导出，确认：
   - 微信封面不黑屏
   - 单词间无闪烁
   - 圆角面板显示正确
   - 音标字符正常（DejaVu Sans）
   - 文件体积显著缩小（预期 < 原来的一半）
3. 对比旧版导出视频的视觉差异

## 风险

- 字体格式兼容性：Noto Sans CJK 是 TTC 格式。FFmpeg drawtext 直接支持 TTC。`image` crate 不直接读 TTC，但面板 PNG 只用圆角矩形不需要字体渲染，所以无影响。
- HEVC 编码兼容性：libx265 需要服务器已安装。当前服务器已有（kuanping 视频用的就是 HEVC）。

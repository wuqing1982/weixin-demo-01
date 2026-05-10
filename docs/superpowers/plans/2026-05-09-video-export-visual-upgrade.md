# 视频导出视觉升级 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Python 脚本迭代出的视频导出视觉方案（圆角面板、HEVC、无闪烁、新字体、封面帧）移植到 Rust 后端。

**Architecture:** 替换 `video_export.rs` 中的滤镜构建和分段生成逻辑。用 `image` crate 生成圆角 PNG overlay，FFmpeg `-filter_complex` 三输入合成。保留现有的 API、数据库、存储层不变。

**Tech Stack:** Rust, FFmpeg CLI (subprocess), `image` crate 0.25 (PNG generation), HEVC (libx265)

**Spec:** `docs/superpowers/specs/2026-05-09-video-export-visual-upgrade-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `backend-rust/Cargo.toml` | Modify | Add `image = "0.25"` dependency |
| `backend-rust/fonts/` | Create dir + copy 3 font files | Bundled fonts, no system dependency |
| `backend-rust/src/services/video_export.rs` | Rewrite | All visual logic: PNG overlay, filters, segments |

---

## Task 1: Add dependency and copy font files

**Files:**
- Modify: `backend-rust/Cargo.toml`
- Create: `backend-rust/fonts/Poppins-Bold.ttf`
- Create: `backend-rust/fonts/Poppins-Regular.ttf`
- Create: `backend-rust/fonts/DejaVuSans.ttf`

- [ ] **Step 1: Add `image` crate to Cargo.toml**

Add to `[dependencies]` section:

```toml
image = "0.25"
```

- [ ] **Step 2: Create fonts directory and copy files**

```bash
mkdir -p backend-rust/fonts
cp /usr/share/fonts/truetype/poppins/Poppins-Bold.ttf backend-rust/fonts/
cp /usr/share/fonts/truetype/poppins/Poppins-Regular.ttf backend-rust/fonts/
cp /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf backend-rust/fonts/
```

Note: Noto Sans CJK is a large TTC file (~16MB). Instead of bundling it, keep using the system path `/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc` since it's already installed on the server. If it's missing, fall back to DroidSans.

- [ ] **Step 3: Verify fonts exist**

```bash
ls -lh backend-rust/fonts/
```

Expected: 3 files totaling ~500KB.

- [ ] **Step 4: Commit**

```bash
git add backend-rust/Cargo.toml backend-rust/fonts/
git commit -m "chore(video): add image crate and bundled fonts for video export"
```

---

## Task 2: Rewrite `video_export.rs` — Constants and helpers

**Files:**
- Rewrite: `backend-rust/src/services/video_export.rs` (lines 1-11 → new constants, keep lines 13-112 `process_video_export` unchanged)

This task replaces the top of the file with new constants and keeps the public entry point `process_video_export` completely unchanged. It also adds the new helper functions.

- [ ] **Step 1: Replace constants and imports (lines 1-11)**

Replace the existing imports and constants with:

```rust
use std::path::Path;

use image::{Rgba, RgbaImage};
use serde_json::Value;

use crate::db;
use crate::state::AppState;

// ---------------------------------------------------------------------------
// Video constants (v5 — 3:4 ratio, HEVC, rounded panel)
// ---------------------------------------------------------------------------

const VIDEO_W: i32 = 720;
const VIDEO_H: i32 = 960;

const FPS: i32 = 24;
const FADE_FRAMES: i32 = 7; // 0.3s * 24fps
const INTRO_DURATION: f64 = 1.5;

const PANEL_RADIUS: i32 = 16;
const PANEL_FILL_ALPHA: u8 = 130;
const PANEL_BORDER_ALPHA: u8 = 45;
const PANEL_BORDER_W: i32 = 1;

const FRAME_BORDER_W: i32 = 8;

const CHINESE_FONT: &str = "/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc";
const ENGLISH_FONT: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/fonts/Poppins-Bold.ttf");
const ENGLISH_FONT_BODY: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/fonts/Poppins-Regular.ttf");
const IPA_FONT: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/fonts/DejaVuSans.ttf");
```

- [ ] **Step 2: Keep `process_video_export` (lines 17-112) exactly as-is**

Do not modify this function. It handles job loading, storage, progress, upload. Only the inner `generate_scene_video` call signature stays the same.

- [ ] **Step 3: Add rounded panel PNG generator (new function)**

Add this function after the `process_video_export` function:

```rust
/// Generate a rounded rectangle PNG with semi-transparent fill and thin border.
/// Uses SDF (Signed Distance Field) for smooth anti-aliased corners.
fn generate_rounded_panel_png(
    path: &Path,
    w: u32,
    h: u32,
    radius: i32,
    fill_rgba: [u8; 4],
    border_rgba: [u8; 4],
    border_w: i32,
) -> Result<(), String> {
    let mut img = RgbaImage::new(w, h);
    let w_f = (w - 1) as f64 / 2.0;
    let h_f = (h - 1) as f64 / 2.0;
    let r = radius as f64;

    for y in 0..h {
        for x in 0..w {
            let qx = (x as f64 - w_f).abs() - w_f + r;
            let qy = (y as f64 - h_f).abs() - h_f + r;

            let outside = (qx.max(0.0).powi(2) + qy.max(0.0).powi(2)).sqrt();
            let inside = qx.max(qy).min(0.0);
            let d = outside + inside - r;

            // Outer edge anti-aliasing (1.5px smooth transition)
            let outer = (0.75 - d).clamp(0.0, 1.0);

            if outer <= 0.0 {
                // Fully outside
                continue;
            }

            let pixel = if border_w > 0 && d > -(border_w as f64) {
                // Border region
                let inner = (d + border_w as f64 + 0.75).clamp(0.0, 1.0);
                let a = (border_rgba[3] as f64 * outer * inner) as u8;
                Rgba([border_rgba[0], border_rgba[1], border_rgba[2], a])
            } else {
                // Fill region
                let a = (fill_rgba[3] as f64 * outer) as u8;
                Rgba([fill_rgba[0], fill_rgba[1], fill_rgba[2], a])
            };

            img.put_pixel(x, y, pixel);
        }
    }

    img.save(path).map_err(|e| format!("save panel png: {e}"))
}
```

- [ ] **Step 4: Add frame border filter builder (new function)**

```rust
fn build_frame_border_filter(img_w: i32, img_h: i32) -> String {
    let bw = FRAME_BORDER_W;
    format!(
        "drawbox=x=0:y=0:w={img_w}:h={bw}:color=white@0.12:t=fill,\
         drawbox=x=0:y={}:w={img_w}:h={bw}:color=white@0.12:t=fill,\
         drawbox=x=0:y=0:w={bw}:h={img_h}:color=white@0.12:t=fill,\
         drawbox=x={}:y=0:w={bw}:h={img_h}:color=white@0.12:t=fill",
        img_h - bw,
        img_w - bw,
    )
}
```

- [ ] **Step 5: Verify compilation**

```bash
cd backend-rust && cargo check 2>&1 | tail -5
```

Expected: compilation errors in `generate_scene_video` etc. (because we haven't rewritten those yet) — that's fine. The new functions should compile.

- [ ] **Step 6: Commit**

```bash
git add backend-rust/src/services/video_export.rs
git commit -m "refactor(video): add new constants, PNG overlay generator, frame border"
```

---

## Task 3: Rewrite `generate_scene_video` — Cover frame + no transitions

**Files:**
- Modify: `backend-rust/src/services/video_export.rs` (lines 114-251 → rewrite)

This task replaces `generate_scene_video`, removes `generate_move_segment`, and adds the cover frame.

- [ ] **Step 1: Rewrite `generate_scene_video`**

Replace the existing `PreparedItem` struct and `generate_scene_video` function with:

```rust
struct PreparedItem {
    item: Value,
    audio_abs: String,
    audio_duration: f64,
}

async fn generate_scene_video(
    state: &AppState,
    scene: &crate::models::scene::Scene,
    output_path: &Path,
    job_id_for_progress: &str,
    storage: &dyn crate::storage::provider::StorageProvider,
) -> Result<(), String> {
    let asset_tmp = std::env::temp_dir().join(format!("video_assets_{}", uuid::Uuid::new_v4()));
    tokio::fs::create_dir_all(&asset_tmp)
        .await
        .map_err(|e| format!("asset tmp mkdir: {e}"))?;

    let bg_key = crate::storage::provider::StorageKey::from_web_path(&scene.background_path);
    let bg_local = asset_tmp.join(format!("bg_{}", bg_key.as_str().replace('/', "_")));
    storage
        .ensure_local(&bg_key, &bg_local)
        .await
        .map_err(|e| format!("download bg: {e}"))?;
    let bg_path = bg_local.to_string_lossy().to_string();

    let items = scene.items.as_array().cloned().unwrap_or_default();
    let verbs = scene.verbs.as_array().cloned().unwrap_or_default();

    let mut prepared: Vec<(PreparedItem, &str)> = Vec::new();

    for item in &items {
        if let Some(audio_rel) = item["audioPath"].as_str() {
            if !audio_rel.is_empty() {
                let audio_key =
                    crate::storage::provider::StorageKey::from_web_path(audio_rel);
                let audio_local =
                    asset_tmp.join(format!("audio_{}", audio_key.as_str().replace('/', "_")));
                if storage
                    .ensure_local(&audio_key, &audio_local)
                    .await
                    .is_ok()
                {
                    let abs = audio_local.to_string_lossy().to_string();
                    let dur = get_audio_duration(&abs);
                    prepared.push((
                        PreparedItem {
                            item: item.clone(),
                            audio_abs: abs,
                            audio_duration: dur,
                        },
                        "noun",
                    ));
                }
            }
        }
    }

    for verb in &verbs {
        if let Some(audio_rel) = verb["audioPath"].as_str() {
            if !audio_rel.is_empty() {
                let audio_key =
                    crate::storage::provider::StorageKey::from_web_path(audio_rel);
                let audio_local =
                    asset_tmp.join(format!("audio_{}", audio_key.as_str().replace('/', "_")));
                if storage
                    .ensure_local(&audio_key, &audio_local)
                    .await
                    .is_ok()
                {
                    let abs = audio_local.to_string_lossy().to_string();
                    let dur = get_audio_duration(&abs);
                    prepared.push((
                        PreparedItem {
                            item: verb.clone(),
                            audio_abs: abs,
                            audio_duration: dur,
                        },
                        "verb",
                    ));
                }
            }
        }
    }

    if prepared.is_empty() {
        let result = generate_static_segment(&bg_path, output_path);
        let _ = tokio::fs::remove_dir_all(&asset_tmp).await;
        return result;
    }

    let tmp_dir =
        std::env::temp_dir().join(format!("video_segs_{}", uuid::Uuid::new_v4()));
    std::fs::create_dir_all(&tmp_dir).map_err(|e| format!("tmp mkdir: {e}"))?;

    let mut segment_paths: Vec<String> = Vec::new();
    let total = prepared.len();

    // --- Cover frame (pure background, no overlay, for WeChat thumbnail) ---
    {
        let cover_path = tmp_dir
            .join("cover.mp4")
            .to_string_lossy()
            .to_string();
        generate_cover_segment(&bg_path, &cover_path)?;
        segment_paths.push(cover_path);
    }

    // --- Intro title card ---
    {
        let intro_path = tmp_dir
            .join("intro.mp4")
            .to_string_loss()
            .to_string();
        let scene_title = scene.title.clone();
        generate_intro_segment(&bg_path, &scene_title, &intro_path)?;
        segment_paths.push(intro_path);
    }

    // --- Display segments (no transition segments, no fade) ---
    for (idx, (pi, item_type)) in prepared.iter().enumerate() {
        let seg_tmp = tmp_dir.join(format!("seg_{idx:03d}"));
        std::fs::create_dir_all(&seg_tmp)
            .map_err(|e| format!("seg tmp mkdir: {e}"))?;

        let seg_path = tmp_dir
            .join(format!("display_{idx:03d}.mp4"))
            .to_string_lossy()
            .to_string();
        generate_display_segment(
            &seg_tmp,
            &bg_path,
            &pi.audio_abs,
            pi.audio_duration,
            &pi.item,
            item_type,
            idx,
            total,
            &seg_path,
        )?;
        segment_paths.push(seg_path);

        let pct = 15 + ((idx + 1) * 65 / total).min(80);
        let _ = db::videos::update_video_export(
            &state.pool,
            job_id_for_progress,
            "running",
            pct as i32,
            None,
            None,
        )
        .await
        .ok();
    }

    concat_segments(&segment_paths, &output_path.to_string_lossy())?;

    let _ = std::fs::remove_dir_all(&tmp_dir);
    let _ = tokio::fs::remove_dir_all(&asset_tmp).await;

    Ok(())
}
```

- [ ] **Step 2: Verify compilation**

```bash
cd backend-rust && cargo check 2>&1 | tail -5
```

Expected: errors about missing functions (`generate_cover_segment`, `generate_intro_segment`, `generate_display_segment` with new signature). That's expected — we add them next.

- [ ] **Step 3: Commit**

```bash
git add backend-rust/src/services/video_export.rs
git commit -m "refactor(video): rewrite generate_scene_video with cover frame, no transitions"
```

---

## Task 4: Rewrite segment generators — Cover, Intro, Static, Display

**Files:**
- Modify: `backend-rust/src/services/video_export.rs` (replace lines 253-354 → new segment generators)

- [ ] **Step 1: Replace all segment generators**

Replace `generate_static_segment`, `generate_move_segment`, and `generate_display_segment` with:

```rust
// ---------------------------------------------------------------------------
// Segment generators
// ---------------------------------------------------------------------------

fn generate_cover_segment(image: &str, output: &str) -> Result<(), String> {
    let (sw, sh) = ensure_even(VIDEO_W, VIDEO_H);
    let border = build_frame_border_filter(sw, sh);
    let vf = format!(
        "scale={sw}:{sh}:force_original_aspect_ratio=increase,crop={sw}:{sh},{border}"
    );
    run_ffmpeg(&[
        "-y",
        "-loop", "1",
        "-i", image,
        "-f", "lavfi",
        "-i", "anullsrc=r=44100:cl=mono",
        "-vf", &vf,
        "-c:v", "libx265",
        "-r", &FPS.to_string(),
        "-preset", "fast",
        "-c:a", "aac",
        "-b:a", "64k",
        "-ar", "44100",
        "-ac", "1",
        "-pix_fmt", "yuv420p",
        "-t", "0.3",
        output,
    ])
}

fn generate_intro_segment(
    image: &str,
    title: &str,
    output: &str,
) -> Result<(), String> {
    let (sw, sh) = ensure_even(VIDEO_W, VIDEO_H);
    let border = build_frame_border_filter(sw, sh);
    let scale = VIDEO_W as f64 / 720.0;

    let mut vf_parts = vec![
        format!("scale={sw}:{sh}:force_original_aspect_ratio=increase,crop={sw}:{sh}"),
        format!("drawbox=x=0:y=0:w={sw}:h={sh}:color=black@0.70:t=fill"),
    ];

    if !title.is_empty() {
        let title_font = (52.0 * scale) as i32;
        let sub_font = (28.0 * scale) as i32;

        // Write text files for FFmpeg
        let title_file =
            std::env::temp_dir().join(format!("intro_title_{}", uuid::Uuid::new_v4()));
        std::fs::write(&title_file, title)
            .map_err(|e| format!("write title file: {e}"))?;

        let sub_file =
            std::env::temp_dir().join(format!("intro_sub_{}", uuid::Uuid::new_v4()));
        std::fs::write(&sub_file, "English Vocabulary")
            .map_err(|e| format!("write sub file: {e}"))?;

        let t1 = title_file.to_string_lossy();
        let t2 = sub_file.to_string_lossy();

        vf_parts.push(format!(
            "drawtext=textfile='{t1}':fontfile='{CHINESE_FONT}':fontcolor=white:fontsize={title_font}:x=(w-tw)/2:y=(h-th)/2-50"
        ));
        vf_parts.push(format!(
            "drawtext=textfile='{t2}':fontfile='{ENGLISH_FONT_BODY}':fontcolor=white@0.40:fontsize={sub_font}:x=(w-tw)/2:y=(h+20)/2+10"
        ));

        // Cleanup temp text files after FFmpeg runs
        let _t1 = title_file;
        let _t2 = sub_file;
    }

    vf_parts.push(border);
    vf_parts.push(format!(
        "fade=out:st={:.3}:d={FADE_FRAMES}",
        INTRO_DURATION - 0.3
    ));

    let vf = vf_parts.join(",");

    let result = run_ffmpeg(&[
        "-y",
        "-loop", "1",
        "-i", image,
        "-f", "lavfi",
        "-i", "anullsrc=r=44100:cl=mono",
        "-vf", &vf,
        "-c:v", "libx265",
        "-r", &FPS.to_string(),
        "-preset", "fast",
        "-c:a", "aac",
        "-b:a", "64k",
        "-ar", "44100",
        "-ac", "1",
        "-pix_fmt", "yuv420p",
        "-t", &format!("{INTRO_DURATION:.3}"),
        output,
    ]);

    // Cleanup temp text files
    if !title.is_empty() {
        let _ = std::fs::remove_file(
            std::env::temp_dir().join(format!("intro_title_{}", uuid::Uuid::new_v4())),
        );
        let _ = std::fs::remove_file(
            std::env::temp_dir().join(format!("intro_sub_{}", uuid::Uuid::new_v4())),
        );
    }

    result
}

fn generate_static_segment(image: &str, output: &Path) -> Result<(), String> {
    let (sw, sh) = ensure_even(VIDEO_W, VIDEO_H);
    let border = build_frame_border_filter(sw, sh);
    let vf = format!(
        "scale={sw}:{sh}:force_original_aspect_ratio=increase,crop={sw}:{sh},{border}"
    );
    run_ffmpeg(&[
        "-y",
        "-loop", "1",
        "-i", image,
        "-c:v", "libx265",
        "-r", &FPS.to_string(),
        "-preset", "fast",
        "-t", "5",
        "-pix_fmt", "yuv420p",
        "-vf", &vf,
        &output.to_string_lossy(),
    ])
}

fn generate_display_segment(
    tmp_dir: &Path,
    image: &str,
    audio: &str,
    audio_duration: f64,
    item: &Value,
    item_type: &str,
    word_idx: usize,
    total_words: usize,
    output: &str,
) -> Result<(), String> {
    let (sw, sh) = ensure_even(VIDEO_W, VIDEO_H);

    // Build highlight filter
    let highlight = if item_type == "noun" {
        if let Some(rect) = item.get("rect") {
            let (x, y, w, h) = to_pixel_rect(rect);
            build_highlight_filter(x, y, w, h)
        } else {
            String::new()
        }
    } else {
        String::new()
    };

    // Build panel info (generates PNG overlay + returns text filter + position)
    let (overlay_png, panel_x, panel_y, text_filter) =
        build_panel_info(tmp_dir, item, word_idx, total_words)?;

    let border = build_frame_border_filter(sw, sh);

    // Build filter_complex chain
    let scale_f =
        format!("scale={sw}:{sh}:force_original_aspect_ratio=increase,crop={sw}:{sh}");

    let mut links = Vec::new();

    // [0:v] -> scale+crop -> [bg]
    links.push(format!("[0:v]{scale_f}[bg]"));

    // [bg] -> highlight -> [hl] (optional)
    if highlight.is_empty() {
        links.push(format!("[bg][2:v]overlay=x={panel_x}:y={panel_y}[wp]"));
    } else {
        links.push(format!("[bg]{highlight}[hl]"));
        links.push(format!(
            "[hl][2:v]overlay=x={panel_x}:y={panel_y}[wp]"
        ));
    }

    // [wp] -> text + border -> [final]
    let after = format!("{text_filter},{border}");
    links.push(format!("[wp]{after}[final]"));

    let filter_complex = links.join(";");

    let dur_str = format!("{:.3}", audio_duration.max(1.0));

    run_ffmpeg(&[
        "-y",
        "-loop", "1",
        "-i", image,
        "-i", audio,
        "-i", &overlay_png,
        "-filter_complex", &filter_complex,
        "-map", "[final]",
        "-map", "1:a",
        "-c:v", "libx265",
        "-r", &FPS.to_string(),
        "-preset", "fast",
        "-c:a", "aac",
        "-b:a", "64k",
        "-ar", "44100",
        "-ac", "1",
        "-pix_fmt", "yuv420p",
        "-t", &dur_str,
        output,
    ])
}
```

- [ ] **Step 2: Verify compilation**

```bash
cd backend-rust && cargo check 2>&1 | tail -5
```

Expected: errors about missing `build_highlight_filter` (old signature) and missing `build_panel_info`. We fix these next.

- [ ] **Step 3: Commit**

```bash
git add backend-rust/src/services/video_export.rs
git commit -m "refactor(video): rewrite segment generators with cover, intro, filter_complex"
```

---

## Task 5: Rewrite filter builders — Highlight + Panel

**Files:**
- Modify: `backend-rust/src/services/video_export.rs` (replace lines 356-524 → new filter builders)

- [ ] **Step 1: Replace `build_highlight_filter`**

Replace with simplified version:

```rust
fn build_highlight_filter(x: i32, y: i32, w: i32, h: i32) -> String {
    format!(
        "drawbox=x={x}:y={y}:w={w}:h={h}:color=white@0.10:t=fill,\
         drawbox=x={x}:y={y}:w={w}:h={h}:color=white@0.85:t=2"
    )
}
```

- [ ] **Step 2: Replace `build_panel_filter` with `build_panel_info`**

This is the core change. Replace the old `build_panel_filter` function with:

```rust
/// Build panel overlay: generates rounded PNG + returns (png_path, panel_x, panel_y, text_filter_string).
fn build_panel_info(
    tmp_dir: &Path,
    item: &Value,
    word_idx: usize,
    total_words: usize,
) -> Result<(String, i32, i32, String), String> {
    let pad_h = (VIDEO_W as f64 * 0.04) as i32;
    let pad_v = (VIDEO_W as f64 * 0.035) as i32;
    let bottom_margin = (VIDEO_H as f64 * 0.025) as i32;
    let usable_w = VIDEO_W - pad_h * 2;
    let scale = VIDEO_W as f64 / 720.0;

    let font_word = (40.0 * scale) as i32;
    let font_ipa = (22.0 * scale) as i32;
    let font_meaning = (26.0 * scale) as i32;
    let font_sentence = (24.0 * scale) as i32;
    let font_translation = (22.0 * scale) as i32;
    let font_progress = (16.0 * scale) as i32;

    let line_spacing_word = (font_word as f64 * 1.10) as i32;
    let line_spacing = (font_sentence as f64 * 1.30) as i32;

    let word = item["word"].as_str().unwrap_or("");
    let ipa = item["ipa"].as_str().unwrap_or("");
    let meaning = item["meaning"].as_str().unwrap_or("");
    let sentence = item["sentence"].as_str().unwrap_or("");
    let translation = item
        .get("sentenceTranslation")
        .or_else(|| item.get("sentence_translation"))
        .and_then(|v| v.as_str())
        .unwrap_or("");

    let sentence_lines = if !sentence.is_empty() {
        wrap_text(sentence, font_sentence, usable_w - pad_h)
    } else {
        vec![]
    };
    let translation_lines = if !translation.is_empty() {
        wrap_text_cjk(translation, font_translation, usable_w - pad_h)
    } else {
        vec![]
    };

    // Calculate panel height (no tag)
    let mut total_height = pad_v;
    total_height += line_spacing_word;
    if !ipa.is_empty() {
        total_height += (font_ipa as f64 * 1.20) as i32;
    }
    if !meaning.is_empty() {
        total_height += (font_meaning as f64 * 1.30) as i32;
    }
    total_height += sentence_lines.len() as i32 * line_spacing;
    total_height += translation_lines.len() as i32 * line_spacing;
    total_height += pad_v;

    let panel_x = pad_h;
    let panel_y = VIDEO_H - total_height - bottom_margin;
    let panel_w = usable_w;

    // Generate rounded panel PNG
    let overlay_path = tmp_dir.join("panel_overlay.png");
    generate_rounded_panel_png(
        &overlay_path,
        panel_w as u32,
        total_height as u32,
        PANEL_RADIUS,
        [0, 0, 0, PANEL_FILL_ALPHA],      // fill: black, semi-transparent
        [255, 255, 255, PANEL_BORDER_ALPHA], // border: white, subtle
        PANEL_BORDER_W,
    )?;

    // Build text filter chain
    let mut text_parts: Vec<String> = Vec::new();
    let mut ty = panel_y + pad_v;

    // Word (Poppins Bold, shadow)
    if !word.is_empty() {
        text_parts.push(drawtext_with_shadow(
            word, ENGLISH_FONT, font_word, "white", "(w-tw)/2", ty, 2, 0.60,
        ));
        ty += line_spacing_word;
    }

    // IPA (DejaVu Sans — supports IPA characters)
    if !ipa.is_empty() {
        text_parts.push(drawtext_with_shadow(
            ipa, IPA_FONT, font_ipa, "white@0.70", "(w-tw)/2", ty, 1, 0.45,
        ));
        ty += (font_ipa as f64 * 1.20) as i32;
    }

    // Meaning (Noto Sans CJK, gold)
    if !meaning.is_empty() {
        text_parts.push(drawtext_with_shadow(
            meaning, CHINESE_FONT, font_meaning, "#ffd93d", "(w-tw)/2", ty, 2, 0.55,
        ));
        ty += (font_meaning as f64 * 1.30) as i32;
    }

    // Sentence (Poppins Regular)
    for line in &sentence_lines {
        text_parts.push(drawtext_with_shadow(
            line, ENGLISH_FONT_BODY, font_sentence, "white", "(w-tw)/2", ty, 1, 0.50,
        ));
        ty += line_spacing;
    }

    // Translation (Noto Sans CJK, gold)
    for line in &translation_lines {
        text_parts.push(drawtext_with_shadow(
            line, CHINESE_FONT, font_translation, "#ffd93d", "(w-tw)/2", ty, 1, 0.50,
        ));
        ty += line_spacing;
    }

    // Progress indicator (top-right)
    if total_words > 1 {
        let progress_text = format!("{} / {}", word_idx + 1, total_words);
        let progress_pad = (8.0 * scale) as i32;
        let progress_bg_w =
            measure_text_width(&progress_text, font_progress) + progress_pad * 2;
        let progress_bg_h = (font_progress as f64 * 1.6) as i32;
        let progress_bg_x = VIDEO_W - progress_bg_w - pad_h;
        let progress_bg_y = pad_h;

        text_parts.push(format!(
            "drawbox=x={progress_bg_x}:y={progress_bg_y}:w={progress_bg_w}:h={progress_bg_h}:color=black@0.30:t=fill"
        ));
        text_parts.push(format!(
            "drawtext=text='{}':fontfile='{ENGLISH_FONT_BODY}':fontcolor=white@0.50:fontsize={font_progress}:x={}:y={}",
            escape_ffmpeg_text(&progress_text),
            progress_bg_x + progress_pad,
            progress_bg_y + (progress_bg_h - font_progress) / 2,
        ));
    }

    let text_filter = text_parts.join(",");
    let overlay_str = overlay_path.to_string_lossy().to_string();

    Ok((overlay_str, panel_x, panel_y, text_filter))
}

/// Draw text with a dark shadow offset for readability without background panel.
fn drawtext_with_shadow(
    text: &str,
    font: &str,
    font_size: i32,
    color: &str,
    x_expr: &str,
    y: i32,
    shadow_offset: i32,
    shadow_opacity: f64,
) -> String {
    let escaped = escape_ffmpeg_text(text);
    format!(
        "drawtext=text='{escaped}':fontfile='{font}':fontcolor=black@{shadow_opacity:.2}:fontsize={font_size}:x={x_expr}+{shadow_offset}:y={y}+{shadow_offset},\
         drawtext=text='{escaped}':fontfile='{font}':fontcolor={color}:fontsize={font_size}:x={x_expr}:y={y}"
    )
}
```

- [ ] **Step 3: Delete `resolve_asset_path` function (no longer needed)**

Remove the `resolve_asset_path` function (lines 530-547 in original). It's unused.

- [ ] **Step 4: Verify compilation**

```bash
cd backend-rust && cargo check 2>&1 | tail -5
```

Expected: should compile successfully now.

- [ ] **Step 5: Commit**

```bash
git add backend-rust/src/services/video_export.rs
git commit -m "feat(video): rounded panel overlay, text shadows, new fonts, no tag label"
```

---

## Task 6: Update helper functions and verify build

**Files:**
- Modify: `backend-rust/src/services/video_export.rs` (helper section)

The existing helper functions (`get_audio_duration`, `ensure_even`, `to_pixel_rect`, `escape_ffmpeg_text`, `measure_text_width`, `wrap_text`, `wrap_text_cjk`, `concat_segments`, `run_ffmpeg`) mostly stay the same. Only minor changes needed.

- [ ] **Step 1: Update `concat_segments` — add `+faststart`**

The existing `concat_segments` already has `-movflags`, `+faststart`. No change needed.

- [ ] **Step 2: Verify `to_pixel_rect` uses VIDEO_H correctly**

The existing `to_pixel_rect` references `VIDEO_H` which is now 960 instead of 1280. This is correct — it will compute pixel coordinates relative to the new resolution.

- [ ] **Step 3: Full build**

```bash
cd backend-rust && cargo build 2>&1 | tail -20
```

Expected: successful build with no errors.

- [ ] **Step 4: Commit if any fixes were needed**

```bash
git add backend-rust/src/services/video_export.rs
git commit -m "fix(video): update helpers for new resolution"
```

---

## Task 7: Deploy and verify

- [ ] **Step 1: Build release binary**

```bash
cd backend-rust && cargo build --release 2>&1 | tail -5
```

- [ ] **Step 2: Stop current backend**

```bash
kill $(pgrep -f 'target/release/backend-rust')
```

- [ ] **Step 3: Copy new binary**

```bash
cp target/release/backend-rust /www/wwwroot/stag.cps.vin/weixin-demo-01/backend-rust/target/release/backend-rust
```

- [ ] **Step 4: Start backend**

```bash
cd /www/wwwroot/stag.cps.vin/weixin-demo-01/backend-rust && nohup ./target/release/backend-rust > /tmp/rust-backend.log 2>&1 &
```

- [ ] **Step 5: Trigger a test export**

From the mini program, navigate to a scene and tap "Export Video". Or use curl:

```bash
# Get a valid token first, then:
curl -X POST https://stag.cps.vin/api/scenes/<scene_id>/export-video \
  -H "Authorization: Bearer <token>"
```

- [ ] **Step 6: Verify the output**

Check the exported video:
- WeChat cover not black
- No flickering between words
- Rounded corners on panel
- IPA characters display correctly
- File size significantly smaller

```bash
# Find the latest export
ls -lt /www/wwwroot/stag.cps.vin/weixin-demo-01/assets/generated/videos/ | head -3

# Check video metadata
ffprobe -v error -show_entries format=duration,size -show_entries stream=width,height,codec_name -of json <latest_video>.mp4
```

Expected:
- `codec_name: "hevc"`
- `width: 720, height: 960`
- File size < half of previous exports for similar duration

- [ ] **Step 7: Commit final state**

```bash
git add -A
git commit -m "feat(video): complete visual upgrade — rounded panel, HEVC, new fonts"
```

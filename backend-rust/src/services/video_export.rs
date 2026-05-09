use std::path::Path;

use image::{Rgba, RgbaImage};
use serde_json::Value;

use crate::db;
use crate::state::AppState;

const VIDEO_W: i32 = 720;
const VIDEO_H: i32 = 960;

const FPS: i32 = 24;
const FADE_FRAMES: i32 = 7;
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

// ---------------------------------------------------------------------------
// Public entry point
// ---------------------------------------------------------------------------

pub async fn process_video_export(state: AppState, job_id: String) {
    let pool = &state.pool;

    let job = match db::videos::get_video_export_job(pool, &job_id).await {
        Ok(Some(j)) => j,
        Ok(None) => {
            tracing::error!(job_id, "video export job not found");
            return;
        }
        Err(e) => {
            tracing::error!(job_id, error = %e, "failed to load job");
            return;
        }
    };

    let scene = match db::scenes::get_scene(pool, &job.scene_id).await {
        Ok(Some(s)) => s,
        Ok(None) => {
            let _ = db::videos::update_video_export(
                pool, &job_id, "failed", 0, None, Some("scene not found"),
            )
            .await;
            return;
        }
        Err(e) => {
            let _ = db::videos::update_video_export(
                pool, &job_id, "failed", 0, None, Some(&e.to_string()),
            )
            .await;
            return;
        }
    };

    let _ = db::videos::update_video_export(pool, &job_id, "running", 10, None, None).await;

    let storage = match crate::storage::resolver::resolve(&state.pool, &state.config).await {
        Ok(s) => s,
        Err(e) => {
            let _ = db::videos::update_video_export(
                pool, &job_id, "failed", 0, None, Some(&format!("storage: {e}")),
            )
            .await;
            return;
        }
    };

    let video_dir = Path::new(&state.config.generated_dir).join("videos");
    if let Err(e) = tokio::fs::create_dir_all(&video_dir).await {
        let _ = db::videos::update_video_export(
            pool, &job_id, "failed", 0, None, Some(&format!("mkdir: {e}")),
        )
        .await;
        return;
    }

    let output_filename = format!("{job_id}.mp4");
    let output_path = video_dir.join(&output_filename);

    let result = generate_scene_video(&state, &scene, &output_path, &job.id, storage.as_ref()).await;

    match result {
        Ok(()) => {
            // Upload MP4 to storage
            let mp4_data = match tokio::fs::read(&output_path).await {
                Ok(d) => d,
                Err(e) => {
                    let _ = db::videos::update_video_export(
                        pool, &job_id, "failed", 0, None, Some(&format!("read mp4: {e}")),
                    )
                    .await;
                    return;
                }
            };
            let key = crate::storage::provider::StorageKey::new(&["generated", "videos", &output_filename]);
            if let Err(e) = storage.put(&key, &mp4_data, "video/mp4").await {
                let _ = db::videos::update_video_export(
                    pool, &job_id, "failed", 0, None, Some(&format!("upload mp4: {e}")),
                )
                .await;
                return;
            }

            let video_url = format!("/assets/generated/videos/{output_filename}");
            let _ = db::videos::update_video_export(
                pool, &job_id, "completed", 100, Some(&video_url), None,
            )
            .await;
            tracing::info!(job_id, "video export completed");
        }
        Err(e) => {
            let _ = db::videos::update_video_export(pool, &job_id, "failed", 0, None, Some(&e))
                .await;
            tracing::error!(job_id, error = %e, "video export failed");
        }
    }
}

// ---------------------------------------------------------------------------
// Scene video generation (segment-based, new visual style)
// ---------------------------------------------------------------------------

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
    // Create a temp directory for downloaded assets (needed for R2 mode)
    let asset_tmp = std::env::temp_dir().join(format!("video_assets_{}", uuid::Uuid::new_v4()));
    tokio::fs::create_dir_all(&asset_tmp)
        .await
        .map_err(|e| format!("asset tmp mkdir: {e}"))?;

    // Ensure background image is available locally
    let bg_key = crate::storage::provider::StorageKey::from_web_path(&scene.background_path);
    let bg_local = asset_tmp.join(format!("bg_{}", bg_key.as_str().replace('/', "_")));
    storage
        .ensure_local(&bg_key, &bg_local)
        .await
        .map_err(|e| format!("download bg: {e}"))?;
    let bg_path = bg_local.to_string_lossy().to_string();

    // Collect items with audio
    let items = scene.items.as_array().cloned().unwrap_or_default();
    let verbs = scene.verbs.as_array().cloned().unwrap_or_default();

    let mut prepared: Vec<(PreparedItem, &str)> = Vec::new(); // (item, type: "noun"/"verb")

    for item in &items {
        if let Some(audio_rel) = item["audioPath"].as_str() {
            if !audio_rel.is_empty() {
                let audio_key = crate::storage::provider::StorageKey::from_web_path(audio_rel);
                let audio_local =
                    asset_tmp.join(format!("audio_{}", audio_key.as_str().replace('/', "_")));
                if storage.ensure_local(&audio_key, &audio_local).await.is_ok() {
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
                let audio_key = crate::storage::provider::StorageKey::from_web_path(audio_rel);
                let audio_local =
                    asset_tmp.join(format!("audio_{}", audio_key.as_str().replace('/', "_")));
                if storage.ensure_local(&audio_key, &audio_local).await.is_ok() {
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
        // Fallback: static image video
        let result = generate_static_segment(&bg_path, output_path);
        let _ = tokio::fs::remove_dir_all(&asset_tmp).await;
        return result;
    }

    // Temp directory for segments
    let tmp_dir = std::env::temp_dir().join(format!("video_segs_{}", uuid::Uuid::new_v4()));
    std::fs::create_dir_all(&tmp_dir).map_err(|e| format!("tmp mkdir: {e}"))?;

    let mut segment_paths: Vec<String> = Vec::new();
    let total = prepared.len();

    // Segment 1: cover frame (0.3s)
    let cover_path = tmp_dir
        .join("cover_000.mp4")
        .to_string_lossy()
        .to_string();
    generate_cover_segment(&bg_path, Path::new(&cover_path))?;
    segment_paths.push(cover_path);

    // Progress after cover
    let _ = db::videos::update_video_export(
        &state.pool,
        job_id_for_progress,
        "running",
        15,
        None,
        None,
    )
    .await
    .ok();

    // Display segments (one per item, no transitions)
    for (idx, (pi, item_type)) in prepared.iter().enumerate() {
        let seg_path = tmp_dir
            .join(format!("display_{idx:03}.mp4"))
            .to_string_lossy()
            .to_string();
        generate_display_segment(
            &tmp_dir,
            &bg_path,
            &pi.audio_abs,
            pi.audio_duration,
            &pi.item,
            item_type,
            idx,
            total,
            Path::new(&seg_path),
        )?;
        segment_paths.push(seg_path);

        // Progress update
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

    // Concat all segments
    concat_segments(&segment_paths, &output_path.to_string_lossy())?;

    // Cleanup temp dirs
    let _ = std::fs::remove_dir_all(&tmp_dir);
    let _ = tokio::fs::remove_dir_all(&asset_tmp).await;

    Ok(())
}

// ---------------------------------------------------------------------------
// Rounded panel PNG generator (SDF anti-aliased)
// ---------------------------------------------------------------------------

fn generate_rounded_panel_png(
    path: &Path,
    w: i32,
    h: i32,
    radius: i32,
    fill_rgba: [u8; 4],
    border_rgba: [u8; 4],
    border_w: i32,
) -> Result<(), String> {
    let w = w.max(1) as u32;
    let h = h.max(1) as u32;
    let radius = radius.max(0) as f64;
    let border_w = border_w.max(0) as f64;

    let mut img = RgbaImage::new(w, h);

    let hw = w as f64 / 2.0;
    let hh = h as f64 / 2.0;

    for y in 0..h {
        for x in 0..w {
            let px = x as f64 + 0.5;
            let py = y as f64 + 0.5;

            // Signed distance to rounded rectangle
            let qx = (px - hw).abs() - (hw - radius);
            let qy = (py - hh).abs() - (hh - radius);
            let d =
                (qx.max(0.0).powi(2) + qy.max(0.0).powi(2)).sqrt() + qx.max(qy).min(0.0) - radius;

            // Anti-aliased outer edge: clamp(0.75 - d, 0, 1)
            let outer_alpha = (0.75 - d).clamp(0.0, 1.0);

            // Border region: distance from outer edge to inner edge
            let d_inner = d + border_w;
            let inner_alpha = (0.75 - d_inner).clamp(0.0, 1.0);

            // Fill alpha = outer - inner, Border alpha = inner
            let fill_a = (outer_alpha - inner_alpha).clamp(0.0, 1.0);
            let border_a = inner_alpha.clamp(0.0, 1.0);

            // Composite: border on bottom, fill on top
            let ba = border_a * (border_rgba[3] as f64 / 255.0);
            let fa = fill_a * (fill_rgba[3] as f64 / 255.0);

            let r = (border_rgba[0] as f64 * ba + fill_rgba[0] as f64 * fa)
                / (ba + fa + 1e-6);
            let g = (border_rgba[1] as f64 * ba + fill_rgba[1] as f64 * fa)
                / (ba + fa + 1e-6);
            let b = (border_rgba[2] as f64 * ba + fill_rgba[2] as f64 * fa)
                / (ba + fa + 1e-6);
            let a = ((ba + fa) * 255.0).min(255.0);

            img.put_pixel(x, y, Rgba([r as u8, g as u8, b as u8, a as u8]));
        }
    }

    img.save(path)
        .map_err(|e| format!("save panel png: {e}"))?;
    Ok(())
}

// ---------------------------------------------------------------------------
// Segment generators
// ---------------------------------------------------------------------------

/// Cover frame: scale+crop+border, libx264, 24fps, 64k mono, 0.3s
fn generate_cover_segment(image: &str, output: &Path) -> Result<(), String> {
    let (sw, sh) = ensure_even(VIDEO_W, VIDEO_H);
    let vf = format!(
        "scale={sw}:{sh}:force_original_aspect_ratio=increase,crop={sw}:{sh},{}",
        build_frame_border_filter(sw, sh)
    );

    run_ffmpeg(&[
        "-y",
        "-loop",
        "1",
        "-i",
        image,
        "-f",
        "lavfi",
        "-i",
        "anullsrc=r=44100:cl=mono",
        "-vf",
        &vf,
        "-c:v",
        "libx264",
        "-r",
        "24",
        "-preset",
        "fast",
        "-c:a",
        "aac",
        "-b:a",
        "64k",
        "-ar",
        "44100",
        "-ac",
        "1",
        "-pix_fmt",
        "yuv420p",
        "-t",
        "0.3",
        &output.to_string_lossy(),
    ])
}

/// Intro segment: scale+crop + black@0.70 overlay + title text + border + fade_out
fn generate_intro_segment(image: &str, title: &str, output: &Path) -> Result<(), String> {
    let (sw, sh) = ensure_even(VIDEO_W, VIDEO_H);
    let scale = VIDEO_W as f64 / 720.0;
    let font_size = (48.0 * scale) as i32;

    // Write title to temp file for FFmpeg textfile parameter
    let tmp_dir = std::env::temp_dir().join(format!("intro_text_{}", uuid::Uuid::new_v4()));
    std::fs::create_dir_all(&tmp_dir).map_err(|e| format!("intro tmp mkdir: {e}"))?;
    let text_file = tmp_dir.join("title.txt");
    std::fs::write(&text_file, title.replace('%', "%%"))
        .map_err(|e| format!("write title text: {e}"))?;

    let text_file_path = text_file.to_string_lossy().to_string();

    let border = build_frame_border_filter(sw, sh);
    let fade_frames = FADE_FRAMES;
    let fade_dur = format!("{:.3}", fade_frames as f64 / FPS as f64);

    let vf = format!(
        "scale={sw}:{sh}:force_original_aspect_ratio=increase,crop={sw}:{sh},\
         drawbox=x=0:y=0:w={sw}:h={sh}:color=black@0.70:t=fill,\
         drawtext=textfile='{text_file_path}':fontfile='{CHINESE_FONT}':\
         fontcolor=white:fontsize={font_size}:x=(w-tw)/2:y=(h-th)/2,\
         {border},\
         fade=t=out:st={fade_dur}:d=0.3"
    );

    let result = run_ffmpeg(&[
        "-y",
        "-loop",
        "1",
        "-i",
        image,
        "-f",
        "lavfi",
        "-i",
        "anullsrc=r=44100:cl=mono",
        "-vf",
        &vf,
        "-c:v",
        "libx264",
        "-r",
        "24",
        "-preset",
        "fast",
        "-c:a",
        "aac",
        "-b:a",
        "64k",
        "-ar",
        "44100",
        "-ac",
        "1",
        "-pix_fmt",
        "yuv420p",
        "-t",
        &format!("{:.3}", INTRO_DURATION),
        &output.to_string_lossy(),
    ]);

    // Clean up temp files
    let _ = std::fs::remove_dir_all(&tmp_dir);

    result
}

/// Static fallback: scale+crop+border, libx264, 5s
fn generate_static_segment(image: &str, output: &Path) -> Result<(), String> {
    let (sw, sh) = ensure_even(VIDEO_W, VIDEO_H);
    let vf = format!(
        "scale={sw}:{sh}:force_original_aspect_ratio=increase,crop={sw}:{sh},{}",
        build_frame_border_filter(sw, sh)
    );

    run_ffmpeg(&[
        "-y",
        "-loop",
        "1",
        "-i",
        image,
        "-f",
        "lavfi",
        "-i",
        "anullsrc=r=44100:cl=mono",
        "-vf",
        &vf,
        "-c:v",
        "libx264",
        "-r",
        "24",
        "-preset",
        "fast",
        "-c:a",
        "aac",
        "-b:a",
        "64k",
        "-ar",
        "44100",
        "-ac",
        "1",
        "-pix_fmt",
        "yuv420p",
        "-t",
        "5",
        &output.to_string_lossy(),
    ])
}

/// Display segment: bg + audio + panel overlay with text. Uses -filter_complex with 3 inputs.
fn generate_display_segment(
    tmp_dir: &Path,
    image: &str,
    audio: &str,
    audio_duration: f64,
    item: &Value,
    item_type: &str,
    word_idx: usize,
    total_words: usize,
    output: &Path,
) -> Result<(), String> {
    let (sw, sh) = ensure_even(VIDEO_W, VIDEO_H);

    // Build panel info (PNG + text filter)
    let (panel_png, panel_x, panel_y, text_filters) =
        build_panel_info(tmp_dir, item, word_idx, total_words)?;

    // Build highlight filter for noun items with rect
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

    let border = build_frame_border_filter(sw, sh);

    // Build filter_complex: 0:bg, 1:audio, 2:panel.png
    let mut fc = format!(
        "[0:v]scale={sw}:{sh}:force_original_aspect_ratio=increase,crop={sw}:{sh}"
    );

    if !highlight.is_empty() {
        fc.push_str(&format!(",{highlight}"));
    }

    fc.push_str("[bg_scaled];");

    // Overlay panel PNG: bg_scaled + panel -> bg_with_panel
    fc.push_str(&format!(
        "[bg_scaled][2:v]overlay={panel_x}:{panel_y}:eval=init[bg_with_panel]"
    ));

    // Text filters on top of panel overlay
    if text_filters.is_empty() {
        fc.push_str(&format!(
            ";[bg_with_panel]{border}[final]"
        ));
    } else {
        fc.push_str(&format!(
            ";[bg_with_panel]{text_filters},{border}[final]"
        ));
    }

    let dur_str = format!("{:.3}", audio_duration.max(1.0));

    run_ffmpeg(&[
        "-y",
        "-loop",
        "1",
        "-i",
        image,
        "-i",
        audio,
        "-i",
        &panel_png,
        "-filter_complex",
        &fc,
        "-map",
        "[final]",
        "-map",
        "1:a",
        "-c:v",
        "libx264",
        "-r",
        "24",
        "-preset",
        "fast",
        "-c:a",
        "aac",
        "-b:a",
        "64k",
        "-ar",
        "44100",
        "-ac",
        "1",
        "-pix_fmt",
        "yuv420p",
        "-t",
        &dur_str,
        &output.to_string_lossy(),
    ])
}

// ---------------------------------------------------------------------------
// FFmpeg filter builders
// ---------------------------------------------------------------------------

/// 4 drawbox for 8px white@0.12 border on all edges
fn build_frame_border_filter(img_w: i32, img_h: i32) -> String {
    let bw = FRAME_BORDER_W;
    let top = format!(
        "drawbox=x=0:y=0:w={img_w}:h={bw}:color=white@0.12:t=fill"
    );
    let bottom = format!(
        "drawbox=x=0:y={}:w={img_w}:h={bw}:color=white@0.12:t=fill",
        img_h - bw
    );
    let left = format!(
        "drawbox=x=0:y=0:w={bw}:h={img_h}:color=white@0.12:t=fill"
    );
    let right = format!(
        "drawbox=x={}:y=0:w={bw}:h={img_h}:color=white@0.12:t=fill",
        img_w - bw
    );
    format!("{top},{bottom},{left},{right}")
}

/// Simple highlight: white@0.10 fill + white@0.85 border t=2
fn build_highlight_filter(x: i32, y: i32, w: i32, h: i32) -> String {
    format!(
        "drawbox=x={x}:y={y}:w={w}:h={h}:color=white@0.10:t=fill,\
         drawbox=x={x}:y={y}:w={w}:h={h}:color=white@0.85:t=2"
    )
}

/// Build rounded panel PNG and text filter chain for a vocabulary item.
/// Returns (overlay_png_path, panel_x, panel_y, text_filter_string).
fn build_panel_info(
    tmp_dir: &Path,
    item: &Value,
    word_idx: usize,
    total_words: usize,
) -> Result<(String, i32, i32, String), String> {
    let scale = VIDEO_W as f64 / 720.0;
    let pad_h = (VIDEO_W as f64 * 0.04) as i32; // horizontal padding
    let pad_v = (VIDEO_H as f64 * 0.02) as i32; // vertical padding
    let usable_w = VIDEO_W - pad_h * 2;

    let font_word = (40.0 * scale) as i32;
    let font_ipa = (22.0 * scale) as i32;
    let font_meaning = (26.0 * scale) as i32;
    let font_sentence = (24.0 * scale) as i32;
    let font_translation = (22.0 * scale) as i32;
    let font_progress = (16.0 * scale) as i32;

    let line_spacing_word = (font_word as f64 * 1.15) as i32;
    let line_spacing = (font_sentence as f64 * 1.35) as i32;

    let word = item["word"].as_str().unwrap_or("");
    let ipa = item["ipa"].as_str().unwrap_or("");
    let meaning = item["meaning"].as_str().unwrap_or("");
    let sentence = item["sentence"].as_str().unwrap_or("");
    let translation = item
        .get("sentenceTranslation")
        .or_else(|| item.get("sentence_translation"))
        .and_then(|v| v.as_str())
        .unwrap_or("");

    // Calculate panel height (no tag height)
    let mut total_height = pad_v;
    total_height += line_spacing_word; // word line
    if !ipa.is_empty() {
        total_height += (font_ipa as f64 * 1.2) as i32;
    }
    if !meaning.is_empty() {
        total_height += (font_meaning as f64 * 1.3) as i32;
    }
    if !sentence.is_empty() {
        let lines = wrap_text(sentence, font_sentence, usable_w - pad_h);
        total_height += lines.len() as i32 * line_spacing;
    }
    if !translation.is_empty() {
        let lines = wrap_text_cjk(translation, font_translation, usable_w - pad_h);
        total_height += lines.len() as i32 * line_spacing;
    }
    total_height += pad_v;

    let panel_w = usable_w;
    let panel_h = total_height;
    let panel_x = pad_h;
    let bottom_margin = (VIDEO_H as f64 * 0.025) as i32;
    let panel_y = VIDEO_H - panel_h - bottom_margin;

    // Generate rounded panel PNG
    let panel_png_path = tmp_dir
        .join(format!("panel_{word_idx}.png"))
        .to_string_lossy()
        .to_string();

    generate_rounded_panel_png(
        Path::new(&panel_png_path),
        panel_w,
        panel_h,
        PANEL_RADIUS,
        [0, 0, 0, PANEL_FILL_ALPHA],     // fill: black semi-transparent
        [255, 255, 255, PANEL_BORDER_ALPHA], // border: white subtle
        PANEL_BORDER_W,
    )?;

    // Build text filter chain
    let mut filters = Vec::new();
    let mut ty = panel_y + pad_v;
    let mut text_idx: usize = 0;

    // Word (centered, white, ENGLISH_FONT)
    if !word.is_empty() {
        filters.push(drawtext_with_shadow(
            tmp_dir, &mut text_idx,
            word,
            ENGLISH_FONT,
            font_word,
            "white",
            "(w-tw)/2",
            ty,
            2,
            0.6,
        )?);
        ty += line_spacing_word;
    }

    // IPA (centered, white@0.70, IPA_FONT)
    if !ipa.is_empty() {
        let ipa_file = write_text_file(tmp_dir, &format!("txt_{}_ipa", text_idx), ipa)?;
        text_idx += 1;
        filters.push(format!(
            "drawtext=textfile='{ipa_file}':fontfile='{IPA_FONT}':fontcolor=white@0.70:fontsize={font_ipa}:x=(w-tw)/2:y={ty}"
        ));
        ty += (font_ipa as f64 * 1.2) as i32;
    }

    // Meaning (centered, #ffd93d, CHINESE_FONT)
    if !meaning.is_empty() {
        filters.push(drawtext_with_shadow(
            tmp_dir, &mut text_idx,
            meaning,
            CHINESE_FONT,
            font_meaning,
            "#ffd93d",
            "(w-tw)/2",
            ty,
            2,
            0.6,
        )?);
        ty += (font_meaning as f64 * 1.3) as i32;
    }

    // Sentence (centered, white, ENGLISH_FONT_BODY) — wrapped
    if !sentence.is_empty() {
        let lines = wrap_text(sentence, font_sentence, usable_w - pad_h);
        for line in &lines {
            filters.push(drawtext_with_shadow(
                tmp_dir, &mut text_idx,
                line,
                ENGLISH_FONT_BODY,
                font_sentence,
                "white",
                "(w-tw)/2",
                ty,
                1,
                0.5,
            )?);
            ty += line_spacing;
        }
    }

    // Translation (centered, #ffd93d, CHINESE_FONT) — wrapped CJK
    if !translation.is_empty() {
        let lines = wrap_text_cjk(translation, font_translation, usable_w - pad_h);
        for line in &lines {
            filters.push(drawtext_with_shadow(
                tmp_dir, &mut text_idx,
                line,
                CHINESE_FONT,
                font_translation,
                "#ffd93d",
                "(w-tw)/2",
                ty,
                1,
                0.5,
            )?);
            ty += line_spacing;
        }
    }

    // Progress indicator in top-right corner if total_words > 1
    if total_words > 1 {
        let progress_text = format!("{}/{}", word_idx + 1, total_words);
        let prog_file = write_text_file(tmp_dir, &format!("txt_{}_prog", text_idx), &progress_text)?;
        text_idx += 1;
        let prog_x = format!("w-tw-{}", pad_h);
        let prog_y = pad_h / 2;
        filters.push(format!(
            "drawtext=textfile='{prog_file}':fontfile='{ENGLISH_FONT}':fontcolor=white@0.50:fontsize={font_progress}:x={prog_x}:y={prog_y}"
        ));
    }

    let text_filter_string = filters.join(",");

    Ok((panel_png_path, panel_x, panel_y, text_filter_string))
}

/// Draw text with shadow effect using textfile to avoid quoting issues.
fn drawtext_with_shadow(
    tmp_dir: &Path,
    idx: &mut usize,
    text: &str,
    font: &str,
    font_size: i32,
    color: &str,
    x_expr: &str,
    y: i32,
    shadow_offset: i32,
    shadow_opacity: f64,
) -> Result<String, String> {
    let shadow_file = write_text_file(tmp_dir, &format!("txt_{}_shadow", idx), text)?;
    let main_file = write_text_file(tmp_dir, &format!("txt_{}_main", idx), text)?;
    *idx += 1;
    Ok(format!(
        "drawtext=textfile='{shadow_file}':fontfile='{font}':fontcolor=black@{shadow_opacity}:fontsize={font_size}:x={x_expr}+{shadow_offset}:y={y}+{shadow_offset},\
         drawtext=textfile='{main_file}':fontfile='{font}':fontcolor={color}:fontsize={font_size}:x={x_expr}:y={y}"
    ))
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

fn get_audio_duration(path: &str) -> f64 {
    let output = std::process::Command::new("ffprobe")
        .args([
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=s=x:p=0",
            path,
        ])
        .output();

    match output {
        Ok(out) if out.status.success() => {
            let text = String::from_utf8_lossy(&out.stdout);
            text.trim().parse::<f64>().unwrap_or(3.0).max(0.5)
        }
        _ => 3.0,
    }
}

fn ensure_even(w: i32, h: i32) -> (i32, i32) {
    (w & !1, h & !1)
}

fn to_pixel_rect(rect: &Value) -> (i32, i32, i32, i32) {
    let l = rect["l"].as_f64().unwrap_or(0.0) / 100.0 * VIDEO_W as f64;
    let t = rect["t"].as_f64().unwrap_or(0.0) / 100.0 * VIDEO_H as f64;
    let w = rect["w"].as_f64().unwrap_or(10.0) / 100.0 * VIDEO_W as f64;
    let h = rect["h"].as_f64().unwrap_or(10.0) / 100.0 * VIDEO_H as f64;
    (l as i32, t as i32, w as i32, h as i32)
}

fn escape_ffmpeg_text(text: &str) -> String {
    text.replace('\\', "\\\\")
        .replace('\'', "\\'")
        .replace(':', "\\:")
        .replace('%', "%%")
        .replace('[', "\\[")
        .replace(']', "\\]")
        .replace(';', "\\;")
        .replace(',', "\\,")
}

/// Write text to a temp file for FFmpeg drawtext textfile parameter.
/// Returns the file path. This avoids shell-quoting issues with drawtext text='...'.
fn write_text_file(tmp_dir: &Path, name: &str, text: &str) -> Result<String, String> {
    let path = tmp_dir.join(format!("{name}.txt"));
    std::fs::write(&path, text.replace('%', "%%"))
        .map_err(|e| format!("write text file: {e}"))?;
    Ok(path.to_string_lossy().to_string())
}

/// Rough text width estimation (characters * font_size / 2 for CJK, / 1.8 for Latin)
fn measure_text_width(text: &str, font_size: i32) -> i32 {
    let mut width = 0.0;
    for ch in text.chars() {
        if ch.is_ascii() {
            width += font_size as f64 / 1.8;
        } else {
            width += font_size as f64;
        }
    }
    width as i32
}

fn wrap_text(text: &str, font_size: i32, max_width: i32) -> Vec<String> {
    let full_width = measure_text_width(text, font_size);
    if full_width <= max_width {
        return vec![text.to_string()];
    }

    let words: Vec<&str> = text.split(' ').collect();
    let mut lines = Vec::new();
    let mut current = String::new();

    for word in &words {
        let test = if current.is_empty() {
            word.to_string()
        } else {
            format!("{current} {word}")
        };
        if measure_text_width(&test, font_size) <= max_width {
            current = test;
        } else {
            if !current.is_empty() {
                lines.push(current);
            }
            current = word.to_string();
        }
    }
    if !current.is_empty() {
        lines.push(current);
    }

    if lines.is_empty() {
        vec![text.to_string()]
    } else {
        lines
    }
}

fn wrap_text_cjk(text: &str, font_size: i32, max_width: i32) -> Vec<String> {
    let full_width = measure_text_width(text, font_size);
    if full_width <= max_width {
        return vec![text.to_string()];
    }

    let mut lines = Vec::new();
    let mut current = String::new();

    for ch in text.chars() {
        let test = format!("{current}{ch}");
        if measure_text_width(&test, font_size) <= max_width {
            current = test;
        } else {
            if !current.is_empty() {
                lines.push(current);
            }
            current = ch.to_string();
        }
    }
    if !current.is_empty() {
        lines.push(current);
    }

    if lines.is_empty() {
        vec![text.to_string()]
    } else {
        lines
    }
}

fn concat_segments(segment_paths: &[String], output: &str) -> Result<(), String> {
    let tmp_dir = std::env::temp_dir().join("video_exports");
    std::fs::create_dir_all(&tmp_dir).map_err(|e| format!("tmp mkdir: {e}"))?;

    let concat_path = tmp_dir.join(format!("final_{}.txt", uuid::Uuid::new_v4()));
    let mut content = String::new();
    for p in segment_paths {
        content.push_str(&format!("file '{p}'\n"));
    }
    std::fs::write(&concat_path, &content).map_err(|e| format!("write concat: {e}"))?;

    let result = run_ffmpeg(&[
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        &concat_path.to_string_lossy(),
        "-c",
        "copy",
        "-movflags",
        "+faststart",
        output,
    ]);

    let _ = std::fs::remove_file(&concat_path);
    result
}

fn run_ffmpeg(args: &[&str]) -> Result<(), String> {
    let output = std::process::Command::new("ffmpeg")
        .args(args)
        .output()
        .map_err(|e| format!("ffmpeg spawn: {e}"))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        let msg = if stderr.len() > 500 {
            &stderr[stderr.len() - 500..]
        } else {
            &stderr
        };
        return Err(format!("ffmpeg failed: {msg}"));
    }
    Ok(())
}

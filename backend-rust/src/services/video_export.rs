use std::path::Path;

use serde_json::Value;

use crate::db;
use crate::state::AppState;

const VIDEO_W: i32 = 720;
const VIDEO_H: i32 = 1280;
const CHINESE_FONT: &str = "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf";
const ENGLISH_FONT: &str = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf";

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
// Scene video generation (segment-based, matches Python version)
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
    tokio::fs::create_dir_all(&asset_tmp).await.map_err(|e| format!("asset tmp mkdir: {e}"))?;

    // Ensure background image is available locally
    let bg_key = crate::storage::provider::StorageKey::from_web_path(&scene.background_path);
    let bg_local = asset_tmp.join(format!("bg_{}", bg_key.as_str().replace('/', "_")));
    storage.ensure_local(&bg_key, &bg_local).await.map_err(|e| format!("download bg: {e}"))?;
    let bg_path = bg_local.to_string_lossy().to_string();

    // Collect items with audio
    let items = scene.items.as_array().cloned().unwrap_or_default();
    let verbs = scene.verbs.as_array().cloned().unwrap_or_default();

    let mut prepared: Vec<(PreparedItem, &str)> = Vec::new(); // (item, type: "noun"/"verb")

    for item in &items {
        if let Some(audio_rel) = item["audioPath"].as_str() {
            if !audio_rel.is_empty() {
                let audio_key = crate::storage::provider::StorageKey::from_web_path(audio_rel);
                let audio_local = asset_tmp.join(format!("audio_{}", audio_key.as_str().replace('/', "_")));
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
                let audio_local = asset_tmp.join(format!("audio_{}", audio_key.as_str().replace('/', "_")));
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

    for (idx, (pi, item_type)) in prepared.iter().enumerate() {
        // Transition segment (0.3s) before each segment except the first
        if idx > 0 {
            let move_path = tmp_dir
                .join(format!("move_{idx:03}.mp4"))
                .to_string_lossy()
                .to_string();
            generate_move_segment(&bg_path, &move_path)?;
            segment_paths.push(move_path);
        }

        // Display segment with highlight + panel
        let seg_path = tmp_dir
            .join(format!("display_{idx:03}.mp4"))
            .to_string_lossy()
            .to_string();
        generate_display_segment(
            &bg_path,
            &pi.audio_abs,
            pi.audio_duration,
            &pi.item,
            item_type,
            &seg_path,
        )?;
        segment_paths.push(seg_path);

        // Progress update
        let pct = 15 + ((idx + 1) * 65 / total).min(80);
        let _ = db::videos::update_video_export(
            &state.pool,
            &job_id_for_progress,
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
// Segment generators
// ---------------------------------------------------------------------------

fn generate_static_segment(image: &str, output: &Path) -> Result<(), String> {
    let (sw, sh) = ensure_even(VIDEO_W, VIDEO_H);
    let vf = format!(
        "scale={sw}:{sh}:force_original_aspect_ratio=increase,crop={sw}:{sh}"
    );
    run_ffmpeg(&[
        "-y",
        "-loop", "1",
        "-i", image,
        "-c:v", "libx264",
        "-t", "5",
        "-r", "25",
        "-pix_fmt", "yuv420p",
        "-vf", &vf,
        &output.to_string_lossy(),
    ])
}

fn generate_move_segment(image: &str, output: &str) -> Result<(), String> {
    let (sw, sh) = ensure_even(VIDEO_W, VIDEO_H);
    let vf = format!(
        "scale={sw}:{sh}:force_original_aspect_ratio=increase,crop={sw}:{sh}"
    );
    run_ffmpeg(&[
        "-y",
        "-loop", "1",
        "-i", image,
        "-f", "lavfi",
        "-i", "anullsrc=r=44100:cl=stereo",
        "-vf", &vf,
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-r", "25",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",
        "-ac", "2",
        "-pix_fmt", "yuv420p",
        "-t", "0.3",
        output,
    ])
}

fn generate_display_segment(
    image: &str,
    audio: &str,
    audio_duration: f64,
    item: &Value,
    item_type: &str,
    output: &str,
) -> Result<(), String> {
    let (sw, sh) = ensure_even(VIDEO_W, VIDEO_H);
    let scale_filter = format!(
        "scale={sw}:{sh}:force_original_aspect_ratio=increase,crop={sw}:{sh}"
    );

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

    // Build info panel
    let panel = build_panel_filter(item, item_type);

    // Combine filter chain
    let vf = if highlight.is_empty() {
        format!("{scale_filter},{panel}")
    } else {
        format!("{scale_filter},{highlight},{panel}")
    };

    let dur_str = format!("{:.3}", audio_duration.max(1.0));

    run_ffmpeg(&[
        "-y",
        "-loop", "1",
        "-i", image,
        "-i", audio,
        "-vf", &vf,
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-r", "25",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",
        "-ac", "2",
        "-pix_fmt", "yuv420p",
        "-t", &dur_str,
        output,
    ])
}

// ---------------------------------------------------------------------------
// FFmpeg filter builders
// ---------------------------------------------------------------------------

fn build_highlight_filter(x: i32, y: i32, w: i32, h: i32) -> String {
    let glow = 12;
    let x1 = (x - glow).max(0);
    let y1 = (y - glow).max(0);
    let x2 = (x + w + glow).min(VIDEO_W);
    let y2 = (y + h + glow).min(VIDEO_H);
    let gw = x2 - x1;
    let gh = y2 - y1;
    format!(
        "drawbox=x={x}:y={y}:w={w}:h={h}:color=white@0.18:t=fill,\
         drawbox=x={x}:y={y}:w={w}:h={h}:color=white@0.95:t=2,\
         drawbox=x={x1}:y={y1}:w={gw}:h={gh}:color=white@0.10:t=8"
    )
}

fn build_panel_filter(item: &Value, item_type: &str) -> String {
    let pad = (VIDEO_W as f64 * 0.035) as i32;
    let usable_w = VIDEO_W - pad * 2;
    let scale = VIDEO_W as f64 / 720.0;

    let font_word = (60.0 * scale) as i32;
    let font_ipa = (36.0 * scale) as i32;
    let font_meaning = (42.0 * scale) as i32;
    let font_sentence = (38.0 * scale) as i32;
    let font_translation = (36.0 * scale) as i32;
    let font_tag = (24.0 * scale) as i32;

    let line_spacing_word = (font_word as f64 * 1.05) as i32;
    let line_spacing = (font_sentence as f64 * 1.25) as i32;
    let tag_height = (font_tag as f64 * 1.6) as i32;

    let word = item["word"].as_str().unwrap_or("");
    let ipa = item["ipa"].as_str().unwrap_or("");
    let meaning = item["meaning"].as_str().unwrap_or("");
    let sentence = item["sentence"].as_str().unwrap_or("");
    let translation = item
        .get("sentenceTranslation")
        .or_else(|| item.get("sentence_translation"))
        .and_then(|v| v.as_str())
        .unwrap_or("");

    // Calculate panel height
    let mut total_height = pad;
    total_height += tag_height;
    total_height += line_spacing_word;
    if !ipa.is_empty() {
        total_height += (font_ipa as f64 * 1.2) as i32;
    }
    if !meaning.is_empty() {
        total_height += (font_meaning as f64 * 1.3) as i32;
    }
    if !sentence.is_empty() {
        total_height += line_spacing;
    }
    if !translation.is_empty() {
        total_height += line_spacing;
    }
    total_height += pad;

    let panel_y = VIDEO_H - total_height;

    // Build filter chain
    let mut filters = Vec::new();

    // Background
    if item_type == "verb" {
        filters.push(format!(
            "drawbox=x={pad}:y={panel_y}:w={usable_w}:h={total_height}:color=black@0.55:t=fill"
        ));
        filters.push(format!(
            "drawbox=x={pad}:y={panel_y}:w={usable_w}:h={total_height}:color=#4fc3f7@0.15:t=2"
        ));
    } else {
        filters.push(format!(
            "drawbox=x={pad}:y={panel_y}:w={usable_w}:h={total_height}:color=black@0.55:t=fill"
        ));
        filters.push(format!(
            "drawbox=x={pad}:y={panel_y}:w={usable_w}:h={total_height}:color=white@0.10:t=1"
        ));
    }

    let mut ty = panel_y + pad;

    // Type tag
    let tag_text = if item_type == "verb" {
        "动词"
    } else {
        "名词"
    };
    let tag_color = if item_type == "verb" {
        "#4fc3f7"
    } else {
        "#ffd93d"
    };
    let tag_bg = if item_type == "verb" {
        "#4fc3f7@0.25"
    } else {
        "#ffd93d@0.25"
    };
    let tag_w = measure_text_width(tag_text, font_tag) + (font_tag / 2) as i32 * 2;
    let tag_h = tag_height - pad / 3;
    let tag_x = (VIDEO_W - tag_w) / 2;
    filters.push(format!(
        "drawbox=x={tag_x}:y={ty}:w={tag_w}:h={tag_h}:color={tag_bg}:t=fill"
    ));
    filters.push(format!(
        "drawtext=text='{}':fontfile='{CHINESE_FONT}':fontcolor={tag_color}:fontsize={font_tag}:x=(w-tw)/2:y={}",
        escape_ffmpeg_text(tag_text),
        ty + (tag_h - font_tag) / 2
    ));
    ty += tag_height;

    // Word
    if !word.is_empty() {
        filters.push(format!(
            "drawtext=text='{}':fontfile='{ENGLISH_FONT}':fontcolor=white:fontsize={font_word}:x=(w-tw)/2:y={ty}",
            escape_ffmpeg_text(word)
        ));
        ty += line_spacing_word;
    }

    // IPA
    if !ipa.is_empty() {
        filters.push(format!(
            "drawtext=text='{}':fontfile='{ENGLISH_FONT}':fontcolor=white@0.72:fontsize={font_ipa}:x=(w-tw)/2:y={ty}",
            escape_ffmpeg_text(ipa)
        ));
        ty += (font_ipa as f64 * 1.2) as i32;
    }

    // Meaning
    if !meaning.is_empty() {
        filters.push(format!(
            "drawtext=text='{}':fontfile='{CHINESE_FONT}':fontcolor=#ffd93d:fontsize={font_meaning}:x=(w-tw)/2:y={ty}",
            escape_ffmpeg_text(meaning)
        ));
        ty += (font_meaning as f64 * 1.3) as i32;
    }

    // Sentence (English) — single line, truncated if too long
    if !sentence.is_empty() {
        let lines = wrap_text(sentence, font_sentence, usable_w);
        for line in &lines {
            filters.push(format!(
                "drawtext=text='{}':fontfile='{ENGLISH_FONT}':fontcolor=white:fontsize={font_sentence}:x=(w-tw)/2:y={ty}",
                escape_ffmpeg_text(line)
            ));
            ty += line_spacing;
        }
    }

    // Translation (Chinese) — single line, truncated if too long
    if !translation.is_empty() {
        let lines = wrap_text_cjk(translation, font_translation, usable_w);
        for line in &lines {
            filters.push(format!(
                "drawtext=text='{}':fontfile='{CHINESE_FONT}':fontcolor=#ffd93d:fontsize={font_translation}:x=(w-tw)/2:y={ty}",
                escape_ffmpeg_text(line)
            ));
            ty += line_spacing;
        }
    }

    filters.join(",")
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

fn resolve_asset_path(relative: &str) -> Result<String, String> {
    let cwd = std::env::current_dir().map_err(|e| format!("get cwd: {e}"))?;
    let rel = if relative.starts_with('/') {
        format!("..{relative}")
    } else {
        relative.to_string()
    };
    let resolved = cwd.join(&rel);
    let abs = resolved
        .canonicalize()
        .unwrap_or(resolved)
        .to_string_lossy()
        .to_string();
    if !Path::new(&abs).exists() {
        return Err(format!("asset not found: {abs}"));
    }
    Ok(abs)
}

fn get_audio_duration(path: &str) -> f64 {
    let output = std::process::Command::new("ffprobe")
        .args([
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "csv=s=x:p=0",
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
        "-f", "concat",
        "-safe", "0",
        "-i", &concat_path.to_string_lossy(),
        "-c", "copy",
        "-movflags", "+faststart",
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
        return Err(format!(
            "ffmpeg failed: {}",
            &stderr[..stderr.len().min(500)]
        ));
    }
    Ok(())
}

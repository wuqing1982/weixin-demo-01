use std::path::Path;

use crate::db;
use crate::state::AppState;

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

    // Load scene
    let scene = match db::scenes::get_scene(pool, &job.scene_id).await {
        Ok(Some(s)) => s,
        Ok(None) => {
            let _ = db::videos::update_video_export(
                pool, &job_id, "failed", 0, None, Some("scene not found"),
            ).await;
            return;
        }
        Err(e) => {
            let _ = db::videos::update_video_export(
                pool, &job_id, "failed", 0, None, Some(&e.to_string()),
            ).await;
            return;
        }
    };

    let _ = db::videos::update_video_export(pool, &job_id, "running", 10, None, None).await;

    // Create output directory
    let video_dir = Path::new(&state.config.generated_dir).join("videos");
    if let Err(e) = tokio::fs::create_dir_all(&video_dir).await {
        let _ = db::videos::update_video_export(
            pool, &job_id, "failed", 0, None, Some(&format!("mkdir: {e}")),
        ).await;
        return;
    }

    let output_filename = format!("{job_id}.mp4");
    let output_path = video_dir.join(&output_filename);

    // Build FFmpeg command to create a video from scene image + audio
    let cwd = std::env::current_dir().unwrap_or_default();
    let bg_path = if scene.background_path.starts_with('/') {
        let resolved = cwd.join(format!(".{}", scene.background_path));
        resolved.canonicalize().unwrap_or(resolved).to_string_lossy().to_string()
    } else {
        scene.background_path.clone()
    };

    // Get audio files from scene items
    let items = scene.items.as_array().cloned().unwrap_or_default();
    let audio_files: Vec<String> = items
        .iter()
        .filter_map(|item| item["audioPath"].as_str().map(|s| s.to_string()))
        .filter(|s| !s.is_empty())
        .collect();

    let result = if audio_files.is_empty() {
        // No audio - just create a 5-second static image video
        run_ffmpeg_static_image(&bg_path, output_path.to_str().unwrap_or(""))
    } else {
        // Concatenate audio files and overlay on image
        run_ffmpeg_with_audio(&bg_path, &audio_files, output_path.to_str().unwrap_or(""), &state).await
    };

    match result {
        Ok(()) => {
            let video_url = format!("/assets/generated/videos/{output_filename}");
            let _ = db::videos::update_video_export(
                pool, &job_id, "completed", 100, Some(&video_url), None,
            ).await;
            tracing::info!(job_id, "video export completed");
        }
        Err(e) => {
            let _ = db::videos::update_video_export(
                pool, &job_id, "failed", 0, None, Some(&e),
            ).await;
            tracing::error!(job_id, error = %e, "video export failed");
        }
    }
}

fn run_ffmpeg_static_image(input_image: &str, output_path: &str) -> Result<(), String> {
    let status = std::process::Command::new("ffmpeg")
        .args([
            "-y",
            "-loop", "1",
            "-i", input_image,
            "-c:v", "libx264",
            "-t", "5",
            "-pix_fmt", "yuv420p",
            "-vf", "scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2",
            output_path,
        ])
        .output()
        .map_err(|e| format!("ffmpeg spawn: {e}"))?;

    if !status.status.success() {
        let stderr = String::from_utf8_lossy(&status.stderr);
        return Err(format!("ffmpeg failed: {}", &stderr[..stderr.len().min(500)]));
    }

    Ok(())
}

async fn run_ffmpeg_with_audio(
    input_image: &str,
    audio_files: &[String],
    output_path: &str,
    state: &AppState,
) -> Result<(), String> {
    // Concatenate audio files into a temp file
    let tmp_dir = std::env::temp_dir().join("video_exports");
    std::fs::create_dir_all(&tmp_dir).map_err(|e| format!("tmp mkdir: {e}"))?;

    let concat_list_path = tmp_dir.join(format!("concat_{}.txt", uuid::Uuid::new_v4()));
    let mut concat_content = String::new();

    let cwd = std::env::current_dir().map_err(|e| format!("get cwd: {e}"))?;
    for audio in audio_files {
        let resolved = if audio.starts_with('/') {
            cwd.join(format!(".{audio}"))
        } else {
            cwd.join(audio)
        };
        let abs_path = resolved
            .canonicalize()
            .unwrap_or(resolved)
            .to_string_lossy()
            .to_string();
        concat_content.push_str(&format!("file '{abs_path}'\n"));
    }

    std::fs::write(&concat_list_path, &concat_content).map_err(|e| format!("write concat: {e}"))?;

    let concat_audio_path = tmp_dir.join(format!("merged_{}.mp3", uuid::Uuid::new_v4()));

    // Merge audio files
    let merge_status = std::process::Command::new("ffmpeg")
        .args([
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list_path.to_str().unwrap_or(""),
            "-c", "copy",
            concat_audio_path.to_str().unwrap_or(""),
        ])
        .output()
        .map_err(|e| format!("ffmpeg concat spawn: {e}"))?;

    if !merge_status.status.success() {
        return Err("failed to concatenate audio".into());
    }

    // Create video with image + merged audio
    let status = std::process::Command::new("ffmpeg")
        .args([
            "-y",
            "-loop", "1",
            "-i", input_image,
            "-i", concat_audio_path.to_str().unwrap_or(""),
            "-c:v", "libx264",
            "-c:a", "aac",
            "-pix_fmt", "yuv420p",
            "-vf", "scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2",
            "-shortest",
            output_path,
        ])
        .output()
        .map_err(|e| format!("ffmpeg spawn: {e}"))?;

    // Cleanup temp files
    let _ = std::fs::remove_file(&concat_list_path);
    let _ = std::fs::remove_file(&concat_audio_path);

    if !status.status.success() {
        let stderr = String::from_utf8_lossy(&status.stderr);
        return Err(format!("ffmpeg failed: {}", &stderr[..stderr.len().min(500)]));
    }

    Ok(())
}

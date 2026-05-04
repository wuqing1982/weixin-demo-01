use axum::extract::{Multipart, State};
use axum::Json;
use serde_json::{json, Value};

use crate::db;
use crate::error::AppError;
use crate::middleware::auth::AuthUser;
use crate::response::success;
use crate::state::AppState;

pub async fn upload_image(
    State(state): State<AppState>,
    auth: AuthUser,
    mut multipart: Multipart,
) -> Result<Json<Value>, AppError> {
    let field = multipart
        .next_field()
        .await
        .map_err(|e| AppError::BadRequest(format!("multipart error: {e}")))?
        .ok_or_else(|| AppError::BadRequest("no file field".into()))?;

    let content_type = field
        .content_type()
        .unwrap_or("application/octet-stream")
        .to_string();
    if !content_type.starts_with("image/") {
        return Err(AppError::BadRequest(
            "only image upload is supported".into(),
        ));
    }

    let filename = field.file_name().unwrap_or("upload").to_string();
    let data = field
        .bytes()
        .await
        .map_err(|e| AppError::BadRequest(format!("read error: {e}")))?;

    if data.is_empty() {
        return Err(AppError::BadRequest("empty file".into()));
    }

    let max_bytes = state.config.max_upload_size_mb * 1024 * 1024;
    if data.len() as i64 > max_bytes {
        return Err(AppError::BadRequest(format!(
            "file too large, max {}MB",
            state.config.max_upload_size_mb
        )));
    }

    let upload_id = format!("upload_{}", uuid::Uuid::new_v4());
    let suffix = filename.rsplit('.').next().unwrap_or("jpg");
    let suffix = match suffix {
        "jpg" | "jpeg" => "jpg",
        "png" => "png",
        "webp" => "webp",
        "gif" => "gif",
        _ => "jpg",
    };

    let dir = std::path::Path::new(&state.config.uploads_dir).join(&upload_id);
    std::fs::create_dir_all(&dir).map_err(|e| AppError::Internal(format!("mkdir: {e}")))?;
    let file_path = dir.join(format!("source.{suffix}"));
    std::fs::write(&file_path, &data).map_err(|e| AppError::Internal(format!("write: {e}")))?;

    let (width, height) = get_image_dimensions(&data);

    let upload = db::uploads::create_upload(
        &state.pool,
        &upload_id,
        &auth.user_id,
        &filename,
        &content_type,
        suffix,
        width,
        height,
        data.len() as i64,
    )
    .await?;

    let file_url = format!(
        "{}/assets/uploads/{}/source.{}",
        state.config.public_base_url, upload_id, suffix
    );

    Ok(success(json!({
        "uploadId": upload_id,
        "fileUrl": file_url,
        "width": upload.width,
        "height": upload.height,
    })))
}

fn get_image_dimensions(data: &[u8]) -> (Option<i32>, Option<i32>) {
    if data.len() < 24 {
        return (None, None);
    }

    // PNG
    if data[0] == 0x89 && data[1] == 0x50 {
        let w = u32::from_be_bytes([data[16], data[17], data[18], data[19]]);
        let h = u32::from_be_bytes([data[20], data[21], data[22], data[23]]);
        return (Some(w as i32), Some(h as i32));
    }

    // JPEG
    if data[0] == 0xFF && data[1] == 0xD8 {
        let mut pos = 2;
        while pos + 9 <= data.len() {
            if data[pos] != 0xFF {
                break;
            }
            let marker = data[pos + 1];
            if marker == 0xC0 || marker == 0xC2 {
                let h =
                    u16::from_be_bytes([data[pos + 5], data[pos + 6]]) as i32;
                let w =
                    u16::from_be_bytes([data[pos + 7], data[pos + 8]]) as i32;
                return (Some(w), Some(h));
            }
            let seg_len =
                u16::from_be_bytes([data[pos + 2], data[pos + 3]]) as usize;
            pos += 2 + seg_len;
        }
    }

    (None, None)
}

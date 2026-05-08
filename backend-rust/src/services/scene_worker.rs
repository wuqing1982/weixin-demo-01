use std::path::Path;
use std::time::Instant;

use serde_json::{json, Value};
use tokio::io::AsyncWriteExt;

use crate::db;
use crate::state::AppState;

pub async fn process_scene_task(state: AppState, task_id: String) {
    let pool = &state.pool;
    let start_time = Instant::now();

    // Step 1: Load task
    let task = match db::tasks::get_task(pool, &task_id).await {
        Ok(Some(t)) => t,
        Ok(None) => {
            tracing::error!(task_id, "task not found");
            return;
        }
        Err(e) => {
            tracing::error!(task_id, error = %e, "failed to load task");
            return;
        }
    };

    let payload = &task.payload;
    let upload_id = payload["uploadId"].as_str().unwrap_or("");
    if upload_id.is_empty() {
        let _ = db::tasks::update_task(pool, &task_id, "failed", "error", 0, None, Some("missing uploadId")).await;
        return;
    }

    // Step 2: Load upload
    let _ = db::tasks::update_task(pool, &task_id, "running", "load_upload", 15, None, None).await;

    let upload = match db::uploads::get_upload(pool, upload_id).await {
        Ok(Some(u)) => u,
        Ok(None) => {
            let _ = db::tasks::update_task(pool, &task_id, "failed", "error", 0, None, Some("upload not found")).await;
            return;
        }
        Err(e) => {
            let _ = db::tasks::update_task(pool, &task_id, "failed", "error", 0, None, Some(&e.to_string())).await;
            return;
        }
    };

    // Step 3: Prepare assets
    let scene_id = format!("scene_user_{}", uuid::Uuid::new_v4());
    let generated_dir = Path::new(&state.config.generated_dir).join(&scene_id);
    if let Err(e) = tokio::fs::create_dir_all(&generated_dir).await {
        let _ = db::tasks::update_task(pool, &task_id, "failed", "error", 0, None, Some(&format!("mkdir: {e}"))).await;
        return;
    }

    // Copy source image
    let src_dir = Path::new(&state.config.uploads_dir).join(upload_id);
    let src_path = src_dir.join(format!("source.{}", upload.file_suffix));
    let dst_path = generated_dir.join("background.jpg");
    if let Err(e) = tokio::fs::copy(&src_path, &dst_path).await {
        let _ = db::tasks::update_task(pool, &task_id, "failed", "error", 0, None, Some(&format!("copy: {e}"))).await;
        return;
    }

    let _ = db::tasks::update_task(pool, &task_id, "running", "prepare_assets", 45, Some(&scene_id), None).await;

    // Step 4: Analyze scene with three-level retry
    let _ = db::tasks::update_task(pool, &task_id, "running", "analyze_scene", 55, None, None).await;

    let image_data = match tokio::fs::read(&dst_path).await {
        Ok(d) => d,
        Err(e) => {
            let _ = db::tasks::update_task(pool, &task_id, "failed", "error", 0, None, Some(&format!("read image: {e}"))).await;
            return;
        }
    };

    let b64 = base64::Engine::encode(&base64::engine::general_purpose::STANDARD, &image_data);
    let image_url = format!("data:image/jpeg;base64,{b64}");

    let include_verbs = payload["includeVerbs"].as_bool().unwrap_or(true);
    let scene_name = payload["title"].as_str().unwrap_or("auto");
    let retry_result = analyze_scene_with_retry(&state, &image_url, scene_name, include_verbs, &task_id, &task.owner_id).await;

    // Write log for every attempt
    write_scene_log(&state.config.generated_dir, &retry_result.log_entries, &task_id, &task.owner_id, &scene_id, start_time).await;

    let core_result = match retry_result.result {
        Ok(r) => r,
        Err(e) => {
            let _ = db::tasks::update_task(pool, &task_id, "failed", "error", 0, None, Some(&format!("GLM-4V error: {e}"))).await;
            return;
        }
    };

    // Step 5: Generate audio via TTS
    let _ = db::tasks::update_task(pool, &task_id, "running", "generate_audio", 75, None, None).await;

    let accent = payload["accent"].as_str().unwrap_or("en-US");
    let voice_gender = payload["voiceGender"].as_str().unwrap_or("Female");
    let voice_name = payload["voiceName"].as_str().unwrap_or("JennyNeural");

    let core_result = generate_audio_for_scene(
        &state,
        &scene_id,
        &core_result,
        accent,
        voice_gender,
        voice_name,
    )
    .await;

    // Step 6: Build scene JSON and save to DB
    let _ = db::tasks::update_task(pool, &task_id, "running", "write_scene", 90, None, None).await;

    let title = core_result
        .get("scene_title")
        .and_then(|v| v.as_str())
        .unwrap_or(scene_name);
    let title = if title == "auto" || title.is_empty() {
        core_result
            .get("scene_id")
            .and_then(|v| v.as_str())
            .unwrap_or("untitled")
            .to_string()
    } else {
        title.to_string()
    };

    let image_asset_path = format!("/assets/generated/{scene_id}/background.jpg");
    let mut scene_json = build_scene_json(
        &scene_id,
        &title,
        &image_asset_path,
        &task.owner_id,
        upload_id,
        accent,
        voice_gender,
        voice_name,
        &core_result,
    );

    // Auto-fill categoryId from AI recommended_category
    let rec_cat = core_result.get("recommended_category").and_then(|v| v.as_str()).unwrap_or("home");
    if let Ok(Some(cat_info)) = db::scenes::get_category_by_code(pool, rec_cat).await {
        if let Some(meta) = scene_json.get_mut("metaJson").and_then(|m| m.as_object_mut()) {
            meta.insert("categoryId".into(), json!(cat_info.id));
        }
        scene_json["category"] = json!(cat_info.name);
    }

    if let Err(e) = db::scenes::upsert_scene(pool, &scene_json).await {
        let _ = db::tasks::update_task(pool, &task_id, "failed", "error", 0, None, Some(&format!("save scene: {e}"))).await;
        return;
    }

    // Deduct credit AFTER successful generation
    let credit_deducted = match db::credits::deduct_credit(
        pool,
        &task.owner_id,
        "scene_generation_credits",
        1,
        "scene_generate",
        &task_id,
        "Scene generation task",
    ).await {
        Ok(_) => true,
        Err(e) => {
            tracing::warn!(task_id, error = %e, "credit deduction failed after successful generation");
            false
        }
    };

    // Step 7: Complete
    let auto_publish = payload["autoPublish"].as_bool().unwrap_or(false);
    if auto_publish {
        let _ = db::tasks::update_task(pool, &task_id, "running", "publishing", 95, None, None).await;
        let _ = db::tasks::set_published_scene(pool, &task_id, &scene_id).await;
    } else {
        let _ = db::tasks::update_task(pool, &task_id, "done", "done", 100, None, None).await;
    }

    tracing::info!(task_id, scene_id, credit_deducted, "scene generation completed");
}

// ─── Retry logic ───────────────────────────────────────────────

struct RetryEntry {
    model: String,
    success: bool,
    error: Option<String>,
    duration_secs: f64,
}

struct RetryResult {
    result: Result<Value, String>,
    log_entries: Vec<RetryEntry>,
}

async fn analyze_scene_with_retry(
    state: &AppState,
    image_url: &str,
    scene_name: &str,
    include_verbs: bool,
    task_id: &str,
    _owner_id: &str,
) -> RetryResult {
    let api_key = &state.config.zhipuai_api_key;
    let categories_hint = match db::scenes::list_active_categories(&state.pool).await {
        Ok(cats) => cats.iter().map(|(code, name)| format!("{}({})", code, name)).collect::<Vec<_>>().join(", "),
        Err(_) => "home(居家生活), school(校园学习), city(城市社区), nature(自然探索), transport(交通出行), sports(运动娱乐)".to_string(),
    };
    let prompt = build_analysis_prompt(scene_name, include_verbs, &categories_hint);
    let models = [
        state.config.core100_model.clone(),
        state.config.core100_retry_model.clone(),
        state.config.core100_fallback_model.clone(),
    ];

    let mut log_entries = Vec::new();
    let mut last_error = String::new();

    for (i, model) in models.iter().enumerate() {
        // Update step to show retry progress
        if i > 0 {
            let step = format!("analyze_scene_retry_{}", i);
            let _ = db::tasks::update_task(&state.pool, task_id, "running", &step, 55, None, None).await;
        }

        let t = Instant::now();
        match call_zhipuai_model(api_key, model, image_url, &prompt).await {
            Ok(v) => {
                log_entries.push(RetryEntry {
                    model: model.clone(),
                    success: true,
                    error: None,
                    duration_secs: t.elapsed().as_secs_f64(),
                });
                return RetryResult { result: Ok(v), log_entries };
            }
            Err(e) => {
                tracing::warn!(task_id, model, attempt = i + 1, error = %e, "scene analysis failed, retrying");
                log_entries.push(RetryEntry {
                    model: model.clone(),
                    success: false,
                    error: Some(e.clone()),
                    duration_secs: t.elapsed().as_secs_f64(),
                });
                last_error = e;
            }
        }
    }

    RetryResult {
        result: Err(format!("all {} models failed: {}", models.len(), last_error)),
        log_entries,
    }
}

async fn call_zhipuai_model(
    api_key: &str,
    model: &str,
    image_url: &str,
    prompt: &str,
) -> Result<Value, String> {
    if api_key.is_empty() {
        return Err("ZHIPUAI_API_KEY not configured".into());
    }

    let client = reqwest::Client::new();
    let body = json!({
        "model": model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": image_url}},
                {"type": "text", "text": prompt}
            ]
        }]
    });

    let resp = client
        .post("https://open.bigmodel.cn/api/paas/v4/chat/completions")
        .header("Authorization", format!("Bearer {api_key}"))
        .json(&body)
        .send()
        .await
        .map_err(|e| format!("request failed: {e}"))?;

    if !resp.status().is_success() {
        let status = resp.status();
        let text = resp.text().await.unwrap_or_default();
        return Err(format!("API error {status}: {text}"));
    }

    let resp_json: Value = resp
        .json()
        .await
        .map_err(|e| format!("parse response: {e}"))?;

    let content = resp_json["choices"][0]["message"]["content"]
        .as_str()
        .unwrap_or("");

    if content.is_empty() {
        return Err("empty response".into());
    }

    parse_json_response(content)
}

// ─── Logging ────────────────────────────────────────────────────

async fn write_scene_log(
    generated_dir: &str,
    entries: &[RetryEntry],
    task_id: &str,
    user_id: &str,
    scene_id: &str,
    start_time: Instant,
) {
    let now = chrono::Local::now();
    let filename = format!("scene-worker-{}.log", now.format("%Y-%m-%d"));

    // logs/ directory is sibling to generated_dir
    let logs_dir = Path::new(generated_dir).parent().unwrap_or(Path::new(".")).join("logs");
    let _ = tokio::fs::create_dir_all(&logs_dir).await;
    let log_path = logs_dir.join(&filename);

    let mut lines = Vec::new();
    lines.push(format!("[{}] task_id={} user_id={}", now.format("%Y-%m-%d %H:%M:%S"), task_id, user_id));

    for (i, entry) in entries.iter().enumerate() {
        let result_str = if entry.success {
            "成功".to_string()
        } else {
            format!("失败({})", entry.error.as_deref().unwrap_or("unknown"))
        };
        lines.push(format!(
            "  尝试{}: model={} 结果={} 耗时={:.1}s",
            i + 1,
            entry.model,
            result_str,
            entry.duration_secs
        ));
    }

    let final_status = entries.last().map(|e| if e.success { "成功" } else { "失败" }).unwrap_or("无尝试");
    let total_secs = start_time.elapsed().as_secs_f64();
    lines.push(format!("  最终: {} | 场景ID={} | 总耗时={:.1}s", final_status, scene_id, total_secs));
    lines.push("---".to_string());

    let content = lines.join("\n") + "\n";

    // Append to log file (create if not exists)
    if let Ok(mut file) = tokio::fs::OpenOptions::new().create(true).append(true).open(&log_path).await {
        let _ = file.write_all(content.as_bytes()).await;
    }
}

// ─── Prompt building ────────────────────────────────────────────

fn build_analysis_prompt(scene_name: &str, include_verbs: bool, categories_hint: &str) -> String {
    let scene_instruction = if scene_name == "auto" || scene_name.is_empty() {
        "请分析这张场景图片，自动识别场景类型。".to_string()
    } else {
        format!("请分析这张 \"{scene_name}\" 场景图片。")
    };

    let noun_instruction = "**⚠️ 数量限制（重要）：**\n- 只识别 5 个名词物体（hotspots）\n- 名词优先选择最明显、最容易识别、最适合儿童学习的物体";

    let (verb_template, verb_workflow, verb_rules) = if include_verbs {
        (
            r#","verbs": [
    {{
      "id": "word_id",
      "word": "english_word",
      "pos": "v./adj./adv.",
      "ipa": "/ipa/",
      "meaning": "中文",
      "related_item": "bench",
      "sentence": "Simple English sentence",
      "sentence_translation": "中文翻译"
    }}
  ]"#.to_string(),
            "\n**⚠️ 非名词要求（必须严格遵守）：**\n- 必须生成恰好 2 个非名词单词\n- 从以下 3 种词性组合中随机选择一种：\n  1. (v., v.)\n  2. (v., adj.)\n  3. (v., adv.)".to_string(),
            "\n- pos 字段标注词性：v.、adj. 或 adv.\n- 每个词关联已识别物体\n- 词用原形（sit, play, happy, fast）".to_string(),
        )
    } else {
        ("".to_string(), "".to_string(), "".to_string())
    };

    let scene_title_field = if scene_name == "auto" || scene_name.is_empty() {
        "\"scene_title\": \"场景中文名\","
    } else {
        ""
    };

    format!(
        r#"你是专业的儿童教育场景标注专家。请分析这张场景图片，为儿童英语学习识别物体。

{scene_instruction}

{noun_instruction}
{verb_workflow}
{verb_rules}

**关键要求 - Hotspot-Object Alignment（热点-对象精确对齐）：**
这是最重要的原则！每个热点的边界框必须精确贴合物体的实际轮廓。

**坐标系统说明：**
- 图片被分为 100x100 的网格
- rect 定义热点区域的边界框（百分比）
- l (left): 边界框左边距占图片宽度的百分比 (0-100)
- t (top): 边界框上边距占图片高度的百分比 (0-100)
- w (width): 边界框宽度占图片宽度的百分比 (0-100)
- h (height): 边界框高度占图片高度的百分比 (0-100)

**返回 JSON 格式：**
{{
  "scene_id": "park",
  {scene_title_field}
  "recommended_category": "分类代码",
  // recommended_category 必须是以下之一: {categories_hint}
  "hotspots": [
    {{
      "id": "unique_object_name",
      "word": "english_word",
      "ipa": "/ipa_pronunciation/",
      "meaning": "中文释义",
      "sentence": "Simple English sentence for children aged 3-8",
      "sentence_translation": "英文句子的准确中文翻译",
      "rect": {{"l": 10.31, "t": 22.52, "w": 32.54, "h": 15}},
      "hidden": false,
      "locked": false
    }}
  ]{verb_template}
}}

**⚠️ 最终检查：hotspots 必须有 5 个。如果数量不对，请修正后再返回。**

**只返回 JSON，不要其他内容。**"#
    )
}

fn parse_json_response(content: &str) -> Result<Value, String> {
    // Strip markdown code fences
    let content = content.trim();
    let content = content
        .strip_prefix("```json")
        .or_else(|| content.strip_prefix("```"))
        .unwrap_or(content);
    let content = content.strip_suffix("```").unwrap_or(content);
    let content = content.trim();

    // Direct parse
    if let Ok(v) = serde_json::from_str::<Value>(content) {
        return Ok(v);
    }

    // Try to find JSON object in content
    if let Some(start) = content.find('{') {
        let mut depth = 0i32;
        let mut end = start;
        for (i, c) in content.char_indices().skip(start) {
            match c {
                '{' => depth += 1,
                '}' => {
                    depth -= 1;
                    if depth == 0 {
                        end = i;
                        break;
                    }
                }
                _ => {}
            }
        }
        if depth == 0 {
            let sub = &content[start..=end];
            if let Ok(v) = serde_json::from_str::<Value>(sub) {
                return Ok(v);
            }
        }
    }

    Err("failed to parse JSON from response".into())
}

// ─── Audio generation ───────────────────────────────────────────

async fn generate_audio_for_scene(
    state: &AppState,
    scene_id: &str,
    core_result: &Value,
    accent: &str,
    _voice_gender: &str,
    voice_name: &str,
) -> Value {
    let tts_url = &state.config.core100_tts_url;
    let client = reqwest::Client::new();
    let mut result = core_result.clone();

    let voice_code = format!("{accent}-{voice_name}");

    // Generate audio for each hotspot
    if let Some(hotspots) = result.get_mut("hotspots").and_then(|h| h.as_array_mut()) {
        for hotspot in hotspots.iter_mut() {
            let id = hotspot["id"].as_str().unwrap_or("");
            let word = hotspot["word"].as_str().unwrap_or("");
            let sentence = hotspot["sentence"].as_str().unwrap_or("");

            let audio_filename = format!("{scene_id}_{id}");
            let audio_path = generate_audio_entry(
                &client,
                tts_url,
                word,
                sentence,
                &voice_code,
                &state.config.generated_dir,
                scene_id,
                &audio_filename,
            )
            .await;

            if let Some(path) = audio_path {
                hotspot["audioPath"] = json!(path);
            }
        }
    }

    // Generate audio for verbs
    if let Some(verbs) = result.get_mut("verbs").and_then(|v| v.as_array_mut()) {
        for verb in verbs.iter_mut() {
            let id = verb["id"].as_str().unwrap_or("");
            let word = verb["word"].as_str().unwrap_or("");
            let sentence = verb["sentence"].as_str().unwrap_or("");

            let audio_filename = format!("{scene_id}_verb_{id}");
            let audio_path = generate_audio_entry(
                &client,
                tts_url,
                word,
                sentence,
                &voice_code,
                &state.config.generated_dir,
                scene_id,
                &audio_filename,
            )
            .await;

            if let Some(path) = audio_path {
                verb["audioPath"] = json!(path);
            }
        }
    }

    result
}

async fn generate_audio_entry(
    client: &reqwest::Client,
    tts_url: &str,
    word: &str,
    sentence: &str,
    voice_code: &str,
    generated_dir: &str,
    scene_id: &str,
    filename: &str,
) -> Option<String> {
    let combined_text = if word == sentence || sentence.is_empty() {
        word.to_string()
    } else if word.is_empty() {
        sentence.to_string()
    } else {
        format!("{word}. {sentence}")
    };

    let tts_url_str = format!(
        "{}/api/tts/speak?text={}&voice={}",
        tts_url,
        urlencoding::encode(&combined_text),
        voice_code
    );
    let audio_data = client
        .get(&tts_url_str)
        .send()
        .await
        .ok()?
        .bytes()
        .await
        .ok()?;

    let dir = Path::new(generated_dir).join(scene_id);
    let output_path = dir.join(format!("{filename}.mp3"));
    tokio::fs::write(&output_path, &audio_data).await.ok()?;

    Some(format!("/assets/generated/{scene_id}/{filename}.mp3"))
}

// ─── Scene JSON builder ─────────────────────────────────────────

fn build_scene_json(
    scene_id: &str,
    title: &str,
    image_asset_path: &str,
    owner_id: &str,
    upload_id: &str,
    accent: &str,
    voice_gender: &str,
    voice_name: &str,
    core_result: &Value,
) -> Value {
    let items: Vec<Value> = core_result
        .get("hotspots")
        .and_then(|h| h.as_array())
        .map(|arr| {
            arr.iter()
                .filter(|item| item.get("id").and_then(|v| v.as_str()).is_some())
                .map(|item| {
                    json!({
                        "id": item["id"],
                        "word": item.get("word").and_then(|v| v.as_str()).unwrap_or("").replace("_", " "),
                        "ipa": item.get("ipa").and_then(|v| v.as_str()).unwrap_or(""),
                        "meaning": item.get("meaning").and_then(|v| v.as_str()).unwrap_or(""),
                        "sentence": item.get("sentence").and_then(|v| v.as_str()).unwrap_or(""),
                        "sentenceTranslation": item.get("sentenceTranslation").or_else(|| item.get("sentence_translation")).and_then(|v| v.as_str()).unwrap_or(""),
                        "audioPath": item.get("audioPath").and_then(|v| v.as_str()).unwrap_or(""),
                        "rect": item.get("rect").cloned().unwrap_or(json!({})),
                    })
                })
                .collect()
        })
        .unwrap_or_default();

    let verbs: Vec<Value> = core_result
        .get("verbs")
        .and_then(|v| v.as_array())
        .map(|arr| {
            arr.iter()
                .filter(|item| item.get("id").and_then(|v| v.as_str()).is_some())
                .map(|item| {
                    json!({
                        "id": item["id"],
                        "word": item.get("word").and_then(|v| v.as_str()).unwrap_or("").replace("_", " "),
                        "ipa": item.get("ipa").and_then(|v| v.as_str()).unwrap_or(""),
                        "meaning": item.get("meaning").and_then(|v| v.as_str()).unwrap_or(""),
                        "relatedItem": item.get("relatedItem").or_else(|| item.get("related_item")).and_then(|v| v.as_str()).unwrap_or(""),
                        "sentence": item.get("sentence").and_then(|v| v.as_str()).unwrap_or(""),
                        "sentenceTranslation": item.get("sentenceTranslation").or_else(|| item.get("sentence_translation")).and_then(|v| v.as_str()).unwrap_or(""),
                        "audioPath": item.get("audioPath").and_then(|v| v.as_str()).unwrap_or(""),
                    })
                })
                .collect()
        })
        .unwrap_or_default();

    let category = core_result
        .get("recommended_category")
        .and_then(|v| v.as_str())
        .unwrap_or("home");
    let tags = core_result.get("recommended_tags").cloned().unwrap_or(json!([]));

    json!({
        "sceneId": scene_id,
        "title": title,
        "category": category,
        "visibility": "private",
        "sceneType": "private",
        "coverPath": image_asset_path,
        "backgroundPath": image_asset_path,
        "items": items,
        "verbs": verbs,
        "metaJson": {
            "sceneType": "private",
            "visibility": "private",
            "sourceType": "upload",
            "ownerId": owner_id,
            "uploadId": upload_id,
            "generatorMode": "core100",
            "accent": accent,
            "voiceGender": voice_gender,
            "voiceName": voice_name,
            "core100SceneId": core_result.get("scene_id").and_then(|v| v.as_str()).unwrap_or(""),
            "core100SceneTitle": core_result.get("scene_title").and_then(|v| v.as_str()).unwrap_or(""),
            "recommendedCategory": category,
            "tags": tags,
            "version": 1,
        }
    })
}

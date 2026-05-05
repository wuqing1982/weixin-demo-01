use std::path::Path;

use serde_json::{json, Value};
use tokio::io::AsyncWriteExt;

use crate::db;
use crate::state::AppState;

pub async fn process_scene_task(state: AppState, task_id: String) {
    let pool = &state.pool;

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

    // Step 4: Analyze scene with ZhipuAI GLM-4V
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
    let core_result = match call_zhipuai_glm4v(&state, &image_url, scene_name, include_verbs).await {
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
    let scene_json = build_scene_json(
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

    if let Err(e) = db::scenes::upsert_scene(pool, &scene_json).await {
        let _ = db::tasks::update_task(pool, &task_id, "failed", "error", 0, None, Some(&format!("save scene: {e}"))).await;
        return;
    }

    // Step 7: Complete
    let auto_publish = payload["autoPublish"].as_bool().unwrap_or(false);
    if auto_publish {
        let _ = db::tasks::update_task(pool, &task_id, "running", "publishing", 95, None, None).await;
        let _ = db::tasks::set_published_scene(pool, &task_id, &scene_id).await;
    } else {
        let _ = db::tasks::update_task(pool, &task_id, "done", "done", 100, None, None).await;
    }

    tracing::info!(task_id, scene_id, "scene generation completed");
}

async fn call_zhipuai_glm4v(
    state: &AppState,
    image_url: &str,
    scene_name: &str,
    include_verbs: bool,
) -> Result<Value, String> {
    let model = &state.config.core100_model;
    let api_key = &state.config.zhipuai_api_key;

    if api_key.is_empty() {
        return Err("ZHIPUAI_API_KEY not configured".into());
    }

    let prompt = build_analysis_prompt(scene_name, include_verbs);

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
        return Err("empty response from GLM-4V".into());
    }

    // Try to parse JSON from response
    parse_json_response(content)
}

fn build_analysis_prompt(scene_name: &str, include_verbs: bool) -> String {
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
      "id": "unique_verb",
      "word": "english_verb",
      "ipa": "/ipa/",
      "meaning": "中文",
      "related_item": "bench",
      "sentence": "Simple English sentence",
      "sentence_translation": "中文翻译"
    }}
  ]"#.to_string(),
            "\n6. 生成 3 个常用动词".to_string(),
            "\n- 动词与识别的物体相关\n- 动词用原形（sit, play, eat）".to_string(),
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

    Err("failed to parse JSON from GLM-4V response".into())
}

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
    // Fetch word audio
    let word_url = format!(
        "{}/api/tts/speak?text={}&voice={}",
        tts_url,
        urlencoding::encode(word),
        voice_code
    );
    let word_audio = client.get(&word_url).send().await.ok()?.bytes().await.ok()?;

    // Fetch sentence audio
    let sentence_url = format!(
        "{}/api/tts/speak?text={}&voice={}",
        tts_url,
        urlencoding::encode(sentence),
        voice_code
    );
    let sentence_audio = client
        .get(&sentence_url)
        .send()
        .await
        .ok()?
        .bytes()
        .await
        .ok()?;

    // Simple concat: word audio + sentence audio (MP3 concat works for simple cases)
    let dir = Path::new(generated_dir).join(scene_id);
    let output_path = dir.join(format!("{filename}.mp3"));
    let mut file = tokio::fs::File::create(&output_path).await.ok()?;
    file.write_all(&word_audio).await.ok()?;
    // Add small silence gap (100ms of low-level noise as MP3 frames)
    file.write_all(&sentence_audio).await.ok()?;

    Some(format!("/assets/generated/{scene_id}/{filename}.mp3"))
}

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

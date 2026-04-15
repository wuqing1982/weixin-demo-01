"""
使用智谱 GLM-4V 分析场景图片，生成 hotspots JSON 配置。

Migrated from /www/wwwroot/e.cps.vin/core100/analyze_scene.py.
"""

import base64
import json
import os
from pathlib import Path

from .json_repair import repair_truncated_json


def generate_verbs_fallback(hotspots, scene_name="scene", api_key=None, model="glm-4.6v-flash"):
    """当主模型未生成动词时，使用纯文本兜底生成 3 个动词。"""
    try:
        from zhipuai import ZhipuAI
    except ImportError:
        raise ImportError("请安装 zhipuai: pip install zhipuai")

    if api_key is None:
        api_key = os.environ.get("ZHIPUAI_API_KEY")
        if not api_key:
            raise ValueError("请设置 ZHIPUAI_API_KEY 环境变量或传入 api_key 参数")

    if not hotspots:
        return []

    client = ZhipuAI(api_key=api_key)
    items_context = "\n".join(
        f"- {h['id']} ({h.get('word', h['id'])}): {h.get('sentence', '')}"
        for h in hotspots[:5]
    )
    scene_display = scene_name.replace("_", " ").title()

    prompt = f"""你是一个儿童英语教育专家。请为以下 "{scene_display}" 场景生成 3 个常用动词。

**已识别的场景物体：**
{items_context}

**动词生成要求：**
1. 恰好生成 3 个与场景活动相关的常用动词
2. 每个动词必须关联到上面某个物体，related_item 必须是物体 id 之一
3. sentence 必须同时包含动词本身和关联物体对应的英文名词
4. 词汇要简单，适合儿童学习

**输出 JSON：**
{{
  "verbs": [
    {{
      "id": "verb_id",
      "word": "verb_word",
      "ipa": "/ipa/",
      "meaning": "中文释义",
      "related_item": "关联物体id",
      "sentence": "包含动词和关联物体的例句",
      "sentence_translation": "例句中文翻译"
    }}
  ]
}}

只输出 JSON，不要其他文字。"""

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    response_text = response.choices[0].message.content
    success, result, _ = repair_truncated_json(response_text, verbose=False)
    if not success or "verbs" not in result:
        return []

    hotspot_ids = [h["id"] for h in hotspots]
    valid_verbs = []
    for verb in result["verbs"]:
        if "id" not in verb or "related_item" not in verb:
            continue
        if verb["related_item"] not in hotspot_ids:
            verb["related_item"] = hotspot_ids[0]
        valid_verbs.append(verb)

    return valid_verbs[:3]


def get_image_dimensions(image_path):
    """获取图片尺寸"""
    try:
        from PIL import Image
        img = Image.open(image_path)
        return img.width, img.height
    except ImportError:
        print("⚠️  警告: 未安装Pillow，无法自动检测图片尺寸")
        return None, None
    except Exception as e:
        print(f"⚠️  警告: 无法读取图片尺寸: {e}")
        return None, None


def normalize_coordinates_in_result(result, image_path):
    """
    将result中的像素坐标转换为百分比坐标
    直接修改result对象
    """
    img_width, img_height = get_image_dimensions(image_path)

    if img_width is None or img_height is None:
        return result

    # 检查是否需要转换
    needs_conversion = False
    for hotspot in result.get("hotspots", []):
        rect = hotspot.get("rect", {})
        l = rect.get("l", 0)
        t = rect.get("t", 0)
        w = rect.get("w", 0)
        h = rect.get("h", 0)

        # 如果任一值 > 100，可能是像素值
        if max(l, t, w, h) > 100:
            needs_conversion = True
            break

    if not needs_conversion:
        return result

    print(f"🖼️  图片尺寸: {img_width} x {img_height}")
    print("📐 转换坐标（像素 → 百分比）:")

    for hotspot in result.get("hotspots", []):
        rect = hotspot.get("rect", {})
        l = rect.get("l", 0)
        t = rect.get("t", 0)
        w = rect.get("w", 0)
        h = rect.get("h", 0)

        # 检查是否需要转换
        if max(l, t, w, h) > 100:
            # 转换为百分比
            new_rect = {
                'l': round(l / img_width * 100, 2),
                't': round(t / img_height * 100, 2),
                'w': round(w / img_width * 100, 2),
                'h': round(h / img_height * 100, 2)
            }
            print(f"   📐 {hotspot.get('id', 'unknown')}: {rect} → {new_rect}")
            hotspot['rect'] = new_rect

    return result


def verb_sentence_mentions_related_noun(verb, hotspots):
    """Check whether the verb sentence mentions its related hotspot word."""
    related_item = verb.get("related_item", "")
    sentence = (verb.get("sentence") or "").lower()
    if not related_item or not sentence:
        return False

    hotspot_map = {hotspot["id"]: hotspot for hotspot in hotspots}
    related_hotspot = hotspot_map.get(related_item)
    if not related_hotspot:
        return False

    related_word = (related_hotspot.get("word") or related_item).lower().replace("_", " ")
    noun_parts = [part for part in related_word.split() if part]
    if not noun_parts:
        return False

    return all(part in sentence for part in noun_parts)


def encode_image(image_path):
    """将图片编码为 base64"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')


def analyze_scene_with_glm4v(image_path, scene_name, api_key=None, model="glm-4v-flash", include_verbs=True):
    """
    使用智谱 GLM-4V 分析图片

    参数:
        image_path: 图片路径
        scene_name: 场景名称
        api_key: API Key
        model: 模型选择 (glm-4v-flash 或 glm-4.5v)
        include_verbs: 是否额外生成 3 个动词（True: 5 个名词 + 3 个动词，False: 仅 5 个名词）

    返回格式（单场景）：
    {
      "scene_id": "park",
      "scene_title": "公园",
      "recommended_category": "existing",
      "recommended_tags": ["学习", "户外", "娱乐"],
      "image": "assets/park.png",
      "hotspots": [
        {
          "id": "bench",
          "word": "bench",
          "ipa": "/bentʃ/",
          "sentence": "Let's sit on the bench.",
          "sentence_translation": "我们坐在长椅上吧。",
          "rect": {"l": 10.31, "t": 53.97, "w": 41.23, "h": 6.85},
          "hidden": false,
          "locked": false
        }
      ],
      "verbs": [...]  # 仅当 include_verbs=True 时
    }
    """
    try:
        from zhipuai import ZhipuAI
    except ImportError:
        raise ImportError("请安装 zhipuai: pip install zhipuai")

    # 检查图片文件大小
    image_file_size = Path(image_path).stat().st_size
    size_mb = image_file_size / (1024 * 1024)

    print(f"📸 图片文件: {image_path}")
    print(f"📊 文件大小: {size_mb:.2f} MB")

    # 智谱API硬限制是10MB（base64编码后）
    if size_mb > 10:
        raise ValueError(
            f"图片文件过大 ({size_mb:.2f}MB)，超过智谱API限制(10MB)\n"
            f"建议：手动压缩图片后重试"
        )

    if size_mb > 5:
        print(f"⚠️  警告: 图片较大 ({size_mb:.2f}MB)，可能影响API调用速度")

    # 获取 API Key
    if api_key is None:
        api_key = os.environ.get("ZHIPUAI_API_KEY")
        if not api_key:
            raise ValueError("请设置 ZHIPUAI_API_KEY 环境变量或传入 api_key 参数")

    # 初始化客户端
    client = ZhipuAI(api_key=api_key)

    # 读取图片
    image_base64 = encode_image(image_path)
    image_url = f"data:image/png;base64,{image_base64}"

    # 如果提供了 scene_name，使用它；否则让 AI 生成
    scene_instruction = """
**场景识别任务：**
- 请根据图片内容识别这是什么场景
- 生成合适的场景名称：
  - scene_id: 小写英文单词，用下划线连接（如 playground, library, train_station）
  - scene_title: 中文场景名称（如 游乐场、图书馆、火车站）
""" if scene_name == "auto" or not scene_name else ""

    # 如果 scene_name 是 "auto"，在 JSON 中使用占位符让 AI 填充
    scene_id_placeholder = "YOUR_SCENE_ID" if scene_name == "auto" or not scene_name else scene_name
    scene_title_field = '"scene_title": "中文场景名称（如：图书馆、医院、火车站）",' if scene_name == "auto" or not scene_name else ''

    if include_verbs:
        noun_count_instruction = """**⚠️ 数量限制（重要）：**
- 只识别 5 个名词物体（hotspots）
- 再生成 3 个与场景相关的常用动词（verbs）
- 名词优先选择最明显、最容易识别、最适合儿童学习的物体"""
        verb_json_template = """,
  "verbs": [
    {
      "id": "verb_id",
      "word": "verb_word",
      "ipa": "/ipa_pronunciation/",
      "meaning": "中文释义",
      "related_item": "关联的名词 hotspot id",
      "sentence": "包含动词和关联物体的例句",
      "sentence_translation": "例句中文翻译"
    }
  ]"""
        verb_workflow = """
8. 生成 3 个常用动词（verbs）：
   - 动词必须和场景活动相关
   - 每个动词必须关联一个已识别名词（related_item）
   - sentence 必须同时包含动词本身和关联物体
   - verbs 不需要 rect 坐标"""
        verb_rules = """
**动词生成规则：**
- 数量必须恰好为 3 个
- related_item 必须是 hotspots 中某个 id
- sentence 必须包含动词本身
- sentence 必须明确包含 related_item 对应热点的英文名词
- 选择高频、儿童友好的动词，如 play, sit, eat, hold, drink, read"""
    else:
        noun_count_instruction = """**⚠️ 数量限制（重要）：**
- 只识别 5 个名词物体（hotspots）
- 不要生成动词
- 名词优先选择最明显、最容易识别、最适合儿童学习的物体"""
        verb_json_template = ""
        verb_workflow = ""
        verb_rules = ""

    prompt = f"""你是专业的儿童教育场景标注专家。请分析这张场景图片，为儿童英语学习识别物体。

{scene_instruction}

{noun_count_instruction}

**关键要求 - Hotspot-Object Alignment（热点-对象精确对齐）：**
这是最重要的原则！每个热点的边界框必须精确贴合物体的实际轮廓。

**坐标系统说明：**
- 图片被分为 100x100 的网格
- rect 定义热点区域的边界框（百分比）
- l (left): 边界框左边距占图片宽度的百分比 (0-100)
- t (top): 边界框上边距占图片高度的百分比 (0-100)
- w (width): 边界框宽度占图片宽度的百分比 (0-100)
- h (height): 边界框高度占图片高度的百分比 (0-100)

**精确对齐规则：**
1. 边界框必须完全包含物体的可见部分
2. 边界框应该尽可能紧凑，不要有太多空白
3. 如果物体延伸到图片边缘，l 或 t 可以是 0
4. 坐标保留 2 位小数（如 10.31, 22.52）
5. 热点区域应该略大于物体本身（方便点击），但不能太大

**分类和标签推荐：**
请根据场景内容智能推荐分类和标签：

1. **场景分类（recommended_category）** - 从以下分类中选择最合适的：
   - `home` - 家庭生活（卧室、客厅、厨房器具、浴室等家居场景）
   - `food` - 饮食（食物、饮品、水果、用餐场景等）
   - `nature` - 自然户外（公园、森林、海滩、花园等自然环境）
   - `animals` - 动物世界（动物园、农场、水族馆、宠物等）
   - `transport` - 交通出行（公交车、火车、飞机、道路等）
   - `community` - 社区职业（超市、医院、消防站、邮局等）
   - `school` - 校园学习（教室、图书馆、实验室、操场等）
   - `sports` - 运动娱乐（游乐场、游泳池、体育场、音乐室等）

2. **场景标签（recommended_tags）** - 选择最相关的3个标签：
   - 标签组合应涵盖不同维度（如：主分类+环境+氛围）
   - 示例：安静教室 → ["学习", "安静", "室内"]

**返回 JSON 格式：**
{{
  "scene_id": "{scene_id_placeholder}",
  {scene_title_field}
  "recommended_category": "分类代码",
  "recommended_tags": ["标签1", "标签2", "标签3"],
  "image": "assets/{scene_id_placeholder}.png",
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
  ]{verb_json_template}
}}

**工作流程：**
1. {"识别场景类型，生成合适的 scene_id（英文）和 scene_title（中文）" if scene_name == "auto" or not scene_name else "使用指定的场景名称"}
2. **分析场景特征，推荐合适的分类（recommended_category）**
3. **根据场景内容推荐3个最相关的标签（recommended_tags）**
4. 识别场景中的主要物体（固定 5 个名词，宁缺毋滥，选择最典型、最容易识别的）
5. 对每个物体：
   - 确定 id（小写英文，下划线连接，如 slide, swing_set）
   - 确定 word（英文单词，单数形式，如 slide 不是 slides）
   - 确定 ipa（国际音标）
   - 确定 meaning（中文释义）
   - 确定 sentence（简单例句，适合3-8岁儿童）
   - 确定 sentence_translation（英文句子的准确中文翻译，帮助儿童理解）
   - **仔细测量物体在图片中的位置和大小**
   - **计算精确的百分比坐标**
6. 验证边界框是否准确对齐物体轮廓
7. 确保热点之间没有太多重叠{verb_workflow}

**注意事项：**
- 严格控制数量：5 个名词物体，不要贪多
- 优先选择大型、明显、容易识别的物体
- 避免选择太小、太隐蔽或遮挡严重的物体
- word 必须使用单数形式（apple, bench, slide）
- sentence 使用简单词汇和语法
- 例句要有语境，帮助孩子理解单词用法
- 坐标必须经过精确计算，不能估算
- scene_id 应该简洁明了，使用常见英文单词
{verb_rules}

**只返回 JSON，不要其他内容。**"""

    try:
        # 调用 GLM-4V API
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url}
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ],
            thinking={"type": "enabled"}
        )

        # 解析返回的 JSON
        response_text = response.choices[0].message.content

        # 使用智能修复模块解析 JSON
        print("📝 解析 JSON 响应...")
        success, result, method = repair_truncated_json(response_text, verbose=True)

        if not success:
            raise ValueError(f"无法解析JSON响应: {method}")

        print(f"✅ JSON解析成功: {method}")
        hotspot_count = len(result.get("hotspots", []))
        print(f"📊 成功解析 {hotspot_count} 个物体")

        # 验证必需字段
        if "scene_id" not in result:
            result["scene_id"] = scene_name
        if "image" not in result:
            result["image"] = f"assets/{scene_name}.png"

        # 处理 hotspots 或 items 字段（兼容性）
        hotspots = result.get("hotspots") or result.get("items")
        if not hotspots:
            raise ValueError("返回结果缺少 hotspots 或 items 字段")

        # 统一使用 hotspots
        result["hotspots"] = hotspots
        if "items" in result:
            del result["items"]

        # 验证每个 hotspot 的必需字段
        for hotspot in result["hotspots"]:
            if "id" not in hotspot:
                raise ValueError("hotspot 缺少 id 字段")
            if "rect" not in hotspot:
                raise ValueError(f"hotspot {hotspot['id']} 缺少 rect 字段")
            if "hidden" not in hotspot:
                hotspot["hidden"] = False
            if "locked" not in hotspot:
                hotspot["locked"] = False

            # 标准化 word 字段：将下划线替换为空格
            if "word" in hotspot:
                hotspot["word"] = hotspot["word"].replace("_", " ")

        # 可选动词处理
        verbs = result.get("verbs", [])
        needs_fallback_verbs = include_verbs and not verbs
        if include_verbs and verbs:
            for verb in verbs:
                if not verb_sentence_mentions_related_noun(verb, result["hotspots"]):
                    print(f"⚠️  动词 {verb.get('id', 'unknown')} 的例句未包含关联名词，尝试使用兜底模型重生成...")
                    needs_fallback_verbs = True
                    break

        if needs_fallback_verbs:
            print("⚠️  主模型未生成动词，尝试使用兜底模型生成...")
            verbs = generate_verbs_fallback(
                result["hotspots"],
                result.get("scene_id", scene_name),
                api_key,
            )
            if verbs:
                result["verbs"] = verbs
                print(f"✅ 兜底成功生成 {len(verbs)} 个动词")

        if include_verbs:
            hotspot_ids = {hotspot["id"] for hotspot in result["hotspots"]}
            normalized_verbs = []
            for verb in result.get("verbs", []):
                if "id" not in verb:
                    raise ValueError("verb 缺少 id 字段")
                if "related_item" not in verb:
                    raise ValueError(f"verb {verb['id']} 缺少 related_item 字段")
                if verb["related_item"] not in hotspot_ids:
                    print(f"⚠️  警告: verb {verb['id']} 的 related_item '{verb['related_item']}' 不在 hotspots 中，改为第一个热点")
                    verb["related_item"] = result["hotspots"][0]["id"]
                normalized_verbs.append(verb)
            result["verbs"] = normalized_verbs[:3]
        else:
            result.pop("verbs", None)

        # 转换坐标：像素 → 百分比
        result = normalize_coordinates_in_result(result, image_path)

        return result

    except Exception as e:
        print(f"❌ API 调用失败: {e}")
        raise

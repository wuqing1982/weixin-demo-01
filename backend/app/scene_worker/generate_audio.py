"""
生成场景音频文件
使用 TTS API 生成所有词汇的mp3文件

音频格式：单词 + 0.1秒静音 + 句子

Migrated from /www/wwwroot/e.cps.vin/core100/generate_audio.py.
"""

import json
import requests
import os
from pathlib import Path
import tempfile

from .scene_assets import (
    build_audio_filename,
    get_entry_sentence,
    get_entry_word,
    get_item_sentence,
    get_item_word,
    get_scene_items,
    get_scene_verbs,
    load_scene,
)

try:
    from pydub import AudioSegment
except ModuleNotFoundError as exc:
    missing_name = getattr(exc, "name", "unknown")
    raise SystemExit(
        "❌ 缺少音频依赖: "
        f"{missing_name}。请执行 `pip install -r requirements.txt`，"
        "在 Python 3.13 下还需要安装 `audioop-lts`。"
    ) from exc


# 配置
DEFAULT_TTS_URL = "http://localhost:5003"  # 使用本地 TTS 服务
VOICE_SLIDE_ROOT = Path(os.environ.get("VOICE_SLIDE_ROOT", "./voice_slide"))

# 支持的语音配置
VOICES = {
    'en-US': {
        'female': 'en-US-JennyNeural',
        'male': 'en-US-ChristopherNeural'
    },
    'en-GB': {
        'female': 'en-GB-LibbyNeural',
        'male': 'en-GB-RyanNeural'
    }
}

# 默认只生成 Jenny 音色
# 如需生成其他音色，请使用 --all-voices 参数
DEFAULT_VOICE_PRIORITY = [
    ('en-US', 'female'),  # Jenny - 美式女性
]

# 所有可用音色
ALL_VOICES = [
    ('en-US', 'female'),  # Jenny
    ('en-GB', 'female'),  # Libby
    ('en-US', 'male'),    # Christopher
    ('en-GB', 'male')     # Ryan
]


def generate_combined_audio(item_id, word, sentence, voice, accent, gender,
                           scene_id, output_dir, tts_url):
    """
    生成音频：将 word 和 sentence 拼接为单段文本，一次 TTS 请求生成。

    返回: True if success, False otherwise
    """
    filename = build_audio_filename(
        scene_id,
        accent,
        gender,
        {"id": item_id, "sentence": sentence, "word": word},
    )
    output_path = output_dir / filename

    # 如果文件已存在，跳过
    if output_path.exists():
        file_size = output_path.stat().st_size
        size_kb = file_size / 1024
        print(f"  ⏭️  跳过: {filename} ({size_kb:.1f} KB)")
        return True

    try:
        # TTS API 端点
        tts_endpoint = f"{tts_url}/api/tts/speak"

        # 拼接文本：word. sentence
        if not word or word == sentence:
            combined_text = sentence or word
        elif not sentence:
            combined_text = word
        else:
            combined_text = f"{word}. {sentence}"

        params = {"text": combined_text, "voice": voice}
        response = requests.get(tts_endpoint, params=params, timeout=30)
        response.raise_for_status()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(response.content)

        file_size = output_path.stat().st_size
        size_kb = file_size / 1024
        print(f"  ✅ 完成: {filename} ({size_kb:.1f} KB)")

        return True

    except Exception as e:
        print(f"  ❌ 失败: {filename} - {e}")
        return False


def validate_tts_service(tts_url):
    """Fail fast when the local TTS service is unavailable."""
    health_url = f"{tts_url.rstrip('/')}/health"
    try:
        response = requests.get(health_url, timeout=5)
        response.raise_for_status()
    except Exception as exc:
        raise RuntimeError(f"TTS 服务不可用: {health_url} ({exc})") from exc


def generate_scene_audio(json_path, tts_url=None, output_root=None, voice_priority=None):
    """
    为场景生成所有音频文件

    参数:
        json_path: hotspots JSON 文件路径
        tts_url: TTS 服务地址
        output_root: 音频输出根目录
        voice_priority: 要生成的音色列表，默认只生成 Jenny
    """
    tts_url = tts_url or DEFAULT_TTS_URL
    output_root = Path(output_root) if output_root else VOICE_SLIDE_ROOT
    voice_priority = voice_priority or DEFAULT_VOICE_PRIORITY
    validate_tts_service(tts_url)

    # 加载场景数据
    scene = load_scene(json_path)
    scene_id = scene.get('scene_id', 'scene')

    # 提取名词和动词数据
    entries = []
    for hotspot in get_scene_items(scene):
        item_data = {
            'id': hotspot['id'],
            'word': get_item_word(hotspot),
            'sentence': get_item_sentence(hotspot),
        }
        entries.append(item_data)

    for verb in get_scene_verbs(scene):
        verb_data = {
            'id': verb['id'],
            'word': get_entry_word(verb),
            'sentence': get_entry_sentence(verb),
        }
        entries.append(verb_data)

    # 创建输出目录
    output_dir = output_root / scene_id
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(f"🚀 生成 {scene_id} 场景音频文件")
    print("=" * 70)
    print(f"📂 输出目录: {output_dir.absolute()}")
    print(f"📡 TTS 服务: {tts_url}")
    print(f"📋 音频格式: 单词 + 0.1秒静音 + 句子")
    print(f"📊 条目数量: {len(entries)}")
    print(f"   名词: {len(get_scene_items(scene))} 个")
    print(f"   动词: {len(get_scene_verbs(scene))} 个")
    print()

    total_items = len(entries)
    total_voices = len(voice_priority)
    total_files = total_items * total_voices

    # 显示生成策略
    print(f"🎯 生成策略 ({total_voices} 种音色):")
    voice_names = {
        ('en-US', 'female'): 'Jenny (美式女性)',
        ('en-GB', 'female'): 'Libby (英式女性)',
        ('en-US', 'male'): 'Christopher (美式男性)',
        ('en-GB', 'male'): 'Ryan (英式男性)'
    }
    for accent, gender in voice_priority:
        name = voice_names.get((accent, gender), f'{accent}-{gender}')
        print(f"   ✅ {name}")

    if len(voice_priority) == 1:
        print(f"   💡 提示: 使用 --all-voices 参数可生成全部 4 种音色")
    print()

    success_count = 0

    # 逐个音色生成
    for accent, gender in voice_priority:
        voice_code = VOICES[accent][gender]
        voice_name = voice_names.get((accent, gender), f'{accent}-{gender}')

        print()
        print("=" * 70)
        print(f"🎯 生成音色: {voice_name}")
        print("=" * 70)

        for item in entries:
            result = generate_combined_audio(
                item['id'], item['word'], item['sentence'],
                voice_code, accent, gender,
                scene_id, output_dir, tts_url
            )
            if result:
                success_count += 1

        print()

    print("=" * 70)
    print(f"✅ 全部完成! 成功生成: {success_count}/{total_files}")
    print(f"📂 文件保存在: {output_dir.absolute()}")
    print("=" * 70)

    # 列出所有生成的文件
    files = sorted(output_dir.glob("*.mp3"))
    if files:
        print("\n📁 已生成的文件:")
        for i, file in enumerate(files, 1):
            file_size = file.stat().st_size / 1024
            print(f"   {i:2d}. {file.name} ({file_size:.1f} KB)")

    return success_count, total_files

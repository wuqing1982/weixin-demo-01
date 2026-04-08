"""
Scene video generator using FFmpeg.

Generates learning videos from panoramic scene images with:
- Per-hotspot highlight overlay (glow effect via drawbox)
- Info panel (word, IPA, meaning, sentence, translation)
- Auto-wrapping long sentences to fit video width
- Synchronized TTS audio playback
- Segment concatenation into final MP4

Output is always 720x1280 (portrait phone screen) regardless of source image size.
"""

import logging
import os
import shutil
import subprocess
import tempfile
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Optional

from PIL import ImageFont

logger = logging.getLogger('video_generator')

FFMPEG_PATH = os.getenv('FFMPEG_PATH', 'ffmpeg')
FFPROBE_PATH = os.getenv('FFPROBE_PATH', 'ffprobe')

CHINESE_FONT = '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf'
ENGLISH_FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

# Fixed output resolution (portrait phone screen)
VIDEO_W = 720
VIDEO_H = 1280


def _get_image_size(image_path: str) -> tuple[int, int]:
    cmd = [
        FFPROBE_PATH, '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height',
        '-of', 'csv=s=x:p=0',
        str(image_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f'ffprobe failed: {result.stderr}')
    w, h = result.stdout.strip().split('x')
    return int(w), int(h)


def _get_audio_duration(audio_path: str) -> float:
    cmd = [
        FFPROBE_PATH, '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'csv=s=x:p=0',
        str(audio_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    if result.returncode != 0:
        return 3.0
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 3.0


def _ensure_even(w: int, h: int) -> tuple[int, int]:
    return (w - 1 if w % 2 else w, h - 1 if h % 2 else h)


def _build_highlight_filter(x: int, y: int, w: int, h: int,
                            img_w: int, img_h: int) -> str:
    glow_max = 12
    x1 = max(0, x - glow_max)
    y1 = max(0, y - glow_max)
    x2 = min(img_w, x + w + glow_max)
    y2 = min(img_h, y + h + glow_max)
    return (
        f'drawbox=x={x}:y={y}:w={w}:h={h}:color=white@0.18:t=fill,'
        f'drawbox=x={x}:y={y}:w={w}:h={h}:color=white@0.95:t=2,'
        f'drawbox=x={x1}:y={y1}:w={min(x2-x1,w+4)}:h={min(y2-y1,h+4)}:color=white@0.25:t=2,'
        f'drawbox=x={x1}:y={y1}:w={min(x2-x1,w+8)}:h={min(y2-y1,h+8)}:color=white@0.20:t=3,'
        f'drawbox=x={x1}:y={y1}:w={min(x2-x1,w+14)}:h={min(y2-y1,h+14)}:color=white@0.15:t=5,'
        f'drawbox=x={x1}:y={y1}:w={x2-x1}:h={y2-y1}:color=white@0.10:t=8'
    )


def _escape_text(text: str) -> str:
    if not text:
        return ''
    t = text.replace('\\', '\\\\')
    t = t.replace("'", "\\'")
    t = t.replace(':', '\\:')
    t = t.replace('%', '%%')
    t = t.replace('\n', ' ')
    t = t.replace('[', '\\[')
    t = t.replace(']', '\\]')
    t = t.replace(';', '\\;')
    t = t.replace(',', '\\,')
    return t


def _measure_text_width(text: str, font_path: str, font_size: int) -> int:
    """Measure rendered text width in pixels using PIL."""
    try:
        font = ImageFont.truetype(font_path, font_size)
        return int(font.getlength(text))
    except Exception:
        return len(text) * font_size


def _wrap_text(text: str, font_path: str, font_size: int, max_width: int) -> list[str]:
    """Wrap text into multiple lines that fit within max_width pixels."""
    if not text:
        return []
    full_width = _measure_text_width(text, font_path, font_size)
    if full_width <= max_width:
        return [text]

    # Try splitting at word boundaries (for English)
    if any(c.isascii() and c.isalpha() for c in text):
        words = text.split(' ')
        lines = []
        current = ''
        for word in words:
            test = f'{current} {word}'.strip() if current else word
            if _measure_text_width(test, font_path, font_size) <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines if lines else [text]

    # For Chinese / other CJK: split into individual chars and group
    lines = []
    current = ''
    for char in text:
        test = current + char
        if _measure_text_width(test, font_path, font_size) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = char
    if current:
        lines.append(current)
    return lines if lines else [text]


def _write_text_file(text: str, filepath: str) -> str:
    """Write text to a temp file for FFmpeg textfile parameter (avoids encoding issues)."""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(text)
    return filepath


def _build_panel_filter(tmp_dir: Path, img_w: int, img_h: int, item: dict,
                        item_type: str = 'noun') -> tuple[str, int]:
    """
    Build the info panel filter chain. Returns (filter_string, panel_height).
    Uses textfile for Chinese text to avoid shell encoding issues.
    Font sizes are proportional to img_w (720 at standard).
    item_type: 'noun' for hotspot items, 'verb' for action verbs.
    """
    pad = int(img_w * 0.035)
    usable_w = img_w - pad * 2

    # Scale font sizes relative to standard 720px width
    scale = img_w / 720.0
    font_word = int(60 * scale)
    font_ipa = int(36 * scale)
    font_meaning = int(42 * scale)
    font_sentence = int(38 * scale)
    font_translation = int(36 * scale)
    font_tag = int(24 * scale)

    line_spacing_word = int(font_word * 1.05)
    line_spacing = int(font_sentence * 1.25)
    tag_height = int(font_tag * 1.6)

    word = item.get('word', '')
    ipa = item.get('ipa', '')
    meaning = item.get('meaning', '')
    sentence = item.get('sentence', '')
    translation = item.get('sentenceTranslation', '') or item.get('sentence_translation', '')

    # Wrap long texts
    sentence_lines = _wrap_text(sentence, ENGLISH_FONT, font_sentence, usable_w) if sentence else []
    translation_lines = _wrap_text(translation, CHINESE_FONT, font_translation, usable_w) if translation else []

    # Calculate total panel height
    total_height = pad
    total_height += tag_height  # type tag line (名词/动词)
    total_height += line_spacing_word  # word line
    if ipa:
        total_height += int(font_ipa * 1.2)  # ipa line
    if meaning:
        total_height += int(font_meaning * 1.3)  # meaning line
    total_height += len(sentence_lines) * line_spacing
    total_height += len(translation_lines) * line_spacing
    total_height += pad  # bottom padding

    panel_height = total_height
    panel_y = img_h - panel_height

    # Background boxes (layered transparency)
    if item_type == 'verb':
        bg = (
            f'drawbox=x={pad}:y={panel_y}:w={usable_w}:h={panel_height}:color=black@0.55:t=fill,'
            f'drawbox=x={pad}:y={panel_y}:w={usable_w}:h={panel_height}:color=#4fc3f7@0.15:t=2'
        )
    else:
        bg = (
            f'drawbox=x={pad}:y={panel_y}:w={usable_w}:h={panel_height}:color=black@0.55:t=fill,'
            f'drawbox=x={pad}:y={panel_y}:w={usable_w}:h={panel_height}:color=white@0.10:t=1'
        )

    text_parts = []
    ty = panel_y + pad

    # Type tag (名词 / 动词)
    tag_text = '动词 VERB' if item_type == 'verb' else '名词 NOUN'
    tag_color = '#4fc3f7' if item_type == 'verb' else '#ffd93d'
    tag_bg_color = '#4fc3f7@0.25' if item_type == 'verb' else '#ffd93d@0.25'
    tag_pad = int(font_tag * 0.4)
    tf_path = str(tmp_dir / 'panel_tag.txt')
    _write_text_file(tag_text, tf_path)
    tag_w = _measure_text_width(tag_text, CHINESE_FONT, font_tag) + tag_pad * 2
    tag_h = tag_height - int(pad * 0.3)
    tag_x = (img_w - tag_w) // 2
    text_parts.append(
        f'drawbox=x={tag_x}:y={ty}:w={tag_w}:h={tag_h}:color={tag_bg_color}:t=fill,'
        f"drawtext=textfile='{tf_path}':fontfile='{CHINESE_FONT}'"
        f':fontcolor={tag_color}:fontsize={font_tag}:x=(w-tw)/2:y={ty + (tag_h - font_tag) // 2}'
    )
    ty += tag_height

    # Word (English)
    tf_path = str(tmp_dir / 'panel_word.txt')
    _write_text_file(word, tf_path)
    text_parts.append(
        f"drawtext=textfile='{tf_path}':fontfile='{ENGLISH_FONT}'"
        f':fontcolor=white:fontsize={font_word}:x=(w-tw)/2:y={ty}'
    )
    ty += line_spacing_word

    # IPA
    if ipa:
        tf_path = str(tmp_dir / 'panel_ipa.txt')
        _write_text_file(ipa, tf_path)
        text_parts.append(
            f"drawtext=textfile='{tf_path}':fontfile='{ENGLISH_FONT}'"
            f':fontcolor=white@0.72:fontsize={font_ipa}:x=(w-tw)/2:y={ty}'
        )
        ty += int(font_ipa * 1.2)

    # Meaning (Chinese)
    if meaning:
        tf_path = str(tmp_dir / 'panel_meaning.txt')
        _write_text_file(meaning, tf_path)
        text_parts.append(
            f"drawtext=textfile='{tf_path}':fontfile='{CHINESE_FONT}'"
            f':fontcolor=#ffd93d:fontsize={font_meaning}:x=(w-tw)/2:y={ty}'
        )
        ty += int(font_meaning * 1.3)

    # Sentence (English, potentially multi-line)
    for i, line in enumerate(sentence_lines):
        tf_path = str(tmp_dir / f'panel_sent_{i}.txt')
        _write_text_file(line, tf_path)
        text_parts.append(
            f"drawtext=textfile='{tf_path}':fontfile='{ENGLISH_FONT}'"
            f':fontcolor=white:fontsize={font_sentence}:x=(w-tw)/2:y={ty}'
        )
        ty += line_spacing

    # Translation (Chinese, potentially multi-line)
    for i, line in enumerate(translation_lines):
        tf_path = str(tmp_dir / f'panel_trans_{i}.txt')
        _write_text_file(line, tf_path)
        text_parts.append(
            f"drawtext=textfile='{tf_path}':fontfile='{CHINESE_FONT}'"
            f':fontcolor=#ffd93d:fontsize={font_translation}:x=(w-tw)/2:y={ty}'
        )
        ty += line_spacing

    return bg + ',' + ','.join(text_parts), panel_height


def _to_pixel_rect(rect: dict, img_w: int, img_h: int) -> tuple[int, int, int, int]:
    l = rect.get('l', 0) / 100.0 * img_w
    t = rect.get('t', 0) / 100.0 * img_h
    w = rect.get('w', 10) / 100.0 * img_w
    h = rect.get('h', 10) / 100.0 * img_h
    return int(l), int(t), int(w), int(h)


def _run_ffmpeg(cmd: list[str]) -> None:
    logger.debug('ffmpeg cmd: %s', ' '.join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f'ffmpeg failed (rc={result.returncode}): {result.stderr[-500:]}')


def _generate_move_segment(image_path: str, output_path: str,
                           duration: float) -> None:
    sw, sh = _ensure_even(VIDEO_W, VIDEO_H)
    cmd = [
        FFMPEG_PATH, '-y',
        '-loop', '1', '-i', str(image_path),
        '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo',
        '-t', str(duration),
        '-c:v', 'libx264', '-tune', 'stillimage',
        '-c:a', 'aac', '-b:a', '192k',
        '-pix_fmt', 'yuv420p',
        '-vf', f'scale={sw}:{sh}:force_original_aspect_ratio=decrease,pad={sw}:{sh}:(ow-iw)/2:(oh-ih)/2:color=black',
        '-shortest',
        str(output_path),
    ]
    _run_ffmpeg(cmd)


def _generate_display_segment(tmp_dir: Path, image_path: str, audio_path: str,
                              output_path: str, item: dict,
                              item_type: str = 'noun') -> None:
    sw, sh = _ensure_even(VIDEO_W, VIDEO_H)
    rect = item.get('rect')
    if rect:
        x, y, w, h = _to_pixel_rect(rect, VIDEO_W, VIDEO_H)
        highlight = _build_highlight_filter(x, y, w, h, VIDEO_W, VIDEO_H)
    else:
        highlight = ''

    panel, _ = _build_panel_filter(tmp_dir, VIDEO_W, VIDEO_H, item, item_type=item_type)

    scale_filter = f'scale={sw}:{sh}:force_original_aspect_ratio=decrease,pad={sw}:{sh}:(ow-iw)/2:(oh-ih)/2:color=black'

    if highlight:
        vf = f'{scale_filter},{highlight},{panel}'
    else:
        vf = f'{scale_filter},{panel}'

    cmd = [
        FFMPEG_PATH, '-y',
        '-loop', '1', '-i', str(image_path),
        '-i', str(audio_path),
        '-vf', vf,
        '-c:v', 'libx264', '-tune', 'stillimage',
        '-c:a', 'aac', '-b:a', '192k',
        '-pix_fmt', 'yuv420p',
        '-shortest',
        str(output_path),
    ]
    _run_ffmpeg(cmd)


def _concat_segments(segment_paths: list[str], output_path: str) -> None:
    concat_file = str(output_path) + '.concat.txt'
    with open(concat_file, 'w', encoding='utf-8') as f:
        for p in segment_paths:
            f.write(f"file '{p}'\n")
    cmd = [
        FFMPEG_PATH, '-y',
        '-f', 'concat', '-safe', '0',
        '-i', concat_file,
        '-c', 'copy',
        str(output_path),
    ]
    try:
        _run_ffmpeg(cmd)
    finally:
        Path(concat_file).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate_scene_video(
    scene: dict,
    assets_root: Path,
    output_path: Path,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Path:
    """
    Generate a learning video from a scene.

    Args:
        scene: Scene dict with backgroundPath, items[] each having
               rect{l,t,w,h}, word, ipa, meaning, sentence, sentenceTranslation, audioPath.
        assets_root: Root directory for resolving relative asset paths.
        output_path: Where to write the final .mp4.
        progress_callback: Optional (percent, message) callback.

    Returns:
        Path to the generated video file.
    """
    def _progress(pct: int, msg: str):
        if progress_callback:
            progress_callback(pct, msg)

    # 1. Resolve background image
    bg_rel = scene.get('backgroundPath', '')
    if bg_rel.startswith('/assets/'):
        bg_rel = bg_rel[len('/assets/'):]
    bg_path = assets_root / bg_rel.lstrip('/') if bg_rel else None
    if not bg_path or not bg_path.exists():
        raise FileNotFoundError(f'Background image not found: {bg_path}')
    _progress(5, '读取场景图片...')

    _progress(10, f'输出尺寸: {VIDEO_W}x{VIDEO_H}')

    # 2. Collect items (nouns) with audio
    items = scene.get('items', [])
    verbs = scene.get('verbs', [])

    prepared_items = []
    for item in items:
        audio_rel = item.get('audioPath', '')
        if not audio_rel:
            continue
        if audio_rel.startswith('/assets/'):
            audio_rel = audio_rel[len('/assets/'):]
        audio_path = assets_root / audio_rel.lstrip('/')
        if not audio_path.exists():
            logger.warning('Audio not found, skipping item %s: %s',
                           item.get('id'), audio_path)
            continue
        duration = _get_audio_duration(str(audio_path))
        prepared_items.append((item, audio_path, duration))

    if not prepared_items:
        raise ValueError('No items with audio found')

    # 2b. Collect verbs with audio
    prepared_verbs = []
    for verb in verbs:
        audio_rel = verb.get('audioPath', '')
        if not audio_rel:
            continue
        if audio_rel.startswith('/assets/'):
            audio_rel = audio_rel[len('/assets/'):]
        audio_path = assets_root / audio_rel.lstrip('/')
        if not audio_path.exists():
            logger.warning('Audio not found, skipping verb %s: %s',
                           verb.get('word'), audio_path)
            continue
        duration = _get_audio_duration(str(audio_path))
        prepared_verbs.append((verb, audio_path, duration))

    _progress(15, f'已准备 {len(prepared_items)} 个名词 + {len(prepared_verbs)} 个动词')

    # 3. Generate segments
    tmp_dir = output_path.parent / f'.tmp_{output_path.stem}'
    tmp_dir.mkdir(parents=True, exist_ok=True)

    try:
        segments: list[str] = []
        total = len(prepared_items) + len(prepared_verbs)
        seg_idx = 0

        # --- Noun segments (with highlight + panel + audio) ---
        for i, (item, audio_path, audio_dur) in enumerate(prepared_items):
            base_pct = 15 + int(seg_idx / total * 65)
            word = item.get('word', f'item-{i}')

            item_tmp = tmp_dir / f'seg_{seg_idx:03d}'
            item_tmp.mkdir(exist_ok=True)

            if seg_idx > 0:
                _progress(base_pct, f'过渡片段 {seg_idx+1}/{total}')
                move_out = str(tmp_dir / f'move_{seg_idx:03d}.mp4')
                _generate_move_segment(str(bg_path), move_out, 0.3)
                segments.append(move_out)

            _progress(base_pct + 3, f'名词 {i+1}/{len(prepared_items)}: {word}')
            display_out = str(tmp_dir / f'display_{seg_idx:03d}.mp4')
            _generate_display_segment(
                item_tmp, str(bg_path), str(audio_path), display_out, item
            )
            segments.append(display_out)
            seg_idx += 1

        # --- Verb segments (panel + audio, no highlight) ---
        for i, (verb, audio_path, audio_dur) in enumerate(prepared_verbs):
            base_pct = 15 + int(seg_idx / total * 65)
            word = verb.get('word', f'verb-{i}')

            item_tmp = tmp_dir / f'seg_{seg_idx:03d}'
            item_tmp.mkdir(exist_ok=True)

            # Transition before verb segment
            _progress(base_pct, f'过渡片段 {seg_idx+1}/{total}')
            move_out = str(tmp_dir / f'move_{seg_idx:03d}.mp4')
            _generate_move_segment(str(bg_path), move_out, 0.3)
            segments.append(move_out)

            _progress(base_pct + 3, f'动词 {i+1}/{len(prepared_verbs)}: {word}')
            display_out = str(tmp_dir / f'display_{seg_idx:03d}.mp4')
            _generate_display_segment(
                item_tmp, str(bg_path), str(audio_path), display_out, verb,
                item_type='verb'
            )
            segments.append(display_out)
            seg_idx += 1

        _progress(85, '合并视频片段...')
        _concat_segments(segments, str(output_path))
        _progress(100, '视频生成完成')
        return output_path

    except Exception:
        if output_path.exists():
            output_path.unlink(missing_ok=True)
        raise
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Async job manager (background thread, in-memory tracking)
# ---------------------------------------------------------------------------

_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()
_output_dir: Optional[Path] = None

# Concurrency control: limit simultaneous FFmpeg processes
_MAX_CONCURRENT_EXPORTS = int(os.getenv('VIDEO_EXPORT_MAX_CONCURRENT', '2'))
_export_semaphore = threading.Semaphore(_MAX_CONCURRENT_EXPORTS)


def init_video_export(output_dir: Path) -> None:
    global _output_dir
    _output_dir = output_dir
    _output_dir.mkdir(parents=True, exist_ok=True)


def create_export_job(scene_id: str, user_id: str) -> dict:
    job_id = f'vid_{datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")}_{uuid.uuid4().hex[:8]}'
    job = {
        'jobId': job_id,
        'sceneId': scene_id,
        'userId': user_id,
        'status': 'pending',
        'progress': 0,
        'message': '',
        'outputPath': '',
        'createdAt': datetime.now(timezone.utc).isoformat(),
        'completedAt': '',
    }
    with _jobs_lock:
        _jobs[job_id] = job
    return dict(job)


def get_export_job(job_id: str) -> Optional[dict]:
    with _jobs_lock:
        return dict(_jobs[job_id]) if job_id in _jobs else None


def get_user_export_jobs(user_id: str) -> list[dict]:
    """Return completed export jobs for a user, sorted newest first."""
    with _jobs_lock:
        jobs = [
            dict(job) for job in _jobs.values()
            if job.get('userId') == user_id and job.get('status') == 'completed'
        ]
    jobs.sort(key=lambda j: j.get('completedAt', ''), reverse=True)
    return jobs


def has_active_export(scene_id: str, user_id: str) -> Optional[str]:
    """Check if user already has an active export for this scene. Returns job_id or None."""
    with _jobs_lock:
        for job_id, job in _jobs.items():
            if (job.get('sceneId') == scene_id
                    and job.get('userId') == user_id
                    and job.get('status') in ('pending', 'processing')):
                return job_id
    return None


def _update_job(job_id: str, **kwargs) -> None:
    with _jobs_lock:
        if job_id in _jobs:
            _jobs[job_id].update(kwargs)


def _run_export(job_id: str, scene: dict, assets_root: Path) -> None:
    acquired = _export_semaphore.acquire(timeout=600)
    if not acquired:
        _update_job(job_id, status='failed', message='导出排队超时，请稍后重试')
        return
    try:
        _update_job(job_id, status='processing', message='开始生成视频...')
        out = _output_dir / f'{job_id}.mp4'

        def on_progress(pct: int, msg: str):
            _update_job(job_id, progress=pct, message=msg)

        generate_scene_video(scene, assets_root, out, progress_callback=on_progress)

        _update_job(
            job_id,
            status='completed',
            progress=100,
            message='视频生成完成',
            outputPath=str(out),
            completedAt=datetime.now(timezone.utc).isoformat(),
        )
        logger.info('Video export completed: %s -> %s', job_id, out)

    except Exception as exc:
        logger.error('Video export failed %s: %s', job_id, exc)
        _update_job(
            job_id,
            status='failed',
            message=str(exc),
            completedAt=datetime.now(timezone.utc).isoformat(),
        )
    finally:
        _export_semaphore.release()


def start_export(job_id: str, scene: dict, assets_root: Path) -> None:
    thread = threading.Thread(
        target=_run_export,
        args=(job_id, scene, assets_root),
        daemon=True,
        name=f'video-export-{job_id}',
    )
    thread.start()


# ---------------------------------------------------------------------------
# Video cleanup (delete expired exports)
# ---------------------------------------------------------------------------

_cleanup_stop = threading.Event()


def start_video_cleanup(output_dir: Path, retention_hours: int, interval_seconds: int = 300) -> None:
    """Start background thread that deletes video files older than retention_hours."""
    def _cleanup_loop():
        while not _cleanup_stop.wait(interval_seconds):
            try:
                cutoff = datetime.now(timezone.utc) - timedelta(hours=retention_hours)
                with _jobs_lock:
                    to_remove = []
                    for job_id, job in _jobs.items():
                        if job.get('status') != 'completed':
                            continue
                        completed = job.get('completedAt', '')
                        if not completed:
                            continue
                        try:
                            completed_dt = datetime.fromisoformat(completed.replace('Z', '+00:00'))
                            if completed_dt < cutoff:
                                to_remove.append(job_id)
                        except (ValueError, TypeError):
                            continue
                    for job_id in to_remove:
                        job = _jobs.pop(job_id)
                        path = job.get('outputPath', '')
                        if path:
                            Path(path).unlink(missing_ok=True)
                        logger.info('Cleaned up expired video: %s', job_id)
            except Exception as exc:
                logger.error('Video cleanup error: %s', exc)

    thread = threading.Thread(target=_cleanup_loop, daemon=True, name='video-cleanup')
    thread.start()


def stop_video_cleanup() -> None:
    _cleanup_stop.set()

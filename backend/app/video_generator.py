"""
Scene video generator using FFmpeg.

Generates learning videos from panoramic scene images with:
- Per-hotspot highlight overlay (glow effect via drawbox)
- Info panel (word, IPA, meaning, sentence, translation)
- Synchronized TTS audio playback
- Segment concatenation into final MP4

Adapted from core-video-export architecture.
"""

import json
import logging
import os
import shutil
import subprocess
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger('video_generator')

FFMPEG_PATH = os.getenv('FFMPEG_PATH', 'ffmpeg')
FFPROBE_PATH = os.getenv('FFPROBE_PATH', 'ffprobe')

CHINESE_FONT = '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf'
ENGLISH_FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'


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
    # Order matters: backslash first, then everything else
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


def _build_panel_filter(img_w: int, img_h: int, item: dict) -> str:
    panel_height = 260
    panel_y = img_h - panel_height
    pad = 12

    bg = (
        f'drawbox=x={pad}:y={panel_y+pad}:w={img_w-pad*2}:h={panel_height-pad*2}:color=black@0.22:t=fill,'
        f'drawbox=x={pad}:y={panel_y+pad+43}:w={img_w-pad*2}:h={panel_height-pad*2-43}:color=black@0.27:t=fill,'
        f'drawbox=x={pad}:y={panel_y+pad+86}:w={img_w-pad*2}:h={panel_height-pad*2-86}:color=black@0.32:t=fill,'
        f'drawbox=x={pad}:y={panel_y+pad}:w={img_w-pad*2}:h={panel_height-pad*2}:color=white@0.18:t=1'
    )

    ty = panel_y + pad
    word = _escape_text(item.get('word', ''))
    ipa = _escape_text(item.get('ipa', ''))
    meaning = _escape_text(item.get('meaning', ''))
    sentence = _escape_text(item.get('sentence', ''))
    translation = _escape_text(item.get('sentenceTranslation', '')
                               or item.get('sentence_translation', ''))

    text_parts = [
        f"drawtext=text='{word}':fontfile='{ENGLISH_FONT}'"
        f':fontcolor=white:fontsize=66:x=(w-tw)/2:y={ty}',
    ]
    if ipa:
        text_parts.append(
            f"drawtext=text='{ipa}':fontfile='{ENGLISH_FONT}'"
            f':fontcolor=white@0.72:fontsize=40:x=(w-tw)/2:y={ty+65}'
        )
    if meaning:
        text_parts.append(
            f"drawtext=text='{meaning}':fontfile='{CHINESE_FONT}'"
            f':fontcolor=#ffd93d:fontsize=45:x=(w-tw)/2:y={ty+105}'
        )
    if sentence:
        text_parts.append(
            f"drawtext=text='{sentence}':fontfile='{ENGLISH_FONT}'"
            f':fontcolor=white:fontsize=50:x=(w-tw)/2:y={ty+150}'
        )
    if translation:
        text_parts.append(
            f"drawtext=text='{translation}':fontfile='{CHINESE_FONT}'"
            f':fontcolor=#ffd93d:fontsize=45:x=(w-tw)/2:y={ty+200}'
        )

    return bg + ',' + ','.join(text_parts)


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
                           duration: float, width: int, height: int) -> None:
    sw, sh = _ensure_even(width, height)
    cmd = [
        FFMPEG_PATH, '-y',
        '-loop', '1', '-i', str(image_path),
        '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo',
        '-t', str(duration),
        '-c:v', 'libx264', '-tune', 'stillimage',
        '-c:a', 'aac', '-b:a', '192k',
        '-pix_fmt', 'yuv420p',
        '-vf', f'scale={sw}:{sh}',
        '-shortest',
        str(output_path),
    ]
    _run_ffmpeg(cmd)


def _generate_display_segment(image_path: str, audio_path: str,
                              output_path: str, item: dict,
                              width: int, height: int) -> None:
    sw, sh = _ensure_even(width, height)
    rect = item.get('rect')
    if rect:
        x, y, w, h = _to_pixel_rect(rect, width, height)
        highlight = _build_highlight_filter(x, y, w, h, width, height)
    else:
        highlight = ''

    panel = _build_panel_filter(width, height, item)

    if highlight:
        vf = f'scale={sw}:{sh},{highlight},{panel}'
    else:
        vf = f'scale={sw}:{sh},{panel}'

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
    # Strip /assets/ prefix since assets_root already points to the assets dir
    if bg_rel.startswith('/assets/'):
        bg_rel = bg_rel[len('/assets/'):]
    bg_path = assets_root / bg_rel.lstrip('/') if bg_rel else None
    if not bg_path or not bg_path.exists():
        raise FileNotFoundError(f'Background image not found: {bg_path}')
    _progress(5, '读取场景图片...')

    img_w, img_h = _get_image_size(str(bg_path))
    _progress(10, f'图片尺寸: {img_w}x{img_h}')

    # 2. Collect items with audio
    items = scene.get('items', [])
    if not items:
        raise ValueError('Scene has no items to export')

    prepared = []
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
        prepared.append((item, audio_path, duration))

    if not prepared:
        raise ValueError('No items with audio found')

    _progress(15, f'已准备 {len(prepared)} 个音频')

    # 3. Generate segments
    tmp_dir = output_path.parent / f'.tmp_{output_path.stem}'
    tmp_dir.mkdir(parents=True, exist_ok=True)

    try:
        segments: list[str] = []
        total = len(prepared)

        for idx, (item, audio_path, audio_dur) in enumerate(prepared):
            base_pct = 15 + int(idx / total * 65)
            word = item.get('word', f'item-{idx}')

            # Move segment (short pause between items)
            if idx > 0:
                _progress(base_pct, f'移动片段 {idx+1}/{total}')
                move_out = str(tmp_dir / f'move_{idx:03d}.mp4')
                _generate_move_segment(str(bg_path), move_out, 0.3, img_w, img_h)
                segments.append(move_out)

            # Display segment (highlight + panel + audio)
            _progress(base_pct + 3, f'展示 {idx+1}/{total}: {word}')
            display_out = str(tmp_dir / f'display_{idx:03d}.mp4')
            _generate_display_segment(
                str(bg_path), str(audio_path), display_out, item, img_w, img_h
            )
            segments.append(display_out)

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


def _update_job(job_id: str, **kwargs) -> None:
    with _jobs_lock:
        if job_id in _jobs:
            _jobs[job_id].update(kwargs)


def _run_export(job_id: str, scene: dict, assets_root: Path) -> None:
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


def start_export(job_id: str, scene: dict, assets_root: Path) -> None:
    thread = threading.Thread(
        target=_run_export,
        args=(job_id, scene, assets_root),
        daemon=True,
        name=f'video-export-{job_id}',
    )
    thread.start()

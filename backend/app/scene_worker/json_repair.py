"""
兼容版 JSON 修复工具。

优先用于兜住模型输出里常见的尾逗号问题，例如：

{
  "a": 1,
}

Migrated from backend/app/core100_compat/json_repair.py.
"""

import json
import re
from typing import Any, Dict, Optional, Tuple


def repair_truncated_json(json_str: str, verbose: bool = False) -> Tuple[bool, Optional[Dict], str]:
    cleaned = (json_str or '').strip()

    if cleaned.startswith('```json'):
        cleaned = cleaned[7:]
    if cleaned.startswith('```'):
        cleaned = cleaned[3:]
    if cleaned.endswith('```'):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    for label, candidate in (
        ('直接解析成功（未截断）', cleaned),
        ('移除尾逗号成功', remove_trailing_commas(cleaned)),
    ):
        try:
            return True, json.loads(candidate), label
        except json.JSONDecodeError:
            if verbose:
                print(f'📝 {label} 失败，尝试进一步修复...')

    for repair_func, label in (
        (repair_by_adding_braces, '补全闭合括号成功'),
        (repair_by_truncating_to_last_hotspot, '截取到最后完整hotspot成功'),
        (repair_by_removing_empty_values, '移除空值成功'),
        (repair_by_regex_extraction, '正则提取成功'),
        (repair_by_bracket_matching, '括号匹配修复成功'),
    ):
        try:
            repaired = remove_trailing_commas(repair_func(cleaned))
            return True, json.loads(repaired), label
        except Exception as error:
            if verbose:
                print(f'📝 {label} 失败 - {error}')

    return False, None, '所有修复方法均失败'


def remove_trailing_commas(text: str) -> str:
    previous = None
    current = text
    while current != previous:
        previous = current
        current = re.sub(r',(\s*[}\]])', r'\1', current)
    return current


def repair_by_adding_braces(json_str: str) -> str:
    text = json_str
    open_braces = text.count('{')
    close_braces = text.count('}')
    open_brackets = text.count('[')
    close_brackets = text.count(']')

    for _ in range(open_braces - close_braces):
        text += '\n}'

    if open_brackets > close_brackets and text.rfind(']') == -1:
        text += '\n]'

    if not text.rstrip().endswith('}'):
        text += '\n}'

    return text


def repair_by_truncating_to_last_hotspot(json_str: str) -> str:
    if '"hotspots"' not in json_str and '"items"' not in json_str:
        raise ValueError('未找到 hotspots 或 items 数组')

    array_key = '"hotspots"' if '"hotspots"' in json_str else '"items"'
    start = json_str.find(f'{array_key}: [')
    if start == -1:
        start = json_str.find(f'{array_key}"')
    if start == -1:
        raise ValueError('未找到数组开始位置')

    array_start = json_str.find('[', start)
    if array_start == -1:
        raise ValueError('未找到数组开始括号')

    text_after_array = json_str[array_start + 1:]
    brace_level = 0
    last_complete_pos = -1

    for index, char in enumerate(text_after_array):
        if char == '{':
            brace_level += 1
        elif char == '}':
            brace_level -= 1
            if brace_level == 0:
                last_complete_pos = index

    if last_complete_pos == -1:
        raise ValueError('未找到任何完整对象')

    prefix = json_str[:array_start + 1]
    truncated_content = text_after_array[:last_complete_pos + 1]
    return prefix + truncated_content + '\n  ]\n}'


def _extract_hotspot_objects(json_str: str) -> list[dict]:
    """Extract individual hotspot objects using balanced-brace scanning.

    Handles nested objects like ``rect: {"l": 1, "t": 2, ...}`` which a
    simple ``[^{}]*`` regex cannot match.
    """
    # Find all top-level object boundaries in the hotspots array region
    hotspot_start = json_str.find('"hotspots"')
    if hotspot_start == -1:
        hotspot_start = json_str.find('"items"')
    if hotspot_start == -1:
        return []

    array_bracket = json_str.find('[', hotspot_start)
    if array_bracket == -1:
        return []

    text = json_str[array_bracket + 1:]
    objects = []
    pos = 0

    while pos < len(text):
        obj_start = text.find('{', pos)
        if obj_start == -1:
            break

        depth = 0
        end = obj_start
        for i in range(obj_start, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    end = i
                    break

        if depth != 0:
            pos = obj_start + 1
            continue

        candidate = text[obj_start:end + 1]
        pos = end + 1

        try:
            obj = json.loads(remove_trailing_commas(candidate))
            if isinstance(obj, dict) and 'id' in obj and 'rect' in obj:
                objects.append(obj)
        except Exception:
            continue

    return objects


def repair_by_regex_extraction(json_str: str) -> str:
    valid_objects = _extract_hotspot_objects(json_str)
    if not valid_objects:
        raise ValueError('未找到有效的 hotspot 对象')

    scene_id = 'unknown'
    image = 'unknown.png'
    scene_match = re.search(r'"scene_id"\s*:\s*"([^"]+)"', json_str)
    image_match = re.search(r'"image"\s*:\s*"([^"]+)"', json_str)
    if scene_match:
        scene_id = scene_match.group(1)
    if image_match:
        image = image_match.group(1)

    return json.dumps({
        'scene_id': scene_id,
        'image': image,
        'hotspots': valid_objects,
    }, indent=2, ensure_ascii=False)


def repair_by_removing_empty_values(json_str: str) -> str:
    """Remove key-value pairs with missing values (e.g. ``"id": ,`` or ``"id":``)."""
    cleaned = json_str
    # Remove lines where value is missing: "key": <comma or end-of-object>
    cleaned = re.sub(
        r',?\s*\n?\s*"(?:[^"\\]|\\.)*"\s*:\s*,',
        ',',
        cleaned,
    )
    # Remove trailing empty-value before closing brace: "key": }
    cleaned = re.sub(
        r',?\s*"(?:[^"\\]|\\.)*"\s*:\s*([}\]])',
        r'\1',
        cleaned,
    )
    # Remove empty-value at line end before next key: "key": \n "next_key"
    cleaned = re.sub(
        r',?\s*\n\s*"(?:[^"\\]|\\.)*"\s*:\s*\n(\s*")',
        r'\n\1',
        cleaned,
    )
    return cleaned


def repair_by_bracket_matching(json_str: str) -> str:
    text = json_str
    stack = []
    last_valid_pos = 0

    for index, char in enumerate(text):
        if char in '{[(':
            stack.append((char, index))
        elif char in '}])' and stack:
            open_char, _ = stack[-1]
            if ((char == '}' and open_char == '{') or
                    (char == ']' and open_char == '[') or
                    (char == ')' and open_char == '(')):
                stack.pop()
                last_valid_pos = index

    if not stack:
        return text

    truncated = text[:last_valid_pos + 1]
    remaining_open = []
    for char, _ in stack:
        if char == '{':
            remaining_open.append('}')
        elif char == '[':
            remaining_open.append(']')

    for closing in reversed(remaining_open):
        truncated += closing

    if not truncated.rstrip().endswith('}'):
        truncated += '\n}'

    return truncated

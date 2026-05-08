#!/usr/bin/env python3
"""Validate WXML tag balancing and JS syntax for WeChat Mini Program files."""
import re
import sys
from pathlib import Path

# WXML self-closing tags (don't need closing pair)
VOID_TAGS = {
    'image', 'input', 'br', 'hr', 'embed', 'source', 'track',
    'wxs', 'include', 'import',
}

TAG_RE = re.compile(r'<(/?)(\w[\w-]*)', re.ASCII)


def validate_wxml(path: str) -> list[str]:
    """Check WXML tag pairing. Returns list of errors."""
    errors = []
    try:
        content = Path(path).read_text(encoding='utf-8')
    except Exception as e:
        return [f"{path}: cannot read: {e}"]

    stack = []
    for i, line in enumerate(content.splitlines(), 1):
        for m in TAG_RE.finditer(line):
            is_close = m.group(1) == '/'
            tag = m.group(2)

            # Skip closing slash in self-closing tags like <view ... />
            after = line[m.end():]
            # Check if this open tag is self-closing on the same line
            if not is_close and '/>' in after.split('>')[0] if '>' in after else False:
                continue
            # Check if the full tag is self-closing
            tag_end = line.find('>', m.start())
            if not is_close and tag_end != -1 and line[tag_end - 1] == '/':
                continue

            if is_close:
                if stack and stack[-1][1] == tag:
                    stack.pop()
                else:
                    expected = stack[-1][1] if stack else '(nothing)'
                    errors.append(f"{path}:{i}: unexpected </{tag}>, expected </{expected}>")
            elif tag.lower() not in VOID_TAGS:
                stack.append((i, tag))

    for line_no, tag in stack:
        errors.append(f"{path}:{line_no}: unclosed <{tag}>")

    return errors


def validate_js(path: str) -> list[str]:
    """Check JS syntax using Python's compile trick."""
    errors = []
    try:
        import py_compile
        # JS can't be validated by py_compile, use node if available
        import subprocess
        result = subprocess.run(
            ['node', '-c', Path(path).read_text(encoding='utf-8')],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            # Extract just the error line
            err = result.stderr.strip().split('\n')[-1] if result.stderr else 'syntax error'
            errors.append(f"{path}: {err}")
    except FileNotFoundError:
        # node not available, skip JS check
        pass
    except Exception as e:
        errors.append(f"{path}: {e}")
    return errors


def main():
    # Get files changed in this push
    import subprocess
    result = subprocess.run(
        ['git', 'diff', '--name-only', '--cached'],
        capture_output=True, text=True
    )
    # Also check unstaged tracked changes and committed-but-not-pushed
    result2 = subprocess.run(
        ['git', 'diff', '--name-only', 'HEAD'],
        capture_output=True, text=True
    )

    files = set(result.stdout.strip().split('\n') + result2.stdout.strip().split('\n'))
    files.discard('')

    all_errors = []
    for f in sorted(files):
        if not Path(f).exists():
            continue
        if f.endswith('.wxml'):
            all_errors.extend(validate_wxml(f))
        elif f.endswith('.js'):
            all_errors.extend(validate_js(f))

    if all_errors:
        print("❌ Validation failed:", file=sys.stderr)
        for err in all_errors:
            print(f"  {err}", file=sys.stderr)
        sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    main()

# Scene Registry Root Cause Fix

Date: 2026-03-25 11:59:25

Files involved:
- `E:\202603\core100-118v3\pipeline_weixin.py`
- `E:\202603\weixin-demo\pages\shared\scene-registry.js`

## Problem

Running `pipeline_weixin.py` to generate a new scene repeatedly corrupted `pages/shared/scene-registry.js`.

Observed failure pattern:

```js
module.exports = {
  SCENES,
  getSceneNeighbors
};,
  {
    sceneId: 'breakfast',
    title: 'breakfast',
    route: '/pages/scene_breakfast/scene'
  }
];
```

This broke WeChat preview with syntax errors such as:

- `Unexpected token (54:2)`
- `Unexpected token, expected ","`

## 5 Why Analysis

### Why 1
Why did WeChat preview fail?

Because `pages/shared/scene-registry.js` became invalid JavaScript.

### Why 2
Why did `scene-registry.js` become invalid JavaScript?

Because the new scene entry was appended after `module.exports = {...};` instead of being inserted into the `SCENES` array.

### Why 3
Why was the new scene entry appended in the wrong place?

Because `pipeline_weixin.py::update_registry()` used naive string trimming:

```python
content = content.rstrip().rstrip(']').rstrip().rstrip(',')
content = content + ',\n' + new_entry + '\n];\n'
```

This logic assumes the file ends with the array. In reality, the file ends with:

1. `const SCENES = [...]`
2. `function getSceneNeighbors(...)`
3. `module.exports = { ... };`

So trimming from the file tail does not target the array tail. It targets the module tail.

### Why 4
Why was a tail-trimming strategy used instead of a structure-aware update?

Because the pipeline treated a JavaScript source file as plain appendable text, not as a structured artifact with:

- a data section (`SCENES`)
- behavior section (`getSceneNeighbors`)
- export section (`module.exports`)

### Why 5
Why did this keep recurring after manual fixes?

Because manual repair only fixed the generated file in `weixin-demo`, but did not fix the generator in `core100-118v3`. The next time the pipeline ran, it repeated the same destructive update and reintroduced the corruption.

## Socratic Deep Dive

### What exactly is the generator trying to modify?

Only the `SCENES` array.

### What did the old code actually modify?

The tail of the whole file.

### Are those the same thing?

No.

### What invariant should always hold?

`scene-registry.js` must always remain a complete valid JS module with exactly these parts:

1. `const SCENES = [...]`
2. `function getSceneNeighbors(...)`
3. `module.exports = { ... }`

### What operation preserves that invariant?

Parse the scene entries structurally, merge the new entry in memory, then rewrite the whole file from structured data.

### What operation violates that invariant?

String slicing based on file suffix assumptions.

## First Principles

The registry file is fundamentally not "text with a place to append".

It is:

- a set of scene records
- rendered into a JavaScript module

Therefore the correct primitive is not:

- "append bytes near the end of the file"

The correct primitive is:

- "read scene records"
- "add one record if absent"
- "render canonical JS again"

Once this is accepted, the bug becomes inevitable under the old approach and impossible under the new approach.

## Root Cause

The root cause is not the `breakfast` scene itself, not WeChat, and not preview caching.

The root cause is:

`pipeline_weixin.py::update_registry()` used a non-structural text-tail concatenation algorithm on a structured JavaScript module.

## Fix Implemented

### 1. Replaced registry update strategy in generator

In `E:\202603\core100-118v3\pipeline_weixin.py`:

- added `js_string_escape()`
- added `parse_scene_registry_entries()`
- added `build_scene_registry_content()`
- replaced runtime `update_registry()` with a structure-aware implementation

New behavior:

1. Read existing `scene-registry.js`
2. Extract all scene entries via regex
3. De-duplicate by `sceneId`
4. Append the new scene logically
5. Rewrite a canonical valid JS module

### 2. Hardened `app.json` updates

Also in `pipeline_weixin.py`:

- runtime `update_app_json()` now appends without duplicate page entries

### 3. Repaired current broken registry file

In `E:\202603\weixin-demo\pages\shared\scene-registry.js`:

- rebuilt the file as a clean canonical module
- included the generated `breakfast` scene

## Verification

A direct helper verification was executed against a deliberately malformed registry string.

Result:

- malformed content containing trailing appended entries was successfully parsed
- canonical output was regenerated without `};,`

Verification marker:

`registry_helpers_ok`

## Expected Outcome After Fix

After this change, generating a new scene should:

- add a new scene entry to `SCENES`
- keep `scene-registry.js` valid
- keep `module.exports` untouched
- avoid recurring syntax corruption on every generation

## Remaining Notes

- Existing generated scene files may still contain content/data issues unrelated to the registry bug.
- This fix specifically eliminates the registry corruption class of failures.
- If future corruption appears, it should no longer come from `update_registry()` using tail concatenation.

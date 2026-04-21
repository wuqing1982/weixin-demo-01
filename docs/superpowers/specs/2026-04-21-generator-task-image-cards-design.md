# Generator Task Image Cards Design

## Summary

Redesign the admin "Scene Generator" task cards from plain text to image-based cards with checkbox selection, select-all, and batch delete.

## Problem

Current task cards in the generator view are text-only with no visual preview, no selection mechanism, and no batch operations. Admins cannot quickly identify tasks by their uploaded images or perform bulk cleanup.

## Solution

### Backend

**`serialize_admin_task()` in `main.py`** — add `coverUrl` field:

- Look up `upload_store.get_upload(task['uploadId'])` to get `filePath`
- Convert to full URL via `asset_url(request, upload['filePath'])`
- Return empty string when `uploadId` is empty or lookup fails
- No new API endpoints needed

### Frontend

**Task card layout** (in `renderGenerator()`):

- Top half: 16:9 cover image from `coverUrl`, placeholder when no image
- Bottom half: title, status badge, progress bar, source label, action buttons
- Top-left corner: checkbox overlay (reuse `.scene-card-check` CSS)

**Batch selection:**

- Select-all checkbox in `gen-tasks-header`
- Per-card checkbox with selection state tracking
- `updateGeneratorBatchState()` for select-all sync and count display
- Floating batch bar at bottom when items selected (reuse `.batch-bar` pattern)

**Batch operations:**

- Delete selected tasks (reuse existing `batchDeleteTasks()` and `/api/admin/tasks/batch-delete` API)
- Clear selection button

### Scope

- Only affects generator view task cards
- Upload area and config panel unchanged
- Existing batch-delete API unchanged
- Reuses existing CSS classes where possible

## Files Changed

- `backend/app/main.py` — `serialize_admin_task()` add `coverUrl`
- `backend/admin_web/admin.js` — `renderGenerator()` card HTML + batch selection logic
- `backend/admin_web/admin.css` — minor adjustments for generator card styling if needed

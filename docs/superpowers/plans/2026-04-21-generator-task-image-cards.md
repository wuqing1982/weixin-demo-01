# Generator Task Image Cards Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform generator task cards from plain text to image-based cards with checkbox selection, select-all, and batch delete.

**Architecture:** Backend adds `coverUrl` to task serialization by looking up `upload_store`. Frontend replaces text-only task cards with image cards (reusing scene card CSS patterns), adds per-card checkboxes, select-all, and a floating batch bar for delete.

**Tech Stack:** Python/FastAPI backend, vanilla JS frontend with CSS custom properties.

---

## Chunk 1: Backend — coverUrl in serialize_admin_task

### Task 1: Add coverUrl to task serialization

**Files:**
- Modify: `backend/app/main.py:611-630` — `serialize_admin_task()`

- [ ] **Step 1: Modify serialize_admin_task to accept request param and add coverUrl**

Current signature is `serialize_admin_task(task: dict)`. Change it to accept `request` so we can call `asset_url()`. The function currently returns a plain dict — add a `coverUrl` key that resolves the task's uploadId to an image URL.

```python
def serialize_admin_task(task: dict, request: Request | None = None) -> dict:
    cover_url = ''
    upload_id = task.get('uploadId', '')
    if upload_id and request is not None:
        upload = upload_store.get_upload(upload_id)
        if upload and upload.get('filePath'):
            cover_url = asset_url(request, upload['filePath'])

    return {
        'taskId': task.get('taskId', ''),
        'ownerId': task.get('ownerId', ''),
        'uploadId': upload_id,
        'coverUrl': cover_url,
        'title': task.get('title', ''),
        'requestSource': task.get('requestSource', 'miniapp'),
        'autoPublish': bool(task.get('autoPublish')),
        'categoryId': task.get('categoryId', ''),
        'collectionIds': task.get('collectionIds', []) or [],
        'publishVisibility': task.get('publishVisibility', 'public'),
        'status': task.get('status', ''),
        'step': task.get('step', ''),
        'progress': task.get('progress', 0),
        'sceneId': task.get('sceneId', ''),
        'publishedSceneId': task.get('publishedSceneId', ''),
        'errorMessage': task.get('errorMessage', ''),
        'createdAt': task.get('createdAt', ''),
        'updatedAt': task.get('updatedAt', ''),
    }
```

- [ ] **Step 2: Update the three call sites to pass request**

There are three places calling `serialize_admin_task`:

1. `admin_list_tasks` (line ~1027): `[serialize_admin_task(t, request) for t in tasks]`
2. `admin_get_task` (line ~1037): `serialize_admin_task(task, request)` — add `request` param
3. `admin_retry_task` (line ~1046): `serialize_admin_task(task, request)` — add `request` param

Search for all `serialize_admin_task(` calls and add `request` as the second argument to each.

- [ ] **Step 3: Verify the API returns coverUrl**

Run: `curl -s http://127.0.0.1:8000/api/admin/tasks -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -m json.tool | head -30`

Expected: Each task object now includes a `coverUrl` field (may be empty string if no upload).

- [ ] **Step 4: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: add coverUrl to admin task serialization via upload lookup"
```

---

## Chunk 2: Frontend — Image card layout + checkbox + batch bar

### Task 2: Rewrite generator task cards with image layout

**Files:**
- Modify: `backend/admin_web/admin.js:1112-1226` — `renderGenerator()` function

- [ ] **Step 1: Rewrite the gen-tasks-grid section in renderGenerator()**

Replace the task card HTML in `renderGenerator()` (the `gen-tasks-section` block, roughly lines 1185-1223). The new structure reuses `.scene-card` and `.scene-card-check` CSS classes already defined in admin.css.

Find this block inside `renderGenerator()`:
```javascript
      <div class="gen-tasks-section">
        <div class="gen-tasks-header">
          <h4>生成任务</h4>
          <span class="meta-chip">${generatorTasks.length} 条</span>
        </div>
        ${generatorTasks.length > 0 ? `
          <div class="gen-tasks-grid">
            ${generatorTasks.map((task) => { ... }).join('')}
          </div>
        ` : '...'}
      </div>
```

Replace the entire `gen-tasks-section` with:

```javascript
      <div class="gen-tasks-section">
        <div class="gen-tasks-header">
          <div style="display:flex;align-items:center;gap:12px">
            <label class="checkbox-cell"><input type="checkbox" id="select-all-gen-tasks"></label>
            <h4>生成任务</h4>
            <span class="meta-chip">${generatorTasks.length} 条</span>
          </div>
        </div>
        ${generatorTasks.length > 0 ? `
          <div class="gen-tasks-grid">
            ${generatorTasks.map((task) => {
              const progress = task.progress || 0;
              const status = task.status || 'pending';
              const statusLabel = { pending: '等待中', processing: '处理中', running: '处理中', done: '已完成', completed: '已完成', failed: '失败' }[status] || status;
              const sourceLabel = task.requestSource === 'admin_web_generator' ? 'Admin' : (task.requestSource === 'miniapp' ? '小程序' : (task.requestSource || '-'));
              const coverUrl = task.coverUrl || '';
              return `
              <div class="scene-card gen-task-card" data-task-id="${escapeHtml(task.taskId)}">
                <label class="scene-card-check">
                  <input type="checkbox" class="gen-task-checkbox" value="${escapeHtml(task.taskId)}">
                  <span class="scene-card-checkmark"></span>
                </label>
                <div class="scene-card-cover">
                  ${coverUrl ? `<img src="${coverUrl}" onerror="this.remove()">` : ''}
                  ${!coverUrl ? '<div class="cover-placeholder">&#127912;</div>' : ''}
                </div>
                <div class="scene-card-body">
                  <strong class="scene-card-title">${escapeHtml(task.title || task.uploadId || '未命名')}</strong>
                  <div class="scene-card-meta">
                    <span class="gen-task-status ${taskStatusClass(status)}">${statusLabel}</span>
                    <span class="scene-card-meta-dot"></span>
                    <span>${sourceLabel}</span>
                    <span class="scene-card-meta-dot"></span>
                    <span>${progress}%</span>
                  </div>
                  <div class="gen-task-progress">
                    <div class="gen-task-progress-bar ${progressBarClass(status)}" style="width:${Math.max(2, progress)}%"></div>
                  </div>
                  <div class="scene-card-actions" style="margin-top:8px">
                    ${status === 'failed' ? `<button class="mini-btn success-btn" data-action="task-retry" data-id="${escapeHtml(task.taskId)}">重试</button>` : ''}
                    ${(task.sceneId || task.publishedSceneId) ? `
                      ${task.sceneId ? `<span class="gen-task-link" title="生成场景">SC ${escapeHtml(task.sceneId).substring(0, 8)}</span>` : ''}
                      ${task.publishedSceneId ? `<span class="gen-task-link" title="发布场景">PB ${escapeHtml(task.publishedSceneId).substring(0, 8)}</span>` : ''}
                    ` : ''}
                  </div>
                </div>
              </div>`;
            }).join('')}
          </div>
        ` : '<div class="gen-tasks-empty">暂无生成任务，上传图片开始创建</div>'}
      </div>
```

Note: The card uses `scene-card` class for the image card layout and `scene-card-check` for the checkbox overlay, both already defined in admin.css. The `gen-task-card` class is kept for any generator-specific overrides.

- [ ] **Step 2: Remove old gen-task CSS that conflicts**

The old `.gen-task-card`, `.gen-task-top`, `.gen-task-title`, `.gen-task-id`, `.gen-task-meta`, `.gen-task-meta-item`, `.gen-task-links`, `.gen-task-link` CSS rules are no longer used by the new card template. They can remain (harmless) or be removed for cleanliness. Recommend leaving them — they don't conflict.

However, `.gen-tasks-grid` needs a minor update to match the scene card grid pattern:

In `admin.css`, find `.gen-tasks-grid` and update it:

```css
.gen-tasks-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}
```

This changes from `minmax(320px, 1fr)` to `minmax(240px, 1fr)` to match the `.card-grid` pattern used by scene management.

- [ ] **Step 3: Commit**

```bash
git add backend/admin_web/admin.js backend/admin_web/admin.css
git commit -m "feat: redesign generator task cards with image covers"
```

### Task 3: Add batch selection and floating delete bar

**Files:**
- Modify: `backend/admin_web/admin.js` — add batch state functions + event handlers

- [ ] **Step 1: Add updateGeneratorBatchState() function**

Add this function near the other batch state functions (after `updateTaskBatchState()` around line 707):

```javascript
function updateGeneratorBatchState() {
  const panel = panelBody;
  const checkboxes = panel.querySelectorAll('.gen-task-checkbox');
  const checked = panel.querySelectorAll('.gen-task-checkbox:checked');
  const selectAll = panel.querySelector('#select-all-gen-tasks');
  const bar = document.getElementById('gen-batch-bar');
  if (selectAll) {
    selectAll.checked = checkboxes.length > 0 && checked.length === checkboxes.length;
    selectAll.indeterminate = checked.length > 0 && checked.length < checkboxes.length;
  }
  if (bar) {
    bar.classList.toggle('visible', checked.length > 0);
    const countEl = bar.querySelector('.batch-bar-count');
    if (countEl) countEl.textContent = `已选 ${checked.length} 项`;
  }
}
```

- [ ] **Step 2: Add floating batch bar to renderGenerator()**

At the end of `renderGenerator()`, before the closing of the function, insert code to add the floating batch bar to the DOM (same pattern as `renderScenes()` does for the scene batch bar):

```javascript
  // Floating batch bar for generator tasks
  const existingBar = document.getElementById('gen-batch-bar');
  if (existingBar) existingBar.remove();
  const batchBarHtml = `
    <div id="gen-batch-bar" class="batch-bar">
      <div class="batch-bar-inner">
        <span class="batch-bar-count">已选 0 项</span>
        <button class="batch-bar-btn batch-bar-btn--danger" data-action="gen-batch-delete">删除</button>
        <button class="batch-bar-close" data-action="gen-batch-clear">&times;</button>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', batchBarHtml);
```

- [ ] **Step 3: Add event handlers for checkbox changes**

In the `panelBody.addEventListener('change', ...)` block (around line 1909), add handlers:

After the existing `scene-checkbox` handler, add:

```javascript
  if (event.target.classList.contains('gen-task-checkbox')) {
    updateGeneratorBatchState();
    return;
  }
  if (event.target.id === 'select-all-gen-tasks') {
    const checked = event.target.checked;
    panelBody.querySelectorAll('.gen-task-checkbox').forEach((cb) => { cb.checked = checked; });
    updateGeneratorBatchState();
    return;
  }
```

- [ ] **Step 4: Add batch delete and clear action handlers**

In `handleAction()` function, add these cases:

```javascript
  if (action === 'gen-batch-clear') {
    panelBody.querySelectorAll('.gen-task-checkbox').forEach((cb) => { cb.checked = false; });
    updateGeneratorBatchState();
    return;
  }
```

In the global `document.addEventListener('click', ...)` block (around line 2059), add:

```javascript
  if (action === 'gen-batch-delete') {
    const ids = Array.from(panelBody.querySelectorAll('.gen-task-checkbox:checked')).map((cb) => cb.value);
    if (ids.length === 0) return;
    if (!window.confirm(`确定要删除选中的 ${ids.length} 条任务吗？此操作不可恢复。`)) return;
    try {
      await api('/api/admin/tasks/batch-delete', { method: 'POST', body: { taskIds: ids } });
      toast(`成功删除 ${ids.length} 条任务`);
      await loadConsole();
    } catch (error) {
      toast(error.message || '批量删除失败', 'error');
    }
    return;
  }
```

- [ ] **Step 5: Clean up batch bar on view switch**

In `renderCurrentView()`, before any view rendering, clean up the generator batch bar if switching away:

At the top of `renderCurrentView()` (after navItems toggle), add:

```javascript
  const genBar = document.getElementById('gen-batch-bar');
  if (genBar && state.currentView !== 'generator') genBar.remove();
```

- [ ] **Step 6: Commit**

```bash
git add backend/admin_web/admin.js
git commit -m "feat: add batch selection and delete to generator task cards"
```

### Task 4: Verify in browser

- [ ] **Step 1: Open admin page and navigate to Scene Generator**

Navigate to `https://e.cps.vin/admin/` and click "场景生成".

- [ ] **Step 2: Verify task cards show cover images**

Each task card should display the uploaded image as a 16:9 cover. Tasks without uploads should show a placeholder.

- [ ] **Step 3: Verify checkbox and batch delete**

- Click a card's checkbox → card gets selected style, batch bar appears
- Click select-all → all cards selected
- Click delete → confirmation dialog, then tasks removed
- Click clear (×) → selection cleared, bar hides

- [ ] **Step 4: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: polish generator task image cards"
```

const state = {
  token: window.localStorage.getItem('admin_access_token') || '',
  currentView: 'overview',
  currentAdmin: null,
  overview: null,
  users: [],
  products: [],
  skus: [],
  orders: [],
  tasks: [],
  cdkCodes: [],
  cdkFilterSkuId: '',
  categories: [],
  collections: [],
  generatedScenes: [],
  scenes: [],
  selectedUser: null,
  selectedOrder: null,
  selectedTask: null,
  editingProduct: null,
  editingSku: null,
  editingScene: null,
  editingCategory: null,
  editingCollection: null,
  publishingDraft: null,
  sceneViewMode: 'card',
  sceneSearchQuery: '',
  sceneFilterCategory: '',
  sceneFilterVisibility: '',
  privateSceneSearchQuery: '',
  privateSceneViewMode: 'card',
  privateSceneSelectedOwnerId: '',
  privateSceneUserSearch: '',
  privateSceneUserResults: [],
  draftViewMode: 'card',
  draftSearchQuery: '',
  userSearchQuery: '',
  userViewMode: 'card',
  userFilterMobile: 'all',
  generatorFiles: [],
  storageOverview: null,
  storageConfigs: null,
  editingBackend: null,
  testingBackend: null
};

const loginForm = document.getElementById('login-form');
const loginError = document.getElementById('login-error');
const loginOverlay = document.getElementById('login-overlay');
const adminPage = document.getElementById('admin-page');
const adminName = document.getElementById('admin-name');
const overviewCards = document.getElementById('overview-cards');
const panelHead = document.getElementById('panel-head');
const panelBody = document.getElementById('panel-body');
const pageTitle = document.getElementById('page-title');
const logoutBtn = document.getElementById('logout-btn');
const refreshBtn = document.getElementById('refresh-btn');
const navItems = Array.from(document.querySelectorAll('.nav-item'));

function openModal(title, bodyHtml) {
  const overlay = document.getElementById('modal-overlay');
  const titleEl = document.getElementById('modal-title');
  const bodyEl = document.getElementById('modal-body');
  if (!overlay) return;
  titleEl.textContent = title;
  bodyEl.innerHTML = bodyHtml;
  overlay.hidden = false;
  requestAnimationFrame(() => overlay.classList.add('showing'));
}

function closeModal() {
  const overlay = document.getElementById('modal-overlay');
  if (!overlay) return;
  overlay.classList.remove('showing');
  setTimeout(() => { overlay.hidden = true; }, 200);
}

function getSceneCategoryId(scene) {
  return (scene.publication && scene.publication.categoryId) || scene.categoryId || '';
}

function resolveCategoryName(categoryId) {
  if (!categoryId) return '';
  const cat = state.categories.find(c => c.categoryId === categoryId);
  return cat ? cat.name : categoryId;
}

function getSceneCategoryDisplay(scene) {
  const catId = getSceneCategoryId(scene);
  return resolveCategoryName(catId) || scene.category || '-';
}

function getFilteredScenes() {
  let list = state.scenes;
  const q = (state.sceneSearchQuery || '').trim().toLowerCase();
  if (q) {
    list = list.filter((s) => {
      const title = (s.title || '').toLowerCase();
      const id = (s.sceneId || '').toLowerCase();
      return title.includes(q) || id.includes(q);
    });
  }
  if (state.sceneFilterCategory) {
    list = list.filter((s) => getSceneCategoryId(s) === state.sceneFilterCategory);
  }
  if (state.sceneFilterVisibility) {
    list = list.filter((s) => (s.visibility || 'public') === state.sceneFilterVisibility);
  }
  return list;
}

function getFilteredUsers() {
  let list = state.users;
  const q = (state.userSearchQuery || '').trim().toLowerCase();
  if (q) {
    list = list.filter((u) => {
      const name = (u.displayName || '').toLowerCase();
      const mobile = (u.mobile || '').toLowerCase();
      const id = (u.id || '').toLowerCase();
      return name.includes(q) || mobile.includes(q) || id.includes(q);
    });
  }
  if (state.userFilterMobile === 'yes') {
    list = list.filter((u) => u.mobileVerified);
  } else if (state.userFilterMobile === 'no') {
    list = list.filter((u) => !u.mobileVerified);
  }
  return list;
}

function getSelectedSceneIds() {
  return Array.from(panelBody.querySelectorAll('.scene-checkbox:checked')).map((cb) => cb.value);
}

function updateSceneBatchBar() {
  const ids = getSelectedSceneIds();
  const bar = document.getElementById('scene-batch-bar');
  if (!bar) return;
  const countEl = bar.querySelector('.batch-bar-count');
  if (countEl) countEl.textContent = `已选 ${ids.length} 项`;
  bar.classList.toggle('visible', ids.length > 0);
  const dropdown = document.getElementById('scene-batch-action');
  const executeBtn = document.getElementById('scene-batch-execute');
  if (dropdown) dropdown.selectedIndex = 0;
  if (executeBtn) executeBtn.disabled = true;
}

function updateSceneBatchState() {
  updateSceneBatchBar();
  const checkboxes = panelBody.querySelectorAll('.scene-checkbox');
  const checked = panelBody.querySelectorAll('.scene-checkbox:checked');
  const selectAll = panelBody.querySelector('#select-all-scenes');
  if (selectAll) {
    selectAll.checked = checkboxes.length > 0 && checked.length === checkboxes.length;
    selectAll.indeterminate = checked.length > 0 && checked.length < checkboxes.length;
  }
}

function escapeHtml(value) {
  return String(value == null ? '' : value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function setLoggedIn(token, admin) {
  state.token = token || '';
  state.currentAdmin = admin || null;
  if (state.token) {
    window.localStorage.setItem('admin_access_token', state.token);
  } else {
    window.localStorage.removeItem('admin_access_token');
  }
  loginOverlay.hidden = !!state.token;
  adminPage.hidden = !state.token;
  adminName.textContent = admin ? `${admin.username} · ${admin.role}` : '';
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    method: options.method || 'GET',
    headers: {
      'Content-Type': 'application/json',
      ...(state.token ? { Authorization: `Bearer ${state.token}` } : {})
    },
    body: options.body ? JSON.stringify(options.body) : undefined
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok || body.code !== 0) {
    throw new Error(body.message || '请求失败');
  }
  return body.data;
}

async function uploadAdminImage(file, filename) {
  const formData = new FormData();
  formData.append('file', file, filename || file.name || 'upload.jpg');
  const response = await fetch('/api/admin/uploads/image', {
    method: 'POST',
    headers: {
      ...(state.token ? { Authorization: `Bearer ${state.token}` } : {})
    },
    body: formData
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok || body.code !== 0) {
    throw new Error(body.message || '图片上传失败');
  }
  return body.data;
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error('图片读取失败'));
    reader.readAsDataURL(file);
  });
}

async function compressImageFile(file, maxEdge = 1600, quality = 0.82) {
  const dataUrl = await readFileAsDataUrl(file);
  const image = await new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error('图片解码失败'));
    img.src = dataUrl;
  });
  const longestEdge = Math.max(image.width, image.height) || 1;
  const scale = longestEdge > maxEdge ? maxEdge / longestEdge : 1;
  const targetWidth = Math.max(1, Math.round(image.width * scale));
  const targetHeight = Math.max(1, Math.round(image.height * scale));
  const canvas = document.createElement('canvas');
  canvas.width = targetWidth;
  canvas.height = targetHeight;
  const context = canvas.getContext('2d');
  context.drawImage(image, 0, 0, targetWidth, targetHeight);
  const blob = await new Promise((resolve, reject) => {
    canvas.toBlob((result) => {
      if (!result) {
        reject(new Error('图片压缩失败'));
        return;
      }
      resolve(result);
    }, 'image/jpeg', quality);
  });
  const safeName = String(file.name || 'upload.jpg').replace(/\.[^.]+$/, '') + '.jpg';
  return new File([blob], safeName, { type: 'image/jpeg' });
}

function toast(message, type) {
  const container = document.getElementById('toast-container');
  if (!container) {
    window.alert(message);
    return;
  }
  const item = document.createElement('div');
  item.className = 'toast-item' + (type === 'error' ? ' toast-item--error' : ' toast-item--success');
  item.textContent = message;
  container.appendChild(item);
  requestAnimationFrame(() => {
    requestAnimationFrame(() => item.classList.add('visible'));
  });
  setTimeout(() => {
    item.classList.remove('visible');
    setTimeout(() => item.remove(), 300);
  }, 2500);
}

function metricCard(label, value) {
  return `
    <article class="metric-card">
      <div class="metric-label">${escapeHtml(label)}</div>
      <div class="metric-value">${escapeHtml(value)}</div>
    </article>
  `;
}

function categoryOptions(selectedCategoryId = '') {
  return state.categories.map((category) => `
    <option value="${escapeHtml(category.categoryId)}" ${category.categoryId === selectedCategoryId ? 'selected' : ''}>${escapeHtml(category.name)}</option>
  `).join('');
}

function collectionCheckboxes(selectedCollectionIds = []) {
  const selected = new Set(selectedCollectionIds || []);
  return state.collections.map((collection) => `
    <label class="checkbox-chip">
      <input type="checkbox" name="collectionIds" value="${escapeHtml(collection.collectionId)}" ${selected.has(collection.collectionId) ? 'checked' : ''}>
      <span>${escapeHtml(collection.name)}</span>
    </label>
  `).join('');
}

function renderPublicationSummary(publication) {
  if (!publication) {
    return '<span class="meta-chip">未发布</span>';
  }
  return `<span class="meta-chip">已发布 · ${escapeHtml(resolveCategoryName(publication.categoryId) || '-')} · ${escapeHtml((publication.collectionIds || []).length)} 个合集</span>`;
}

function renderOverview() {
  const overview = state.overview || {};
  overviewCards.innerHTML = [
    metricCard('用户数', overview.userCount || 0),
    metricCard('有效会员', overview.activeMemberCount || 0),
    metricCard('商品数', overview.productCount || 0),
    metricCard('今日订单', overview.todayOrderCount || 0),
    metricCard('今日支付', `¥${overview.todayPaidAmountTotal || '0.00'}`),
    metricCard('失败任务', overview.failedTaskCount || 0),
    metricCard('今日任务', overview.todayTaskCount || 0),
    metricCard('总任务数', overview.taskCount || 0)
  ].join('');
}

function getSelectedUserIds() {
  return Array.from(panelBody.querySelectorAll('.user-checkbox:checked')).map((cb) => cb.value);
}

function updateUserBatchState() {
  const checkboxes = panelBody.querySelectorAll('.user-checkbox');
  const checked = panelBody.querySelectorAll('.user-checkbox:checked');
  const selectAll = panelBody.querySelector('#select-all-users');
  const deleteBtn = document.getElementById('batch-delete-users-btn');
  const countSpan = document.getElementById('users-selected-count');
  if (selectAll) {
    selectAll.checked = checkboxes.length > 0 && checked.length === checkboxes.length;
    selectAll.indeterminate = checked.length > 0 && checked.length < checkboxes.length;
  }
  if (deleteBtn) {
    deleteBtn.disabled = checked.length === 0;
  }
  if (countSpan) {
    countSpan.textContent = checked.length > 0 ? `已选 ${checked.length} 项` : '';
  }
}

async function batchDeleteUsers() {
  const ids = getSelectedUserIds();
  if (ids.length === 0) return;
  if (!window.confirm(`确定要删除选中的 ${ids.length} 个用户吗？此操作不可恢复。`)) return;
  try {
    await api('/api/admin/users/batch-delete', { method: 'POST', body: { userIds: ids } });
    toast(`成功删除 ${ids.length} 个用户`);
    state.selectedUser = null;
    await loadConsole();
  } catch (error) {
    toast(error.message || '批量删除失败');
  }
}

function renderUsers() {
  const filtered = getFilteredUsers();
  const u = state.selectedUser;

  // --- User detail panel ---
  let detail = '';
  if (u) {
    const ms = u.memberSummary || {};
    const cs = u.creditSummary || {};
    const orders = u.orders || [];
    const scenes = u.generatedScenes || [];
    const entitlements = u.entitlements || [];
    const isActive = ms.isActive;
    const creditsUsed = (cs.totalCredits || 0) - (cs.sceneGenerateBalance || 0);
    const creditsTotal = cs.totalCredits || 0;
    const creditsPct = creditsTotal > 0 ? Math.round(creditsUsed / creditsTotal * 100) : 0;

    // Membership progress
    let memberPct = 0;
    let memberDaysLeft = '';
    if (isActive && ms.expiresAt) {
      const expiry = new Date(ms.expiresAt);
      const start = u.createdAt ? new Date(u.createdAt) : new Date(Date.now() - 365 * 86400000);
      const now = new Date();
      const total = expiry - start;
      const elapsed = now - start;
      memberPct = total > 0 ? Math.min(100, Math.round(elapsed / total * 100)) : 100;
      const daysLeft = Math.max(0, Math.ceil((expiry - now) / 86400000));
      memberDaysLeft = daysLeft + ' 天';
    }

    // Recent activity
    const lastLogin = u.lastLoginAt ? u.lastLoginAt.slice(0, 16).replace('T', ' ') : '从未登录';
    const createdAt = u.createdAt ? u.createdAt.slice(0, 10) : '-';

    detail = `
    <article class="detail-card" style="margin-bottom:20px;">
      <div class="detail-head">
        <div>
          <h4>${escapeHtml(u.displayName || u.id)}</h4>
          <p>${escapeHtml(u.id)}</p>
        </div>
        <span class="meta-chip">${escapeHtml(u.status || 'active')}</span>
        <button class="mini-btn" data-action="user-close-detail" style="margin-left:auto;">关闭</button>
      </div>

      <!-- Stat cards row -->
      <div class="user-stat-grid">
        <div class="user-stat-card">
          <div class="user-stat-label">创建场景</div>
          <div class="user-stat-value">${scenes.length}</div>
        </div>
        <div class="user-stat-card">
          <div class="user-stat-label">订单数</div>
          <div class="user-stat-value">${orders.length}</div>
        </div>
        <div class="user-stat-card">
          <div class="user-stat-label">积分消耗</div>
          <div class="user-stat-value">${creditsUsed}<span class="user-stat-total"> / ${creditsTotal}</span></div>
          <div class="user-stat-bar-wrap">
            <div class="user-stat-bar" style="width:${creditsPct}%;background:${creditsPct > 80 ? '#ef4444' : creditsPct > 50 ? '#f59e0b' : '#4ade80'}"></div>
          </div>
        </div>
        <div class="user-stat-card">
          <div class="user-stat-label">注册时间</div>
          <div class="user-stat-value" style="font-size:16px;">${createdAt}</div>
        </div>
        <div class="user-stat-card">
          <div class="user-stat-label">最后登录</div>
          <div class="user-stat-value" style="font-size:16px;">${lastLogin}</div>
        </div>
        <div class="user-stat-card">
          <div class="user-stat-label">手机号</div>
          <div class="user-stat-value" style="font-size:16px;">${u.mobileVerified ? escapeHtml(u.mobile || '-') : '未绑定'}</div>
        </div>
      </div>

      <!-- Membership section -->
      <div class="detail-subsection">
        <h5>会员状态</h5>
        ${isActive ? `
          <div style="display:flex;align-items:center;gap:12px;margin-top:8px;">
            <strong style="color:#4ade80;">${escapeHtml(ms.entitlementCode || '已开通')}</strong>
            ${memberDaysLeft ? `<span style="color:var(--muted);font-size:13px;">剩余 ${memberDaysLeft}</span>` : ''}
          </div>
          <div class="user-stat-bar-wrap" style="margin-top:6px;">
            <div class="user-stat-bar" style="width:${memberPct}%;background:${memberPct > 90 ? '#ef4444' : memberPct > 70 ? '#f59e0b' : '#4ade80'}"></div>
          </div>
          <div style="display:flex;justify-content:space-between;font-size:12px;color:var(--muted);margin-top:4px;">
            <span>开通</span><span>到期 ${ms.expiresAt ? ms.expiresAt.slice(0, 10) : '-'}</span>
          </div>
        ` : '<p style="color:var(--muted);">未开通会员</p>'}
      </div>

      <!-- Orders -->
      ${orders.length > 0 ? `
      <div class="detail-subsection">
        <h5>订单记录（${orders.length}）</h5>
        <div class="user-order-list">
          ${orders.map((o) => `
            <div class="user-order-item">
              <span class="user-order-no">${escapeHtml(o.orderNo || '-')}</span>
              <span class="user-order-status ${o.status === 'paid' ? 'status-paid' : ''}">${escapeHtml(o.status)}</span>
              <span style="color:var(--muted);font-size:12px;">${o.createdAt ? o.createdAt.slice(0, 10) : '-'}</span>
            </div>
          `).join('')}
        </div>
      </div>
      ` : ''}

      <!-- Entitlements -->
      ${entitlements.length > 0 ? `
      <div class="detail-subsection">
        <h5>权益</h5>
        <p>${entitlements.map((e) => `<span class="meta-chip">${escapeHtml(e.entitlementCode)}</span>`).join(' ')}</p>
      </div>
      ` : ''}
    </article>`;
  }

  const viewMode = state.userViewMode || 'card';

  panelHead.innerHTML = `
    <div class="scene-toolbar">
      <div class="scene-toolbar-left">
        <div class="scene-search">
          <input type="text" id="user-search-input" placeholder="搜索用户名、手机号或 ID..." value="${escapeHtml(state.userSearchQuery)}">
        </div>
        <div class="scene-filter-group">
          <select class="scene-filter-select" id="user-filter-mobile">
            <option value="all" ${state.userFilterMobile === 'all' ? 'selected' : ''}>全部用户</option>
            <option value="yes" ${state.userFilterMobile === 'yes' ? 'selected' : ''}>已绑定手机</option>
            <option value="no" ${state.userFilterMobile === 'no' ? 'selected' : ''}>未绑定手机</option>
          </select>
        </div>
        <span class="meta-chip">${filtered.length} / ${state.users.length} 位用户</span>
      </div>
      <div class="scene-toolbar-right">
        <div class="scene-view-toggles">
          <button class="scene-view-toggle ${viewMode === 'card' ? 'active' : ''}" data-action="set-user-view-card" title="卡片视图">&#9638;</button>
          <button class="scene-view-toggle ${viewMode === 'table' ? 'active' : ''}" data-action="set-user-view-table" title="列表视图">&#9776;</button>
        </div>
        <span id="users-selected-count" class="selected-count"></span>
        <button id="batch-delete-users-btn" class="mini-btn danger-btn" disabled data-action="batch-delete-users">批量删除</button>
      </div>
    </div>
  `;

  if (filtered.length === 0 && !detail) {
    panelBody.innerHTML = `
      ${detail}
      <div class="scene-empty">
        <div class="scene-empty-icon">${state.userSearchQuery ? '🔍' : '👥'}</div>
        <div class="scene-empty-title">${state.userSearchQuery ? '没有匹配的用户' : '暂无用户'}</div>
      </div>
    `;
  } else if (viewMode === 'table') {
    panelBody.innerHTML = detail + renderUserTable(filtered);
  } else {
    panelBody.innerHTML = detail + renderUserCards(filtered);
  }
}

function renderUserCards(users) {
  return `
    <div class="scene-list-header">
      <div class="scene-list-header-left">
        <label class="checkbox-cell"><input type="checkbox" id="select-all-users"></label>
        <span class="scene-list-count">共 <strong>${users.length}</strong> 位用户</span>
      </div>
    </div>
    <div class="card-grid">
      ${users.map((user) => {
        const ms = user.memberSummary || {};
        const cs = user.creditSummary || {};
        const isActive = ms.isActive;
        const loginAt = user.lastLoginAt ? user.lastLoginAt.slice(0, 10) : '-';
        const avatarUrl = user.avatarUrl || '';
        return `
        <div class="user-card" data-id="${escapeHtml(user.id)}">
          <label class="scene-card-check">
            <input type="checkbox" class="user-checkbox" value="${escapeHtml(user.id)}">
            <span class="scene-card-checkmark"></span>
          </label>
          <div class="user-card-avatar">
            ${avatarUrl
              ? `<img src="${escapeHtml(avatarUrl)}" onerror="this.remove();this.parentNode.innerHTML='<div class=\\'avatar-placeholder\\'>${(user.displayName || 'U')[0]}</div>'">`
              : `<div class="avatar-placeholder">${(user.displayName || 'U')[0]}</div>`}
          </div>
          <div class="user-card-body">
            <strong class="scene-card-title">${escapeHtml(user.displayName || user.id)}</strong>
            <div class="scene-card-meta">
              <span>${user.mobileVerified ? escapeHtml(user.mobile || '-') : '未绑定'}</span>
              <span class="scene-card-meta-dot"></span>
              <span>${loginAt}</span>
            </div>
            <div class="scene-card-tags">
              ${isActive ? '<span class="scene-tag scene-tag--member">会员</span>' : ''}
              ${user.status === 'blocked' ? '<span class="scene-tag scene-tag--private">封禁</span>' : ''}
              ${user.role === 'admin' || user.role === 'super_admin' ? '<span class="scene-tag scene-tag--public">Admin</span>' : ''}
              <span class="scene-tag scene-tag--free">${cs.sceneGenerateBalance || 0} 积分</span>
            </div>
            <div class="scene-card-actions">
              <button class="mini-btn" data-action="user-detail" data-id="${escapeHtml(user.id)}">详情</button>
            </div>
          </div>
        </div>`;
      }).join('')}
    </div>
  `;
}

function renderUserTable(users) {
  return `
    <div class="table">
      <div class="table-head">
        <label class="checkbox-cell"><input type="checkbox" id="select-all-users"></label>
        <strong>用户</strong>
        <span>手机号</span>
        <span>角色</span>
        <span>会员</span>
        <span>注册时间</span>
        <span>最后登录</span>
        <span>操作</span>
      </div>
      ${users.map((user) => {
        const loginAt = user.lastLoginAt ? user.lastLoginAt.slice(0, 10) : '-';
        const regAt = user.createdAt ? user.createdAt.slice(0, 10) : '-';
        return `
        <div class="table-row">
          <label class="checkbox-cell"><input type="checkbox" class="user-checkbox" value="${escapeHtml(user.id)}"></label>
          <strong>${escapeHtml(user.displayName || user.id)}<br><small>${escapeHtml(user.id)}</small></strong>
          <span>${user.mobileVerified ? escapeHtml(user.mobile || '-') : '<em style="opacity:.4">未绑定</em>'}</span>
          <span>${escapeHtml(user.role || 'user')}</span>
          <span>${user.memberSummary && user.memberSummary.isActive ? '已开通' : '未开通'}</span>
          <span>${regAt}</span>
          <span>${loginAt}</span>
          <span class="action-group">
            <button class="mini-btn" data-action="user-detail" data-id="${escapeHtml(user.id)}">详情</button>
            ${user.status === 'blocked'
              ? `<button class="mini-btn success-btn" data-action="user-unblock" data-id="${escapeHtml(user.id)}">解封</button>`
              : `<button class="mini-btn danger-btn" data-action="user-block" data-id="${escapeHtml(user.id)}">封禁</button>`}
          </span>
        </div>`;
      }).join('')}
    </div>
  `;
}

function productOptions(selectedProductId = '') {
  return state.products.map((product) => `
    <option value="${escapeHtml(product.productId)}" ${product.productId === selectedProductId ? 'selected' : ''}>${escapeHtml(product.name)}</option>
  `).join('');
}

function renderProducts() {
  const product = state.editingProduct || {};
  const sku = state.editingSku || {};
  panelHead.innerHTML = `
    <div>
      <h3 class="panel-title">商品与 SKU 管理</h3>
      <p class="panel-subtitle">支持新建、编辑、上下架商品，以及维护 SKU 和权益。</p>
    </div>
    <span class="meta-chip">${state.products.length} 个商品 / ${state.skus.length} 个 SKU</span>
  `;

  panelBody.innerHTML = `
    <div class="editor-grid">
      <form id="product-form" class="editor-card">
        <div class="editor-title-row">
          <h4>${product.productId ? '编辑商品' : '新建商品'}</h4>
          ${product.productId ? '<button type="button" class="mini-btn" data-action="product-cancel-edit">取消</button>' : ''}
        </div>
        <div class="field-grid">
          <label><span>商品编码</span><input name="productCode" value="${escapeHtml(product.productCode || '')}" required></label>
          <label><span>商品类型</span><input name="productType" value="${escapeHtml(product.productType || 'membership')}" required></label>
          <label><span>商品名称</span><input name="name" value="${escapeHtml(product.name || '')}" required></label>
          <label><span>状态</span><input name="status" value="${escapeHtml(product.status || 'draft')}" required></label>
          <label class="full"><span>副标题</span><input name="subtitle" value="${escapeHtml(product.subtitle || '')}"></label>
          <label class="full"><span>描述</span><textarea name="description">${escapeHtml(product.description || '')}</textarea></label>
        </div>
        <div class="form-actions">
          <button class="primary-btn compact" type="submit">${product.productId ? '保存商品' : '创建商品'}</button>
        </div>
      </form>

      <form id="sku-form" class="editor-card">
        <div class="editor-title-row">
          <h4>${sku.skuId ? '编辑 SKU' : '新建 SKU'}</h4>
          ${sku.skuId ? '<button type="button" class="mini-btn" data-action="sku-cancel-edit">取消</button>' : ''}
        </div>
        <div class="field-grid">
          <label><span>所属商品</span><select name="productId">${productOptions(sku.productId || (state.products[0] && state.products[0].productId) || '')}</select></label>
          <label><span>SKU 编码</span><input name="skuCode" value="${escapeHtml(sku.skuCode || '')}" required></label>
          <label><span>SKU 名称</span><input name="name" value="${escapeHtml(sku.name || '')}" required></label>
          <label><span>计费周期</span><input name="billingType" value="${escapeHtml(sku.billingType || 'yearly')}" required></label>
          <label><span>原价</span><input name="listPrice" value="${escapeHtml(sku.listPrice || '0.00')}" required></label>
          <label><span>售价</span><input name="salePrice" value="${escapeHtml(sku.salePrice || '0.00')}" required></label>
          <label><span>有效天数</span><input name="durationDays" value="${escapeHtml(sku.durationDays || '')}"></label>
          <label><span>状态</span><input name="status" value="${escapeHtml(sku.status || 'draft')}" required></label>
          <label class="full"><span>权益 JSON</span><textarea name="benefits">${escapeHtml(JSON.stringify((sku.benefits || []).map((item) => ({
            benefitType: item.benefitType,
            benefitValue: item.benefitValue,
            benefitJson: item.benefitJson || {}
          })), null, 2))}</textarea></label>
        </div>
        <div class="form-actions">
          <button class="primary-btn compact" type="submit">${sku.skuId ? '保存 SKU' : '创建 SKU'}</button>
        </div>
      </form>
    </div>

    <div class="stack">
      ${state.products.map((item) => `
        <article class="detail-card">
          <div class="detail-head">
            <div>
              <h4>${escapeHtml(item.name)}</h4>
              <p>${escapeHtml(item.productCode)} · ${escapeHtml(item.productType)}</p>
            </div>
            <span class="meta-chip">${escapeHtml(item.status)}</span>
          </div>
          <div class="action-group">
            <button class="mini-btn" data-action="product-edit" data-id="${escapeHtml(item.productId)}">编辑</button>
            <button class="mini-btn success-btn" data-action="product-publish" data-id="${escapeHtml(item.productId)}">上架</button>
            <button class="mini-btn danger-btn" data-action="product-disable" data-id="${escapeHtml(item.productId)}">下架</button>
          </div>
          <div class="stack compact-stack">
            ${(item.skus || []).map((skuItem) => `
              <div class="table-row compact-row">
                <strong>${escapeHtml(skuItem.name)}<br><small>${escapeHtml(skuItem.skuCode)}</small></strong>
                <span>¥${escapeHtml(skuItem.salePrice)}</span>
                <span>${escapeHtml(skuItem.billingType)}${skuItem.durationDays ? ` · ${escapeHtml(skuItem.durationDays)}天` : ''}</span>
                <span class="action-group">
                  <button class="mini-btn" data-action="sku-edit" data-id="${escapeHtml(skuItem.skuId)}">编辑 SKU</button>
                </span>
              </div>
            `).join('') || '<div class="empty-copy">暂无 SKU</div>'}
          </div>
        </article>
      `).join('')}
    </div>
  `;
}

function getSelectedOrderIds() {
  return Array.from(panelBody.querySelectorAll('.order-checkbox:checked')).map((cb) => cb.value);
}

function updateBatchDeleteState() {
  const checkboxes = panelBody.querySelectorAll('.order-checkbox');
  const checked = panelBody.querySelectorAll('.order-checkbox:checked');
  const selectAll = panelBody.querySelector('#select-all-orders');
  const deleteBtn = document.getElementById('batch-delete-btn');
  const countSpan = document.getElementById('selected-count');
  if (selectAll) {
    selectAll.checked = checkboxes.length > 0 && checked.length === checkboxes.length;
    selectAll.indeterminate = checked.length > 0 && checked.length < checkboxes.length;
  }
  if (deleteBtn) {
    deleteBtn.disabled = checked.length === 0;
  }
  if (countSpan) {
    countSpan.textContent = checked.length > 0 ? `已选 ${checked.length} 项` : '';
  }
}

async function batchDeleteOrders() {
  const ids = getSelectedOrderIds();
  if (ids.length === 0) return;
  if (!window.confirm(`确定要删除选中的 ${ids.length} 笔订单吗？此操作不可恢复。`)) return;
  try {
    await api('/api/admin/orders/batch-delete', { method: 'POST', body: { orderIds: ids } });
    toast(`成功删除 ${ids.length} 笔订单`);
    state.selectedOrder = null;
    await loadConsole();
  } catch (error) {
    toast(error.message || '批量删除失败');
  }
}

function renderOrders() {
  const detail = state.selectedOrder ? `
    <article class="detail-card">
      <div class="detail-head">
        <div>
          <h4>${escapeHtml(state.selectedOrder.orderNo)}</h4>
          <p>${escapeHtml(state.selectedOrder.userId)}</p>
        </div>
        <span class="meta-chip">${escapeHtml(state.selectedOrder.status)}</span>
      </div>
      <div class="detail-grid">
        <div><span>应付金额</span><strong>¥${escapeHtml(state.selectedOrder.payableAmount)}</strong></div>
        <div><span>支付状态</span><strong>${escapeHtml(state.selectedOrder.paymentStatus)}</strong></div>
        <div><span>创建时间</span><strong>${escapeHtml(state.selectedOrder.createdAt || '-')}</strong></div>
        <div><span>支付时间</span><strong>${escapeHtml(state.selectedOrder.paidAt || '-')}</strong></div>
      </div>
      <div class="detail-subsection">
        <h5>订单项</h5>
        <p>${(state.selectedOrder.items || []).map((item) => `${item.productName} / ${item.skuName} / ¥${item.totalPrice}`).join('，') || '暂无'}</p>
      </div>
    </article>
  ` : '';

  panelHead.innerHTML = `
    <div>
      <h3 class="panel-title">订单管理</h3>
      <p class="panel-subtitle">支持查看订单详情和支付状态。</p>
    </div>
    <div class="panel-actions">
      <span id="selected-count" class="selected-count"></span>
      <button id="batch-delete-btn" class="mini-btn danger-btn" disabled data-action="batch-delete-orders">批量删除</button>
      <span class="meta-chip">${state.orders.length} 笔订单</span>
    </div>
  `;

  panelBody.innerHTML = `
    ${detail}
    <div class="table">
      <div class="table-head">
        <label class="checkbox-cell"><input type="checkbox" id="select-all-orders"></label>
        <strong>订单号</strong>
        <span>用户</span>
        <span>金额</span>
        <span>状态</span>
        <span>操作</span>
      </div>
      ${state.orders.map((order) => `
        <div class="table-row">
          <label class="checkbox-cell"><input type="checkbox" class="order-checkbox" value="${escapeHtml(order.orderId)}"></label>
          <strong>${escapeHtml(order.orderNo)}<br><small>${escapeHtml((order.items || []).map((item) => item.skuName).join(' / '))}</small></strong>
          <span>${escapeHtml(order.userId)}</span>
          <span>¥${escapeHtml(order.payableAmount)}</span>
          <span class="status-${escapeHtml(order.status)}">${escapeHtml(order.status)}</span>
          <span class="action-group"><button class="mini-btn" data-action="order-detail" data-id="${escapeHtml(order.orderId)}">详情</button></span>
        </div>
      `).join('')}
    </div>
  `;
}

function getSelectedCdkIds() {
  return Array.from(panelBody.querySelectorAll('.cdk-checkbox:checked')).map((cb) => cb.value);
}

function updateCdkBatchState() {
  const checkboxes = panelBody.querySelectorAll('.cdk-checkbox');
  const checked = panelBody.querySelectorAll('.cdk-checkbox:checked');
  const selectAll = panelBody.querySelector('#select-all-cdk');
  const deleteBtn = document.getElementById('batch-delete-cdk-btn');
  const countSpan = document.getElementById('cdk-selected-count');
  if (selectAll) {
    selectAll.checked = checkboxes.length > 0 && checked.length === checkboxes.length;
    selectAll.indeterminate = checked.length > 0 && checked.length < checkboxes.length;
  }
  if (deleteBtn) {
    deleteBtn.disabled = checked.length === 0;
  }
  if (countSpan) {
    countSpan.textContent = checked.length > 0 ? `已选 ${checked.length} 项` : '';
  }
}

async function batchDeleteCdk() {
  const ids = getSelectedCdkIds();
  if (ids.length === 0) return;
  if (!window.confirm(`确定要删除选中的 ${ids.length} 条卡密吗？此操作不可恢复。`)) return;
  try {
    await api('/api/admin/cdk-codes/batch-delete', { method: 'POST', body: { cdkIds: ids } });
    toast(`成功删除 ${ids.length} 条卡密`);
    await loadConsole();
  } catch (error) {
    toast(error.message || '批量删除失败');
  }
}

async function generateCdk() {
  const skuId = document.getElementById('cdk-sku-select').value;
  const quantity = parseInt(document.getElementById('cdk-quantity').value || '1', 10);
  const note = (document.getElementById('cdk-note').value || '').trim();
  if (!skuId) {
    toast('请选择 SKU');
    return;
  }
  try {
    const result = await api('/api/admin/cdk-codes/generate', {
      method: 'POST',
      body: { skuId, quantity, note }
    });
    toast(`成功生成 ${(result.list || []).length} 条卡密`);
    await loadConsole();
  } catch (error) {
    toast(error.message || '生成卡密失败');
  }
}

function renderCdk() {
  // Build SKU options grouped by product
  const productSkuMap = {};
  const skuNameMap = {};
  for (const sku of state.skus) {
    const pid = sku.productId || '';
    const productName = (state.products.find((p) => p.productId === pid) || {}).name || '未知产品';
    skuNameMap[sku.skuId] = `${productName} - ${sku.name}`;
    if (!productSkuMap[pid]) {
      productSkuMap[pid] = { product: state.products.find((p) => p.productId === pid), skus: [] };
    }
    productSkuMap[pid].skus.push(sku);
  }
  const skuOptions = Object.values(productSkuMap).map(({ product, skus }) => {
    const label = product ? product.name : '未知产品';
    const items = skus.map((sku) =>
      `<option value="${escapeHtml(sku.skuId)}">${escapeHtml(label)} - ${escapeHtml(sku.name)} (${escapeHtml(sku.salePrice)}元/年)</option>`
    ).join('');
    return items;
  }).join('');

  const statusBadge = (status) => {
    if (status === 'unused') return '<span class="status-unused">未使用</span>';
    if (status === 'redeemed') return '<span class="status-paid">已兑换</span>';
    return `<span>${escapeHtml(status)}</span>`;
  };

  const filterLabel = state.cdkFilterSkuId ? `筛选中: ${escapeHtml(skuNameMap[state.cdkFilterSkuId] || state.cdkFilterSkuId)}` : '';

  panelHead.innerHTML = `
    <div>
      <h3 class="panel-title">卡密管理</h3>
      <p class="panel-subtitle">生成卡密分发给用户，用户在小程序内兑换获取会员权益。</p>
    </div>
    <div class="panel-actions">
      <span id="cdk-selected-count" class="selected-count"></span>
      <button id="batch-delete-cdk-btn" class="mini-btn danger-btn" disabled data-action="batch-delete-cdk">批量删除</button>
      <span class="meta-chip">${state.cdkCodes.length} 条卡密${filterLabel ? ' · ' + filterLabel : ''}</span>
    </div>
  `;

  panelBody.innerHTML = `
    <div class="inline-form">
      <select id="cdk-sku-select" class="form-select"><option value="">选择 SKU...</option>${skuOptions}</select>
      <input id="cdk-quantity" type="number" class="form-input" placeholder="数量" value="1" min="1" max="500" style="width:80px">
      <input id="cdk-note" type="text" class="form-input" placeholder="备注（可选）" style="flex:1">
    </div>
    <div class="cdk-action-buttons">
      <button class="primary-btn cdk-gen-btn" data-action="generate-cdk">生成卡密</button>
      <button class="primary-btn cdk-filter-btn" data-action="filter-cdk">筛选卡密</button>
      ${state.cdkFilterSkuId ? '<button class="primary-btn cdk-showall-btn" data-action="show-all-cdk">显示全部</button>' : ''}
    </div>
    <div class="table">
      <div class="table-head">
        <label class="checkbox-cell"><input type="checkbox" id="select-all-cdk"></label>
        <strong>卡密码</strong>
        <span>SKU</span>
        <span>状态</span>
        <span>兑换用户</span>
        <span>生成时间</span>
        <span>操作</span>
      </div>
      ${state.cdkCodes.map((item) => `
        <div class="table-row">
          <label class="checkbox-cell"><input type="checkbox" class="cdk-checkbox" value="${escapeHtml(item.cdkId)}"></label>
          <strong class="cdk-code">${escapeHtml(item.code)}</strong>
          <span>${escapeHtml(skuNameMap[item.skuId] || item.skuId || '-')}</span>
          ${statusBadge(item.status)}
          <span>${item.redeemedBy ? escapeHtml(item.redeemedBy).substring(0, 12) + '...' : '-'}</span>
          <span class="meta-copy">${escapeHtml(item.createdAt || '-')}</span>
          <span class="action-group"><button class="mini-btn" data-action="cdk-copy" data-code="${escapeHtml(item.code)}">复制</button></span>
        </div>
      `).join('')}
    </div>
  `;
}

function getSelectedTaskIds() {
  return Array.from(panelBody.querySelectorAll('.task-checkbox:checked')).map((cb) => cb.value);
}

function updateTaskBatchState() {
  const checkboxes = panelBody.querySelectorAll('.task-checkbox');
  const checked = panelBody.querySelectorAll('.task-checkbox:checked');
  const selectAll = panelBody.querySelector('#select-all-tasks');
  const deleteBtn = document.getElementById('batch-delete-tasks-btn');
  const countSpan = document.getElementById('tasks-selected-count');
  if (selectAll) {
    selectAll.checked = checkboxes.length > 0 && checked.length === checkboxes.length;
    selectAll.indeterminate = checked.length > 0 && checked.length < checkboxes.length;
  }
  if (deleteBtn) {
    deleteBtn.disabled = checked.length === 0;
  }
  if (countSpan) {
    countSpan.textContent = checked.length > 0 ? `已选 ${checked.length} 项` : '';
  }
}

function updateGeneratorBatchState() {
  const checkboxes = panelBody.querySelectorAll('.gen-task-checkbox');
  const checked = panelBody.querySelectorAll('.gen-task-checkbox:checked');
  const selectAll = panelBody.querySelector('#select-all-gen-tasks');
  const bar = document.getElementById('gen-batch-bar');
  if (selectAll) {
    selectAll.checked = checkboxes.length > 0 && checked.length === checkboxes.length;
    selectAll.indeterminate = checked.length > 0 && checked.length < checkboxes.length;
  }
  if (bar) {
    bar.classList.toggle('visible', checked.length > 0);
    const countEl = bar.querySelector('.batch-bar-count');
    if (countEl) countEl.textContent = `已选 ${checked.length} 项`;
    const dropdown = document.getElementById('gen-batch-action');
    const executeBtn = document.getElementById('gen-batch-execute');
    if (dropdown) dropdown.selectedIndex = 0;
    if (executeBtn) executeBtn.disabled = true;
  }
}

async function batchDeleteTasks() {
  const ids = getSelectedTaskIds();
  if (ids.length === 0) return;
  if (!window.confirm(`确定要删除选中的 ${ids.length} 条任务吗？此操作不可恢复。`)) return;
  try {
    await api('/api/admin/tasks/batch-delete', { method: 'POST', body: { taskIds: ids } });
    toast(`成功删除 ${ids.length} 条任务`);
    state.selectedTask = null;
    await loadConsole();
  } catch (error) {
    toast(error.message || '批量删除失败');
  }
}

function renderTasks() {
  const detail = state.selectedTask ? `
    <article class="detail-card">
      <div class="detail-head">
        <div>
          <h4>${escapeHtml(state.selectedTask.title || state.selectedTask.taskId)}</h4>
          <p>${escapeHtml(state.selectedTask.taskId)}</p>
        </div>
        <span class="meta-chip">${escapeHtml(state.selectedTask.status)}</span>
      </div>
      <div class="detail-grid">
        <div><span>归属用户</span><strong>${escapeHtml(state.selectedTask.ownerId || '-')}</strong></div>
        <div><span>当前步骤</span><strong>${escapeHtml(state.selectedTask.step || '-')}</strong></div>
        <div><span>进度</span><strong>${escapeHtml(state.selectedTask.progress || 0)}%</strong></div>
        <div><span>场景 ID</span><strong>${escapeHtml(state.selectedTask.sceneId || '-')}</strong></div>
      </div>
      <div class="detail-subsection">
        <h5>错误信息</h5>
        <p>${escapeHtml(state.selectedTask.errorMessage || '暂无')}</p>
      </div>
    </article>
  ` : '';

  panelHead.innerHTML = `
    <div>
      <h3 class="panel-title">任务管理</h3>
      <p class="panel-subtitle">支持查看详情和失败任务重试。</p>
    </div>
    <div class="panel-actions">
      <span id="tasks-selected-count" class="selected-count"></span>
      <button id="batch-delete-tasks-btn" class="mini-btn danger-btn" disabled data-action="batch-delete-tasks">批量删除</button>
      <span class="meta-chip">${state.tasks.length} 条任务</span>
    </div>
  `;

  panelBody.innerHTML = `
    ${detail}
    <div class="table">
      <div class="table-head">
        <label class="checkbox-cell"><input type="checkbox" id="select-all-tasks"></label>
        <strong>任务</strong>
        <span>归属用户</span>
        <span>进度</span>
        <span>状态</span>
        <span>操作</span>
      </div>
      ${state.tasks.map((task) => `
        <div class="table-row">
          <label class="checkbox-cell"><input type="checkbox" class="task-checkbox" value="${escapeHtml(task.taskId)}"></label>
          <strong>${escapeHtml(task.title || task.taskId)}<br><small>${escapeHtml(task.taskId)}</small></strong>
          <span>${escapeHtml(task.ownerId || '-')}</span>
          <span>${escapeHtml(task.progress || 0)}%</span>
          <span class="status-${escapeHtml(task.status)}">${escapeHtml(task.status)}</span>
          <span class="action-group">
            <button class="mini-btn" data-action="task-detail" data-id="${escapeHtml(task.taskId)}">详情</button>
            <button class="mini-btn success-btn" data-action="task-retry" data-id="${escapeHtml(task.taskId)}">重试</button>
          </span>
        </div>
      `).join('')}
    </div>
  `;
}

async function batchDeleteScenes() {
  const ids = getSelectedSceneIds();
  if (ids.length === 0) return;
  if (!window.confirm(`确定要删除选中的 ${ids.length} 个场景吗？此操作不可恢复。`)) return;
  try {
    await api('/api/admin/public-scenes/batch-delete', { method: 'POST', body: { sceneIds: ids } });
    toast(`成功删除 ${ids.length} 个场景`);
    state.editingScene = null;
    await loadConsole();
  } catch (error) {
    toast(error.message || '批量删除失败');
  }
}

async function batchSceneVisibility(visibility) {
  const ids = getSelectedSceneIds();
  if (ids.length === 0) return;
  const label = { public: '公开', private: '隐藏' }[visibility] || visibility;
  if (!window.confirm(`确定将选中的 ${ids.length} 个场景设为「${label}」吗？`)) return;
  try {
    await api('/api/admin/public-scenes/batch-visibility', { method: 'POST', body: { sceneIds: ids, visibility } });
    toast(`已将 ${ids.length} 个场景设为「${label}」`);
    await loadConsole();
  } catch (error) {
    toast(error.message || '批量修改失败');
  }
}

async function batchSceneFree(free) {
  const ids = getSelectedSceneIds();
  if (ids.length === 0) return;
  const label = free ? '免费可见' : '取消免费可见';
  if (!window.confirm(`确定将选中的 ${ids.length} 个场景${free ? '设为' : '取消'}「免费可见」吗？`)) return;
  try {
    await api('/api/admin/public-scenes/batch-free', { method: 'POST', body: { sceneIds: ids, free } });
    toast(`已${free ? '设为' : '取消'} ${ids.length} 个场景的「免费可见」`);
    await loadConsole();
  } catch (error) {
    toast(error.message || '批量修改失败');
  }
}

async function batchSceneCategory(categoryId, categoryName) {
  const ids = getSelectedSceneIds();
  if (ids.length === 0) return;
  if (!window.confirm(`确认将选中的 ${ids.length} 个场景移动到「${categoryName}」？`)) return;
  try {
    await api('/api/admin/public-scenes/batch-category', { method: 'POST', body: { sceneIds: ids, categoryId } });
    toast(`已将 ${ids.length} 个场景移动到「${categoryName}」`);
    await loadConsole();
  } catch (error) {
    toast(error.message || '批量移动失败');
  }
}

function buildCoverUrl(path) {
  if (!path) return '';
  if (path.startsWith('http')) return path;
  return window.location.origin + '/' + path.replace(/^\//, '');
}

function openSceneModal() {
  const scene = state.editingScene || {};
  const isEdit = !!scene.sceneId;
  const formHtml = `
    <form id="scene-form">
      <div class="field-grid">
        <label><span>标题</span><input name="title" value="${escapeHtml(scene.title || '')}" required></label>
        <label><span>分类</span>
          <select name="category">
            <option value="">请选择分类</option>
            ${state.categories.map((cat) => {
              const match = cat.name === (scene.category || '') || cat.categoryId === (scene.category || '');
              return `<option value="${escapeHtml(cat.name)}" ${match ? 'selected' : ''}>${escapeHtml(cat.name)}</option>`;
            }).join('')}
          </select>
        </label>
        <label><span>可见性</span>
          <select name="visibility">
            <option value="public" ${scene.visibility === 'public' || !scene.visibility ? 'selected' : ''}>公开</option>
            <option value="private" ${scene.visibility === 'private' ? 'selected' : ''}>隐藏</option>
            <option value="member" ${scene.visibility === 'member' ? 'selected' : ''}>会员</option>
          </select>
        </label>
        <label><span>场景类型</span>
          <select name="sceneType">
            <option value="public" ${scene.sceneType === 'public' || !scene.sceneType ? 'selected' : ''}>公共</option>
            <option value="private" ${scene.sceneType === 'private' ? 'selected' : ''}>私有</option>
          </select>
        </label>
        <label class="full"><span>背景图路径</span><input name="backgroundPath" value="${escapeHtml(scene.backgroundPath || '')}"></label>
        <label class="full"><span>封面图路径</span><input name="coverPath" value="${escapeHtml(scene.coverPath || '')}"></label>
      </div>
      <div class="form-actions" style="display:flex;gap:10px;margin-top:18px">
        <button class="primary-btn compact" type="submit">${isEdit ? '保存场景' : '创建场景'}</button>
        <button type="button" class="ghost-btn" data-action="scene-cancel-edit">取消</button>
      </div>
    </form>
  `;
  openModal(isEdit ? '编辑场景' : '新建场景', formHtml);
}

function renderScenes() {
  const viewMode = state.sceneViewMode || 'card';
  const filteredScenes = getFilteredScenes();
  panelHead.innerHTML = `
    <div class="scene-toolbar">
      <div class="scene-toolbar-left">
        <div class="scene-search">
          <input type="text" id="scene-search-input" placeholder="搜索标题或 ID..." value="${escapeHtml(state.sceneSearchQuery)}">
        </div>
        <div class="scene-filter-group">
          <select class="scene-filter-select" id="scene-filter-category">
            <option value="">全部分类</option>
            ${state.categories.map((cat) => `<option value="${escapeHtml(cat.categoryId)}" ${cat.categoryId === state.sceneFilterCategory ? 'selected' : ''}>${escapeHtml(cat.name)}</option>`).join('')}
          </select>
          <select class="scene-filter-select" id="scene-filter-visibility">
            <option value="">全部状态</option>
            <option value="public" ${state.sceneFilterVisibility === 'public' ? 'selected' : ''}>公开</option>
            <option value="member" ${state.sceneFilterVisibility === 'member' ? 'selected' : ''}>会员</option>
            <option value="private" ${state.sceneFilterVisibility === 'private' ? 'selected' : ''}>隐藏</option>
          </select>
        </div>
      </div>
      <div class="scene-toolbar-right">
        <button class="btn-new-scene" data-action="scene-open-create">新建场景</button>
        <div class="scene-view-toggles">
          <button class="scene-view-toggle ${viewMode === 'card' ? 'active' : ''}" data-action="set-scene-view-card" title="卡片视图">&#9638;</button>
          <button class="scene-view-toggle ${viewMode === 'table' ? 'active' : ''}" data-action="set-scene-view-table" title="列表视图">&#9776;</button>
        </div>
      </div>
    </div>
  `;

  if (filteredScenes.length === 0) {
    const isFiltered = state.sceneSearchQuery || state.sceneFilterCategory || state.sceneFilterVisibility;
    panelBody.innerHTML = `
      <div class="scene-empty">
        <div class="scene-empty-icon">${isFiltered ? '\uD83D\uDD0D' : '\uD83C\uDFAC'}</div>
        <div class="scene-empty-title">${isFiltered ? '没有匹配的场景' : '暂无场景'}</div>
        <div class="scene-empty-desc">${isFiltered ? '试试调整搜索条件或筛选项' : '点击上方「新建场景」添加第一个场景'}</div>
      </div>
    `;
  } else if (viewMode === 'table') {
    panelBody.innerHTML = renderSceneTable(filteredScenes);
  } else {
    panelBody.innerHTML = renderSceneCards(filteredScenes);
  }

  // Floating batch bar
  const existingBar = document.getElementById('scene-batch-bar');
  if (existingBar) existingBar.remove();
  const batchBarHtml = `
    <div id="scene-batch-bar" class="batch-bar">
      <div class="batch-bar-inner">
        <span class="batch-bar-count">已选 0 项</span>
        <div class="batch-bar-dropdown-wrap">
          <select id="scene-batch-action" class="batch-bar-dropdown">
            <option value="">选择操作…</option>
            <optgroup label="可见性">
              <option value="visibility:public">设为公开</option>
              <option value="visibility:member">设为会员</option>
              <option value="visibility:private">设为隐藏</option>
            </optgroup>
            <optgroup label="价格">
              <option value="free:true">设为免费</option>
              <option value="free:false">取消免费</option>
            </optgroup>
            <optgroup label="分类">
              ${state.categories.map((cat) => `<option value="category:${escapeHtml(cat.categoryId)}:${escapeHtml(cat.name)}">移动到「${escapeHtml(cat.name)}」</option>`).join('')}
            </optgroup>
            <optgroup label="危险操作">
              <option value="delete" style="color:#e74c3c">删除</option>
            </optgroup>
          </select>
          <button class="batch-bar-execute-btn" id="scene-batch-execute" data-action="scene-batch-execute" disabled>执行</button>
        </div>
        <button class="batch-bar-close" data-action="scene-batch-clear">&times;</button>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', batchBarHtml);
}

function renderSceneCards(scenes) {
  return `
    <div class="scene-list-header">
      <div class="scene-list-header-left">
        <label class="checkbox-cell"><input type="checkbox" id="select-all-scenes"></label>
        <span class="scene-list-count">共 <strong>${scenes.length}</strong> 个场景</span>
      </div>
    </div>
    <div class="card-grid">
      ${scenes.map((item) => {
        const cat = getSceneCategoryDisplay(item);
        const vis = item.visibility || 'public';
        const coverUrl = buildCoverUrl(item.coverPath || item.backgroundPath);
        return `
        <div class="scene-card" data-id="${escapeHtml(item.sceneId)}">
          <label class="scene-card-check">
            <input type="checkbox" class="scene-checkbox" value="${escapeHtml(item.sceneId)}">
            <span class="scene-card-checkmark"></span>
          </label>
          <div class="scene-card-cover">
            ${coverUrl ? `<img src="${coverUrl}" onerror="this.remove()">` : ''}
            ${!coverUrl ? '<div class="cover-placeholder">\uD83C\uDFAC</div>' : ''}
          </div>
          <div class="scene-card-body">
            <strong class="scene-card-title">${escapeHtml(item.title)}</strong>
            <div class="scene-card-meta">
              <span>${escapeHtml(cat)}</span>
              <span class="scene-card-meta-dot"></span>
              <span>${item.itemCount || 0} 词 / ${item.verbCount || 0} 动词</span>
            </div>
            <div class="scene-card-tags">
              ${vis === 'public' ? '<span class="scene-tag scene-tag--public">公开</span>' : ''}
              ${vis === 'member' ? '<span class="scene-tag scene-tag--member">会员</span>' : ''}
              ${vis === 'private' ? '<span class="scene-tag scene-tag--private">隐藏</span>' : ''}
              ${item.free ? '<span class="scene-tag scene-tag--free">免费</span>' : ''}
            </div>
            <div class="scene-card-actions">
              <button class="mini-btn" data-action="scene-edit" data-id="${escapeHtml(item.sceneId)}">编辑</button>
              ${item.publication && item.publication.sourceGeneratedSceneId
                ? `<button class="mini-btn success-btn" data-action="scene-republish" data-id="${escapeHtml(item.sceneId)}">覆盖发布</button>`
                : ''}
            </div>
          </div>
        </div>`;
      }).join('')}
    </div>
  `;
}

function renderSceneTable(scenes) {
  return `
    <div class="scene-list-header">
      <div class="scene-list-header-left">
        <label class="checkbox-cell"><input type="checkbox" id="select-all-scenes"></label>
        <span class="scene-list-count">共 <strong>${scenes.length}</strong> 个场景</span>
      </div>
    </div>
    <div class="scene-table">
      <div class="scene-table-head">
        <label class="checkbox-cell" style="padding:0"><input type="checkbox" class="scene-select-all"></label>
        <span>场景</span>
        <span>分类</span>
        <span>词汇</span>
        <span>状态</span>
        <span>免费</span>
        <span>操作</span>
      </div>
      ${scenes.map((item) => {
        const cat = getSceneCategoryDisplay(item);
        const vis = item.visibility || 'public';
        return `
        <div class="scene-table-row" data-id="${escapeHtml(item.sceneId)}">
          <label class="checkbox-cell" style="padding:0"><input type="checkbox" class="scene-checkbox" value="${escapeHtml(item.sceneId)}"></label>
          <div class="scene-table-title">
            <strong>${escapeHtml(item.title)}</strong>
            <small>${escapeHtml(item.sceneId)}</small>
          </div>
          <span style="font-size:13px">${escapeHtml(cat)}</span>
          <span style="font-size:13px">${item.itemCount || 0} / ${item.verbCount || 0}</span>
          <span>
            ${vis === 'public' ? '<span class="scene-tag scene-tag--public">公开</span>' : ''}
            ${vis === 'member' ? '<span class="scene-tag scene-tag--member">会员</span>' : ''}
            ${vis === 'private' ? '<span class="scene-tag scene-tag--private">隐藏</span>' : ''}
          </span>
          <span style="font-size:13px">${item.free ? '\u2705' : '-'}</span>
          <span class="action-group">
            <button class="mini-btn" data-action="scene-edit" data-id="${escapeHtml(item.sceneId)}">编辑</button>
            ${item.publication && item.publication.sourceGeneratedSceneId
              ? `<button class="mini-btn success-btn" data-action="scene-republish" data-id="${escapeHtml(item.sceneId)}">覆盖发布</button>`
              : ''}
          </span>
        </div>`;
      }).join('')}
    </div>
  `;
}

function addGeneratorFiles(fileList) {
  const files = Array.from(fileList || []);
  files.forEach((file) => {
    const reader = new FileReader();
    reader.onload = () => {
      state.generatorFiles.push({ file, dataUrl: reader.result });
      renderGeneratorPreviews();
    };
    reader.readAsDataURL(file);
  });
}

function removeGeneratorFile(index) {
  state.generatorFiles.splice(index, 1);
  renderGeneratorPreviews();
}

function renderGeneratorPreviews() {
  const grid = document.getElementById('gen-preview-grid');
  const count = document.getElementById('gen-file-count');
  const submitBtn = document.getElementById('gen-submit-btn');
  if (!grid) return;
  grid.innerHTML = state.generatorFiles.map((item, i) => `
    <div class="gen-preview-card">
      <img src="${item.dataUrl}" alt="${escapeHtml(item.file.name)}">
      <button type="button" class="gen-preview-delete" data-action="gen-remove-file" data-index="${i}">&times;</button>
      <div class="gen-preview-name">${escapeHtml(item.file.name)}</div>
    </div>
  `).join('');
  if (count) {
    count.innerHTML = state.generatorFiles.length > 0
      ? `<strong>${state.generatorFiles.length}</strong> 张图片已选择`
      : '';
  }
  if (submitBtn) {
    submitBtn.disabled = state.generatorFiles.length === 0;
  }
}

function taskStatusClass(status) {
  if (status === 'done' || status === 'completed') return 'gen-task-status--done';
  if (status === 'failed') return 'gen-task-status--failed';
  if (status === 'processing' || status === 'running') return 'gen-task-status--processing';
  return 'gen-task-status--pending';
}

function progressBarClass(status) {
  if (status === 'done' || status === 'completed') return 'done';
  if (status === 'failed') return 'failed';
  return '';
}

function renderGenerator() {
  const generatorTasks = state.tasks;
  panelHead.innerHTML = `
    <div>
      <h3 class="panel-title">场景生成器</h3>
      <p class="panel-subtitle">所有来源的生成任务（Admin 上传 + 小程序拍照）。</p>
    </div>
    <span class="meta-chip">${generatorTasks.length} 条任务</span>
  `;

  const hasFiles = state.generatorFiles.length > 0;
  panelBody.innerHTML = `
    <div class="gen-layout">
      <div class="gen-upload-section">
        <div class="gen-drop-zone" id="gen-drop-zone">
          <div class="gen-drop-zone-icon">&#128247;</div>
          <div class="gen-drop-zone-title">拖拽图片到此处，或点击选择</div>
          <div class="gen-drop-zone-desc">支持 JPG / PNG，可多选</div>
          <input type="file" accept="image/*" multiple id="gen-file-input">
        </div>
        <div id="gen-file-count" class="gen-file-count">${hasFiles ? `<strong>${state.generatorFiles.length}</strong> 张图片已选择` : ''}</div>
        <div class="gen-preview-grid" id="gen-preview-grid">
          ${state.generatorFiles.map((item, i) => `
            <div class="gen-preview-card">
              <img src="${item.dataUrl}" alt="${escapeHtml(item.file.name)}">
              <button type="button" class="gen-preview-delete" data-action="gen-remove-file" data-index="${i}">&times;</button>
              <div class="gen-preview-name">${escapeHtml(item.file.name)}</div>
            </div>
          `).join('')}
        </div>
      </div>

      <div class="gen-config">
        <h4 class="gen-config-title">生成配置</h4>
        <div class="gen-field">
          <span class="gen-field-label">主分类</span>
          <select name="categoryId" id="gen-category">
            <option value="">请选择分类</option>
            ${categoryOptions('')}
          </select>
        </div>
        <div class="gen-field">
          <span class="gen-field-label">可见性</span>
          <select id="gen-visibility">
            <option value="public" selected>公开</option>
            <option value="member">会员</option>
            <option value="private">隐藏</option>
          </select>
        </div>
        <div class="gen-field">
          <span class="gen-field-label">生成动词</span>
          <select id="gen-include-verbs">
            <option value="true" selected>生成动词</option>
            <option value="false">不生成动词</option>
          </select>
        </div>
        <div class="gen-field">
          <span class="gen-field-label">合集</span>
          <div class="gen-checkbox-group">
            ${collectionCheckboxes([]) || '<span class="empty-copy" style="font-size:13px">请先创建合集</span>'}
          </div>
        </div>
        <div class="gen-field">
          <span class="gen-field-label">发布策略</span>
          <div class="gen-checkbox-group">
            <label class="gen-checkbox-item"><input type="checkbox" id="gen-auto-publish" checked> 生成后自动发布</label>
          </div>
        </div>
        <button class="gen-submit-btn" id="gen-submit-btn" data-action="gen-submit" ${hasFiles ? '' : 'disabled'}>
          压缩上传并开始生成
        </button>
      </div>

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
    </div>
  `;

  const existingBar = document.getElementById('gen-batch-bar');
  if (existingBar) existingBar.remove();
  const batchBarHtml = `
    <div id="gen-batch-bar" class="batch-bar">
      <div class="batch-bar-inner">
        <span class="batch-bar-count">已选 0 项</span>
        <div class="batch-bar-dropdown-wrap">
          <select id="gen-batch-action" class="batch-bar-dropdown">
            <option value="">选择操作…</option>
            <option value="delete">删除</option>
            <option value="retry">重试</option>
          </select>
          <button class="batch-bar-execute-btn" id="gen-batch-execute" data-action="gen-batch-execute" disabled>执行</button>
        </div>
        <button class="batch-bar-close" data-action="gen-batch-clear">&times;</button>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', batchBarHtml);
}

function renderTaxonomy() {
  const category = state.editingCategory || {};
  const collection = state.editingCollection || {};
  panelHead.innerHTML = `
    <div>
      <h3 class="panel-title">场景分类与合集</h3>
      <p class="panel-subtitle">分类单选，合集多选。这里负责运营基础数据，不直接发布场景。</p>
    </div>
    <span class="meta-chip">${state.categories.length} 个分类 / ${state.collections.length} 个合集</span>
  `;

  panelBody.innerHTML = `
    <div class="editor-grid">
      <form id="category-form" class="editor-card">
        <div class="editor-title-row">
          <h4>${category.categoryId ? '编辑分类' : '新建分类'}</h4>
          ${category.categoryId ? '<button type="button" class="mini-btn" data-action="category-cancel-edit">取消</button>' : ''}
        </div>
        <div class="field-grid">
          <label><span>分类编码</span><input name="categoryCode" value="${escapeHtml(category.categoryCode || '')}" required></label>
          <label><span>分类名称</span><input name="name" value="${escapeHtml(category.name || '')}" required></label>
          <label><span>状态</span><input name="status" value="${escapeHtml(category.status || 'active')}" required></label>
          <label><span>排序</span><input name="sortOrder" value="${escapeHtml(category.sortOrder || 0)}" required></label>
          <label class="full"><span>描述</span><textarea name="description">${escapeHtml(category.description || '')}</textarea></label>
        </div>
        <div class="form-actions">
          <button class="primary-btn compact" type="submit">${category.categoryId ? '保存分类' : '创建分类'}</button>
        </div>
      </form>

      <form id="collection-form" class="editor-card">
        <div class="editor-title-row">
          <h4>${collection.collectionId ? '编辑合集' : '新建合集'}</h4>
          ${collection.collectionId ? '<button type="button" class="mini-btn" data-action="collection-cancel-edit">取消</button>' : ''}
        </div>
        <div class="field-grid">
          <label><span>合集编码</span><input name="collectionCode" value="${escapeHtml(collection.collectionCode || '')}" required></label>
          <label><span>合集名称</span><input name="name" value="${escapeHtml(collection.name || '')}" required></label>
          <label><span>状态</span><input name="status" value="${escapeHtml(collection.status || 'active')}" required></label>
          <label><span>排序</span><input name="sortOrder" value="${escapeHtml(collection.sortOrder || 0)}" required></label>
          <label class="full"><span>封面地址</span><input name="coverUrl" value="${escapeHtml(collection.coverUrl || '')}"></label>
          <label class="full"><span>描述</span><textarea name="description">${escapeHtml(collection.description || '')}</textarea></label>
        </div>
        <div class="form-actions">
          <button class="primary-btn compact" type="submit">${collection.collectionId ? '保存合集' : '创建合集'}</button>
        </div>
      </form>
    </div>

    <div class="stack">
      <article class="detail-card">
        <div class="editor-title-row">
          <h4>分类列表</h4>
          <span class="meta-chip">${state.categories.length} 个</span>
        </div>
        <div class="table">
          <div class="table-head">
            <strong>分类</strong>
            <span>编码</span>
            <span>状态</span>
            <span>操作</span>
          </div>
          ${state.categories.map((item) => `
            <div class="table-row">
              <strong>${escapeHtml(item.name)}<br><small>${escapeHtml(item.description || '')}</small></strong>
              <span>${escapeHtml(item.categoryCode)}</span>
              <span>${escapeHtml(item.status)}</span>
              <span class="action-group">
                <button class="mini-btn" data-action="category-edit" data-id="${escapeHtml(item.categoryId)}">编辑</button>
                <button class="mini-btn danger-btn" data-action="category-delete" data-id="${escapeHtml(item.categoryId)}">删除</button>
              </span>
            </div>
          `).join('') || '<div class="empty-copy">暂无分类</div>'}
        </div>
      </article>

      <article class="detail-card">
        <div class="editor-title-row">
          <h4>合集列表</h4>
          <span class="meta-chip">${state.collections.length} 个</span>
        </div>
        <div class="table">
          <div class="table-head">
            <strong>合集</strong>
            <span>编码</span>
            <span>状态</span>
            <span>操作</span>
          </div>
          ${state.collections.map((item) => `
            <div class="table-row">
              <strong>${escapeHtml(item.name)}<br><small>${escapeHtml(item.description || '')}</small></strong>
              <span>${escapeHtml(item.collectionCode)}</span>
              <span>${escapeHtml(item.status)}</span>
              <span class="action-group">
                <button class="mini-btn" data-action="collection-edit" data-id="${escapeHtml(item.collectionId)}">编辑</button>
                <button class="mini-btn danger-btn" data-action="collection-delete" data-id="${escapeHtml(item.collectionId)}">删除</button>
              </span>
            </div>
          `).join('') || '<div class="empty-copy">暂无合集</div>'}
        </div>
      </article>
    </div>
  `;
}

function getFilteredDrafts() {
  let list = state.generatedScenes;
  const q = (state.draftSearchQuery || '').trim().toLowerCase();
  if (q) {
    list = list.filter((s) => {
      const title = (s.title || '').toLowerCase();
      const id = (s.sceneId || '').toLowerCase();
      const owner = (resolveOwnerName(s.ownerId)).toLowerCase();
      return title.includes(q) || id.includes(q) || owner.includes(q);
    });
  }
  return list;
}

function getSelectedDraftIds() {
  return Array.from(panelBody.querySelectorAll('.draft-checkbox:checked')).map((cb) => cb.value);
}

function updateDraftBatchBar() {
  const ids = getSelectedDraftIds();
  const bar = document.getElementById('draft-batch-bar');
  if (!bar) return;
  const countEl = bar.querySelector('.batch-bar-count');
  if (countEl) countEl.textContent = `已选 ${ids.length} 项`;
  bar.classList.toggle('visible', ids.length > 0);
  const dropdown = document.getElementById('draft-batch-action');
  const executeBtn = document.getElementById('draft-batch-execute');
  if (dropdown) dropdown.selectedIndex = 0;
  if (executeBtn) executeBtn.disabled = true;
}

function updateDraftBatchState() {
  updateDraftBatchBar();
  const checkboxes = panelBody.querySelectorAll('.draft-checkbox');
  const checked = panelBody.querySelectorAll('.draft-checkbox:checked');
  const selectAll = panelBody.querySelector('#select-all-drafts');
  if (selectAll) {
    selectAll.checked = checkboxes.length > 0 && checked.length === checkboxes.length;
    selectAll.indeterminate = checked.length > 0 && checked.length < checkboxes.length;
  }
}

function renderDrafts() {
  const viewMode = state.draftViewMode || 'card';
  const filtered = getFilteredDrafts();
  const draft = state.publishingDraft;
  const publication = draft && draft.publication ? draft.publication : null;

  // Publish form section (shown when a draft is selected for publishing)
  const publishSection = draft ? `
    <div class="editor-grid" style="margin-bottom:20px;">
      <article class="detail-card">
        <div class="detail-head">
          <div>
            <h4>${escapeHtml(draft.title)}</h4>
            <p>${escapeHtml(draft.sceneId)} · ${escapeHtml(resolveOwnerName(draft.ownerId))}</p>
          </div>
          ${renderPublicationSummary(publication)}
          <button class="mini-btn" data-action="draft-close-publish" style="margin-left:auto;">关闭</button>
        </div>
        <div class="detail-grid">
          <div><span>热点数</span><strong>${escapeHtml(draft.itemCount || 0)}</strong></div>
          <div><span>非名词数</span><strong>${escapeHtml(draft.verbCount || 0)}</strong></div>
          <div><span>可见性</span><strong>${escapeHtml(draft.visibility || 'private')}</strong></div>
          <div><span>分类</span><strong>${escapeHtml(publication ? (resolveCategoryName(publication.categoryId) || '-') : '-')}</strong></div>
        </div>
      </article>
      <form id="publish-form" class="editor-card">
        <div class="editor-title-row">
          <h4>${publication ? '更新公开版本' : '发布到公开库'}</h4>
        </div>
        <input type="hidden" name="sceneId" value="${escapeHtml(draft.sceneId)}">
        <div class="field-grid">
          <label class="full"><span>公开标题</span><input name="title" value="${escapeHtml((publication && draft.title) || draft.title || '')}" required></label>
          <label><span>公开可见性</span><input name="visibility" value="${escapeHtml((publication && publication.visibility) || 'public')}" required></label>
          <label><span>主分类</span>
            <select name="categoryId" required>
              <option value="">请选择分类</option>
              ${categoryOptions(publication ? publication.categoryId : '')}
            </select>
          </label>
          <label class="full"><span>合集</span>
            <div class="checkbox-grid">
              ${collectionCheckboxes(publication ? publication.collectionIds : []) || '<span class="empty-copy">请先创建合集</span>'}
            </div>
          </label>
        </div>
        <div class="form-actions">
          <button class="primary-btn compact" type="submit">${publication ? '更新发布' : '发布场景'}</button>
        </div>
      </form>
    </div>
  ` : '';

  panelHead.innerHTML = `
    <div class="scene-toolbar">
      <div class="scene-toolbar-left">
        <div class="scene-search">
          <input type="text" id="draft-search-input" placeholder="搜索标题、ID 或归属用户..." value="${escapeHtml(state.draftSearchQuery)}">
        </div>
        <span class="meta-chip">${filtered.length} / ${state.generatedScenes.length} 个草稿</span>
      </div>
      <div class="scene-toolbar-right">
        <div class="scene-view-toggles">
          <button class="scene-view-toggle ${viewMode === 'card' ? 'active' : ''}" data-action="set-draft-view-card" title="卡片视图">&#9638;</button>
          <button class="scene-view-toggle ${viewMode === 'table' ? 'active' : ''}" data-action="set-draft-view-table" title="列表视图">&#9776;</button>
        </div>
      </div>
    </div>
  `;

  if (filtered.length === 0 && !draft) {
    const isFiltered = !!state.draftSearchQuery;
    panelBody.innerHTML = `
      ${publishSection}
      <div class="scene-empty">
        <div class="scene-empty-icon">${isFiltered ? '🔍' : '📝'}</div>
        <div class="scene-empty-title">${isFiltered ? '没有匹配的草稿' : '暂无草稿'}</div>
        <div class="scene-empty-desc">${isFiltered ? '试试调整搜索条件' : '用户创建的场景草稿会出现在这里'}</div>
      </div>
    `;
  } else if (viewMode === 'table') {
    panelBody.innerHTML = publishSection + renderDraftTable(filtered);
  } else {
    panelBody.innerHTML = publishSection + renderDraftCards(filtered);
  }

  // Floating batch bar
  const existingBar = document.getElementById('draft-batch-bar');
  if (existingBar) existingBar.remove();
  const batchBarHtml = `
    <div id="draft-batch-bar" class="batch-bar">
      <div class="batch-bar-inner">
        <span class="batch-bar-count">已选 0 项</span>
        <div class="batch-bar-dropdown-wrap">
          <select id="draft-batch-action" class="batch-bar-dropdown">
            <option value="">选择操作…</option>
            <optgroup label="可见性">
              <option value="visibility:private">设为隐藏</option>
            </optgroup>
            <optgroup label="危险操作">
              <option value="delete" style="color:#e74c3c">删除</option>
            </optgroup>
          </select>
          <button class="batch-bar-execute-btn" id="draft-batch-execute" data-action="draft-batch-execute" disabled>执行</button>
        </div>
        <button class="batch-bar-close" data-action="draft-batch-clear">&times;</button>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', batchBarHtml);
}

function renderDraftCards(scenes) {
  return `
    <div class="scene-list-header">
      <div class="scene-list-header-left">
        <label class="checkbox-cell"><input type="checkbox" id="select-all-drafts"></label>
        <span class="scene-list-count">共 <strong>${scenes.length}</strong> 个草稿</span>
      </div>
    </div>
    <div class="card-grid">
      ${scenes.map((item) => {
        const vis = item.visibility || 'private';
        const coverUrl = buildCoverUrl(item.coverPath || item.backgroundPath);
        return `
        <div class="scene-card" data-id="${escapeHtml(item.sceneId)}">
          <label class="scene-card-check">
            <input type="checkbox" class="draft-checkbox" value="${escapeHtml(item.sceneId)}">
            <span class="scene-card-checkmark"></span>
          </label>
          <div class="scene-card-cover">
            ${coverUrl ? `<img src="${coverUrl}" onerror="this.remove()">` : ''}
            ${!coverUrl ? '<div class="cover-placeholder">📝</div>' : ''}
          </div>
          <div class="scene-card-body">
            <strong class="scene-card-title">${escapeHtml(item.title)}</strong>
            <div class="scene-card-meta">
              <span>${escapeHtml(resolveOwnerName(item.ownerId))}</span>
              <span class="scene-card-meta-dot"></span>
              <span>${item.itemCount || 0} 词 / ${item.verbCount || 0} 动词</span>
            </div>
            <div class="scene-card-tags">
              ${vis === 'private' ? '<span class="scene-tag scene-tag--private">隐藏</span>' : ''}
              ${vis === 'public' ? '<span class="scene-tag scene-tag--public">公开</span>' : ''}
              ${item.publication ? '<span class="scene-tag scene-tag--member">已发布</span>' : '<span class="scene-tag scene-tag--free">草稿</span>'}
            </div>
            <div class="scene-card-actions">
              <button class="mini-btn" data-action="draft-publish" data-id="${escapeHtml(item.sceneId)}">${item.publication ? '重新发布' : '发布'}</button>
            </div>
          </div>
        </div>`;
      }).join('')}
    </div>
  `;
}

function renderDraftTable(scenes) {
  return `
    <div class="table">
      <div class="table-head">
        <label class="checkbox-cell"><input type="checkbox" id="select-all-drafts"></label>
        <strong>草稿场景</strong>
        <span>归属用户</span>
        <span>热点</span>
        <span>可见性</span>
        <span>发布状态</span>
        <span>创建时间</span>
        <span>操作</span>
      </div>
      ${scenes.map((item) => `
        <div class="table-row">
          <label class="checkbox-cell"><input type="checkbox" class="draft-checkbox" value="${escapeHtml(item.sceneId)}"></label>
          <strong>${escapeHtml(item.title)}<br><small>${escapeHtml(item.sceneId)}</small></strong>
          <span>${escapeHtml(resolveOwnerName(item.ownerId))}</span>
          <span>${item.itemCount || 0} 词 / ${item.verbCount || 0} 动词</span>
          <span>${escapeHtml(item.visibility || 'private')}</span>
          <span>${item.publication ? '已发布' : '草稿'}</span>
          <span>${item.createdAt ? item.createdAt.slice(0, 10) : '-'}</span>
          <span class="action-group">
            <button class="mini-btn" data-action="draft-publish" data-id="${escapeHtml(item.sceneId)}">${item.publication ? '重新发布' : '发布'}</button>
          </span>
        </div>
      `).join('') || '<div class="empty-copy">暂无草稿</div>'}
    </div>
  `;
}

function resolveOwnerName(ownerId) {
  if (!ownerId) return '';
  const user = state.users.find((u) => u.id === ownerId);
  if (!user) return ownerId;
  const parts = [];
  if (user.displayName) parts.push(user.displayName);
  if (user.mobileVerified && user.mobile) parts.push(user.mobile);
  return parts.length ? parts.join(' / ') : ownerId;
}

function getFilteredPrivateScenes() {
  let list = state.generatedScenes;
  const ownerId = state.privateSceneSelectedOwnerId;
  if (ownerId) {
    list = list.filter((s) => s.ownerId === ownerId);
  }
  const q = (state.privateSceneSearchQuery || '').trim().toLowerCase();
  if (q) {
    list = list.filter((s) => {
      const title = (s.title || '').toLowerCase();
      const id = (s.sceneId || '').toLowerCase();
      const owner = (s.ownerId || '').toLowerCase();
      return title.includes(q) || id.includes(q) || owner.includes(q);
    });
  }
  return list;
}

function getSelectedPrivateSceneIds() {
  return Array.from(panelBody.querySelectorAll('.pscene-checkbox:checked')).map((cb) => cb.value);
}

function updatePrivateSceneBatchBar() {
  const ids = getSelectedPrivateSceneIds();
  const bar = document.getElementById('pscene-batch-bar');
  if (!bar) return;
  const countEl = bar.querySelector('.batch-bar-count');
  if (countEl) countEl.textContent = `已选 ${ids.length} 项`;
  bar.classList.toggle('visible', ids.length > 0);
  const dropdown = document.getElementById('pscene-batch-action');
  const executeBtn = document.getElementById('pscene-batch-execute');
  if (dropdown) dropdown.selectedIndex = 0;
  if (executeBtn) executeBtn.disabled = true;
}

function updatePrivateSceneBatchState() {
  updatePrivateSceneBatchBar();
  const checkboxes = panelBody.querySelectorAll('.pscene-checkbox');
  const checked = panelBody.querySelectorAll('.pscene-checkbox:checked');
  const selectAll = panelBody.querySelector('#select-all-pscenes');
  if (selectAll) {
    selectAll.checked = checkboxes.length > 0 && checked.length === checkboxes.length;
    selectAll.indeterminate = checked.length > 0 && checked.length < checkboxes.length;
  }
}

function renderPrivateScenes() {
  const viewMode = state.privateSceneViewMode || 'card';
  const filtered = getFilteredPrivateScenes();
  const selectedOwner = state.privateSceneSelectedOwnerId;
  const ownerLabel = selectedOwner ? resolveOwnerName(selectedOwner) : '';

  panelHead.innerHTML = `
    <div class="scene-toolbar">
      <div class="scene-toolbar-left">
        <div class="scene-search">
          <input type="text" id="private-scene-search-input" placeholder="搜索标题、ID..." value="${escapeHtml(state.privateSceneSearchQuery)}">
        </div>
        <div class="scene-filter-group">
          <div class="user-filter-wrap" style="position:relative;display:inline-flex;align-items:center;">
            <input type="text" id="pscene-user-search-input" class="scene-filter-select" style="width:180px;padding-right:28px;" placeholder="筛选用户名/手机号..." value="${escapeHtml(state.privateSceneUserSearch)}">
            ${selectedOwner ? `<button data-action="pscene-clear-owner" style="position:absolute;right:4px;background:none;border:none;cursor:pointer;font-size:16px;color:#999;" title="清除">&times;</button>` : ''}
          </div>
          ${selectedOwner ? `<span class="meta-chip" style="font-size:12px;">${escapeHtml(ownerLabel)}</span>` : ''}
        </div>
        <span class="meta-chip">${filtered.length} / ${state.generatedScenes.length} 个私人场景</span>
      </div>
      <div class="scene-toolbar-right">
        <div class="scene-view-toggles">
          <button class="scene-view-toggle ${viewMode === 'card' ? 'active' : ''}" data-action="set-pscene-view-card" title="卡片视图">&#9638;</button>
          <button class="scene-view-toggle ${viewMode === 'table' ? 'active' : ''}" data-action="set-pscene-view-table" title="列表视图">&#9776;</button>
        </div>
      </div>
    </div>
    <div id="pscene-user-dropdown" class="user-dropdown" style="display:none;position:absolute;z-index:100;background:#fff;border:1px solid #ddd;border-radius:8px;max-height:240px;overflow-y:auto;box-shadow:0 4px 12px rgba(0,0,0,.15);min-width:260px;"></div>
  `;

  if (filtered.length === 0) {
    const isFiltered = !!state.privateSceneSearchQuery || !!state.privateSceneSelectedOwnerId;
    panelBody.innerHTML = `
      <div class="scene-empty">
        <div class="scene-empty-icon">${isFiltered ? '🔍' : '🎬'}</div>
        <div class="scene-empty-title">${isFiltered ? '没有匹配的场景' : '暂无私人场景'}</div>
        <div class="scene-empty-desc">${isFiltered ? '试试调整搜索条件' : '用户创建的场景会出现在这里'}</div>
      </div>
    `;
  } else if (viewMode === 'table') {
    panelBody.innerHTML = renderPrivateSceneTable(filtered);
  } else {
    panelBody.innerHTML = renderPrivateSceneCards(filtered);
  }

  // Floating batch bar
  const existingBar = document.getElementById('pscene-batch-bar');
  if (existingBar) existingBar.remove();
  const batchBarHtml = `
    <div id="pscene-batch-bar" class="batch-bar">
      <div class="batch-bar-inner">
        <span class="batch-bar-count">已选 0 项</span>
        <div class="batch-bar-dropdown-wrap">
          <select id="pscene-batch-action" class="batch-bar-dropdown">
            <option value="">选择操作…</option>
            <optgroup label="可见性">
              <option value="visibility:private">设为隐藏</option>
            </optgroup>
            <optgroup label="危险操作">
              <option value="delete" style="color:#e74c3c">删除</option>
            </optgroup>
          </select>
          <button class="batch-bar-execute-btn" id="pscene-batch-execute" data-action="pscene-batch-execute" disabled>执行</button>
        </div>
        <button class="batch-bar-close" data-action="pscene-batch-clear">&times;</button>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', batchBarHtml);
}

function renderPrivateSceneCards(scenes) {
  return `
    <div class="scene-list-header">
      <div class="scene-list-header-left">
        <label class="checkbox-cell"><input type="checkbox" id="select-all-pscenes"></label>
        <span class="scene-list-count">共 <strong>${scenes.length}</strong> 个场景</span>
      </div>
    </div>
    <div class="card-grid">
      ${scenes.map((item) => {
        const vis = item.visibility || 'private';
        const coverUrl = buildCoverUrl(item.coverPath || item.backgroundPath);
        return `
        <div class="scene-card" data-id="${escapeHtml(item.sceneId)}">
          <label class="scene-card-check">
            <input type="checkbox" class="pscene-checkbox" value="${escapeHtml(item.sceneId)}">
            <span class="scene-card-checkmark"></span>
          </label>
          <div class="scene-card-cover">
            ${coverUrl ? `<img src="${coverUrl}" onerror="this.remove()">` : ''}
            ${!coverUrl ? '<div class="cover-placeholder">🎬</div>' : ''}
          </div>
          <div class="scene-card-body">
            <strong class="scene-card-title">${escapeHtml(item.title)}</strong>
            <div class="scene-card-meta">
              <span>${escapeHtml(resolveOwnerName(item.ownerId))}</span>
              <span class="scene-card-meta-dot"></span>
              <span>${item.itemCount || 0} 词 / ${item.verbCount || 0} 动词</span>
            </div>
            <div class="scene-card-tags">
              ${vis === 'private' ? '<span class="scene-tag scene-tag--private">私人</span>' : ''}
              ${vis === 'public' ? '<span class="scene-tag scene-tag--public">公开</span>' : ''}
              ${item.publication ? '<span class="scene-tag scene-tag--member">已发布</span>' : '<span class="scene-tag scene-tag--free">未发布</span>'}
            </div>
            <div class="scene-card-actions">
              <button class="mini-btn" data-action="draft-publish" data-id="${escapeHtml(item.sceneId)}">${item.publication ? '重新发布' : '去发布'}</button>
            </div>
          </div>
        </div>`;
      }).join('')}
    </div>
  `;
}

function renderPrivateSceneTable(scenes) {
  return `
    <div class="table">
      <div class="table-head">
        <label class="checkbox-cell"><input type="checkbox" id="select-all-pscenes"></label>
        <strong>场景</strong>
        <span>归属用户</span>
        <span>热点</span>
        <span>可见性</span>
        <span>发布状态</span>
        <span>创建时间</span>
        <span>操作</span>
      </div>
      ${scenes.map((item) => `
        <div class="table-row">
          <label class="checkbox-cell"><input type="checkbox" class="pscene-checkbox" value="${escapeHtml(item.sceneId)}"></label>
          <strong>${escapeHtml(item.title)}<br><small>${escapeHtml(item.sceneId)}</small></strong>
          <span>${escapeHtml(resolveOwnerName(item.ownerId))}</span>
          <span>${item.itemCount || 0} 词 / ${item.verbCount || 0} 动词</span>
          <span>${escapeHtml(item.visibility || 'private')}</span>
          <span>${item.publication ? '已发布' : '未发布'}</span>
          <span>${item.createdAt ? item.createdAt.slice(0, 10) : '-'}</span>
          <span class="action-group">
            <button class="mini-btn" data-action="draft-publish" data-id="${escapeHtml(item.sceneId)}">${item.publication ? '重新发布' : '发布'}</button>
          </span>
        </div>
      `).join('') || '<div class="empty-copy">暂无场景</div>'}
    </div>
  `;
}

const VIEW_TITLES = {
  overview: '数据概览',
  scenes: '场景管理',
  generator: '场景生成',
  drafts: '草稿发布',
  'private-scenes': '私人场景',
  taxonomy: '分类/合集',
  users: '用户管理',
  products: '商品管理',
  orders: '订单管理',
  tasks: '任务管理',
  cdk: '卡密管理',
  storage: '存储管理',
  'scene-logs': '生成日志'
};

function formatBytes(bytes) {
  if (!bytes || bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return (bytes / Math.pow(1024, i)).toFixed(2) + ' ' + units[i];
}

async function loadStorageData() {
  try {
    const [overview, configs] = await Promise.all([
      api('/api/admin/storage/overview'),
      api('/api/admin/storage/configs'),
    ]);
    state.storageOverview = overview;
    state.storageConfigs = configs;
  } catch (error) {
    toast(error.message || '加载存储数据失败', 'error');
  }
}

async function renderSceneLogs() {
  panelHead.innerHTML = `
    <div>
      <h3 class="panel-title">生成日志</h3>
      <p class="panel-subtitle">场景生成任务的三级重试记录，按天分文件。</p>
    </div>
  `;
  panelBody.innerHTML = '<div class="empty-copy">加载中...</div>';

  try {
    const result = await api('/api/admin/scene-logs');
    const logs = result.list || [];
    if (logs.length === 0) {
      panelBody.innerHTML = '<div class="empty-copy">暂无日志文件</div>';
      return;
    }
    panelBody.innerHTML = `
      <div class="log-file-list">
        ${logs.map((f) => `
          <button class="log-file-item" data-action="view-log" data-filename="${escapeHtml(f.filename)}">
            <strong>${escapeHtml(f.filename)}</strong>
            <span class="meta-chip">${(f.size / 1024).toFixed(1)} KB</span>
          </button>
        `).join('')}
      </div>
      <div id="log-content-area" class="log-content-area" style="display:none">
        <pre id="log-content" class="log-content"></pre>
      </div>
    `;
  } catch (error) {
    panelBody.innerHTML = `<div class="empty-copy">加载失败: ${escapeHtml(error.message)}</div>`;
  }
}

function renderStorage() {
  const overview = state.storageOverview || {};
  const usage = overview.usage || {};
  const backends = overview.backends || {};
  const activeId = overview.activeBackend || 'local';
  const editing = state.editingBackend;
  const editingConfig = editing ? (state.storageConfigs && state.storageConfigs.backends && state.storageConfigs.backends[editing]) || {} : {};

  const backendCards = Object.entries(backends).map(([id, cfg]) => {
    const isActive = id === activeId;
    const isEnabled = cfg.enabled;
    const statusLabel = isActive ? '使用中' : (isEnabled ? '已启用' : '未启用');
    const statusClass = isActive ? 'scene-tag--public' : (isEnabled ? 'scene-tag--member' : 'scene-tag--private');
    const canActivate = isEnabled && !isActive;
    return `
      <div class="storage-backend-card ${isActive ? 'storage-backend-card--active' : ''}">
        <div class="storage-backend-header">
          <strong class="storage-backend-name">${escapeHtml(cfg.name || id)}</strong>
          <span class="scene-tag ${statusClass}">${statusLabel}</span>
        </div>
        <div class="storage-backend-type">${escapeHtml(cfg.type || id)}</div>
        <div class="storage-backend-actions">
          <button class="mini-btn" data-action="storage-edit" data-id="${escapeHtml(id)}">配置</button>
          ${canActivate ? `<button class="mini-btn success-btn" data-action="storage-test-activate" data-id="${escapeHtml(id)}">${state.testingBackend === id ? '测试中...' : '设为默认'}</button>` : ''}
          <button class="mini-btn" data-action="storage-test" data-id="${escapeHtml(id)}">${state.testingBackend === id ? '测试中...' : '测试连接'}</button>
        </div>
      </div>
    `;
  }).join('');

  const byTypeEntries = Object.entries(usage.byType || {});
  const maxTypeBytes = Math.max(...byTypeEntries.map(([, v]) => v), 1);
  const typeBreakdown = byTypeEntries.length > 0 ? byTypeEntries.map(([type, bytes]) => `
    <div class="storage-type-row">
      <span class="storage-type-label">${escapeHtml(type)}</span>
      <div class="storage-type-bar-wrap">
        <div class="storage-type-bar" style="width:${Math.max(2, (bytes / maxTypeBytes) * 100)}%"></div>
      </div>
      <span class="storage-type-value">${formatBytes(bytes)}</span>
    </div>
  `).join('') : '<div class="empty-copy">暂无分类数据</div>';

  panelHead.innerHTML = `
    <div>
      <h3 class="panel-title">存储管理</h3>
      <p class="panel-subtitle">配置存储后端、监控用量、切换默认存储。</p>
    </div>
  `;

  panelBody.innerHTML = `
    <div class="storage-metrics">
      ${metricCard('已用空间', formatBytes(usage.usedBytes))}
      ${metricCard('总容量', formatBytes(usage.totalBytes))}
      ${metricCard('剩余空间', formatBytes(Math.max(0, (usage.totalBytes || 0) - (usage.usedBytes || 0))))}
      ${metricCard('文件数量', usage.fileCount || 0)}
    </div>

    <div class="storage-section-title">存储后端配置</div>
    <div class="storage-backends-grid">
      ${backendCards}
    </div>

    <div class="storage-section-title">文件类型分布</div>
    <div class="storage-type-breakdown">
      ${typeBreakdown}
    </div>
  `;
}

function getStorageConfigFields(backendId, config) {
  const type = config.type || backendId;
  const cfg = config.config || {};
  if (type === 'local') {
    return `<label class="full"><span>根目录</span><input name="root_dir" value="${escapeHtml(cfg.root_dir || 'assets')}" readonly></label>`;
  }
  if (type === 'r2') {
    return `
      <label><span>Account ID</span><input name="account_id" value="${escapeHtml(cfg.account_id || '')}"></label>
      <label><span>Access Key ID</span><input name="access_key_id" value="${escapeHtml(cfg.access_key_id || '')}"></label>
      <label><span>Secret Access Key</span><input name="secret_access_key" type="password" value="${escapeHtml(cfg.secret_access_key || '')}" placeholder="留空保持不变"></label>
      <label><span>Bucket</span><input name="bucket" value="${escapeHtml(cfg.bucket || '')}"></label>
      <label class="full"><span>Public URL</span><input name="public_url" value="${escapeHtml(cfg.public_url || '')}"></label>
      <label><span>启用</span>
        <select name="enabled">
          <option value="true" ${cfg.enabled !== false ? 'selected' : ''}>启用</option>
          <option value="false" ${cfg.enabled === false ? 'selected' : ''}>禁用</option>
        </select>
      </label>
    `;
  }
  if (type === 'cos') {
    return `
      <label><span>Secret ID</span><input name="secret_id" value="${escapeHtml(cfg.secret_id || '')}"></label>
      <label><span>Secret Key</span><input name="secret_key" type="password" value="${escapeHtml(cfg.secret_key || '')}" placeholder="留空保持不变"></label>
      <label><span>Region</span><input name="region" value="${escapeHtml(cfg.region || '')}"></label>
      <label><span>Bucket</span><input name="bucket" value="${escapeHtml(cfg.bucket || '')}"></label>
      <label class="full"><span>Public URL</span><input name="public_url" value="${escapeHtml(cfg.public_url || '')}"></label>
      <label><span>启用</span>
        <select name="enabled">
          <option value="true" ${cfg.enabled !== false ? 'selected' : ''}>启用</option>
          <option value="false" ${cfg.enabled === false ? 'selected' : ''}>禁用</option>
        </select>
      </label>
    `;
  }
  return '';
}

function renderCurrentView() {
  navItems.forEach((button) => {
    button.classList.toggle('active', button.dataset.view === state.currentView);
  });

  pageTitle.textContent = VIEW_TITLES[state.currentView] || state.currentView;

  const genBar = document.getElementById('gen-batch-bar');
  if (genBar && state.currentView !== 'generator') genBar.remove();

  if (state.currentView === 'overview') {
    overviewCards.hidden = false;
    panelHead.innerHTML = '';
    panelBody.innerHTML = '';
    return;
  }

  overviewCards.hidden = true;

  if (state.currentView === 'products') {
    renderProducts();
    return;
  }
  if (state.currentView === 'orders') {
    renderOrders();
    return;
  }
  if (state.currentView === 'cdk') {
    renderCdk();
    return;
  }
  if (state.currentView === 'tasks') {
    renderTasks();
    return;
  }
  if (state.currentView === 'generator') {
    renderGenerator();
    return;
  }
  if (state.currentView === 'taxonomy') {
    renderTaxonomy();
    return;
  }
  if (state.currentView === 'drafts') {
    renderDrafts();
    return;
  }
  if (state.currentView === 'private-scenes') {
    renderPrivateScenes();
    return;
  }
  if (state.currentView === 'scenes') {
    renderScenes();
    return;
  }
  if (state.currentView === 'storage') {
    if (!state.storageOverview) {
      loadStorageData().then(() => renderStorage());
      panelBody.innerHTML = '<div class="empty-copy">加载中...</div>';
      return;
    }
    renderStorage();
    return;
  }
  if (state.currentView === 'scene-logs') {
    renderSceneLogs();
    return;
  }
  renderUsers();
}

async function loadConsole() {
  const [admin, overview, users, products, skus, orders, tasks, categories, collections, drafts, scenes, cdkResult] = await Promise.all([
    api('/api/admin/auth/me'),
    api('/api/admin/overview'),
    api('/api/admin/users'),
    api('/api/admin/products'),
    api('/api/admin/skus'),
    api('/api/admin/orders'),
    api('/api/admin/tasks'),
    api('/api/admin/scene-categories'),
    api('/api/admin/scene-collections'),
    api('/api/admin/generated-scenes'),
    api('/api/admin/public-scenes'),
    api('/api/admin/cdk-codes').catch(() => ({ list: [] }))
  ]);

  setLoggedIn(state.token, admin);
  state.overview = overview;
  state.users = users.list || [];
  state.products = products.list || [];
  state.skus = skus.list || [];
  state.orders = orders.list || [];
  state.tasks = tasks.list || [];
  state.categories = categories.list || [];
  state.collections = collections.list || [];
  state.generatedScenes = drafts.list || [];
  state.scenes = scenes.list || [];
  state.cdkCodes = cdkResult.list || [];
  state.publishingDraft = state.generatedScenes.find((item) => item.sceneId === (state.publishingDraft && state.publishingDraft.sceneId)) || null;
  renderOverview();
  renderCurrentView();
}

function parseBenefits(value) {
  const trimmed = String(value || '').trim();
  if (!trimmed) {
    return [];
  }
  return JSON.parse(trimmed);
}

async function submitProductForm(form) {
  const payload = {
    productCode: form.productCode.value.trim(),
    productType: form.productType.value.trim(),
    name: form.name.value.trim(),
    subtitle: form.subtitle.value.trim(),
    description: form.description.value.trim(),
    status: form.status.value.trim() || 'draft',
    coverUrl: '',
    sortOrder: 0
  };
  if (state.editingProduct && state.editingProduct.productId) {
    await api(`/api/admin/products/${state.editingProduct.productId}`, { method: 'PUT', body: payload });
    toast('商品已更新');
  } else {
    await api('/api/admin/products', { method: 'POST', body: payload });
    toast('商品已创建');
  }
  state.editingProduct = null;
  await loadConsole();
}

async function submitSkuForm(form) {
  const payload = {
    productId: form.productId.value,
    skuCode: form.skuCode.value.trim(),
    name: form.name.value.trim(),
    billingType: form.billingType.value.trim(),
    durationDays: form.durationDays.value ? Number(form.durationDays.value) : null,
    status: form.status.value.trim(),
    listPrice: form.listPrice.value.trim(),
    salePrice: form.salePrice.value.trim(),
    currency: 'CNY',
    stockType: 'unlimited',
    stockCount: null,
    sortOrder: 0,
    benefits: parseBenefits(form.benefits.value)
  };
  if (state.editingSku && state.editingSku.skuId) {
    await api(`/api/admin/skus/${state.editingSku.skuId}`, { method: 'PUT', body: payload });
    toast('SKU 已更新');
  } else {
    await api('/api/admin/skus', { method: 'POST', body: payload });
    toast('SKU 已创建');
  }
  state.editingSku = null;
  await loadConsole();
}

async function submitSceneForm(form) {
  const payload = {
    title: form.title.value.trim(),
    category: form.category.value,
    visibility: form.visibility.value || 'public',
    sceneType: form.sceneType.value || 'public',
    backgroundPath: form.backgroundPath.value.trim(),
    coverPath: form.coverPath.value.trim(),
    items: state.editingScene && state.editingScene.items ? state.editingScene.items : [],
    verbs: state.editingScene && state.editingScene.verbs ? state.editingScene.verbs : [],
    meta: state.editingScene && state.editingScene.meta ? state.editingScene.meta : {}
  };
  if (state.editingScene && state.editingScene.sceneId) {
    await api(`/api/admin/public-scenes/${state.editingScene.sceneId}`, { method: 'PUT', body: payload });
    toast('场景已更新');
  } else {
    await api('/api/admin/public-scenes', { method: 'POST', body: payload });
    toast('场景已创建');
  }
  state.editingScene = null;
  await loadConsole();
}

async function submitCategoryForm(form) {
  const payload = {
    categoryCode: form.categoryCode.value.trim(),
    name: form.name.value.trim(),
    description: form.description.value.trim(),
    status: form.status.value.trim() || 'active',
    sortOrder: Number(form.sortOrder.value || 0)
  };
  if (state.editingCategory && state.editingCategory.categoryId) {
    await api(`/api/admin/scene-categories/${state.editingCategory.categoryId}`, { method: 'PUT', body: payload });
    toast('分类已更新');
  } else {
    await api('/api/admin/scene-categories', { method: 'POST', body: payload });
    toast('分类已创建');
  }
  state.editingCategory = null;
  await loadConsole();
}

async function submitCollectionForm(form) {
  const payload = {
    collectionCode: form.collectionCode.value.trim(),
    name: form.name.value.trim(),
    description: form.description.value.trim(),
    status: form.status.value.trim() || 'active',
    coverUrl: form.coverUrl.value.trim(),
    sortOrder: Number(form.sortOrder.value || 0)
  };
  if (state.editingCollection && state.editingCollection.collectionId) {
    await api(`/api/admin/scene-collections/${state.editingCollection.collectionId}`, { method: 'PUT', body: payload });
    toast('合集已更新');
  } else {
    await api('/api/admin/scene-collections', { method: 'POST', body: payload });
    toast('合集已创建');
  }
  state.editingCollection = null;
  await loadConsole();
}

async function submitPublishForm(form) {
  const collectionIds = Array.from(form.querySelectorAll('input[name="collectionIds"]:checked')).map((input) => input.value);
  const sceneId = form.sceneId.value.trim();
  const payload = {
    title: form.title.value.trim(),
    visibility: form.visibility.value.trim() || 'public',
    categoryId: form.categoryId.value,
    collectionIds
  };
  await api(`/api/admin/generated-scenes/${sceneId}/publish`, { method: 'POST', body: payload });
  toast('草稿已发布到公开库');
  await loadConsole();
}

async function submitGeneratorForm() {
  if (!state.generatorFiles.length) {
    toast('请先选择至少一张图片', 'error');
    return;
  }
  const categoryId = (document.getElementById('gen-category') || {}).value || '';
  const publishVisibility = (document.getElementById('gen-visibility') || {}).value || 'public';
  const includeVerbs = ((document.getElementById('gen-include-verbs') || {}).value || 'true') === 'true';
  const autoPublish = !!(document.getElementById('gen-auto-publish') || {}).checked;
  const collectionIds = Array.from(panelBody.querySelectorAll('input[name="collectionIds"]:checked')).map((input) => input.value);

  const submitBtn = document.getElementById('gen-submit-btn');
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = '上传中...';
  }

  try {
    const items = [];
    for (const entry of state.generatorFiles) {
      const compressed = await compressImageFile(entry.file);
      const upload = await uploadAdminImage(compressed, compressed.name);
      items.push({ uploadId: upload.uploadId, title: '' });
    }

    const result = await api('/api/admin/tasks/scene-generate-batch', {
      method: 'POST',
      body: { items, includeVerbs, autoPublish, categoryId, collectionIds, publishVisibility }
    });
    toast(`已创建 ${result.list.length} 条生成任务`);
    state.generatorFiles = [];
    await loadConsole();
  } catch (error) {
    toast(error.message || '提交失败', 'error');
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = '压缩上传并开始生成';
    }
  }
}

async function handleAction(action, id) {
  if (action === 'gen-remove-file') {
    removeGeneratorFile(Number(event.target.dataset.index));
    return;
  }
  if (action === 'gen-submit') {
    await submitGeneratorForm();
    return;
  }
  if (action === 'user-detail') {
    state.selectedUser = await api(`/api/admin/users/${id}`);
    renderUsers();
    return;
  }
  if (action === 'user-close-detail') {
    state.selectedUser = null;
    renderUsers();
    return;
  }
  if (action === 'user-block') {
    await api(`/api/admin/users/${id}/block`, { method: 'POST' });
    await loadConsole();
    toast('用户已封禁');
    return;
  }
  if (action === 'user-unblock') {
    await api(`/api/admin/users/${id}/unblock`, { method: 'POST' });
    await loadConsole();
    toast('用户已解封');
    return;
  }
  if (action === 'user-grant-admin') {
    await api(`/api/admin/users/${id}/grant-admin`, { method: 'POST' });
    await loadConsole();
    toast('用户已提升为 Admin');
    return;
  }
  if (action === 'user-revoke-admin') {
    await api(`/api/admin/users/${id}/revoke-admin`, { method: 'POST' });
    await loadConsole();
    toast('用户已降为普通用户');
    return;
  }
  if (action === 'category-edit') {
    state.editingCategory = state.categories.find((item) => item.categoryId === id) || null;
    renderCurrentView();
    return;
  }
  if (action === 'category-cancel-edit') {
    state.editingCategory = null;
    renderCurrentView();
    return;
  }
  if (action === 'category-delete') {
    await api(`/api/admin/scene-categories/${id}`, { method: 'DELETE' });
    await loadConsole();
    toast('分类已删除');
    return;
  }
  if (action === 'collection-edit') {
    state.editingCollection = state.collections.find((item) => item.collectionId === id) || null;
    renderCurrentView();
    return;
  }
  if (action === 'collection-cancel-edit') {
    state.editingCollection = null;
    renderCurrentView();
    return;
  }
  if (action === 'collection-delete') {
    await api(`/api/admin/scene-collections/${id}`, { method: 'DELETE' });
    await loadConsole();
    toast('合集已删除');
    return;
  }
  if (action === 'draft-publish') {
    state.publishingDraft = state.generatedScenes.find((item) => item.sceneId === id) || null;
    renderCurrentView();
    return;
  }
  if (action === 'product-edit') {
    state.editingProduct = state.products.find((item) => item.productId === id) || null;
    renderCurrentView();
    return;
  }
  if (action === 'product-publish') {
    await api(`/api/admin/products/${id}/publish`, { method: 'POST' });
    await loadConsole();
    toast('商品已上架');
    return;
  }
  if (action === 'product-disable') {
    await api(`/api/admin/products/${id}/disable`, { method: 'POST' });
    await loadConsole();
    toast('商品已下架');
    return;
  }
  if (action === 'product-cancel-edit') {
    state.editingProduct = null;
    renderCurrentView();
    return;
  }
  if (action === 'sku-edit') {
    state.editingSku = state.skus.find((item) => item.skuId === id) || null;
    renderCurrentView();
    return;
  }
  if (action === 'sku-cancel-edit') {
    state.editingSku = null;
    renderCurrentView();
    return;
  }
  if (action === 'order-detail') {
    state.selectedOrder = await api(`/api/admin/orders/${id}`);
    renderCurrentView();
    return;
  }
  if (action === 'batch-delete-orders') {
    await batchDeleteOrders();
    return;
  }
  if (action === 'task-detail') {
    state.selectedTask = await api(`/api/admin/tasks/${id}`);
    renderCurrentView();
    return;
  }
  if (action === 'task-retry') {
    await api(`/api/admin/tasks/${id}/retry`, { method: 'POST' });
    await loadConsole();
    toast('任务已重新入队');
    return;
  }
  if (action === 'scene-edit') {
    state.editingScene = state.scenes.find((item) => item.sceneId === id) || null;
    openSceneModal();
    return;
  }
  if (action === 'scene-republish') {
    await api(`/api/admin/public-scenes/${id}/republish`, { method: 'POST' });
    await loadConsole();
    toast('公开场景已按源草稿重新覆盖发布');
    return;
  }
  if (action === 'generate-cdk') {
    try {
      await generateCdk();
    } catch (error) {
      toast(error.message || '生成卡密失败');
    }
    return;
  }
  if (action === 'filter-cdk') {
    const skuId = document.getElementById('cdk-sku-select').value;
    if (!skuId) { toast('请先选择 SKU'); return; }
    state.cdkFilterSkuId = skuId;
    try {
      const result = await api(`/api/admin/cdk-codes?sku_id=${encodeURIComponent(skuId)}`);
      state.cdkCodes = result.list || [];
      renderCdk();
    } catch (error) { toast(error.message || '筛选失败', 'error'); }
    return;
  }
  if (action === 'show-all-cdk') {
    state.cdkFilterSkuId = '';
    try {
      const result = await api('/api/admin/cdk-codes');
      state.cdkCodes = result.list || [];
      renderCdk();
    } catch (error) { toast(error.message || '加载失败', 'error'); }
    return;
  }
  if (action === 'cdk-copy') {
    const code = event.target.dataset.code || '';
    if (code) {
      try {
        await navigator.clipboard.writeText(code);
        toast('卡密已复制到剪贴板');
      } catch (_) {
        toast('复制失败，请手动复制');
      }
    }
    return;
  }
  if (action === 'view-log') {
    const filename = event.target.closest('[data-filename]').dataset.filename;
    try {
      const result = await api(`/api/admin/scene-logs/${encodeURIComponent(filename)}`);
      const area = document.getElementById('log-content-area');
      const content = document.getElementById('log-content');
      if (area && content) {
        content.textContent = result.content || '(empty)';
        area.style.display = 'block';
      }
    } catch (error) {
      toast(error.message || '加载日志失败', 'error');
    }
    return;
  }
  if (action === 'scene-cancel-edit') {
    state.editingScene = null;
    closeModal();
    renderCurrentView();
    return;
  }
  if (action === 'scene-open-create') {
    state.editingScene = null;
    openSceneModal();
    return;
  }
  if (action === 'storage-edit') {
    state.editingBackend = id;
    const configs = state.storageConfigs || {};
    const backends = configs.backends || {};
    const cfg = backends[id] || {};
    const formHtml = `
      <form id="storage-config-form">
        <input type="hidden" name="backend_id" value="${escapeHtml(id)}">
        <div class="field-grid">
          ${getStorageConfigFields(id, cfg)}
        </div>
        <div class="form-actions" style="display:flex;gap:10px;margin-top:18px">
          <button class="primary-btn compact" type="submit">保存配置</button>
          <button type="button" class="ghost-btn" data-action="storage-cancel-edit">取消</button>
        </div>
      </form>
    `;
    openModal(`配置 ${escapeHtml(cfg.name || id)}`, formHtml);
    return;
  }
  if (action === 'storage-cancel-edit') {
    state.editingBackend = null;
    closeModal();
    return;
  }
  if (action === 'storage-test') {
    state.testingBackend = id;
    renderStorage();
    try {
      const result = await api(`/api/admin/storage/test/${id}`, { method: 'POST' });
      toast(result.ok ? result.message : result.message, result.ok ? undefined : 'error');
    } catch (error) {
      toast(error.message || '测试失败', 'error');
    }
    state.testingBackend = null;
    await loadStorageData();
    renderStorage();
    return;
  }
  if (action === 'storage-test-activate') {
    state.testingBackend = id;
    renderStorage();
    try {
      const testResult = await api(`/api/admin/storage/test/${id}`, { method: 'POST' });
      if (!testResult.ok) {
        toast(testResult.message, 'error');
        state.testingBackend = null;
        await loadStorageData();
        renderStorage();
        return;
      }
      await api(`/api/admin/storage/activate/${id}`, { method: 'POST' });
      toast('已切换活跃存储后端');
    } catch (error) {
      toast(error.message || '切换失败', 'error');
    }
    state.testingBackend = null;
    await loadStorageData();
    renderStorage();
    return;
  }
  if (action === 'set-scene-view-card') {
    state.sceneViewMode = 'card';
    renderScenes();
    return;
  }
  if (action === 'set-scene-view-table') {
    state.sceneViewMode = 'table';
    renderScenes();
    return;
  }
  if (action === 'set-pscene-view-card') {
    state.privateSceneViewMode = 'card';
    renderPrivateScenes();
    return;
  }
  if (action === 'set-pscene-view-table') {
    state.privateSceneViewMode = 'table';
    renderPrivateScenes();
    return;
  }
  if (action === 'set-draft-view-card') {
    state.draftViewMode = 'card';
    renderDrafts();
    return;
  }
  if (action === 'set-draft-view-table') {
    state.draftViewMode = 'table';
    renderDrafts();
    return;
  }
  if (action === 'set-user-view-card') {
    state.userViewMode = 'card';
    renderUsers();
    return;
  }
  if (action === 'set-user-view-table') {
    state.userViewMode = 'table';
    renderUsers();
    return;
  }
  if (action === 'draft-close-publish') {
    state.publishingDraft = null;
    renderDrafts();
    return;
  }
  if (action === 'scene-batch-clear') {
    panelBody.querySelectorAll('.scene-checkbox').forEach((cb) => { cb.checked = false; });
    updateSceneBatchBar();
    return;
  }
  if (action === 'gen-batch-clear') {
    panelBody.querySelectorAll('.gen-task-checkbox').forEach((cb) => { cb.checked = false; });
    updateGeneratorBatchState();
    return;
  }
}

document.addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    if (event.target.id === 'product-form') {
      await submitProductForm(event.target);
      return;
    }
    if (event.target.id === 'sku-form') {
      await submitSkuForm(event.target);
      return;
    }
    if (event.target.id === 'category-form') {
      await submitCategoryForm(event.target);
      return;
    }
    if (event.target.id === 'collection-form') {
      await submitCollectionForm(event.target);
      return;
    }
    if (event.target.id === 'publish-form') {
      await submitPublishForm(event.target);
      return;
    }
    if (event.target.id === 'storage-config-form') {
      const form = event.target;
      const backendId = form.backend_id.value;
      const config = {};
      const enabledVal = form.querySelector('[name="enabled"]');
      const fields = form.querySelectorAll('input[name]:not([name="backend_id"]):not([name="enabled"]), select[name]:not([name="enabled"])');
      fields.forEach((input) => {
        config[input.name] = input.value;
      });
      const payload = { config };
      if (enabledVal) {
        payload.enabled = enabledVal.value === 'true';
      }
      await api(`/api/admin/storage/configs/${backendId}`, { method: 'PUT', body: payload });
      toast('配置已保存');
      state.editingBackend = null;
      closeModal();
      await loadStorageData();
      renderStorage();
      return;
    }
  } catch (error) {
    toast(error.message || '提交失败');
  }
});

panelBody.addEventListener('click', async (event) => {
  const action = event.target.dataset.action;
  const id = event.target.dataset.id;
  if (!action) {
    return;
  }
  try {
    await handleAction(action, id);
  } catch (error) {
    toast(error.message || '操作失败');
  }
});

panelBody.addEventListener('change', (event) => {
  if (event.target.classList.contains('order-checkbox')) {
    updateBatchDeleteState();
    return;
  }
  if (event.target.id === 'select-all-orders') {
    const checked = event.target.checked;
    panelBody.querySelectorAll('.order-checkbox').forEach((cb) => { cb.checked = checked; });
    updateBatchDeleteState();
    return;
  }
  if (event.target.classList.contains('task-checkbox')) {
    updateTaskBatchState();
    return;
  }
  if (event.target.id === 'select-all-tasks') {
    const checked = event.target.checked;
    panelBody.querySelectorAll('.task-checkbox').forEach((cb) => { cb.checked = checked; });
    updateTaskBatchState();
    return;
  }
  if (event.target.classList.contains('user-checkbox')) {
    updateUserBatchState();
    return;
  }
  if (event.target.id === 'select-all-users') {
    const checked = event.target.checked;
    panelBody.querySelectorAll('.user-checkbox').forEach((cb) => { cb.checked = checked; });
    updateUserBatchState();
    return;
  }
  if (event.target.classList.contains('scene-checkbox')) {
    updateSceneBatchState();
    return;
  }
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
  if (event.target.classList.contains('cdk-checkbox')) {
    updateCdkBatchState();
    return;
  }
  if (event.target.id === 'select-all-cdk') {
    const checked = event.target.checked;
    panelBody.querySelectorAll('.cdk-checkbox').forEach((cb) => { cb.checked = checked; });
    updateCdkBatchState();
    return;
  }
  if (event.target.classList.contains('pscene-checkbox')) {
    updatePrivateSceneBatchState();
    return;
  }
  if (event.target.id === 'select-all-pscenes') {
    const checked = event.target.checked;
    panelBody.querySelectorAll('.pscene-checkbox').forEach((cb) => { cb.checked = checked; });
    updatePrivateSceneBatchState();
    return;
  }
});

panelHead.addEventListener('click', async (event) => {
  const action = event.target.dataset.action;
  if (!action) return;

  if (action === 'batch-delete-orders') {
    try { await batchDeleteOrders(); } catch (error) { toast(error.message || '批量删除失败', 'error'); }
    return;
  }
  if (action === 'batch-delete-tasks') {
    try { await batchDeleteTasks(); } catch (error) { toast(error.message || '批量删除失败', 'error'); }
    return;
  }
  if (action === 'batch-delete-users') {
    try { await batchDeleteUsers(); } catch (error) { toast(error.message || '批量删除失败', 'error'); }
    return;
  }
  if (action === 'batch-delete-scenes') {
    try { await batchDeleteScenes(); } catch (error) { toast(error.message || '批量删除失败', 'error'); }
    return;
  }
  if (action === 'batch-delete-cdk') {
    try { await batchDeleteCdk(); } catch (error) { toast(error.message || '批量删除失败', 'error'); }
    return;
  }
  try {
    await handleAction(action, event.target.dataset.id);
  } catch (error) {
    toast(error.message || '操作失败');
  }
});

// Generator: drag/drop + file selection (delegated from panelBody)
panelBody.addEventListener('dragover', (event) => {
  const zone = document.getElementById('gen-drop-zone');
  if (zone && zone.contains(event.target)) {
    event.preventDefault();
    zone.classList.add('drag-over');
  }
});

panelBody.addEventListener('dragleave', (event) => {
  const zone = document.getElementById('gen-drop-zone');
  if (zone) {
    const related = event.relatedTarget;
    if (!zone.contains(related)) {
      zone.classList.remove('drag-over');
    }
  }
});

panelBody.addEventListener('drop', (event) => {
  const zone = document.getElementById('gen-drop-zone');
  if (zone && zone.contains(event.target)) {
    event.preventDefault();
    zone.classList.remove('drag-over');
    if (event.dataTransfer && event.dataTransfer.files.length) {
      addGeneratorFiles(event.dataTransfer.files);
    }
  }
});

panelBody.addEventListener('change', (event) => {
  if (event.target.id === 'gen-file-input') {
    if (event.target.files && event.target.files.length) {
      addGeneratorFiles(event.target.files);
      event.target.value = '';
    }
    return;
  }
  if (event.target.id === 'select-all-scenes') {
    const checked = event.target.checked;
    panelBody.querySelectorAll('.scene-checkbox').forEach((cb) => { cb.checked = checked; });
    updateSceneBatchState();
  }
});

// Scene search and filter (delegated from panelHead)
panelHead.addEventListener('input', (event) => {
  if (event.target.id === 'scene-search-input') {
    state.sceneSearchQuery = event.target.value;
    renderScenes();
    // Refocus and restore cursor position
    const input = document.getElementById('scene-search-input');
    if (input) {
      input.focus();
      input.setSelectionRange(input.value.length, input.value.length);
    }
  }
  if (event.target.id === 'private-scene-search-input') {
    state.privateSceneSearchQuery = event.target.value;
    renderPrivateScenes();
    const input = document.getElementById('private-scene-search-input');
    if (input) {
      input.focus();
      input.setSelectionRange(input.value.length, input.value.length);
    }
  }
  if (event.target.id === 'pscene-user-search-input') {
    const q = event.target.value.trim().toLowerCase();
    state.privateSceneUserSearch = event.target.value;
    const dropdown = document.getElementById('pscene-user-dropdown');
    if (!q) {
      if (dropdown) dropdown.style.display = 'none';
      return;
    }
    const matched = state.users.filter((u) => {
      const name = (u.displayName || '').toLowerCase();
      const mobile = (u.mobile || '').toLowerCase();
      const id = (u.id || '').toLowerCase();
      return name.includes(q) || mobile.includes(q) || id.includes(q);
    }).slice(0, 10);
    if (!dropdown) return;
    if (matched.length === 0) {
      dropdown.style.display = 'none';
      return;
    }
    const rect = event.target.getBoundingClientRect();
    dropdown.style.top = (rect.bottom + window.scrollY + 4) + 'px';
    dropdown.style.left = rect.left + 'px';
    dropdown.style.display = 'block';
    dropdown.innerHTML = matched.map((u) => `
      <div class="user-dropdown-item" data-action="pscene-select-owner" data-owner-id="${escapeHtml(u.id)}" style="padding:8px 12px;cursor:pointer;border-bottom:1px solid #f0f0f0;font-size:13px;">
        <strong>${escapeHtml(u.displayName || u.id)}</strong>
        ${u.mobileVerified ? `<span style="color:#888;margin-left:8px;">${escapeHtml(u.mobile)}</span>` : ''}
      </div>
    `).join('');
  }
});

panelHead.addEventListener('change', (event) => {
  if (event.target.id === 'scene-filter-category') {
    state.sceneFilterCategory = event.target.value;
    renderScenes();
    return;
  }
  if (event.target.id === 'scene-filter-visibility') {
    state.sceneFilterVisibility = event.target.value;
    renderScenes();
    return;
  }
  if (event.target.id === 'user-filter-mobile') {
    state.userFilterMobile = event.target.value;
    renderUsers();
    return;
  }
});

panelHead.addEventListener('input', (event) => {
  if (event.target.id === 'draft-search-input') {
    state.draftSearchQuery = event.target.value;
    renderDrafts();
    const input = document.getElementById('draft-search-input');
    if (input) {
      input.focus();
      input.setSelectionRange(input.value.length, input.value.length);
    }
  }
  if (event.target.id === 'user-search-input') {
    state.userSearchQuery = event.target.value;
    renderUsers();
    const input = document.getElementById('user-search-input');
    if (input) {
      input.focus();
      input.setSelectionRange(input.value.length, input.value.length);
    }
  }
});

// Global delegated events: modal, batch bar, close dropdowns
document.addEventListener('click', async (event) => {
  // Modal close button (×) — has no data-action, must check before early return
  if (event.target.id === 'modal-close') {
    state.editingScene = null;
    state.editingBackend = null;
    closeModal();
    return;
  }

  const action = event.target.dataset.action;
  if (!action) return;

  // Modal close/cancel buttons
  if (action === 'scene-cancel-edit' || action === 'storage-cancel-edit') {
    state.editingScene = null;
    state.editingBackend = null;
    closeModal();
    return;
  }

  // Batch bar actions
  if (action === 'scene-batch-clear') {
    panelBody.querySelectorAll('.scene-checkbox').forEach((cb) => { cb.checked = false; });
    updateSceneBatchBar();
    return;
  }
  if (action === 'scene-batch-execute') {
    const dropdown = document.getElementById('scene-batch-action');
    const selectedAction = dropdown ? dropdown.value : '';
    if (!selectedAction) { toast('请先选择操作', 'error'); return; }
    const ids = getSelectedSceneIds();
    if (ids.length === 0) return;

    if (selectedAction === 'delete') {
      if (!window.confirm(`确定要删除选中的 ${ids.length} 个场景吗？此操作不可恢复。`)) return;
      try { await batchDeleteScenes(); } catch (error) { toast(error.message || '批量删除失败', 'error'); }
    } else if (selectedAction.startsWith('visibility:')) {
      const visibility = selectedAction.split(':')[1];
      try { await batchSceneVisibility(visibility); } catch (error) { toast(error.message || '批量修改失败', 'error'); }
    } else if (selectedAction.startsWith('free:')) {
      const free = selectedAction.split(':')[1] === 'true';
      try { await batchSceneFree(free); } catch (error) { toast(error.message || '批量修改失败', 'error'); }
    } else if (selectedAction.startsWith('category:')) {
      const parts = selectedAction.split(':');
      const categoryId = parts[1];
      const categoryName = parts.slice(2).join(':');
      try { await batchSceneCategory(categoryId, categoryName); } catch (error) { toast(error.message || '批量移动失败', 'error'); }
    }
    return;
  }
  if (action === 'gen-batch-execute') {
    const dropdown = document.getElementById('gen-batch-action');
    const selectedAction = dropdown ? dropdown.value : '';
    if (!selectedAction) { toast('请先选择操作', 'error'); return; }
    const ids = Array.from(panelBody.querySelectorAll('.gen-task-checkbox:checked')).map((cb) => cb.value);
    if (ids.length === 0) return;

    if (selectedAction === 'delete') {
      if (!window.confirm(`确定要删除选中的 ${ids.length} 条任务吗？此操作不可恢复。`)) return;
      try {
        await api('/api/admin/tasks/batch-delete', { method: 'POST', body: { taskIds: ids } });
        toast(`成功删除 ${ids.length} 条任务`);
        await loadConsole();
      } catch (error) {
        toast(error.message || '批量删除失败', 'error');
      }
    } else if (selectedAction === 'retry') {
      if (!window.confirm(`确定要重试选中的 ${ids.length} 条失败任务吗？`)) return;
      let successCount = 0;
      for (const id of ids) {
        try {
          await api(`/api/admin/tasks/${id}/retry`, { method: 'POST' });
          successCount++;
        } catch (_) { /* skip individual failures */ }
      }
      toast(`已重新排队 ${successCount} 条任务`);
      await loadConsole();
    }
    return;
  }
  if (action === 'draft-batch-execute') {
    const dropdown = document.getElementById('draft-batch-action');
    const selectedAction = dropdown ? dropdown.value : '';
    if (!selectedAction) { toast('请先选择操作', 'error'); return; }
    const ids = getSelectedDraftIds();
    if (ids.length === 0) return;

    if (selectedAction === 'delete') {
      if (!window.confirm(`确定要删除选中的 ${ids.length} 个草稿场景吗？此操作不可恢复。`)) return;
      try {
        await api('/api/admin/public-scenes/batch-delete', { method: 'POST', body: { sceneIds: ids } });
        toast(`成功删除 ${ids.length} 个草稿`);
        state.publishingDraft = null;
        await loadConsole();
        renderDrafts();
      } catch (error) {
        toast(error.message || '批量删除失败', 'error');
      }
    } else if (selectedAction.startsWith('visibility:')) {
      const visibility = selectedAction.split(':')[1];
      if (!window.confirm(`确定要将选中的 ${ids.length} 个草稿设为「${visibility === 'private' ? '隐藏' : visibility}」吗？`)) return;
      try {
        await api('/api/admin/public-scenes/batch-visibility', { method: 'POST', body: { sceneIds: ids, visibility } });
        toast(`成功更新 ${ids.length} 个草稿`);
        await loadConsole();
        renderDrafts();
      } catch (error) {
        toast(error.message || '批量操作失败', 'error');
      }
    }
    return;
  }
  if (action === 'draft-batch-clear') {
    const selectAll = panelBody.querySelector('#select-all-drafts');
    if (selectAll) { selectAll.checked = false; selectAll.indeterminate = false; }
    panelBody.querySelectorAll('.draft-checkbox').forEach((cb) => { cb.checked = false; });
    updateDraftBatchState();
    return;
  }
  if (action === 'pscene-batch-execute') {
    const dropdown = document.getElementById('pscene-batch-action');
    const selectedAction = dropdown ? dropdown.value : '';
    if (!selectedAction) { toast('请先选择操作', 'error'); return; }
    const ids = getSelectedPrivateSceneIds();
    if (ids.length === 0) return;

    if (selectedAction === 'delete') {
      if (!window.confirm(`确定要删除选中的 ${ids.length} 个私人场景吗？此操作不可恢复。`)) return;
      try {
        await api('/api/admin/public-scenes/batch-delete', { method: 'POST', body: { sceneIds: ids } });
        toast(`成功删除 ${ids.length} 个场景`);
        await loadConsole();
        renderPrivateScenes();
      } catch (error) {
        toast(error.message || '批量删除失败', 'error');
      }
    } else if (selectedAction.startsWith('visibility:')) {
      const visibility = selectedAction.split(':')[1];
      if (!window.confirm(`确定要设为「${visibility === 'private' ? '隐藏' : visibility}」吗？`)) return;
      try {
        await api('/api/admin/public-scenes/batch-visibility', { method: 'POST', body: { sceneIds: ids, visibility } });
        toast(`成功更新 ${ids.length} 个场景`);
        await loadConsole();
        renderPrivateScenes();
      } catch (error) {
        toast(error.message || '批量操作失败', 'error');
      }
    }
    return;
  }
  if (action === 'pscene-batch-clear') {
    const selectAll = panelBody.querySelector('#select-all-pscenes');
    if (selectAll) { selectAll.checked = false; selectAll.indeterminate = false; }
    panelBody.querySelectorAll('.pscene-checkbox').forEach((cb) => { cb.checked = false; });
    updatePrivateSceneBatchBar();
    return;
  }
  if (action === 'pscene-clear-owner') {
    state.privateSceneSelectedOwnerId = '';
    state.privateSceneUserSearch = '';
    renderPrivateScenes();
    return;
  }
  if (action === 'pscene-select-owner') {
    const ownerId = event.target.dataset.ownerId;
    state.privateSceneSelectedOwnerId = ownerId;
    state.privateSceneUserSearch = resolveOwnerName(ownerId);
    const dropdown = document.getElementById('pscene-user-dropdown');
    if (dropdown) dropdown.style.display = 'none';
    renderPrivateScenes();
    return;
  }
});

// Dropdown change toggles execute button
document.addEventListener('change', (event) => {
  if (event.target.id === 'gen-batch-action') {
    const executeBtn = document.getElementById('gen-batch-execute');
    if (executeBtn) executeBtn.disabled = !event.target.value;
  }
  if (event.target.id === 'scene-batch-action') {
    const executeBtn = document.getElementById('scene-batch-execute');
    if (executeBtn) executeBtn.disabled = !event.target.value;
  }
  if (event.target.id === 'draft-batch-action') {
    const executeBtn = document.getElementById('draft-batch-execute');
    if (executeBtn) executeBtn.disabled = !event.target.value;
  }
  if (event.target.id === 'pscene-batch-action') {
    const executeBtn = document.getElementById('pscene-batch-execute');
    if (executeBtn) executeBtn.disabled = !event.target.value;
  }
  // Draft checkboxes
  if (event.target.classList.contains('draft-checkbox')) {
    updateDraftBatchState();
  }
  if (event.target.id === 'select-all-drafts') {
    const checked = event.target.checked;
    panelBody.querySelectorAll('.draft-checkbox').forEach((cb) => { cb.checked = checked; });
    updateDraftBatchState();
  }
});

// Modal overlay backdrop click to close
const modalOverlay = document.getElementById('modal-overlay');
if (modalOverlay) {
  modalOverlay.addEventListener('click', (event) => {
    if (event.target === modalOverlay) {
      state.editingScene = null;
      closeModal();
    }
  });

  // Handle scene form submit inside modal
  document.getElementById('modal-body').addEventListener('submit', async (event) => {
    if (event.target.id === 'scene-form') {
      event.preventDefault();
      try {
        await submitSceneForm(event.target);
        closeModal();
      } catch (error) {
        toast(error.message || '提交失败', 'error');
      }
    }
  });

  // Handle cancel button click inside modal
  document.getElementById('modal-body').addEventListener('click', (event) => {
    const action = event.target.dataset.action;
    if (action === 'scene-cancel-edit' || action === 'storage-cancel-edit') {
      state.editingScene = null;
      state.editingBackend = null;
      closeModal();
    }
  });
}

loginForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  loginError.textContent = '';
  try {
    const payload = await api('/api/admin/auth/login', {
      method: 'POST',
      body: {
        username: document.getElementById('username').value.trim(),
        password: document.getElementById('password').value
      }
    });
    setLoggedIn(payload.accessToken, payload.admin);
    await loadConsole();
  } catch (error) {
    loginError.textContent = error.message;
  }
});

logoutBtn.addEventListener('click', () => {
  setLoggedIn('', null);
  state.overview = null;
  state.users = [];
  state.products = [];
  state.skus = [];
  state.orders = [];
  state.tasks = [];
  state.cdkCodes = [];
  state.categories = [];
  state.collections = [];
  state.generatedScenes = [];
  state.scenes = [];
  state.selectedUser = null;
  state.selectedOrder = null;
  state.selectedTask = null;
  state.editingProduct = null;
  state.editingSku = null;
  state.editingScene = null;
  state.editingCategory = null;
  state.editingCollection = null;
  state.publishingDraft = null;
  state.sceneSearchQuery = '';
  state.sceneFilterCategory = '';
  state.sceneFilterVisibility = '';
  state.generatorFiles = [];
  const bar = document.getElementById('scene-batch-bar');
  if (bar) bar.remove();
  const genBarLogout = document.getElementById('gen-batch-bar');
  if (genBarLogout) genBarLogout.remove();
});

refreshBtn.addEventListener('click', async () => {
  try {
    await loadConsole();
    toast('后台数据已刷新');
  } catch (error) {
    toast(error.message || '刷新失败');
  }
});

navItems.forEach((button) => {
  button.addEventListener('click', () => {
    state.currentView = button.dataset.view;
    renderCurrentView();
  });
});

if (state.token) {
  loadConsole().catch(() => {
    setLoggedIn('', null);
  });
}

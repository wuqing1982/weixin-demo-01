const state = {
  token: window.localStorage.getItem('admin_access_token') || '',
  currentView: 'users',
  currentAdmin: null,
  overview: null,
  users: [],
  products: [],
  skus: [],
  orders: [],
  tasks: [],
  scenes: [],
  selectedUser: null,
  selectedOrder: null,
  selectedTask: null,
  editingProduct: null,
  editingSku: null,
  editingScene: null
};

const loginForm = document.getElementById('login-form');
const loginError = document.getElementById('login-error');
const consoleRoot = document.getElementById('console');
const adminName = document.getElementById('admin-name');
const overviewCards = document.getElementById('overview-cards');
const panelHead = document.getElementById('panel-head');
const panelBody = document.getElementById('panel-body');
const logoutBtn = document.getElementById('logout-btn');
const refreshBtn = document.getElementById('refresh-btn');
const tabButtons = Array.from(document.querySelectorAll('.tab-btn'));

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
  consoleRoot.hidden = !state.token;
  loginForm.hidden = !!state.token;
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

function toast(message) {
  window.alert(message);
}

function metricCard(label, value) {
  return `
    <article class="metric-card">
      <div class="metric-label">${escapeHtml(label)}</div>
      <div class="metric-value">${escapeHtml(value)}</div>
    </article>
  `;
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

function renderUsers() {
  const detail = state.selectedUser ? `
    <article class="detail-card">
      <div class="detail-head">
        <div>
          <h4>${escapeHtml(state.selectedUser.displayName || state.selectedUser.id)}</h4>
          <p>${escapeHtml(state.selectedUser.id)}</p>
        </div>
        <span class="meta-chip">${escapeHtml(state.selectedUser.status || 'active')}</span>
      </div>
      <div class="detail-grid">
        <div><span>角色</span><strong>${escapeHtml(state.selectedUser.role || 'user')}</strong></div>
        <div><span>手机号</span><strong>${escapeHtml(state.selectedUser.mobile || '-')}</strong></div>
        <div><span>会员</span><strong>${state.selectedUser.memberSummary && state.selectedUser.memberSummary.isActive ? '已开通' : '未开通'}</strong></div>
        <div><span>点数</span><strong>${escapeHtml((state.selectedUser.creditSummary && state.selectedUser.creditSummary.sceneGenerateBalance) || 0)}</strong></div>
        <div><span>注册时间</span><strong>${escapeHtml(state.selectedUser.createdAt || '-')}</strong></div>
      </div>
      <div class="detail-subsection">
        <h5>订单</h5>
        <p>${(state.selectedUser.orders || []).map((item) => `${item.orderNo} / ${item.status}`).join('，') || '暂无'}</p>
      </div>
      <div class="detail-subsection">
        <h5>权益</h5>
        <p>${(state.selectedUser.entitlements || []).map((item) => item.entitlementCode).join('，') || '暂无'}</p>
      </div>
    </article>
  ` : '';

  panelHead.innerHTML = `
    <div>
      <h3 class="panel-title">用户管理</h3>
      <p class="panel-subtitle">支持查看详情、封禁与解封。</p>
    </div>
    <span class="meta-chip">${state.users.length} 位用户</span>
  `;

  panelBody.innerHTML = `
    ${detail}
    <div class="table">
      <div class="table-head">
        <strong>用户</strong>
        <span>角色</span>
        <span>会员</span>
        <span>点数</span>
        <span>状态</span>
        <span>操作</span>
      </div>
      ${state.users.map((user) => `
        <div class="table-row">
          <strong>${escapeHtml(user.displayName || user.id)}<br><small>${escapeHtml(user.id)}</small></strong>
          <span>${escapeHtml(user.role || 'user')}</span>
          <span>${user.memberSummary && user.memberSummary.isActive ? '已开通' : '未开通'}</span>
          <span>${escapeHtml((user.creditSummary && user.creditSummary.sceneGenerateBalance) || 0)}</span>
          <span>${escapeHtml(user.status || 'active')}</span>
          <span class="action-group">
            <button class="mini-btn" data-action="user-detail" data-id="${escapeHtml(user.id)}">详情</button>
            ${user.isAdmin
              ? `<button class="mini-btn" data-action="user-revoke-admin" data-id="${escapeHtml(user.id)}">撤销 Admin</button>`
              : `<button class="mini-btn success-btn" data-action="user-grant-admin" data-id="${escapeHtml(user.id)}">设为 Admin</button>`}
            ${user.status === 'blocked'
              ? `<button class="mini-btn success-btn" data-action="user-unblock" data-id="${escapeHtml(user.id)}">解封</button>`
              : `<button class="mini-btn danger-btn" data-action="user-block" data-id="${escapeHtml(user.id)}">封禁</button>`}
          </span>
        </div>
      `).join('')}
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
    <span class="meta-chip">${state.orders.length} 笔订单</span>
  `;

  panelBody.innerHTML = `
    ${detail}
    <div class="table">
      <div class="table-head">
        <strong>订单号</strong>
        <span>用户</span>
        <span>金额</span>
        <span>状态</span>
        <span>操作</span>
      </div>
      ${state.orders.map((order) => `
        <div class="table-row">
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
    <span class="meta-chip">${state.tasks.length} 条任务</span>
  `;

  panelBody.innerHTML = `
    ${detail}
    <div class="table">
      <div class="table-head">
        <strong>任务</strong>
        <span>归属用户</span>
        <span>进度</span>
        <span>状态</span>
        <span>操作</span>
      </div>
      ${state.tasks.map((task) => `
        <div class="table-row">
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

function renderScenes() {
  const scene = state.editingScene || {};
  panelHead.innerHTML = `
    <div>
      <h3 class="panel-title">公共场景管理</h3>
      <p class="panel-subtitle">支持新增和编辑公共场景元数据，便于内容运营。</p>
    </div>
    <span class="meta-chip">${state.scenes.length} 个场景</span>
  `;

  panelBody.innerHTML = `
    <form id="scene-form" class="editor-card">
      <div class="editor-title-row">
        <h4>${scene.sceneId ? '编辑场景' : '新建场景'}</h4>
        ${scene.sceneId ? '<button type="button" class="mini-btn" data-action="scene-cancel-edit">取消</button>' : ''}
      </div>
      <div class="field-grid">
        <label><span>标题</span><input name="title" value="${escapeHtml(scene.title || '')}" required></label>
        <label><span>分类</span><input name="category" value="${escapeHtml(scene.category || '')}"></label>
        <label><span>可见性</span><input name="visibility" value="${escapeHtml(scene.visibility || 'public')}"></label>
        <label><span>场景类型</span><input name="sceneType" value="${escapeHtml(scene.sceneType || 'public')}"></label>
        <label class="full"><span>背景图路径</span><input name="backgroundPath" value="${escapeHtml(scene.backgroundPath || '')}"></label>
        <label class="full"><span>封面图路径</span><input name="coverPath" value="${escapeHtml(scene.coverPath || '')}"></label>
      </div>
      <div class="form-actions">
        <button class="primary-btn compact" type="submit">${scene.sceneId ? '保存场景' : '创建场景'}</button>
      </div>
    </form>

    <div class="table">
      <div class="table-head">
        <strong>场景</strong>
        <span>分类</span>
        <span>热点数</span>
        <span>可见性</span>
        <span>操作</span>
      </div>
      ${state.scenes.map((item) => `
        <div class="table-row">
          <strong>${escapeHtml(item.title)}<br><small>${escapeHtml(item.sceneId)}</small></strong>
          <span>${escapeHtml(item.category || '-')}</span>
          <span>${escapeHtml(item.itemCount || 0)} / ${escapeHtml(item.verbCount || 0)}</span>
          <span>${escapeHtml(item.visibility || 'public')}</span>
          <span class="action-group"><button class="mini-btn" data-action="scene-edit" data-id="${escapeHtml(item.sceneId)}">编辑</button></span>
        </div>
      `).join('')}
    </div>
  `;
}

function renderCurrentView() {
  tabButtons.forEach((button) => {
    button.classList.toggle('active', button.dataset.view === state.currentView);
  });

  if (state.currentView === 'products') {
    renderProducts();
    return;
  }
  if (state.currentView === 'orders') {
    renderOrders();
    return;
  }
  if (state.currentView === 'tasks') {
    renderTasks();
    return;
  }
  if (state.currentView === 'scenes') {
    renderScenes();
    return;
  }
  renderUsers();
}

async function loadConsole() {
  const [admin, overview, users, products, skus, orders, tasks, scenes] = await Promise.all([
    api('/api/admin/auth/me'),
    api('/api/admin/overview'),
    api('/api/admin/users'),
    api('/api/admin/products'),
    api('/api/admin/skus'),
    api('/api/admin/orders'),
    api('/api/admin/tasks'),
    api('/api/admin/public-scenes')
  ]);

  setLoggedIn(state.token, admin);
  state.overview = overview;
  state.users = users.list || [];
  state.products = products.list || [];
  state.skus = skus.list || [];
  state.orders = orders.list || [];
  state.tasks = tasks.list || [];
  state.scenes = scenes.list || [];
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
    category: form.category.value.trim(),
    visibility: form.visibility.value.trim() || 'public',
    sceneType: form.sceneType.value.trim() || 'public',
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

async function handleAction(action, id) {
  if (action === 'user-detail') {
    state.selectedUser = await api(`/api/admin/users/${id}`);
    renderCurrentView();
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
    renderCurrentView();
    return;
  }
  if (action === 'scene-cancel-edit') {
    state.editingScene = null;
    renderCurrentView();
  }
}

panelBody.addEventListener('submit', async (event) => {
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
    if (event.target.id === 'scene-form') {
      await submitSceneForm(event.target);
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
  state.scenes = [];
  state.selectedUser = null;
  state.selectedOrder = null;
  state.selectedTask = null;
  state.editingProduct = null;
  state.editingSku = null;
  state.editingScene = null;
});

refreshBtn.addEventListener('click', async () => {
  try {
    await loadConsole();
    toast('后台数据已刷新');
  } catch (error) {
    toast(error.message || '刷新失败');
  }
});

tabButtons.forEach((button) => {
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

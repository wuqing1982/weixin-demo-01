const { updateNavBar } = require('../../shared/theme-helper');
const { getMyScenes, getSceneCategories, batchDeleteMyScenes } = require('../../services/scene');
const { request } = require('../../services/api');

Page({
  data: {
    theme: 'dark',
    loading: true,
    scenes: [],
    errorMessage: '',
    page: 1,
    pageSize: 20,
    totalCount: 0,
    totalPages: 1,
    pageNumbers: [1],
    hasMore: true,
    loadingMore: false,
    viewMode: 'grid',
    selectedCategoryId: '',
    categories: [],
    // Edit mode
    editMode: false,
    selectedIds: [],
    selectAllChecked: false,
    deleting: false
  },

  onShow() {
    const theme = getApp().globalData.theme;
    this.setData({ theme });
    updateNavBar(theme);
    this.loadConfig();
  },

  onPullDownRefresh() {
    this.setData({ page: 1, hasMore: true, editMode: false, selectedIds: [], selectAllChecked: false });
    this.loadScenes().finally(() => {
      wx.stopPullDownRefresh();
    });
  },

  onToggleViewMode() {
    const next = this.data.viewMode === 'grid' ? 'list' : 'grid';
    this.setData({ viewMode: next });
  },

  onSelectCategory(event) {
    const { categoryId } = event.currentTarget.dataset;
    const nextCategoryId = categoryId === this.data.selectedCategoryId ? '' : (categoryId || '');
    this.setData({ selectedCategoryId: nextCategoryId, editMode: false, selectedIds: [], selectAllChecked: false });
    this.loadScenes();
  },

  onReachBottom() {
    if (!this.data.hasMore || this.data.loadingMore) {
      return;
    }
    this.loadMoreScenes();
  },

  // ---- Edit mode ----

  onEnterEditMode() {
    this.setData({
      editMode: true,
      selectedIds: [],
      selectAllChecked: false
    });
    // Clear any stale _selected flags
    const scenes = this.data.scenes.map(s => ({ ...s, _selected: false }));
    this.setData({ scenes });
  },

  onExitEditMode() {
    const scenes = this.data.scenes.map(s => {
      const { _selected, ...rest } = s;
      return rest;
    });
    this.setData({ editMode: false, selectedIds: [], selectAllChecked: false, scenes });
  },

  onToggleSelect(e) {
    const { sceneId, index } = e.currentTarget.dataset;
    const scenes = this.data.scenes;
    const selected = !scenes[index]._selected;
    scenes[index]._selected = selected;

    let selectedIds = this.data.selectedIds.slice();
    if (selected) {
      if (!selectedIds.includes(sceneId)) {
        selectedIds.push(sceneId);
      }
    } else {
      selectedIds = selectedIds.filter(id => id !== sceneId);
    }

    const selectAllChecked = selectedIds.length === scenes.length && scenes.length > 0;
    this.setData({ scenes, selectedIds, selectAllChecked });
  },

  onToggleSelectAll() {
    const scenes = this.data.scenes;
    const selectAllChecked = !this.data.selectAllChecked;
    const selectedIds = [];

    for (let i = 0; i < scenes.length; i++) {
      scenes[i]._selected = selectAllChecked;
      if (selectAllChecked) {
        selectedIds.push(scenes[i].sceneId);
      }
    }

    this.setData({ scenes, selectedIds, selectAllChecked });
  },

  onDeleteSelected() {
    const count = this.data.selectedIds.length;
    if (count === 0 || this.data.deleting) return;

    wx.showModal({
      title: '确认删除',
      content: `确定要删除选中的 ${count} 个场景吗？此操作不可撤销。`,
      confirmText: '删除',
      confirmColor: '#fa5151',
      success: (res) => {
        if (res.confirm) {
          this.doDelete();
        }
      }
    });
  },

  async doDelete() {
    this.setData({ deleting: true });
    wx.showLoading({ title: '删除中...', mask: true });

    try {
      const result = await batchDeleteMyScenes(this.data.selectedIds);
      wx.hideLoading();
      wx.showToast({ title: `已删除 ${result.count || this.data.selectedIds.length} 个场景`, icon: 'success' });
      this.setData({ editMode: false, selectedIds: [], selectAllChecked: false, deleting: false });
      this.loadScenes();
    } catch (error) {
      wx.hideLoading();
      this.setData({ deleting: false });
      wx.showToast({ title: error.message || '删除失败', icon: 'none' });
    }
  },

  // ---- Data loading ----

  async loadConfig() {
    try {
      const res = await request({ url: '/config' });
      const pageSize = res.scenePageSize || 20;
      this.setData({ pageSize });
    } catch (e) {
      // use default pageSize
    }
    this.loadScenes();
  },

  async loadScenes() {
    this.setData({
      loading: true,
      errorMessage: '',
      page: 1,
      hasMore: true
    });

    try {
      const params = {
        page: 1,
        pageSize: this.data.pageSize
      };
      if (this.data.selectedCategoryId) {
        params.categoryId = this.data.selectedCategoryId;
      }

      const [data, categoriesData] = await Promise.all([
        getMyScenes(params),
        this.data.categories.length ? Promise.resolve(null) : getSceneCategories()
      ]);

      const list = (data.list || []).map(s => ({ ...s, _selected: false }));
      const totalCount = data.total || 0;
      const totalPages = Math.ceil(totalCount / this.data.pageSize) || 1;
      const updates = {
        loading: false,
        scenes: list,
        totalCount,
        totalPages,
        pageNumbers: this.calcPageNumbers(1, totalPages),
        hasMore: 1 < totalPages
      };
      if (categoriesData && categoriesData.list) {
        updates.categories = categoriesData.list;
      }
      this.setData(updates);
    } catch (error) {
      this.setData({
        loading: false,
        errorMessage: error.message || '我的场景加载失败'
      });
    }
  },

  async loadMoreScenes() {
    const nextPage = this.data.page + 1;
    this.setData({ loadingMore: true });

    try {
      const params = {
        page: nextPage,
        pageSize: this.data.pageSize
      };
      if (this.data.selectedCategoryId) {
        params.categoryId = this.data.selectedCategoryId;
      }
      const data = await getMyScenes(params);

      const newList = (data.list || []).map(s => ({ ...s, _selected: false }));
      const totalCount = data.total || 0;
      const totalPages = Math.ceil(totalCount / this.data.pageSize) || 1;
      this.setData({
        scenes: this.data.scenes.concat(newList),
        page: nextPage,
        totalCount,
        totalPages,
        pageNumbers: this.calcPageNumbers(nextPage, totalPages),
        hasMore: nextPage < totalPages,
        loadingMore: false
      });
    } catch (error) {
      this.setData({ loadingMore: false });
      wx.showToast({ title: '加载失败', icon: 'none' });
    }
  },

  onGoToPage(e) {
    const { page } = e.currentTarget.dataset;
    if (page < 1 || page > this.data.totalPages || page === this.data.page) return;
    this.setData({
      page,
      scenes: [],
      hasMore: true,
      loading: true,
      editMode: false,
      selectedIds: [],
      selectAllChecked: false
    });
    this.loadPage(page);
  },

  async loadPage(page) {
    this.setData({ loading: true, errorMessage: '' });
    try {
      const params = {
        page,
        pageSize: this.data.pageSize
      };
      if (this.data.selectedCategoryId) {
        params.categoryId = this.data.selectedCategoryId;
      }
      const data = await getMyScenes(params);
      const list = (data.list || []).map(s => ({ ...s, _selected: false }));
      const totalCount = data.total || 0;
      const totalPages = Math.ceil(totalCount / this.data.pageSize) || 1;
      this.setData({
        scenes: list,
        page,
        totalCount,
        totalPages,
        pageNumbers: this.calcPageNumbers(page, totalPages),
        hasMore: page < totalPages,
        loading: false
      });
    } catch (error) {
      this.setData({
        loading: false,
        errorMessage: error.message || '我的场景加载失败'
      });
    }
  },

  calcPageNumbers(current, total) {
    if (total <= 5) {
      return Array.from({ length: total }, function (_, i) { return i + 1; });
    }
    var start = Math.max(1, current - 2);
    var end = start + 4;
    if (end > total) {
      end = total;
      start = Math.max(1, end - 4);
    }
    return Array.from({ length: end - start + 1 }, function (_, i) { return start + i; });
  },

  onOpenScene(event) {
    if (this.data.editMode) return;
    const { sceneId } = event.currentTarget.dataset;
    wx.navigateTo({
      url: `/pages/scene_runtime/index?sceneId=${sceneId}`
    });
  },

  onOpenCreate() {
    wx.navigateTo({
      url: '/pages/create_scene/index'
    });
  },

  onShareAppMessage() {
    return {
      title: '全景英语场景 — 我生成的英语学习场景',
      path: '/pages/home/index'
    };
  },

  onShareTimeline() {
    return {
      title: '全景英语场景 — 我生成的英语学习场景'
    };
  }
});

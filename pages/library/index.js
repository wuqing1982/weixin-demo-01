const { updateNavBar } = require('../../shared/theme-helper');
const { getSceneList, getSceneCategories, getSceneCollections } = require('../../services/scene');
const { request } = require('../../services/api');

Page({
  data: {
    theme: 'dark',
    loading: true,
    scenes: [],
    categories: [],
    collections: [],
    selectedCategoryId: '',
    selectedCollectionId: '',
    errorMessage: '',
    page: 1,
    pageSize: 20,
    totalCount: 0,
    totalPages: 1,
    pageNumbers: [1],
    hasMore: true,
    loadingMore: false,
    viewMode: 'grid'
  },

  onShow() {
    const theme = getApp().globalData.theme;
    this.setData({ theme });
    updateNavBar(theme);
    this.loadConfig();
  },

  onPullDownRefresh() {
    this.setData({ page: 1, hasMore: true });
    this.loadScenes().finally(() => {
      wx.stopPullDownRefresh();
    });
  },

  onToggleViewMode() {
    const next = this.data.viewMode === 'grid' ? 'list' : 'grid';
    this.setData({ viewMode: next });
  },

  onReachBottom() {
    if (!this.data.hasMore || this.data.loadingMore) {
      return;
    }
    this.loadMoreScenes();
  },

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
      const [publicData, categoriesData, collectionsData] = await Promise.all([
        getSceneList({
          type: 'public',
          categoryId: this.data.selectedCategoryId,
          collectionId: this.data.selectedCollectionId,
          page: 1,
          pageSize: this.data.pageSize
        }),
        getSceneCategories(),
        getSceneCollections()
      ]);

      const list = publicData.list || [];
      const totalCount = publicData.total || 0;
      const totalPages = Math.ceil(totalCount / this.data.pageSize) || 1;
      this.setData({
        scenes: list,
        categories: categoriesData.list || [],
        collections: collectionsData.list || [],
        totalCount,
        totalPages,
        pageNumbers: this.calcPageNumbers(1, totalPages),
        hasMore: 1 < totalPages,
        loading: false
      });
    } catch (error) {
      this.setData({
        loading: false,
        errorMessage: error.message || '场景列表加载失败'
      });
    }
  },

  async loadMoreScenes() {
    const nextPage = this.data.page + 1;
    this.setData({ loadingMore: true });

    try {
      const publicData = await getSceneList({
        type: 'public',
        categoryId: this.data.selectedCategoryId,
        collectionId: this.data.selectedCollectionId,
        page: nextPage,
        pageSize: this.data.pageSize
      });

      const newList = publicData.list || [];
      const totalCount = publicData.total || 0;
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
      loading: true
    });
    this.loadPage(page);
  },

  async loadPage(page) {
    this.setData({ loading: true, errorMessage: '' });
    try {
      const publicData = await getSceneList({
        type: 'public',
        categoryId: this.data.selectedCategoryId,
        collectionId: this.data.selectedCollectionId,
        page,
        pageSize: this.data.pageSize
      });
      const list = publicData.list || [];
      const totalCount = publicData.total || 0;
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
        errorMessage: error.message || '场景列表加载失败'
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

  onSelectCategory(event) {
    const { categoryId } = event.currentTarget.dataset;
    const nextCategoryId = categoryId === this.data.selectedCategoryId ? '' : (categoryId || '');
    this.setData({
      selectedCategoryId: nextCategoryId
    });
    this.loadScenes();
  },

  onSelectCollection(event) {
    const { collectionId } = event.currentTarget.dataset;
    const nextCollectionId = collectionId === this.data.selectedCollectionId ? '' : (collectionId || '');
    this.setData({
      selectedCollectionId: nextCollectionId
    });
    this.loadScenes();
  }
});

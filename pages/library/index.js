const { updateNavBar } = require('../../shared/theme-helper');
const { getSceneList, getSceneCategories, getSceneCollections } = require('../../services/scene');

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
    hasMore: true,
    loadingMore: false,
    viewMode: 'grid',
    maxPages: 5
  },

  onShow() {
    const theme = getApp().globalData.theme;
    this.setData({ theme });
    updateNavBar(theme);
    this.loadScenes();
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
      this.setData({
        scenes: list,
        categories: categoriesData.list || [],
        collections: collectionsData.list || [],
        hasMore: list.length >= this.data.pageSize,
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
    if (this.data.page >= this.data.maxPages) {
      this.setData({ hasMore: false });
      return;
    }
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
      this.setData({
        scenes: this.data.scenes.concat(newList),
        page: nextPage,
        hasMore: newList.length >= this.data.pageSize,
        loadingMore: false
      });
    } catch (error) {
      this.setData({ loadingMore: false });
      wx.showToast({ title: '加载失败', icon: 'none' });
    }
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

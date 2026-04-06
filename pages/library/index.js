const { getMyScenes, getSceneList, getSceneCategories, getSceneCollections } = require('../../services/scene');

Page({
  data: {
    loading: true,
    scenes: [],
    myScenes: [],
    categories: [],
    collections: [],
    selectedCategoryId: '',
    selectedCollectionId: '',
    errorMessage: '',
    page: 1,
    pageSize: 20,
    hasMore: true,
    loadingMore: false
  },

  onShow() {
    this.loadScenes();
  },

  onPullDownRefresh() {
    this.setData({ page: 1, hasMore: true });
    this.loadScenes().finally(() => {
      wx.stopPullDownRefresh();
    });
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
      const [publicData, myData, categoriesData, collectionsData] = await Promise.all([
        getSceneList({
          type: 'public',
          categoryId: this.data.selectedCategoryId,
          collectionId: this.data.selectedCollectionId,
          page: 1,
          pageSize: this.data.pageSize
        }),
        getMyScenes({
          page: 1,
          pageSize: 20
        }),
        getSceneCategories(),
        getSceneCollections()
      ]);

      const list = publicData.list || [];
      this.setData({
        scenes: list,
        myScenes: myData.list || [],
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

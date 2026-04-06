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
    errorMessage: ''
  },

  onShow() {
    this.loadScenes();
  },

  async loadScenes() {
    this.setData({
      loading: true,
      errorMessage: ''
    });

    try {
      const [publicData, myData, categoriesData, collectionsData] = await Promise.all([
        getSceneList({
          type: 'public',
          categoryId: this.data.selectedCategoryId,
          collectionId: this.data.selectedCollectionId,
          page: 1,
          pageSize: 20
        }),
        getMyScenes({
          page: 1,
          pageSize: 20
        }),
        getSceneCategories(),
        getSceneCollections()
      ]);

      this.setData({
        scenes: publicData.list || [],
        myScenes: myData.list || [],
        categories: categoriesData.list || [],
        collections: collectionsData.list || [],
        loading: false
      });
    } catch (error) {
      this.setData({
        loading: false,
        errorMessage: error.message || '场景列表加载失败'
      });
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

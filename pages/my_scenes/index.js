const { getMyScenes } = require('../../services/scene');

Page({
  data: {
    loading: true,
    scenes: [],
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
      const data = await getMyScenes({
        page: 1,
        pageSize: this.data.pageSize
      });

      const list = data.list || [];
      this.setData({
        loading: false,
        scenes: list,
        hasMore: list.length >= this.data.pageSize
      });
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
      const data = await getMyScenes({
        page: nextPage,
        pageSize: this.data.pageSize
      });

      const newList = data.list || [];
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
  }
});

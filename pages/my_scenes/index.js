const { getMyScenes } = require('../../services/scene');

Page({
  data: {
    loading: true,
    scenes: [],
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
      const data = await getMyScenes({
        page: 1,
        pageSize: 50
      });

      this.setData({
        loading: false,
        scenes: data.list || []
      });
    } catch (error) {
      this.setData({
        loading: false,
        errorMessage: error.message || '我的场景加载失败'
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
  }
});

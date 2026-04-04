const { getSceneList } = require('../../services/scene');

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
      const data = await getSceneList({
        type: 'public',
        page: 1,
        pageSize: 20
      });

      this.setData({
        scenes: data.list || [],
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
  }
});

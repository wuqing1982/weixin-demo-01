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
    this.setData({ loading: true, errorMessage: '' });
    try {
      const data = await getMyScenes({ page: 1, pageSize: 20 });
      this.setData({ scenes: data.list || [], loading: false });
    } catch (error) {
      this.setData({ loading: false, errorMessage: error.message || '我的场景加载失败' });
    }
  },

  onOpenScene(event) {
    wx.navigateTo({ url: `/pages/scene_runtime/index?sceneId=${event.currentTarget.dataset.sceneId}` });
  }
});

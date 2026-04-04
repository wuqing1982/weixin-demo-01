const { createScenePage } = require('../shared/scene-page');
const { getSceneDetail } = require('../../services/scene');

Page(Object.assign({}, createScenePage(), {
  async onLoad(options) {
    const sceneId = options.sceneId || 'scene_breakfast';
    try {
      const data = await getSceneDetail(sceneId);
      this.setupScene(data);
    } catch (error) {
      this.setData({
        loading: false,
        errorMessage: error.message || '场景加载失败'
      });
    }
  }
}));

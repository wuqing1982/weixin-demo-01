const { createScenePage } = require('../shared/scene-page');
const { getSceneDetail, getSceneList } = require('../../services/scene');

Page(Object.assign({}, createScenePage(), {
  async onLoad(options) {
    this.initializeScenePage();

    const sceneId = options.sceneId || 'scene_breakfast';

    try {
      const [sceneListData, sceneDetailData] = await Promise.all([
        getSceneList({
          type: 'public',
          page: 1,
          pageSize: 50
        }),
        getSceneDetail(sceneId)
      ]);

      const sceneTabs = (sceneListData.list || []).map((item) => ({
        sceneId: item.sceneId,
        title: item.title
      }));

      this.setupScene(Object.assign({}, sceneDetailData, {
        sceneTabs
      }));
    } catch (error) {
      this.setLoadError(error.message || '场景加载失败');
    }
  }
}));

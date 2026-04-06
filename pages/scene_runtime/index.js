const { createScenePage } = require('../../shared/scene/scene-page');
const { getMyScenes, getSceneDetail, getSceneList } = require('../../services/scene');

function buildSceneTabs(publicList, myList, currentScene) {
  const map = {};
  const tabs = [];

  function append(items) {
    (items || []).forEach((item) => {
      if (!item || !item.sceneId || map[item.sceneId]) {
        return;
      }
      map[item.sceneId] = true;
      tabs.push({
        sceneId: item.sceneId,
        title: item.title
      });
    });
  }

  append(myList);
  append(publicList);

  if (currentScene && currentScene.sceneId && !map[currentScene.sceneId]) {
    tabs.unshift({
      sceneId: currentScene.sceneId,
      title: currentScene.title || currentScene.sceneId
    });
  }

  return tabs;
}

Page(Object.assign({}, createScenePage(), {
  async onLoad(options) {
    this.initializeScenePage();

    const sceneId = options.sceneId || 'scene_breakfast';

    try {
      const [sceneListData, mySceneListData, sceneDetailData] = await Promise.all([
        getSceneList({
          type: 'public',
          page: 1,
          pageSize: 50
        }),
        getMyScenes({
          page: 1,
          pageSize: 50
        }),
        getSceneDetail(sceneId)
      ]);

      const sceneTabs = buildSceneTabs(
        sceneListData.list || [],
        mySceneListData.list || [],
        sceneDetailData
      );

      this.setupScene(Object.assign({}, sceneDetailData, {
        sceneTabs
      }));
    } catch (error) {
      this.setLoadError(error.message || '场景加载失败');
    }
  },

  onShareAppMessage() {
    const scene = this.data.scene || {};
    return {
      title: scene.title || '全景英语场景',
      path: `/pages/scene_runtime/index?sceneId=${this.data.sceneId || ''}`
    };
  },

  onShareTimeline() {
    const scene = this.data.scene || {};
    return {
      title: scene.title || '全景英语场景'
    };
  }
}));

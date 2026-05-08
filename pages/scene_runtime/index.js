const { updateNavBar } = require('../../shared/theme-helper');
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
  data: {
    theme: 'dark'
  },

  async onLoad(options) {
    const theme = getApp().globalData.theme;
    this.setData({ theme });
    updateNavBar(theme);
    this.initializeScenePage();

    let sceneId = 'scene_breakfast';
    if (options.q) {
      const url = decodeURIComponent(options.q);
      sceneId = url.split('/q/')[1] || 'scene_breakfast';
    } else if (options.sceneId) {
      sceneId = options.sceneId;
    }

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
    const title = this.data.title || '全景英语场景';
    const imageUrl = this.data.cover || this.data.background || '';
    return {
      title: `跟我一起学：${title}`,
      path: `/pages/scene_runtime/index?sceneId=${this.data.sceneId || ''}`,
      imageUrl
    };
  },

  onShareTimeline() {
    const title = this.data.title || '全景英语场景';
    const imageUrl = this.data.cover || this.data.background || '';
    return {
      title: `跟我一起学：${title}`,
      imageUrl
    };
  }
}));

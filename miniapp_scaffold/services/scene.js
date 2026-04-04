const { request } = require('./api');
const { MOCK_SCENES, MOCK_SCENE_DETAIL } = require('./mock');

async function getSceneList(params = {}) {
  try {
    return await request({ url: '/scenes', data: params });
  } catch (error) {
    return {
      list: MOCK_SCENES,
      total: MOCK_SCENES.length,
      page: 1,
      pageSize: MOCK_SCENES.length,
      mocked: true
    };
  }
}

async function getSceneDetail(sceneId) {
  try {
    return await request({ url: `/scenes/${sceneId}` });
  } catch (error) {
    return Object.assign({}, MOCK_SCENE_DETAIL, {
      sceneId: sceneId || MOCK_SCENE_DETAIL.sceneId,
      mocked: true
    });
  }
}

async function getMyScenes(params = {}) {
  try {
    return await request({ url: '/my/scenes', data: params });
  } catch (error) {
    return {
      list: [],
      total: 0,
      page: 1,
      pageSize: 20,
      mocked: true
    };
  }
}

module.exports = {
  getSceneList,
  getSceneDetail,
  getMyScenes
};

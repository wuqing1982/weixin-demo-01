const { request } = require('./api');

function getSceneList(params = {}) {
  return request({
    url: '/scenes',
    data: params
  });
}

function getSceneDetail(sceneId) {
  return request({
    url: `/scenes/${sceneId}`
  });
}

function getMyScenes(params = {}) {
  return request({
    url: '/my/scenes',
    data: params
  });
}

function getSceneCategories() {
  return request({
    url: '/scene-categories'
  });
}

function getSceneCollections() {
  return request({
    url: '/scene-collections'
  });
}

function saveSceneHotspots(sceneId, items) {
  return request({
    url: `/scenes/${sceneId}/hotspots`,
    method: 'POST',
    data: {
      items
    }
  });
}

module.exports = {
  getSceneList,
  getSceneDetail,
  getMyScenes,
  getSceneCategories,
  getSceneCollections,
  saveSceneHotspots
};

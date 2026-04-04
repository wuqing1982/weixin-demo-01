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

module.exports = {
  getSceneList,
  getSceneDetail,
  getMyScenes
};

const { request } = require('./api');
const { getConfig } = require('./config');

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

function batchDeleteMyScenes(sceneIds) {
  return request({
    url: '/my/scenes/batch-delete',
    method: 'POST',
    data: { sceneIds }
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

function getTtsUrl(text) {
  const { apiBaseUrl } = getConfig();
  return `${apiBaseUrl}/tts?text=${encodeURIComponent(text)}`;
}

function startVideoExport(sceneId) {
  return request({
    url: `/scenes/${sceneId}/export-video`,
    method: 'POST'
  });
}

function getVideoExportStatus(jobId) {
  return request({
    url: `/video-exports/${jobId}`
  });
}

function getMyVideoExports() {
  return request({ url: '/me/video-exports' });
}

module.exports = {
  getSceneList,
  getSceneDetail,
  getMyScenes,
  batchDeleteMyScenes,
  getSceneCategories,
  getSceneCollections,
  saveSceneHotspots,
  getTtsUrl,
  startVideoExport,
  getVideoExportStatus,
  getMyVideoExports
};

const { request } = require('./api');

function createSceneTask(payload) {
  return request({
    url: '/my/tasks/scene-generate',
    method: 'POST',
    data: payload
  });
}

function getSceneTask(taskId) {
  return request({
    url: `/my/tasks/${taskId}`
  });
}

module.exports = {
  createSceneTask,
  getSceneTask
};

const { request } = require('./api');

async function createTask(payload) {
  return request({
    url: '/tasks',
    method: 'POST',
    data: payload
  });
}

async function getTaskDetail(jobId) {
  return request({
    url: `/tasks/${jobId}`
  });
}

module.exports = {
  createTask,
  getTaskDetail
};

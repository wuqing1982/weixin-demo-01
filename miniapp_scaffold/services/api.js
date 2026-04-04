const { getConfig } = require('./config');

function request({ url, method = 'GET', data, header = {} }) {
  const app = getApp();
  const { apiBaseUrl } = getConfig();
  const token = (app && app.globalData && app.globalData.authToken) || wx.getStorageSync('authToken') || '';

  return new Promise((resolve, reject) => {
    wx.request({
      url: `${apiBaseUrl}${url}`,
      method,
      data,
      timeout: 12000,
      header: Object.assign({}, header, token ? { Authorization: `Bearer ${token}` } : {}),
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          const body = res.data || {};
          if (typeof body.code === 'number' && body.code !== 0) {
            reject(body);
            return;
          }
          resolve(body.data !== undefined ? body.data : body);
          return;
        }
        reject({ code: res.statusCode, message: 'request failed', raw: res.data });
      },
      fail(error) {
        reject(error);
      }
    });
  });
}

module.exports = {
  request
};

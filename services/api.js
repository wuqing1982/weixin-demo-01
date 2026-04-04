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
        const body = res.data || {};

        if (res.statusCode >= 200 && res.statusCode < 300) {
          if (typeof body.code === 'number' && body.code !== 0) {
            reject(body);
            return;
          }

          resolve(body.data !== undefined ? body.data : body);
          return;
        }

        reject({
          code: body.code || res.statusCode,
          message: body.message || 'request failed',
          raw: body
        });
      },
      fail(error) {
        reject({
          code: 'NETWORK_ERROR',
          message: error.errMsg || 'network request failed',
          raw: error
        });
      }
    });
  });
}

module.exports = {
  request
};

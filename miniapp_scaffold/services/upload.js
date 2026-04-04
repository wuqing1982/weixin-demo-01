const { getConfig } = require('./config');

function uploadImage(filePath) {
  const app = getApp();
  const { apiBaseUrl } = getConfig();
  const token = (app && app.globalData && app.globalData.authToken) || wx.getStorageSync('authToken') || '';

  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: `${apiBaseUrl}/uploads/file`,
      filePath,
      name: 'file',
      timeout: 30000,
      header: token ? { Authorization: `Bearer ${token}` } : {},
      success(res) {
        try {
          const body = JSON.parse(res.data || '{}');
          if (body.code && body.code !== 0) {
            reject(body);
            return;
          }
          resolve(body.data !== undefined ? body.data : body);
        } catch (error) {
          reject(error);
        }
      },
      fail(error) {
        reject(error);
      }
    });
  });
}

module.exports = {
  uploadImage
};

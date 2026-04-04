const { getConfig } = require('./config');

function uploadImage(filePath) {
  const app = getApp();
  const { apiBaseUrl } = getConfig();
  const token = (app && app.globalData && app.globalData.authToken) || wx.getStorageSync('authToken') || '';
  const debugUserId = (app && app.globalData && app.globalData.debugUserId) || wx.getStorageSync('debugUserId') || '';
  const header = Object.assign(
    {},
    token ? { Authorization: `Bearer ${token}` } : {},
    debugUserId ? { 'X-Debug-User-Id': debugUserId } : {}
  );

  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: `${apiBaseUrl}/uploads/image`,
      filePath,
      name: 'file',
      timeout: 30000,
      header,
      success(res) {
        try {
          const body = JSON.parse(res.data || '{}');
          if (typeof body.code === 'number' && body.code !== 0) {
            reject(body);
            return;
          }
          resolve(body.data !== undefined ? body.data : body);
        } catch (error) {
          reject({
            code: 'UPLOAD_PARSE_ERROR',
            message: 'upload response parse failed',
            raw: error
          });
        }
      },
      fail(error) {
        reject({
          code: 'UPLOAD_FAILED',
          message: error.errMsg || 'upload failed',
          raw: error
        });
      }
    });
  });
}

module.exports = {
  uploadImage
};

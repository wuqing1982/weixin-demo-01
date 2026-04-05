const { getConfig } = require('./config');
const { buildBaseHeader, waitForAuthReady } = require('./api');

async function uploadImage(filePath) {
  const { apiBaseUrl } = getConfig();
  await waitForAuthReady();
  const header = buildBaseHeader();

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

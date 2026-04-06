const { getConfig } = require('./config');
const { buildBaseHeader, waitForAuthReady, tryRefreshToken } = require('./api');

function doUpload(filePath, header) {
  const { apiBaseUrl } = getConfig();
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
            reject({ statusCode: res.statusCode, code: body.code, message: body.message || 'upload failed', raw: body });
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

async function uploadImage(filePath) {
  await waitForAuthReady();

  try {
    return await doUpload(filePath, buildBaseHeader());
  } catch (error) {
    if (error.statusCode === 401 || error.code === 4001) {
      const refreshed = await tryRefreshToken();
      if (refreshed) {
        return doUpload(filePath, buildBaseHeader());
      }
    }
    throw error;
  }
}

module.exports = {
  uploadImage
};

const { getConfig } = require('./config');
const { getAccessToken, getDebugUserId } = require('./session');

function getAppSafe() {
  try {
    return getApp();
  } catch (error) {
    return null;
  }
}

function buildBaseHeader() {
  const token = getAccessToken();
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }

  const app = getAppSafe();
  const useDebugAuth = !!(app && app.globalData && app.globalData.useDebugAuth);
  if (!useDebugAuth) {
    return {};
  }

  const debugUserId = getDebugUserId();
  return debugUserId ? { 'X-Debug-User-Id': debugUserId } : {};
}

async function waitForAuthReady() {
  const app = getAppSafe();
  const pending = app && app.globalData && app.globalData.authReadyPromise;
  if (!pending) {
    return;
  }

  try {
    await pending;
  } catch (error) {
    console.log('wait auth ready failed', error);
  }
}

function rawRequest({ url, method = 'GET', data, header = {} }) {
  const { apiBaseUrl } = getConfig();
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${apiBaseUrl}${url}`,
      method,
      data,
      timeout: 12000,
      header: Object.assign({}, header),
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

async function request({ url, method = 'GET', data, header = {} }) {
  await waitForAuthReady();
  return rawRequest({
    url,
    method,
    data,
    header: Object.assign({}, buildBaseHeader(), header)
  });
}

module.exports = {
  buildBaseHeader,
  rawRequest,
  request,
  waitForAuthReady
};

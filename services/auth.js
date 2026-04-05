const { rawRequest } = require('./api');
const {
  applySessionToApp,
  clearSession,
  getAccessToken,
  getOrCreateDeviceId,
  getRefreshToken,
  readSession,
  saveSession,
  storeCurrentUser
} = require('./session');

function loginWithWechatCode() {
  return new Promise((resolve, reject) => {
    wx.login({
      success(res) {
        if (!res.code) {
          reject(new Error('wx.login returned empty code'));
          return;
        }
        resolve(res.code);
      },
      fail(error) {
        reject(error);
      }
    });
  });
}

function getMiniProgramVersion() {
  try {
    const accountInfo = wx.getAccountInfoSync();
    return (accountInfo && accountInfo.miniProgram && accountInfo.miniProgram.version) || '';
  } catch (error) {
    return '';
  }
}

function buildAuthHeader(accessToken) {
  return accessToken ? { Authorization: `Bearer ${accessToken}` } : {};
}

async function fetchMe(accessToken) {
  return rawRequest({
    url: '/me',
    header: buildAuthHeader(accessToken)
  });
}

async function loginSilently(appInstance) {
  const code = await loginWithWechatCode();
  const result = await rawRequest({
    url: '/auth/wechat/login',
    method: 'POST',
    data: {
      code,
      device: {
        deviceId: getOrCreateDeviceId(),
        deviceType: 'wechat_mini_program',
        appVersion: getMiniProgramVersion()
      }
    }
  });
  saveSession(result, appInstance);
  return result;
}

async function refreshSession(appInstance) {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    throw new Error('missing refresh token');
  }

  const result = await rawRequest({
    url: '/auth/refresh',
    method: 'POST',
    data: {
      refreshToken
    }
  });
  saveSession(result, appInstance);
  return result;
}

async function initializeAuth(appInstance) {
  const initialSession = readSession();
  applySessionToApp(initialSession, appInstance);

  if (initialSession.accessToken) {
    try {
      const me = await fetchMe(initialSession.accessToken);
      storeCurrentUser(me, appInstance);
      return me;
    } catch (error) {
      console.log('fetch me with cached access token failed', error);
    }
  }

  if (initialSession.refreshToken) {
    try {
      const refreshed = await refreshSession(appInstance);
      const me = refreshed.me || (await fetchMe(refreshed.accessToken));
      storeCurrentUser(me, appInstance);
      return me;
    } catch (error) {
      console.log('refresh session failed', error);
      clearSession(appInstance);
    }
  }

  const loginResult = await loginSilently(appInstance);
  const me = loginResult.me || (await fetchMe(getAccessToken()));
  storeCurrentUser(me, appInstance);
  return me;
}

async function logout(appInstance) {
  const refreshToken = getRefreshToken();
  const accessToken = getAccessToken();

  if (refreshToken || accessToken) {
    try {
      await rawRequest({
        url: '/auth/logout',
        method: 'POST',
        data: refreshToken ? { refreshToken } : {},
        header: buildAuthHeader(accessToken)
      });
    } catch (error) {
      console.log('logout request failed', error);
    }
  }

  clearSession(appInstance);
}

module.exports = {
  fetchMe,
  initializeAuth,
  loginSilently,
  logout,
  refreshSession
};

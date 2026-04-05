const STORAGE_KEYS = {
  accessToken: 'accessToken',
  refreshToken: 'refreshToken',
  accessTokenExpireAt: 'accessTokenExpireAt',
  refreshTokenExpireAt: 'refreshTokenExpireAt',
  currentUser: 'currentUser',
  deviceId: 'deviceId',
  debugUserId: 'debugUserId'
};

function safeGetStorage(key, fallback = '') {
  try {
    const value = wx.getStorageSync(key);
    return value === undefined || value === null ? fallback : value;
  } catch (error) {
    console.log('read session storage failed', key, error);
    return fallback;
  }
}

function safeSetStorage(key, value) {
  try {
    wx.setStorageSync(key, value);
  } catch (error) {
    console.log('write session storage failed', key, error);
  }
}

function safeRemoveStorage(key) {
  try {
    wx.removeStorageSync(key);
  } catch (error) {
    console.log('remove session storage failed', key, error);
  }
}

function buildDeviceId() {
  return `device_${Date.now()}_${Math.random().toString(16).slice(2, 10)}`;
}

function buildDebugUserId() {
  return `debug_user_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`;
}

function getAppSafe() {
  try {
    return getApp();
  } catch (error) {
    return null;
  }
}

function getOrCreateDeviceId() {
  const stored = safeGetStorage(STORAGE_KEYS.deviceId, '');
  if (stored) {
    return stored;
  }
  const nextValue = buildDeviceId();
  safeSetStorage(STORAGE_KEYS.deviceId, nextValue);
  return nextValue;
}

function getOrCreateDebugUserId() {
  const stored = safeGetStorage(STORAGE_KEYS.debugUserId, '');
  if (stored) {
    return stored;
  }
  const nextValue = buildDebugUserId();
  safeSetStorage(STORAGE_KEYS.debugUserId, nextValue);
  return nextValue;
}

function readSession() {
  return {
    accessToken: safeGetStorage(STORAGE_KEYS.accessToken, ''),
    refreshToken: safeGetStorage(STORAGE_KEYS.refreshToken, ''),
    accessTokenExpireAt: safeGetStorage(STORAGE_KEYS.accessTokenExpireAt, ''),
    refreshTokenExpireAt: safeGetStorage(STORAGE_KEYS.refreshTokenExpireAt, ''),
    currentUser: safeGetStorage(STORAGE_KEYS.currentUser, null),
    deviceId: getOrCreateDeviceId(),
    debugUserId: getOrCreateDebugUserId()
  };
}

function applySessionToApp(session, appInstance) {
  const app = appInstance || getAppSafe();
  if (!app || !app.globalData) {
    return session;
  }

  app.globalData.authToken = session.accessToken || '';
  app.globalData.accessToken = session.accessToken || '';
  app.globalData.refreshToken = session.refreshToken || '';
  app.globalData.currentUser = session.currentUser || null;
  app.globalData.deviceId = session.deviceId || '';
  app.globalData.debugUserId = session.debugUserId || '';
  return session;
}

function saveSession(payload, appInstance) {
  const current = readSession();
  const nextSession = {
    accessToken: payload && payload.accessToken ? payload.accessToken : current.accessToken,
    refreshToken: payload && payload.refreshToken ? payload.refreshToken : current.refreshToken,
    accessTokenExpireAt: payload && payload.accessTokenExpireAt ? payload.accessTokenExpireAt : current.accessTokenExpireAt,
    refreshTokenExpireAt: payload && payload.refreshTokenExpireAt ? payload.refreshTokenExpireAt : current.refreshTokenExpireAt,
    currentUser: (payload && (payload.me || payload.user)) || current.currentUser || null,
    deviceId: current.deviceId,
    debugUserId: current.debugUserId
  };

  safeSetStorage(STORAGE_KEYS.accessToken, nextSession.accessToken);
  safeSetStorage(STORAGE_KEYS.refreshToken, nextSession.refreshToken);
  safeSetStorage(STORAGE_KEYS.accessTokenExpireAt, nextSession.accessTokenExpireAt);
  safeSetStorage(STORAGE_KEYS.refreshTokenExpireAt, nextSession.refreshTokenExpireAt);
  safeSetStorage(STORAGE_KEYS.currentUser, nextSession.currentUser);
  applySessionToApp(nextSession, appInstance);
  return nextSession;
}

function storeCurrentUser(currentUser, appInstance) {
  const current = readSession();
  const nextSession = Object.assign({}, current, {
    currentUser: currentUser || null
  });
  safeSetStorage(STORAGE_KEYS.currentUser, nextSession.currentUser);
  applySessionToApp(nextSession, appInstance);
  return nextSession;
}

function clearSession(appInstance) {
  safeRemoveStorage(STORAGE_KEYS.accessToken);
  safeRemoveStorage(STORAGE_KEYS.refreshToken);
  safeRemoveStorage(STORAGE_KEYS.accessTokenExpireAt);
  safeRemoveStorage(STORAGE_KEYS.refreshTokenExpireAt);
  safeRemoveStorage(STORAGE_KEYS.currentUser);

  const nextSession = {
    accessToken: '',
    refreshToken: '',
    accessTokenExpireAt: '',
    refreshTokenExpireAt: '',
    currentUser: null,
    deviceId: getOrCreateDeviceId(),
    debugUserId: getOrCreateDebugUserId()
  };
  applySessionToApp(nextSession, appInstance);
  return nextSession;
}

function getAccessToken() {
  return readSession().accessToken || '';
}

function getRefreshToken() {
  return readSession().refreshToken || '';
}

function getDebugUserId() {
  return readSession().debugUserId || '';
}

module.exports = {
  applySessionToApp,
  clearSession,
  getAccessToken,
  getDebugUserId,
  getOrCreateDeviceId,
  getRefreshToken,
  readSession,
  saveSession,
  storeCurrentUser
};

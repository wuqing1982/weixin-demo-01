const { DEFAULT_RUNTIME_CONFIG } = require('./config/runtime');
const { initializeAuth } = require('./services/auth');
const { applySessionToApp, readSession } = require('./services/session');

App({
  globalData: {
    apiBaseUrl: DEFAULT_RUNTIME_CONFIG.apiBaseUrl,
    staticBaseUrl: DEFAULT_RUNTIME_CONFIG.staticBaseUrl,
    currentUser: null,
    authToken: '',
    accessToken: '',
    refreshToken: '',
    deviceId: '',
    debugUserId: ''
  },

  onLaunch() {
    const session = readSession();
    applySessionToApp(session, this);
    this.globalData.isAuthReady = false;
    this.globalData.authReadyPromise = initializeAuth(this)
      .catch((error) => {
        console.log('initialize auth failed', error);
        return null;
      })
      .finally(() => {
        this.globalData.isAuthReady = true;
      });
  }
});

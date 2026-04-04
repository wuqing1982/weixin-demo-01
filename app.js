const { DEFAULT_RUNTIME_CONFIG } = require('./config/runtime');

function buildDebugUserId() {
  return `debug_user_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`;
}

App({
  globalData: {
    apiBaseUrl: DEFAULT_RUNTIME_CONFIG.apiBaseUrl,
    staticBaseUrl: DEFAULT_RUNTIME_CONFIG.staticBaseUrl,
    currentUser: null,
    authToken: '',
    debugUserId: ''
  },

  onLaunch() {
    try {
      const token = wx.getStorageSync('authToken') || '';
      const currentUser = wx.getStorageSync('currentUser') || null;
      const debugUserId = wx.getStorageSync('debugUserId') || buildDebugUserId();
      wx.setStorageSync('debugUserId', debugUserId);
      this.globalData.authToken = token;
      this.globalData.currentUser = currentUser;
      this.globalData.debugUserId = debugUserId;
    } catch (error) {
      console.log('load app storage failed', error);
    }
  }
});

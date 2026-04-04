const { DEFAULT_RUNTIME_CONFIG } = require('./config/runtime');

App({
  globalData: {
    apiBaseUrl: DEFAULT_RUNTIME_CONFIG.apiBaseUrl,
    staticBaseUrl: DEFAULT_RUNTIME_CONFIG.staticBaseUrl,
    currentUser: null,
    authToken: ''
  },

  onLaunch() {
    try {
      const token = wx.getStorageSync('authToken') || '';
      const currentUser = wx.getStorageSync('currentUser') || null;
      this.globalData.authToken = token;
      this.globalData.currentUser = currentUser;
    } catch (error) {
      console.log('load app storage failed', error);
    }
  }
});

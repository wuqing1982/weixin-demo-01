App({
  globalData: {
    apiBaseUrl: 'http://127.0.0.1:8000/api',
    staticBaseUrl: 'http://127.0.0.1:8000',
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

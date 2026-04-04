const { getCurrentUser } = require('../../services/auth');

Page({
  data: {
    user: null,
    errorMessage: ''
  },

  async onShow() {
    try {
      const user = await getCurrentUser();
      this.setData({ user, errorMessage: '' });
      wx.setStorageSync('currentUser', user);
      getApp().globalData.currentUser = user;
    } catch (error) {
      const fallback = wx.getStorageSync('currentUser') || null;
      this.setData({ user: fallback, errorMessage: fallback ? '' : '请先登录后查看资料' });
    }
  },

  onGoLogin() {
    wx.navigateTo({ url: '/pages/login/index' });
  }
});

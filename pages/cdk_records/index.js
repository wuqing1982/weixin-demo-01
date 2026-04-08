const { updateNavBar } = require('../../shared/theme-helper');
const { getMyRedemptions } = require('../../services/cdk');
const { getMe } = require('../../services/user');
const { readSession } = require('../../services/session');

Page({
  data: {
    loading: true,
    records: [],
    me: null,
    errorMessage: '',
    theme: 'dark'
  },

  onShow() {
    const theme = getApp().globalData.theme;
    this.setData({ theme });
    updateNavBar(theme);
    if (!readSession().accessToken) {
      wx.reLaunch({ url: '/pages/login/index' });
      return;
    }
    this.loadPage();
  },

  async loadPage() {
    this.setData({ loading: true, errorMessage: '' });
    try {
      const [data, me] = await Promise.all([
        getMyRedemptions(),
        getMe()
      ]);
      this.setData({
        loading: false,
        records: data.list || [],
        me
      });
    } catch (error) {
      this.setData({
        loading: false,
        errorMessage: error.message || '加载失败'
      });
    }
  },

  onGoBack() {
    wx.navigateTo({ url: '/pages/products/index' });
  }
});

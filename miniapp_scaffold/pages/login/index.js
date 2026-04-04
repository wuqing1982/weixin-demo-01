const { login } = require('../../services/auth');

Page({
  data: {
    loading: false,
    errorMessage: ''
  },

  async onLogin() {
    this.setData({ loading: true, errorMessage: '' });
    try {
      await login();
      this.setData({ loading: false });
      wx.showToast({ title: '登录成功', icon: 'success' });
      setTimeout(() => wx.navigateBack({ delta: 1 }), 500);
    } catch (error) {
      this.setData({ loading: false, errorMessage: error.message || '登录失败，请确认后端接口已启动' });
    }
  }
});

const { request } = require('./api');

async function login() {
  const loginResult = await new Promise((resolve, reject) => {
    wx.login({
      success: resolve,
      fail: reject
    });
  });

  const data = await request({
    url: '/auth/wx-login',
    method: 'POST',
    data: { code: loginResult.code }
  });

  if (data && data.token) {
    wx.setStorageSync('authToken', data.token);
    wx.setStorageSync('currentUser', data.user || null);
    const app = getApp();
    app.globalData.authToken = data.token;
    app.globalData.currentUser = data.user || null;
  }

  return data;
}

async function getCurrentUser() {
  return request({ url: '/me' });
}

module.exports = {
  login,
  getCurrentUser
};

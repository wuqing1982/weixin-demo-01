const { logout } = require('../../services/auth');
const { readSession } = require('../../services/session');
const { getMe } = require('../../services/user');

Page({
  data: {
    me: null,
    errorMessage: '',
    actions: [
      {
        id: 'products',
        title: '会员与点数商品',
        desc: '浏览包年会员、月卡和生成点数商品，完成购买闭环。',
        url: '/pages/products/index'
      },
      {
        id: 'orders',
        title: '我的订单',
        desc: '查看订单状态，继续完成待支付的 mock 支付。',
        url: '/pages/orders/index'
      },
      {
        id: 'library',
        title: '公开场景库',
        desc: '从后端加载场景列表，再进入统一 runtime 页面。',
        url: '/pages/library/index'
      },
      {
        id: 'create',
        title: '拍照生成我的场景',
        desc: '上传图片，提交后端任务，轮询生成进度，再打开私人场景。',
        url: '/pages/create_scene/index'
      },
      {
        id: 'mine',
        title: '我的生成场景',
        desc: '查看当前调试用户生成过的私人场景列表。',
        url: '/pages/my_scenes/index'
      },
      {
        id: 'breakfast',
        title: '直接打开早餐场景',
        desc: '跳过列表，直接验证场景详情接口和图片音频加载。',
        url: '/pages/scene_runtime/index?sceneId=scene_breakfast'
      },
      {
        id: 'videos',
        title: '我的导出视频',
        desc: '查看已导出的学习视频，点击即可播放。',
        url: '/pages/my_videos/index'
      }
    ]
  },

  onShow() {
    this.loadMe();
  },

  async loadMe() {
    const session = readSession();
    if (!session.accessToken) {
      wx.reLaunch({
        url: '/pages/login/index'
      });
      return;
    }

    try {
      const me = await getMe();
      getApp().globalData.currentUser = me;
      this.setData({
        me,
        errorMessage: ''
      });
    } catch (error) {
      const isAuthError = error && (error.code === 4001 || error.code === 401);
      this.setData({
        errorMessage: error.message || '用户信息加载失败'
      });
      if (isAuthError) {
        await logout(getApp());
        wx.reLaunch({
          url: '/pages/login/index'
        });
      }
    }
  },

  onOpen(event) {
    wx.navigateTo({
      url: event.currentTarget.dataset.url
    });
  },

  async onLogout() {
    await logout(getApp());
    wx.reLaunch({
      url: '/pages/login/index'
    });
  }
});

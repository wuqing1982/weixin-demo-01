const { updateNavBar } = require('../../shared/theme-helper');
const { getOrders } = require('../../services/order');
const { payOrder } = require('../../services/payment');
const { readSession } = require('../../services/session');
const { getMe } = require('../../services/user');

Page({
  data: {
    loading: true,
    orders: [],
    me: null,
    errorMessage: '',
    payingOrderId: '',
    theme: 'dark'
  },

  onShow() {
    const theme = getApp().globalData.theme;
    this.setData({ theme });
    updateNavBar(theme);
    if (!readSession().accessToken) {
      wx.reLaunch({
        url: '/pages/login/index'
      });
      return;
    }
    this.loadPage();
  },

  async loadPage() {
    this.setData({
      loading: true,
      errorMessage: ''
    });

    try {
      const [orderData, me] = await Promise.all([
        getOrders(),
        getMe()
      ]);
      this.setData({
        loading: false,
        orders: orderData.list || [],
        me
      });
    } catch (error) {
      this.setData({
        loading: false,
        errorMessage: error.message || '订单加载失败'
      });
    }
  },

  async onPayOrder(event) {
    const { orderId } = event.currentTarget.dataset;
    if (!orderId || this.data.payingOrderId) {
      return;
    }

    this.setData({
      payingOrderId: orderId
    });

    try {
      await payOrder(orderId, getApp());
      wx.showToast({
        title: '支付成功',
        icon: 'success'
      });
      this.loadPage();
    } catch (error) {
      if (error && error.code !== 'PAY_CANCELLED') {
        wx.showToast({
          title: error.message || '支付失败',
          icon: 'none'
        });
      }
    } finally {
      this.setData({
        payingOrderId: ''
      });
    }
  },

  onOpenProducts() {
    wx.navigateTo({
      url: '/pages/products/index'
    });
  }
});

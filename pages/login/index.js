const { loginSilently } = require('../../services/auth');
const { getProducts, getProductSkus } = require('../../services/product');
const { readSession } = require('../../services/session');
const { getMe, updateMyProfile } = require('../../services/user');

function pickFeaturedSku(products) {
  const membershipProduct = products.find((item) => item.productType === 'membership') || products[0] || null;
  if (!membershipProduct) {
    return null;
  }
  const skus = (membershipProduct.skus || []).slice().sort((a, b) => (b.durationDays || 0) - (a.durationDays || 0));
  return skus[0] ? { ...membershipProduct, featuredSku: skus[0] } : null;
}

Page({
  data: {
    loggingIn: false,
    loadingOffers: true,
    loadingMe: false,
    syncingProfile: false,
    errorMessage: '',
    offerMessage: '',
    profileMessage: '',
    featuredProduct: null,
    me: null,
    avatarLetter: '微'
  },

  async onShow() {
    const app = getApp();
    if (app && app.globalData && app.globalData.authReadyPromise) {
      try {
        await app.globalData.authReadyPromise;
      } catch (error) {
        console.log('wait auth ready on login page failed', error);
      }
    }
    await this.loadCurrentMe();
    this.loadFeaturedOffer();
  },

  async loadCurrentMe() {
    const session = readSession();
    if (!session.accessToken) {
      this.setData({
        me: null,
        avatarLetter: '微',
        profileMessage: ''
      });
      return;
    }

    this.setData({
      loadingMe: true
    });
    try {
      const me = await getMe();
      const displayName = (me.displayName || '').trim();
      this.setData({
        me,
        avatarLetter: (displayName || '微').slice(0, 1).toUpperCase(),
        profileMessage: ''
      });
    } catch (error) {
      this.setData({
        me: null,
        avatarLetter: '微',
        errorMessage: error.message || '当前用户信息加载失败'
      });
    } finally {
      this.setData({
        loadingMe: false
      });
    }
  },

  async loadFeaturedOffer() {
    this.setData({
      loadingOffers: true,
      offerMessage: ''
    });

    try {
      const productsResult = await getProducts();
      const products = productsResult.list || [];
      const skuResults = await Promise.all(products.map((product) => getProductSkus(product.productId)));
      const merged = products.map((product, index) => ({
        ...product,
        skus: (skuResults[index] && skuResults[index].list) || []
      }));
      this.setData({
        loadingOffers: false,
        featuredProduct: pickFeaturedSku(merged)
      });
    } catch (error) {
      this.setData({
        loadingOffers: false,
        offerMessage: error.message || '会员套餐加载失败'
      });
    }
  },

  async onWechatLogin() {
    if (this.data.loggingIn) {
      return;
    }
    this.setData({
      loggingIn: true,
      errorMessage: ''
    });

    try {
      await loginSilently(getApp());
      await this.loadCurrentMe();
      wx.showToast({
        title: '登录成功',
        icon: 'success'
      });
    } catch (error) {
      this.setData({
        errorMessage: error.message || '微信登录失败，请稍后再试'
      });
    } finally {
      this.setData({
        loggingIn: false
      });
    }
  },

  onOpenProducts() {
    wx.navigateTo({
      url: '/pages/products/index'
    });
  },

  onOpenHome() {
    wx.reLaunch({
      url: '/pages/home/index'
    });
  },

  async onSyncWechatProfile() {
    if (this.data.syncingProfile) {
      return;
    }
    if (!this.data.me) {
      this.setData({
        errorMessage: '请先完成微信登录'
      });
      return;
    }
    if (!wx.getUserProfile) {
      this.setData({
        errorMessage: '当前微信版本不支持同步头像昵称'
      });
      return;
    }

    this.setData({
      syncingProfile: true,
      errorMessage: '',
      profileMessage: ''
    });

    try {
      const profile = await new Promise((resolve, reject) => {
        wx.getUserProfile({
          desc: '用于完善会员资料',
          success: resolve,
          fail: reject
        });
      });
      const userInfo = profile && profile.userInfo ? profile.userInfo : {};
      const me = await updateMyProfile({
        displayName: userInfo.nickName || '',
        avatarUrl: userInfo.avatarUrl || ''
      });
      getApp().globalData.currentUser = me;
      this.setData({
        me,
        avatarLetter: ((me.displayName || '微').slice(0, 1) || '微').toUpperCase(),
        profileMessage: '微信头像昵称已同步'
      });
    } catch (error) {
      this.setData({
        errorMessage: error.errMsg || error.message || '同步头像昵称失败'
      });
    } finally {
      this.setData({
        syncingProfile: false
      });
    }
  }
});

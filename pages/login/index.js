const { loginSilently } = require('../../services/auth');
const { getProducts, getProductSkus } = require('../../services/product');
const { readSession } = require('../../services/session');

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
    errorMessage: '',
    offerMessage: '',
    featuredProduct: null
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
    this.redirectIfLoggedIn();
    this.loadFeaturedOffer();
  },

  redirectIfLoggedIn() {
    const session = readSession();
    if (!session.accessToken) {
      return;
    }
    wx.reLaunch({
      url: '/pages/home/index'
    });
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
      wx.showToast({
        title: '登录成功',
        icon: 'success'
      });
      wx.reLaunch({
        url: '/pages/home/index'
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
  }
});

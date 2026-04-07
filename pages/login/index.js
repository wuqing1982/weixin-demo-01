const { updateNavBar } = require('../../shared/theme-helper');
const { loginSilently } = require('../../services/auth');
const { getProducts, getProductSkus } = require('../../services/product');
const { readSession } = require('../../services/session');
const { getMe, updateMyProfile } = require('../../services/user');
const { uploadImage } = require('../../services/upload');

function buildAvatarLetter(name) {
  return ((name || '微').slice(0, 1) || '微').toUpperCase();
}

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
    theme: 'dark',
    loggingIn: false,
    loadingOffers: true,
    loadingMe: false,
    syncingProfile: false,
    errorMessage: '',
    offerMessage: '',
    profileMessage: '',
    featuredProduct: null,
    me: null,
    avatarLetter: '微',
    profileDraftName: '',
    profileDraftAvatarPreview: '',
    profileDraftRemoteAvatar: '',
    profilePendingAvatarPath: ''
  },

  async onShow() {
    const app = getApp();
    const theme = getApp().globalData.theme;
    this.setData({ theme });
    updateNavBar(theme);
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
        profileMessage: '',
        profileDraftName: '',
        profileDraftAvatarPreview: '',
        profileDraftRemoteAvatar: '',
        profilePendingAvatarPath: ''
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
        avatarLetter: buildAvatarLetter(displayName),
        profileMessage: '',
        profileDraftName: displayName,
        profileDraftAvatarPreview: (me.avatarUrl || '').trim(),
        profileDraftRemoteAvatar: (me.avatarUrl || '').trim(),
        profilePendingAvatarPath: ''
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
    this.setData({
      syncingProfile: true,
      errorMessage: '',
      profileMessage: ''
    });

    try {
      const displayName = (this.data.profileDraftName || '').trim();
      const pendingAvatarPath = (this.data.profilePendingAvatarPath || '').trim();
      let avatarUrl = (this.data.profileDraftRemoteAvatar || '').trim();

      if (pendingAvatarPath) {
        const upload = await uploadImage(pendingAvatarPath);
        avatarUrl = (upload.fileUrl || upload.url || '').trim();
        if (!avatarUrl) {
          throw new Error('头像上传成功，但未返回可用地址');
        }
      }

      if (!displayName && !avatarUrl) {
        throw new Error('请先选择头像或填写昵称');
      }

      const me = await updateMyProfile({
        displayName,
        avatarUrl
      });
      getApp().globalData.currentUser = me;
      this.setData({
        me,
        avatarLetter: buildAvatarLetter(me.displayName || displayName),
        profileDraftName: (me.displayName || '').trim(),
        profileDraftAvatarPreview: (me.avatarUrl || avatarUrl || '').trim(),
        profileDraftRemoteAvatar: (me.avatarUrl || avatarUrl || '').trim(),
        profilePendingAvatarPath: '',
        profileMessage: '头像昵称已保存到当前账号'
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
  },

  onProfileNicknameInput(event) {
    this.setData({
      profileDraftName: event.detail.value || '',
      errorMessage: '',
      profileMessage: ''
    });
  },

  onChooseAvatar(event) {
    const avatarPath = (event.detail && event.detail.avatarUrl) || '';
    if (!avatarPath) {
      this.setData({
        errorMessage: '没有拿到头像，请重新选择'
      });
      return;
    }
    this.setData({
      profileDraftAvatarPreview: avatarPath,
      profilePendingAvatarPath: avatarPath,
      errorMessage: '',
      profileMessage: '新头像已选中，点击保存后同步'
    });
  }
});

const { updateNavBar } = require('../../shared/theme-helper');
const { createOrder } = require('../../services/order');
const { payOrder } = require('../../services/payment');
const { getProducts, getProductSkus } = require('../../services/product');
const { readSession } = require('../../services/session');
const { getMe } = require('../../services/user');

const TIER_META = {
  tier_pro: {
    credits: 50,
    videoExport: false,
    priorityQueue: false,
    recommended: false,
  },
  tier_plus: {
    credits: 150,
    videoExport: true,
    priorityQueue: false,
    recommended: true,
  },
  tier_max: {
    credits: 500,
    videoExport: true,
    priorityQueue: true,
    recommended: false,
  },
};

function buildTierCards(products, allSkus, currentEntitlementCode) {
  const cards = [];
  for (const product of products) {
    const skus = allSkus[product.productId] || [];
    const sku = skus[0];
    if (!sku) continue;
    const meta = TIER_META[product.productCode] || {};
    cards.push({
      skuId: sku.skuId,
      name: product.name,
      salePrice: sku.salePrice,
      listPrice: sku.listPrice,
      credits: meta.credits || 0,
      videoExport: meta.videoExport || false,
      priorityQueue: meta.priorityQueue || false,
      recommended: meta.recommended || false,
      isCurrent: currentEntitlementCode && sku.benefits && sku.benefits.some(
        (b) => b.benefitType === 'membership' && b.benefitValue === currentEntitlementCode
      ),
    });
  }
  return cards;
}

Page({
  data: {
    theme: 'dark',
    loading: true,
    tierCards: [],
    me: null,
    guestMode: true,
    errorMessage: '',
    payingSkuId: ''
  },

  onShow() {
    const theme = getApp().globalData.theme;
    this.setData({ theme });
    updateNavBar(theme);
    this.loadPage();
  },

  async loadPage() {
    this.setData({ loading: true, errorMessage: '' });

    try {
      const productData = await getProducts();
      const products = productData.list || [];
      const skuResults = await Promise.all(products.map((p) => getProductSkus(p.productId)));
      const allSkus = {};
      skuResults.forEach((res, i) => {
        allSkus[products[i].productId] = (res && res.list) || [];
      });

      let me = null;
      try {
        me = await getMe();
      } catch (_) {
        me = null;
      }

      const currentCode = me && me.memberSummary && me.memberSummary.isActive
        ? me.memberSummary.entitlementCode
        : '';

      const tierCards = buildTierCards(products, allSkus, currentCode);
      this.setData({
        loading: false,
        tierCards,
        me,
        guestMode: !me,
      });
    } catch (error) {
      this.setData({
        loading: false,
        errorMessage: error.message || '商品加载失败',
      });
    }
  },

  async onBuySku(event) {
    const { skuId } = event.currentTarget.dataset;
    if (!skuId || this.data.payingSkuId) return;
    if (!readSession().accessToken) {
      wx.navigateTo({ url: '/pages/login/index' });
      return;
    }

    this.setData({ payingSkuId: skuId });

    try {
      const order = await createOrder({ skuId, quantity: 1 });
      await payOrder(order.orderId, getApp());
      wx.showToast({ title: '支付成功', icon: 'success' });
      this.loadPage();
    } catch (error) {
      if (error && error.code !== 'PAY_CANCELLED') {
        wx.showToast({ title: error.message || '支付失败', icon: 'none' });
      }
    } finally {
      this.setData({ payingSkuId: '' });
    }
  },

  onOpenOrders() {
    if (!readSession().accessToken) {
      wx.navigateTo({ url: '/pages/login/index' });
      return;
    }
    wx.navigateTo({ url: '/pages/orders/index' });
  },
});

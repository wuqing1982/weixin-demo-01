const { updateNavBar } = require('../../shared/theme-helper');
const { createOrder } = require('../../services/order');
const { payOrder } = require('../../services/payment');
const { getProducts, getProductSkus } = require('../../services/product');
const { readSession } = require('../../services/session');
const { getMe, getUpgradePreview } = require('../../services/user');
const { redeemCdk } = require('../../services/cdk');

const TIER_RANK = { pro: 1, plus: 2, max: 3 };

const TIER_LABELS = {
  pro: 'Pro会员',
  plus: 'Plus会员',
  max: 'Max会员',
};

function getMemberTierLabel(me) {
  if (!me || !me.memberSummary || !me.memberSummary.isActive) return '未开通';
  return TIER_LABELS[me.memberSummary.entitlementCode] || '已开通';
}

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
  const currentRank = TIER_RANK[currentEntitlementCode] || 0;

  for (const product of products) {
    const skus = allSkus[product.productId] || [];
    const sku = skus[0];
    if (!sku) continue;

    const meta = TIER_META[product.productCode] || {};
    const tierCode = (product.productCode || '').replace('tier_', '');
    const cardRank = TIER_RANK[tierCode] || 0;

    let purchaseAction = 'buy';
    let canPurchase = true;

    if (currentEntitlementCode) {
      if (tierCode === currentEntitlementCode) {
        purchaseAction = 'renew';
      } else if (cardRank > currentRank) {
        purchaseAction = 'upgrade';
      } else {
        purchaseAction = 'blocked';
        canPurchase = false;
      }
    }

    cards.push({
      skuId: sku.skuId,
      tierCode: tierCode,
      name: product.name,
      salePrice: sku.salePrice,
      listPrice: sku.listPrice,
      credits: meta.credits || 0,
      videoExport: meta.videoExport || false,
      priorityQueue: meta.priorityQueue || false,
      recommended: meta.recommended || false,
      isCurrent: tierCode === currentEntitlementCode,
      purchaseAction: purchaseAction,
      canPurchase: canPurchase,
      upgradeHint: '',
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
    memberTierLabel: '未开通',
    guestMode: true,
    errorMessage: '',
    payingSkuId: '',
    showCdkModal: false,
    cdkInput: '',
    cdkRedeeming: false
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

      // Load upgrade previews for upgrade-able cards
      if (me && currentCode) {
        const upgradeCards = tierCards.filter((c) => c.purchaseAction === 'upgrade');
        const previews = await Promise.all(
          upgradeCards.map((card) =>
            getUpgradePreview(card.skuId).catch(() => null)
          )
        );
        previews.forEach((preview, i) => {
          if (preview && preview.convertedDays > 0) {
            upgradeCards[i].upgradeHint = '剩余 ' + preview.remainingDays + ' 天折算 ' + preview.convertedDays + ' 天，合计 ' + preview.newDurationDays + ' 天';
          }
        });
      }

      this.setData({
        loading: false,
        tierCards,
        me,
        memberTierLabel: getMemberTierLabel(me),
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
    const card = this.data.tierCards.find((c) => c.skuId === skuId);
    if (!skuId || this.data.payingSkuId) return;
    if (card && !card.canPurchase) return;
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
      if (error && error.code === 'PAY_CANCELLED') {
        // user cancelled
      } else {
        const msg = error && (error.errMsg || error.message || '支付失败');
        console.error('[pay] payment failed:', JSON.stringify(error));
        wx.showToast({ title: msg, icon: 'none', duration: 3000 });
      }
    } finally {
      this.setData({ payingSkuId: '' });
    }
  },

  onOpenCdkModal() {
    if (!readSession().accessToken) {
      wx.navigateTo({ url: '/pages/login/index' });
      return;
    }
    this.setData({ showCdkModal: true, cdkInput: '', cdkRedeeming: false });
  },

  onCloseCdkModal() {
    this.setData({ showCdkModal: false, cdkInput: '', cdkRedeeming: false });
  },

  onCdkInput(e) {
    this.setData({ cdkInput: e.detail.value.toUpperCase() });
  },

  async onRedeemCdk() {
    const code = (this.data.cdkInput || '').trim();
    if (!code) return;

    this.setData({ cdkRedeeming: true });
    try {
      await redeemCdk(code);
      wx.showToast({ title: '兑换成功', icon: 'success' });
      this.setData({ showCdkModal: false, cdkInput: '' });
      this.loadPage();
    } catch (error) {
      wx.showToast({ title: error.message || '兑换失败', icon: 'none' });
    } finally {
      this.setData({ cdkRedeeming: false });
    }
  },

  onOpenOrders() {
    if (!readSession().accessToken) {
      wx.navigateTo({ url: '/pages/login/index' });
      return;
    }
    wx.navigateTo({ url: '/pages/orders/index' });
  },

  onOpenCdkRecords() {
    if (!readSession().accessToken) {
      wx.navigateTo({ url: '/pages/login/index' });
      return;
    }
    wx.navigateTo({ url: '/pages/cdk_records/index' });
  },
});

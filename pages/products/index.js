const { createOrder } = require('../../services/order');
const { payOrder } = require('../../services/payment');
const { getProducts, getProductSkus } = require('../../services/product');
const { getMe } = require('../../services/user');

Page({
  data: {
    loading: true,
    products: [],
    me: null,
    errorMessage: '',
    payingSkuId: ''
  },

  onShow() {
    this.loadPage();
  },

  async loadPage() {
    this.setData({
      loading: true,
      errorMessage: ''
    });

    try {
      const [productData, me] = await Promise.all([
        getProducts(),
        getMe()
      ]);
      const products = productData.list || [];
      const skuResults = await Promise.all(products.map((product) => getProductSkus(product.productId)));
      const enriched = products.map((product, index) => ({
        ...product,
        skus: (skuResults[index] && skuResults[index].list) || []
      }));
      this.setData({
        loading: false,
        products: enriched,
        me
      });
    } catch (error) {
      this.setData({
        loading: false,
        errorMessage: error.message || '商品加载失败'
      });
    }
  },

  async onBuySku(event) {
    const { skuId } = event.currentTarget.dataset;
    if (!skuId || this.data.payingSkuId) {
      return;
    }

    this.setData({
      payingSkuId: skuId
    });

    try {
      const order = await createOrder({
        skuId,
        quantity: 1
      });
      await payOrder(order.orderId, getApp());
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
        payingSkuId: ''
      });
    }
  },

  onOpenOrders() {
    wx.navigateTo({
      url: '/pages/orders/index'
    });
  }
});

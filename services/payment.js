const { fetchMe } = require('./auth');
const { completeMockOrderPayment, createOrderPayment } = require('./order');
const { getAccessToken, storeCurrentUser } = require('./session');

function showModalAsync(options) {
  return new Promise((resolve, reject) => {
    wx.showModal({
      ...options,
      success: resolve,
      fail: reject
    });
  });
}

function requestPaymentAsync(params) {
  return new Promise((resolve, reject) => {
    wx.requestPayment({
      ...params,
      success: resolve,
      fail: reject
    });
  });
}

async function refreshCurrentUser(appInstance) {
  const accessToken = getAccessToken();
  if (!accessToken) {
    return null;
  }
  const me = await fetchMe(accessToken);
  storeCurrentUser(me, appInstance);
  return me;
}

async function payOrder(orderId, appInstance) {
  const payment = await createOrderPayment(orderId);

  if (payment.alreadyPaid) {
    await refreshCurrentUser(appInstance);
    return payment.order;
  }

  if (payment.paymentMode === 'mock') {
    const order = payment.order || {};
    const modal = await showModalAsync({
      title: '模拟支付',
      content: `确认支付 ${order.payableAmount || '0.00'} ${order.currency || 'CNY'}？`,
      confirmText: '支付成功',
      cancelText: '取消'
    });
    if (!modal.confirm) {
      throw {
        code: 'PAY_CANCELLED',
        message: '已取消模拟支付'
      };
    }
    const completed = await completeMockOrderPayment(orderId, payment.paymentId);
    if (completed && completed.me) {
      storeCurrentUser(completed.me, appInstance);
    } else {
      await refreshCurrentUser(appInstance);
    }
    return completed.order;
  }

  await requestPaymentAsync(payment.requestPayment || {});
  await refreshCurrentUser(appInstance);
  return payment.order;
}

module.exports = {
  payOrder,
  refreshCurrentUser
};

const { fetchMe } = require('./auth');
const { completeMockOrderPayment, createOrderPayment, syncOrderPayment } = require('./order');
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

function requestVirtualPaymentAsync(params) {
  return new Promise((resolve, reject) => {
    if (!wx.canIUse || !wx.canIUse('requestVirtualPayment')) {
      reject({ errMsg: '当前微信版本不支持虚拟支付，请升级微信', errCode: -1 });
      return;
    }
    console.log('[virtual-pay] requestVirtualPayment params:', JSON.stringify(params));
    wx.requestVirtualPayment({
      signData: params.signData,
      mode: params.mode,
      paySig: params.paySig,
      signature: params.signature,
      success(res) {
        console.log('[virtual-pay] requestVirtualPayment success:', JSON.stringify(res));
        resolve(res);
      },
      fail(err) {
        console.error('[virtual-pay] requestVirtualPayment fail:', JSON.stringify(err));
        reject(err);
      }
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

  if (payment.paymentMode === 'virtual_pay') {
    const rp = payment.requestPayment || {};
    try {
      await requestVirtualPaymentAsync(rp);
    } catch (vpError) {
      console.error('[virtual-pay] wx.requestVirtualPayment failed:', vpError);
      throw vpError;
    }
    const synced = await syncOrderPayment(orderId);
    if (synced && synced.me) {
      storeCurrentUser(synced.me, appInstance);
    } else {
      await refreshCurrentUser(appInstance);
    }
    return synced.order || payment.order;
  }

  // Legacy wechat_pay mode
  await requestPaymentAsync(payment.requestPayment || {});
  const synced = await syncOrderPayment(orderId);
  if (synced && synced.me) {
    storeCurrentUser(synced.me, appInstance);
  } else {
    await refreshCurrentUser(appInstance);
  }
  return synced.order || payment.order;
}

module.exports = {
  payOrder,
  refreshCurrentUser
};

const { request } = require('./api');

function createOrder(payload) {
  return request({
    url: '/orders',
    method: 'POST',
    data: payload
  });
}

function getOrders() {
  return request({
    url: '/orders'
  });
}

function getOrder(orderId) {
  return request({
    url: `/orders/${orderId}`
  });
}

function createOrderPayment(orderId) {
  return request({
    url: `/orders/${orderId}/pay`,
    method: 'POST'
  });
}

function syncOrderPayment(orderId) {
  return request({
    url: `/orders/${orderId}/payment-sync`,
    method: 'POST'
  });
}

function completeMockOrderPayment(orderId, paymentId) {
  return request({
    url: `/orders/${orderId}/mock-pay-success`,
    method: 'POST',
    data: {
      paymentId
    }
  });
}

module.exports = {
  completeMockOrderPayment,
  createOrder,
  createOrderPayment,
  getOrder,
  getOrders,
  syncOrderPayment
};

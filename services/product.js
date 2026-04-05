const { request } = require('./api');

function getProducts(params = {}) {
  return request({
    url: '/products',
    data: params
  });
}

function getProduct(productId) {
  return request({
    url: `/products/${productId}`
  });
}

function getProductSkus(productId) {
  return request({
    url: `/products/${productId}/skus`
  });
}

module.exports = {
  getProduct,
  getProducts,
  getProductSkus
};

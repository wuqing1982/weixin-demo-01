const { request } = require('./api');

function redeemCdk(code) {
  return request({
    url: '/cdk/redeem',
    method: 'POST',
    data: { code }
  });
}

function getMyRedemptions() {
  return request({
    url: '/cdk/my-redemptions',
    method: 'GET'
  });
}

module.exports = {
  redeemCdk,
  getMyRedemptions
};

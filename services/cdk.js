const { request } = require('./api');

function redeemCdk(code) {
  return request({
    url: '/cdk/redeem',
    method: 'POST',
    data: { code }
  });
}

module.exports = {
  redeemCdk
};

const { request } = require('./api');

function getMe() {
  return request({
    url: '/me'
  });
}

function getMembership() {
  return request({
    url: '/me/membership'
  });
}

function getCredits() {
  return request({
    url: '/me/credits'
  });
}

function getEntitlements() {
  return request({
    url: '/me/entitlements'
  });
}

function updateMyProfile(payload) {
  return request({
    url: '/me/profile',
    method: 'PUT',
    data: payload
  });
}

function getUpgradePreview(skuId) {
  return request({ url: '/me/upgrade-preview', data: { skuId } });
}

function bindPhone(code) {
  return request({
    url: '/me/bind-phone',
    method: 'POST',
    data: { code }
  });
}

module.exports = {
  bindPhone,
  getCredits,
  getEntitlements,
  getMe,
  getMembership,
  getUpgradePreview,
  updateMyProfile
};

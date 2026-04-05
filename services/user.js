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

module.exports = {
  getCredits,
  getEntitlements,
  getMe,
  getMembership,
  updateMyProfile
};

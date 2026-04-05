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

module.exports = {
  getCredits,
  getEntitlements,
  getMe,
  getMembership
};

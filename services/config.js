const { DEFAULT_RUNTIME_CONFIG } = require('../config/runtime');

function getConfig() {
  const app = getApp();
  const globalData = (app && app.globalData) || {};

  return {
    apiBaseUrl: globalData.apiBaseUrl || DEFAULT_RUNTIME_CONFIG.apiBaseUrl,
    staticBaseUrl: globalData.staticBaseUrl || DEFAULT_RUNTIME_CONFIG.staticBaseUrl
  };
}

module.exports = {
  getConfig
};

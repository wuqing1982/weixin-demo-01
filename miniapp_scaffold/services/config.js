const app = getApp();

function getConfig() {
  const globalData = (app && app.globalData) || {};
  return {
    apiBaseUrl: globalData.apiBaseUrl || 'http://127.0.0.1:8000/api',
    staticBaseUrl: globalData.staticBaseUrl || 'http://127.0.0.1:8000'
  };
}

module.exports = {
  getConfig
};

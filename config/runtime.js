/**
 * Environment profile configuration.
 * Switch CURRENT_ENV to target a different backend server.
 *
 * Profiles:
 *   'local'       → http://localhost:8000        (本地开发)
 *   'staging'     → https://stag.cps.vin         (测试服务器)
 *   'production'  → https://e.cps.vin            (生产环境)
 */
const ENV_PROFILES = {
  local: {
    apiBaseUrl: 'http://localhost:8000/api',
    staticBaseUrl: 'http://localhost:8000'
  },
  staging: {
    apiBaseUrl: 'https://stag.cps.vin/api',
    staticBaseUrl: 'https://stag.cps.vin'
  },
  production: {
    apiBaseUrl: 'https://e.cps.vin/api',
    staticBaseUrl: 'https://e.cps.vin'
  }
};

// <-- 切换这一行即可更换环境
const CURRENT_ENV = 'staging';

const DEFAULT_RUNTIME_CONFIG = ENV_PROFILES[CURRENT_ENV];

module.exports = {
  DEFAULT_RUNTIME_CONFIG
};

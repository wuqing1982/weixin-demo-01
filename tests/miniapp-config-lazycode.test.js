const assert = require('assert');
const fs = require('fs');
const path = require('path');

const appConfigPath = path.join(__dirname, '..', 'app.json');
const appConfig = JSON.parse(fs.readFileSync(appConfigPath, 'utf8'));

assert.strictEqual(
  appConfig.lazyCodeLoading,
  'requiredComponents',
  'miniapp should enable component lazy code loading for required components'
);

console.log('miniapp config lazy code loading tests passed');

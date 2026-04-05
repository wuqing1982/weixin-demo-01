const assert = require('assert');
const fs = require('fs');
const path = require('path');

const templatePath = path.join(__dirname, '..', 'pages', 'shared', 'scene-template.wxml');
const template = fs.readFileSync(templatePath, 'utf8');

assert(
  !template.includes('class="toolbar-group device-group"'),
  'device switch group should be removed from the toolbar'
);

assert(
  template.includes('class="toolbar-group editor-mode-group"'),
  'toolbar should include the red/green editor mode group'
);

assert(
  template.includes('floating-save-btn'),
  'editor mode should render a floating save button'
);

console.log('scene template toolbar layout tests passed');

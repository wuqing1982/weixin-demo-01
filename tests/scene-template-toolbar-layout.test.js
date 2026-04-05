const assert = require('assert');
const fs = require('fs');
const path = require('path');

const templatePath = path.join(__dirname, '..', 'pages', 'scene_runtime', 'index.wxml');
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
  template.includes('<view class="rate-control-row">') && template.includes('editor-mode-group'),
  'editor mode group should be rendered on the same toolbar row as the rate controls'
);

assert(
  template.includes('floating-save-btn'),
  'editor mode should render a floating save button'
);

assert(
  template.includes('floating-save-handle'),
  'floating save button should expose a dedicated drag handle'
);

assert(
  !template.includes('class="editor-panel"'),
  'legacy hotspot adjustment panel should be removed from edit mode'
);

console.log('scene template toolbar layout tests passed');

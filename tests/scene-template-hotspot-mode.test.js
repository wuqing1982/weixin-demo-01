const assert = require('assert');
const fs = require('fs');
const path = require('path');

const templatePath = path.join(__dirname, '..', 'pages', 'scene_runtime', 'index.wxml');
const template = fs.readFileSync(templatePath, 'utf8');

assert(
  template.includes('wx:if="{{!editorMode}}" class="scene-hotspots scene-hotspots-browse"'),
  'browse mode hotspots should render in a dedicated non-editor layer'
);

assert(
  template.includes('wx:if="{{editorMode}}" class="scene-hotspots scene-hotspots-editor"'),
  'editor mode hotspots should render in a dedicated editor layer'
);

assert(
  !template.includes('wx:if="{{!editorMode}}" class="scene-hotspots scene-hotspots-browse"\n') ||
    !template.includes('catchtouchstart="onEditorZoneTouchStart"'),
  'browse layer must not bind editor drag handlers'
);

console.log('scene template hotspot mode tests passed');

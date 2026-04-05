const assert = require('assert');
const {
  applyMoveDelta,
  applyResizeDelta,
  normalizeFloatingButtonPosition,
  applyFloatingButtonDelta
} = require('../pages/shared/hotspot-editor');

const baseRect = { l: 20, t: 30, w: 20, h: 20 };

function expectRect(actual, expected) {
  assert.deepStrictEqual(actual, expected);
}

expectRect(
  applyMoveDelta(baseRect, 70, -50),
  { l: 80, t: 0, w: 20, h: 20 }
);

expectRect(
  applyResizeDelta(baseRect, 'e', 70, 0),
  { l: 20, t: 30, w: 80, h: 20 }
);

expectRect(
  applyResizeDelta(baseRect, 'w', 18, 0),
  { l: 36, t: 30, w: 4, h: 20 }
);

expectRect(
  applyResizeDelta(baseRect, 'nw', 10, 12),
  { l: 30, t: 42, w: 10, h: 8 }
);

expectRect(
  applyResizeDelta(baseRect, 'n', 0, -40),
  { l: 20, t: 0, w: 20, h: 50 }
);

expectRect(
  normalizeFloatingButtonPosition({ x: 98, y: -5 }),
  { x: 90, y: 8 }
);

expectRect(
  applyFloatingButtonDelta({ x: 82, y: 76 }, 40, 20),
  { x: 90, y: 90 }
);

console.log('hotspot editor geometry tests passed');

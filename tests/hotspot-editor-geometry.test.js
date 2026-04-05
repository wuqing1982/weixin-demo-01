const assert = require('assert');
const {
  applyMoveDelta,
  applyResizeDelta,
  normalizeFloatingButtonPosition,
  applyFloatingButtonDelta
} = require('../shared/scene/hotspot-editor');

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
  normalizeFloatingButtonPosition({ left: 2, top: -5 }, { width: 375, height: 667 }),
  { left: 10, top: 20 }
);

expectRect(
  applyFloatingButtonDelta({ left: 10, top: 80 }, 40, 20, { width: 375, height: 667 }),
  { left: 50, top: 100 }
);

console.log('hotspot editor geometry tests passed');

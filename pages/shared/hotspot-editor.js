const MIN_HOTSPOT_SIZE = 4;
const FLOATING_BUTTON_MIN_X = 10;
const FLOATING_BUTTON_MAX_X = 90;
const FLOATING_BUTTON_MIN_Y = 8;
const FLOATING_BUTTON_MAX_Y = 90;

function roundPercent(value) {
  return Math.round(value * 100) / 100;
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function clampPercent(value) {
  const number = parseFloat(value);
  if (!Number.isFinite(number)) {
    return 0;
  }
  return roundPercent(clamp(number, 0, 100));
}

function normalizeEditorRect(rect) {
  const safeRect = rect || {};
  const width = roundPercent(clamp(clampPercent(safeRect.w), MIN_HOTSPOT_SIZE, 100));
  const height = roundPercent(clamp(clampPercent(safeRect.h), MIN_HOTSPOT_SIZE, 100));
  const left = roundPercent(clamp(clampPercent(safeRect.l), 0, 100 - width));
  const top = roundPercent(clamp(clampPercent(safeRect.t), 0, 100 - height));

  return {
    l: left,
    t: top,
    w: width,
    h: height
  };
}

function applyMoveDelta(startRect, deltaXPct, deltaYPct) {
  const rect = normalizeEditorRect(startRect);
  return {
    l: roundPercent(clamp(rect.l + deltaXPct, 0, 100 - rect.w)),
    t: roundPercent(clamp(rect.t + deltaYPct, 0, 100 - rect.h)),
    w: rect.w,
    h: rect.h
  };
}

function applyResizeDelta(startRect, handle, deltaXPct, deltaYPct) {
  const rect = normalizeEditorRect(startRect);
  const direction = String(handle || '').toLowerCase();
  let left = rect.l;
  let top = rect.t;
  let right = rect.l + rect.w;
  let bottom = rect.t + rect.h;

  if (direction.indexOf('w') >= 0) {
    left = clamp(left + deltaXPct, 0, right - MIN_HOTSPOT_SIZE);
  }
  if (direction.indexOf('e') >= 0) {
    right = clamp(right + deltaXPct, left + MIN_HOTSPOT_SIZE, 100);
  }
  if (direction.indexOf('n') >= 0) {
    top = clamp(top + deltaYPct, 0, bottom - MIN_HOTSPOT_SIZE);
  }
  if (direction.indexOf('s') >= 0) {
    bottom = clamp(bottom + deltaYPct, top + MIN_HOTSPOT_SIZE, 100);
  }

  return {
    l: roundPercent(left),
    t: roundPercent(top),
    w: roundPercent(right - left),
    h: roundPercent(bottom - top)
  };
}

function normalizeFloatingButtonPosition(position) {
  const safePosition = position || {};
  return {
    x: roundPercent(clamp(clampPercent(safePosition.x), FLOATING_BUTTON_MIN_X, FLOATING_BUTTON_MAX_X)),
    y: roundPercent(clamp(clampPercent(safePosition.y), FLOATING_BUTTON_MIN_Y, FLOATING_BUTTON_MAX_Y))
  };
}

function applyFloatingButtonDelta(startPosition, deltaXPct, deltaYPct) {
  const position = normalizeFloatingButtonPosition(startPosition);
  return normalizeFloatingButtonPosition({
    x: position.x + deltaXPct,
    y: position.y + deltaYPct
  });
}

module.exports = {
  MIN_HOTSPOT_SIZE,
  clampPercent,
  normalizeEditorRect,
  applyMoveDelta,
  applyResizeDelta,
  normalizeFloatingButtonPosition,
  applyFloatingButtonDelta
};

/**
 * Theme helpers shared across all pages.
 */

/**
 * Apply navigation bar colors to match the current theme.
 * Call this in each page's onShow / onLoad.
 * @param {string} theme - 'dark' or 'light'
 */
function updateNavBar(theme) {
  var isDark = theme !== 'light';
  wx.setNavigationBarColor({
    frontColor: isDark ? '#ffffff' : '#000000',
    backgroundColor: isDark ? '#0d1117' : '#f5f6f8',
    animation: { duration: 300, timingFunc: 'easeIn' }
  });
}

module.exports = { updateNavBar };

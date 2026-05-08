/**
 * Theme helpers shared across all pages.
 */

/**
 * Apply navigation bar colors to match the current theme.
 * Call this in each page's onShow / onLoad.
 * @param {string} theme - 'dark', 'light', or 'ocean'
 */
function updateNavBar(theme) {
  var config = {
    dark:  { frontColor: '#ffffff', backgroundColor: '#0b0b0c' },
    light: { frontColor: '#000000', backgroundColor: '#f5f6f8' },
    ocean:  { frontColor: '#ffffff', backgroundColor: '#041526' },
    notion: { frontColor: '#000000', backgroundColor: '#ffffff' }
  };
  var c = config[theme] || config.dark;
  wx.setNavigationBarColor({
    frontColor: c.frontColor,
    backgroundColor: c.backgroundColor,
    animation: { duration: 300, timingFunc: 'easeIn' }
  });
}

module.exports = { updateNavBar };

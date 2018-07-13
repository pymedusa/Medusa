const hooks = require('require-extension-hooks');
import jQuery from 'jquery';

// Setup browser environment
require('browser-env')();

// Setup jQuery
global.$ = jQuery(window);

// Setup vue files to be processed by `require-extension-hooks-vue`
hooks('vue').plugin('vue').push();
// Setup vue and js files to be processed by `require-extension-hooks-babel`
// This also requires `require-extension-hooks-vue`
hooks(['vue', 'js']).plugin('babel').push();

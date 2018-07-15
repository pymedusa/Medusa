import browserEnv from 'browser-env';
import jQuery from 'jquery';

const hooks = require('require-extension-hooks');

// Setup browser environment
browserEnv();

// Setup document variables
const baseElement = document.createElement('base');
baseElement.setAttribute('href', 'http://localhost:8081');
document.head.appendChild(baseElement);

// Setup jQuery
global.$ = jQuery(window);

// Setup vue files to be processed by `require-extension-hooks-vue`
hooks('vue').plugin('vue').push();
// Setup vue and js files to be processed by `require-extension-hooks-babel`
// This also requires `require-extension-hooks-vue`
hooks(['vue', 'js']).plugin('babel').push();

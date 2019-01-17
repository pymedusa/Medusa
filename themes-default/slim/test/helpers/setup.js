import browserEnv from 'browser-env';
import jQuery from 'jquery';
import hooks from 'require-extension-hooks';

// Setup browser environment
browserEnv({
    // This needs to be set otherwise we get errors from vue-router
    url: 'http://localhost:8081/'
});

// Setup document variables
const baseElement = document.createElement('base');
baseElement.setAttribute('href', 'http://localhost:8081');
document.head.append(baseElement);

// Setup jQuery
global.$ = jQuery(window);

// Setup vue files to be processed by `require-extension-hooks-vue`
hooks('vue').plugin('vue').push();
// Setup vue and js files to be processed by `require-extension-hooks-babel`
// This also requires `require-extension-hooks-vue`
hooks(['vue', 'js']).plugin('babel').push();

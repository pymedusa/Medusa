// ./test/helpers/setup.js

// Setup browser environment
require('browser-env')();
const hooks = require('require-extension-hooks');
const Vue = require('vue');
const VueRouter = require('vue-router');
const VueResource = require('vue-resource');

// Setup Vue.js to remove production tip
Vue.config.productionTip = false;

// Setup vue globals
Vue.use(VueRouter);
Vue.use(VueResource);

// Setup vue files to be processed by `require-extension-hooks-vue`
hooks('vue').plugin('vue').push();
// Setup vue and js files to be processed by `require-extension-hooks-babel`
hooks(['vue', 'js']).plugin('babel').push();

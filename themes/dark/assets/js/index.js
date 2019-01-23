(window["webpackJsonp"] = window["webpackJsonp"] || []).push([["index"],{

/***/ "./src/index.js":
/*!**********************!*\
  !*** ./src/index.js ***!
  \**********************/
/*! no exports provided */
/***/ (function(module, __webpack_exports__, __webpack_require__) {

"use strict";
eval("__webpack_require__.r(__webpack_exports__);\n/* harmony import */ var jquery__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! jquery */ \"./node_modules/jquery/dist/jquery.js\");\n/* harmony import */ var jquery__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(jquery__WEBPACK_IMPORTED_MODULE_0__);\n/* harmony import */ var bootstrap__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! bootstrap */ \"./node_modules/bootstrap/dist/js/npm.js\");\n/* harmony import */ var bootstrap__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(bootstrap__WEBPACK_IMPORTED_MODULE_1__);\n/* harmony import */ var bootstrap_dist_css_bootstrap_min_css__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! bootstrap/dist/css/bootstrap.min.css */ \"./node_modules/bootstrap/dist/css/bootstrap.min.css\");\n/* harmony import */ var bootstrap_dist_css_bootstrap_min_css__WEBPACK_IMPORTED_MODULE_2___default = /*#__PURE__*/__webpack_require__.n(bootstrap_dist_css_bootstrap_min_css__WEBPACK_IMPORTED_MODULE_2__);\n/* harmony import */ var vue_snotify_styles_material_css__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! vue-snotify/styles/material.css */ \"./node_modules/vue-snotify/styles/material.css\");\n/* harmony import */ var vue_snotify_styles_material_css__WEBPACK_IMPORTED_MODULE_3___default = /*#__PURE__*/__webpack_require__.n(vue_snotify_styles_material_css__WEBPACK_IMPORTED_MODULE_3__);\n/* harmony import */ var _vendor_js_tablesorter__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(/*! ../vendor/js/tablesorter */ \"./vendor/js/tablesorter.js\");\n/* harmony import */ var _vendor_css_open_sans_css__WEBPACK_IMPORTED_MODULE_5__ = __webpack_require__(/*! ../vendor/css/open-sans.css */ \"./vendor/css/open-sans.css\");\n/* harmony import */ var _vendor_css_open_sans_css__WEBPACK_IMPORTED_MODULE_5___default = /*#__PURE__*/__webpack_require__.n(_vendor_css_open_sans_css__WEBPACK_IMPORTED_MODULE_5__);\n/* harmony import */ var vue__WEBPACK_IMPORTED_MODULE_6__ = __webpack_require__(/*! vue */ \"./node_modules/vue/dist/vue.esm.js\");\n/* harmony import */ var vuex__WEBPACK_IMPORTED_MODULE_7__ = __webpack_require__(/*! vuex */ \"./node_modules/vuex/dist/vuex.esm.js\");\n/* harmony import */ var vue_meta__WEBPACK_IMPORTED_MODULE_8__ = __webpack_require__(/*! vue-meta */ \"./node_modules/vue-meta/lib/vue-meta.js\");\n/* harmony import */ var vue_meta__WEBPACK_IMPORTED_MODULE_8___default = /*#__PURE__*/__webpack_require__.n(vue_meta__WEBPACK_IMPORTED_MODULE_8__);\n/* harmony import */ var vue_router__WEBPACK_IMPORTED_MODULE_9__ = __webpack_require__(/*! vue-router */ \"./node_modules/vue-router/dist/vue-router.esm.js\");\n/* harmony import */ var vue_native_websocket__WEBPACK_IMPORTED_MODULE_10__ = __webpack_require__(/*! vue-native-websocket */ \"./node_modules/vue-native-websocket/dist/build.js\");\n/* harmony import */ var vue_native_websocket__WEBPACK_IMPORTED_MODULE_10___default = /*#__PURE__*/__webpack_require__.n(vue_native_websocket__WEBPACK_IMPORTED_MODULE_10__);\n/* harmony import */ var vue_async_computed__WEBPACK_IMPORTED_MODULE_11__ = __webpack_require__(/*! vue-async-computed */ \"./node_modules/vue-async-computed/dist/vue-async-computed.esm.js\");\n/* harmony import */ var vue_js_toggle_button__WEBPACK_IMPORTED_MODULE_12__ = __webpack_require__(/*! vue-js-toggle-button */ \"./node_modules/vue-js-toggle-button/dist/index.js\");\n/* harmony import */ var vue_js_toggle_button__WEBPACK_IMPORTED_MODULE_12___default = /*#__PURE__*/__webpack_require__.n(vue_js_toggle_button__WEBPACK_IMPORTED_MODULE_12__);\n/* harmony import */ var vue_snotify__WEBPACK_IMPORTED_MODULE_13__ = __webpack_require__(/*! vue-snotify */ \"./node_modules/vue-snotify/vue-snotify.esm.js\");\n/* harmony import */ var vue_truncate_collapsed__WEBPACK_IMPORTED_MODULE_14__ = __webpack_require__(/*! vue-truncate-collapsed */ \"./node_modules/vue-truncate-collapsed/dist/vue-truncate-collapsed.es.js\");\n/* harmony import */ var axios__WEBPACK_IMPORTED_MODULE_15__ = __webpack_require__(/*! axios */ \"./node_modules/axios/index.js\");\n/* harmony import */ var axios__WEBPACK_IMPORTED_MODULE_15___default = /*#__PURE__*/__webpack_require__.n(axios__WEBPACK_IMPORTED_MODULE_15__);\n/* harmony import */ var lodash_debounce__WEBPACK_IMPORTED_MODULE_16__ = __webpack_require__(/*! lodash/debounce */ \"./node_modules/lodash/debounce.js\");\n/* harmony import */ var lodash_debounce__WEBPACK_IMPORTED_MODULE_16___default = /*#__PURE__*/__webpack_require__.n(lodash_debounce__WEBPACK_IMPORTED_MODULE_16__);\n/* harmony import */ var _store__WEBPACK_IMPORTED_MODULE_17__ = __webpack_require__(/*! ./store */ \"./src/store/index.js\");\n/* harmony import */ var _router__WEBPACK_IMPORTED_MODULE_18__ = __webpack_require__(/*! ./router */ \"./src/router.js\");\n/* harmony import */ var _utils__WEBPACK_IMPORTED_MODULE_19__ = __webpack_require__(/*! ./utils */ \"./src/utils.js\");\n/* harmony import */ var _api__WEBPACK_IMPORTED_MODULE_20__ = __webpack_require__(/*! ./api */ \"./src/api.js\");\n/* harmony import */ var _components__WEBPACK_IMPORTED_MODULE_21__ = __webpack_require__(/*! ./components */ \"./src/components/index.js\");\n/* eslint-disable import/no-unassigned-import */\n\n\n\n\n\n\n/* eslint-enable import/no-unassigned-import */\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\nif (window) {\n  window.isDevelopment = _utils__WEBPACK_IMPORTED_MODULE_19__[\"isDevelopment\"]; // Adding libs to window so mako files can use them\n\n  window.$ = jquery__WEBPACK_IMPORTED_MODULE_0___default.a;\n  window.jQuery = jquery__WEBPACK_IMPORTED_MODULE_0___default.a;\n  window.Vue = vue__WEBPACK_IMPORTED_MODULE_6__[\"default\"];\n  window.Vuex = vuex__WEBPACK_IMPORTED_MODULE_7__[\"default\"];\n  window.VueMeta = vue_meta__WEBPACK_IMPORTED_MODULE_8___default.a;\n  window.VueRouter = vue_router__WEBPACK_IMPORTED_MODULE_9__[\"default\"];\n  window.VueNativeSock = vue_native_websocket__WEBPACK_IMPORTED_MODULE_10___default.a;\n  window.AsyncComputed = vue_async_computed__WEBPACK_IMPORTED_MODULE_11__[\"default\"];\n  window.ToggleButton = vue_js_toggle_button__WEBPACK_IMPORTED_MODULE_12__[\"ToggleButton\"];\n  window.Snotify = vue_snotify__WEBPACK_IMPORTED_MODULE_13__[\"default\"];\n  window.Truncate = vue_truncate_collapsed__WEBPACK_IMPORTED_MODULE_14__[\"default\"];\n  window.axios = axios__WEBPACK_IMPORTED_MODULE_15___default.a;\n  window._ = {\n    debounce: lodash_debounce__WEBPACK_IMPORTED_MODULE_16___default.a\n  };\n  window.store = _store__WEBPACK_IMPORTED_MODULE_17__[\"default\"];\n  window.router = _router__WEBPACK_IMPORTED_MODULE_18__[\"default\"];\n  window.apiRoute = _api__WEBPACK_IMPORTED_MODULE_20__[\"apiRoute\"];\n  window.apiv1 = _api__WEBPACK_IMPORTED_MODULE_20__[\"apiv1\"];\n  window.api = _api__WEBPACK_IMPORTED_MODULE_20__[\"api\"];\n  window.MEDUSA = {\n    common: {},\n    config: {},\n    home: {},\n    addShows: {}\n  };\n  window.webRoot = _api__WEBPACK_IMPORTED_MODULE_20__[\"webRoot\"];\n  window.apiKey = _api__WEBPACK_IMPORTED_MODULE_20__[\"apiKey\"];\n  window.apiRoot = _api__WEBPACK_IMPORTED_MODULE_20__[\"webRoot\"] + '/api/v2/'; // Push pages that load via a vue file but still use `el` for mounting\n\n  window.components = [];\n  window.components.push(_components__WEBPACK_IMPORTED_MODULE_21__[\"AddShowOptions\"]);\n  window.components.push(_components__WEBPACK_IMPORTED_MODULE_21__[\"AnidbReleaseGroupUi\"]);\n  window.components.push(_components__WEBPACK_IMPORTED_MODULE_21__[\"AppHeader\"]);\n  window.components.push(_components__WEBPACK_IMPORTED_MODULE_21__[\"AppLink\"]);\n  window.components.push(_components__WEBPACK_IMPORTED_MODULE_21__[\"Asset\"]);\n  window.components.push(_components__WEBPACK_IMPORTED_MODULE_21__[\"Backstretch\"]);\n  window.components.push(_components__WEBPACK_IMPORTED_MODULE_21__[\"ConfigTemplate\"]);\n  window.components.push(_components__WEBPACK_IMPORTED_MODULE_21__[\"ConfigTextbox\"]);\n  window.components.push(_components__WEBPACK_IMPORTED_MODULE_21__[\"ConfigTextboxNumber\"]);\n  window.components.push(_components__WEBPACK_IMPORTED_MODULE_21__[\"ConfigToggleSlider\"]);\n  window.components.push(_components__WEBPACK_IMPORTED_MODULE_21__[\"FileBrowser\"]);\n  window.components.push(_components__WEBPACK_IMPORTED_MODULE_21__[\"Home\"]);\n  window.components.push(_components__WEBPACK_IMPORTED_MODULE_21__[\"LanguageSelect\"]);\n  window.components.push(_components__WEBPACK_IMPORTED_MODULE_21__[\"ManualPostProcess\"]);\n  window.components.push(_components__WEBPACK_IMPORTED_MODULE_21__[\"NamePattern\"]);\n  window.components.push(_components__WEBPACK_IMPORTED_MODULE_21__[\"PlotInfo\"]);\n  window.components.push(_components__WEBPACK_IMPORTED_MODULE_21__[\"QualityPill\"]); // This component is also used in a hack/workaround in `./static/js/ajax-episode-search.js`\n\n  window.components.push(_components__WEBPACK_IMPORTED_MODULE_21__[\"RootDirs\"]);\n  window.components.push(_components__WEBPACK_IMPORTED_MODULE_21__[\"ScrollButtons\"]);\n  window.components.push(_components__WEBPACK_IMPORTED_MODULE_21__[\"SelectList\"]);\n  window.components.push(_components__WEBPACK_IMPORTED_MODULE_21__[\"Show\"]);\n  window.components.push(_components__WEBPACK_IMPORTED_MODULE_21__[\"ShowSelector\"]);\n  window.components.push(_components__WEBPACK_IMPORTED_MODULE_21__[\"SnatchSelection\"]);\n  window.components.push(_components__WEBPACK_IMPORTED_MODULE_21__[\"StateSwitch\"]);\n  window.components.push(_components__WEBPACK_IMPORTED_MODULE_21__[\"Status\"]);\n}\n\nvar UTIL = {\n  exec: function exec(controller, action) {\n    var ns = MEDUSA;\n    action = action === undefined ? 'init' : action;\n\n    if (controller !== '' && ns[controller] && typeof ns[controller][action] === 'function') {\n      ns[controller][action]();\n    }\n  },\n  init: function init() {\n    jquery__WEBPACK_IMPORTED_MODULE_0___default()('[v-cloak]').removeAttr('v-cloak');\n    var _document = document,\n        body = _document.body;\n    var controller = body.getAttribute('data-controller');\n    var action = body.getAttribute('data-action');\n    UTIL.exec('common'); // Load common\n\n    UTIL.exec(controller); // Load MEDUSA[controller]\n\n    UTIL.exec(controller, action); // Load MEDUSA[controller][action]\n\n    window.dispatchEvent(new Event('medusa-loaded'));\n  }\n};\nvar pathname = window.location.pathname;\n\nif (!pathname.includes('/login') && !pathname.includes('/apibuilder')) {\n  _api__WEBPACK_IMPORTED_MODULE_20__[\"api\"].get('config/main').then(function (response) {\n    jquery__WEBPACK_IMPORTED_MODULE_0___default.a.extend(MEDUSA.config, response.data);\n    MEDUSA.config.themeSpinner = MEDUSA.config.themeName === 'dark' ? '-dark' : '';\n    MEDUSA.config.loading = '<img src=\"images/loading16' + MEDUSA.config.themeSpinner + '.gif\" height=\"16\" width=\"16\" />';\n    jquery__WEBPACK_IMPORTED_MODULE_0___default()(document).ready(UTIL.init);\n\n    MEDUSA.config.indexers.indexerIdToName = function (indexerId) {\n      if (!indexerId) {\n        return '';\n      }\n\n      return Object.keys(MEDUSA.config.indexers.config.indexers).filter(function (indexer) {\n        // eslint-disable-line array-callback-return\n        if (MEDUSA.config.indexers.config.indexers[indexer].id === parseInt(indexerId, 10)) {\n          return MEDUSA.config.indexers.config.indexers[indexer].name;\n        }\n      })[0];\n    };\n\n    MEDUSA.config.indexers.nameToIndexerId = function (name) {\n      if (!name) {\n        return '';\n      }\n\n      return MEDUSA.config.indexers.config.indexers[name];\n    };\n  }).catch(function (error) {\n    console.debug(error);\n    alert('Unable to connect to Medusa!'); // eslint-disable-line no-alert\n  });\n}\n\n//# sourceURL=webpack:///./src/index.js?");

/***/ })

},[["./src/index.js","vendors","medusa-runtime"]]]);
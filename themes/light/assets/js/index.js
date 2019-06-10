(window["webpackJsonp"] = window["webpackJsonp"] || []).push([["index"],{

/***/ "./src/index.js":
/*!**********************!*\
  !*** ./src/index.js ***!
  \**********************/
/*! no exports provided */
/***/ (function(module, __webpack_exports__, __webpack_require__) {

"use strict";
eval("__webpack_require__.r(__webpack_exports__);\n/* harmony import */ var jquery__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! jquery */ \"./node_modules/jquery/dist/jquery.js\");\n/* harmony import */ var jquery__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(jquery__WEBPACK_IMPORTED_MODULE_0__);\n/* harmony import */ var bootstrap__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! bootstrap */ \"./node_modules/bootstrap/dist/js/npm.js\");\n/* harmony import */ var bootstrap__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(bootstrap__WEBPACK_IMPORTED_MODULE_1__);\n/* harmony import */ var bootstrap_dist_css_bootstrap_min_css__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! bootstrap/dist/css/bootstrap.min.css */ \"./node_modules/bootstrap/dist/css/bootstrap.min.css\");\n/* harmony import */ var bootstrap_dist_css_bootstrap_min_css__WEBPACK_IMPORTED_MODULE_2___default = /*#__PURE__*/__webpack_require__.n(bootstrap_dist_css_bootstrap_min_css__WEBPACK_IMPORTED_MODULE_2__);\n/* harmony import */ var vue_snotify_styles_material_css__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! vue-snotify/styles/material.css */ \"./node_modules/vue-snotify/styles/material.css\");\n/* harmony import */ var vue_snotify_styles_material_css__WEBPACK_IMPORTED_MODULE_3___default = /*#__PURE__*/__webpack_require__.n(vue_snotify_styles_material_css__WEBPACK_IMPORTED_MODULE_3__);\n/* harmony import */ var _vendor_js_tablesorter__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(/*! ../vendor/js/tablesorter */ \"./vendor/js/tablesorter.js\");\n/* harmony import */ var _vendor_css_open_sans_css__WEBPACK_IMPORTED_MODULE_5__ = __webpack_require__(/*! ../vendor/css/open-sans.css */ \"./vendor/css/open-sans.css\");\n/* harmony import */ var _vendor_css_open_sans_css__WEBPACK_IMPORTED_MODULE_5___default = /*#__PURE__*/__webpack_require__.n(_vendor_css_open_sans_css__WEBPACK_IMPORTED_MODULE_5__);\n/* harmony import */ var vue__WEBPACK_IMPORTED_MODULE_6__ = __webpack_require__(/*! vue */ \"./node_modules/vue/dist/vue.esm.js\");\n/* harmony import */ var vuex__WEBPACK_IMPORTED_MODULE_7__ = __webpack_require__(/*! vuex */ \"./node_modules/vuex/dist/vuex.esm.js\");\n/* harmony import */ var vue_js_toggle_button__WEBPACK_IMPORTED_MODULE_8__ = __webpack_require__(/*! vue-js-toggle-button */ \"./node_modules/vue-js-toggle-button/dist/index.js\");\n/* harmony import */ var vue_js_toggle_button__WEBPACK_IMPORTED_MODULE_8___default = /*#__PURE__*/__webpack_require__.n(vue_js_toggle_button__WEBPACK_IMPORTED_MODULE_8__);\n/* harmony import */ var axios__WEBPACK_IMPORTED_MODULE_9__ = __webpack_require__(/*! axios */ \"./node_modules/axios/index.js\");\n/* harmony import */ var axios__WEBPACK_IMPORTED_MODULE_9___default = /*#__PURE__*/__webpack_require__.n(axios__WEBPACK_IMPORTED_MODULE_9__);\n/* harmony import */ var lodash_debounce__WEBPACK_IMPORTED_MODULE_10__ = __webpack_require__(/*! lodash/debounce */ \"./node_modules/lodash/debounce.js\");\n/* harmony import */ var lodash_debounce__WEBPACK_IMPORTED_MODULE_10___default = /*#__PURE__*/__webpack_require__.n(lodash_debounce__WEBPACK_IMPORTED_MODULE_10__);\n/* harmony import */ var _store__WEBPACK_IMPORTED_MODULE_11__ = __webpack_require__(/*! ./store */ \"./src/store/index.js\");\n/* harmony import */ var _router__WEBPACK_IMPORTED_MODULE_12__ = __webpack_require__(/*! ./router */ \"./src/router/index.js\");\n/* harmony import */ var _api__WEBPACK_IMPORTED_MODULE_13__ = __webpack_require__(/*! ./api */ \"./src/api.js\");\n/* harmony import */ var _components__WEBPACK_IMPORTED_MODULE_14__ = __webpack_require__(/*! ./components */ \"./src/components/index.js\");\n/* harmony import */ var _global_vue_shim__WEBPACK_IMPORTED_MODULE_15__ = __webpack_require__(/*! ./global-vue-shim */ \"./src/global-vue-shim.js\");\nfunction _objectSpread(target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i] != null ? arguments[i] : {}; var ownKeys = Object.keys(source); if (typeof Object.getOwnPropertySymbols === 'function') { ownKeys = ownKeys.concat(Object.getOwnPropertySymbols(source).filter(function (sym) { return Object.getOwnPropertyDescriptor(source, sym).enumerable; })); } ownKeys.forEach(function (key) { _defineProperty(target, key, source[key]); }); } return target; }\n\nfunction _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }\n\n/* eslint-disable import/no-unassigned-import */\n\n\n\n\n\n\n/* eslint-enable import/no-unassigned-import */\n\n\n\n\n\n\n\n\n\n\n\n\nif (window) {\n  // @TODO: Remove this before v1.0.0\n  window.globalVueShim = _global_vue_shim__WEBPACK_IMPORTED_MODULE_15__[\"default\"]; // Adding libs to window so mako files can use them\n\n  window.$ = jquery__WEBPACK_IMPORTED_MODULE_0___default.a;\n  window.jQuery = jquery__WEBPACK_IMPORTED_MODULE_0___default.a;\n  window.Vue = vue__WEBPACK_IMPORTED_MODULE_6__[\"default\"];\n  window.Vuex = vuex__WEBPACK_IMPORTED_MODULE_7__[\"default\"];\n  window.ToggleButton = vue_js_toggle_button__WEBPACK_IMPORTED_MODULE_8__[\"ToggleButton\"];\n  window.axios = axios__WEBPACK_IMPORTED_MODULE_9___default.a;\n  window._ = {\n    debounce: (lodash_debounce__WEBPACK_IMPORTED_MODULE_10___default())\n  };\n  window.store = _store__WEBPACK_IMPORTED_MODULE_11__[\"default\"];\n  window.router = _router__WEBPACK_IMPORTED_MODULE_12__[\"default\"];\n  window.apiRoute = _api__WEBPACK_IMPORTED_MODULE_13__[\"apiRoute\"];\n  window.apiv1 = _api__WEBPACK_IMPORTED_MODULE_13__[\"apiv1\"];\n  window.api = _api__WEBPACK_IMPORTED_MODULE_13__[\"api\"];\n  window.MEDUSA = {\n    common: {},\n    config: {},\n    home: {},\n    addShows: {}\n  };\n  window.webRoot = _api__WEBPACK_IMPORTED_MODULE_13__[\"webRoot\"];\n  window.apiKey = _api__WEBPACK_IMPORTED_MODULE_13__[\"apiKey\"]; // @FIXME: (sharkykh) This component is used in a hack/workaround in `static/js/ajax-episode-search.js`\n\n  window.componentQualityPill = _components__WEBPACK_IMPORTED_MODULE_14__[\"QualityPill\"]; // Push x-template components to this array to register them globally\n\n  window.components = [];\n}\n\nconst UTIL = {\n  exec(controller, action) {\n    const ns = MEDUSA;\n    action = action === undefined ? 'init' : action;\n\n    if (controller !== '' && ns[controller] && typeof ns[controller][action] === 'function') {\n      ns[controller][action]();\n    }\n  },\n\n  init() {\n    jquery__WEBPACK_IMPORTED_MODULE_0___default()('[v-cloak]').removeAttr('v-cloak');\n    const {\n      body\n    } = document;\n    const controller = body.getAttribute('data-controller');\n    const action = body.getAttribute('data-action');\n    UTIL.exec('common'); // Load common\n\n    UTIL.exec(controller); // Load MEDUSA[controller]\n\n    UTIL.exec(controller, action); // Load MEDUSA[controller][action]\n\n    window.dispatchEvent(new Event('medusa-loaded'));\n  }\n\n};\nconst {\n  pathname\n} = window.location;\n\nif (!pathname.includes('/login') && !pathname.includes('/apibuilder')) {\n  const configLoaded = event => {\n    const data = event.detail;\n    const themeSpinner = data.themeName === 'dark' ? '-dark' : '';\n    MEDUSA.config = _objectSpread({}, MEDUSA.config, data, {\n      themeSpinner,\n      loading: '<img src=\"images/loading16' + themeSpinner + '.gif\" height=\"16\" width=\"16\" />'\n    });\n    jquery__WEBPACK_IMPORTED_MODULE_0___default()(document).ready(UTIL.init);\n  };\n\n  window.addEventListener('medusa-config-loaded', configLoaded, {\n    once: true\n  });\n}\n\n//# sourceURL=webpack:///./src/index.js?");

/***/ })

},[["./src/index.js","vendors","medusa-runtime","vendors~date-fns"]]]);
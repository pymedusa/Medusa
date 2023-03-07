"use strict";
/*
 * ATTENTION: The "eval" devtool has been used (maybe by default in mode: "development").
 * This devtool is neither made for production nor for readable output files.
 * It uses "eval()" calls to create a separate source file in the browser devtools.
 * If you are trying to read the output file, select a different devtool (https://webpack.js.org/configuration/devtool/)
 * or disable the default devtool with "devtool: false".
 * If you are looking for production-ready output files, see mode: "production" (https://webpack.js.org/configuration/mode/).
 */
(self["webpackChunkslim"] = self["webpackChunkslim"] || []).push([["index"],{

/***/ "./src/index.js":
/*!**********************!*\
  !*** ./src/index.js ***!
  \**********************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

eval("__webpack_require__.r(__webpack_exports__);\n/* harmony import */ var jquery__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! jquery */ \"./node_modules/jquery/dist/jquery.js\");\n/* harmony import */ var jquery__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(jquery__WEBPACK_IMPORTED_MODULE_0__);\n/* harmony import */ var bootstrap__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! bootstrap */ \"./node_modules/bootstrap/dist/js/npm.js\");\n/* harmony import */ var bootstrap__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(bootstrap__WEBPACK_IMPORTED_MODULE_1__);\n/* harmony import */ var bootstrap_dist_css_bootstrap_min_css__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! bootstrap/dist/css/bootstrap.min.css */ \"./node_modules/bootstrap/dist/css/bootstrap.min.css\");\n/* harmony import */ var vue_snotify_styles_material_css__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! vue-snotify/styles/material.css */ \"./node_modules/vue-snotify/styles/material.css\");\n/* harmony import */ var _vendor_js_tablesorter__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(/*! ../vendor/js/tablesorter */ \"./vendor/js/tablesorter.js\");\n/* harmony import */ var _vendor_css_open_sans_css__WEBPACK_IMPORTED_MODULE_5__ = __webpack_require__(/*! ../vendor/css/open-sans.css */ \"./vendor/css/open-sans.css\");\n/* harmony import */ var _global_vue_shim__WEBPACK_IMPORTED_MODULE_6__ = __webpack_require__(/*! ./global-vue-shim */ \"./src/global-vue-shim.js\");\n/* eslint-disable import/no-unassigned-import */\n\n\n\n\n\n\n/* eslint-enable import/no-unassigned-import */\n\n\n\nif (window) {\n  // @TODO: Remove this before v1.0.0\n  window.globalVueShim = _global_vue_shim__WEBPACK_IMPORTED_MODULE_6__[\"default\"]; // Adding libs to window so mako files can use them\n\n  window.$ = (jquery__WEBPACK_IMPORTED_MODULE_0___default());\n  window.jQuery = (jquery__WEBPACK_IMPORTED_MODULE_0___default());\n  window.MEDUSA = {\n    common: {},\n    config: {\n      general: {},\n      layout: {}\n    },\n    home: {},\n    addShows: {}\n  };\n}\n\nconst UTIL = {\n  init() {\n    jquery__WEBPACK_IMPORTED_MODULE_0___default()('[v-cloak]').removeAttr('v-cloak');\n    window.dispatchEvent(new Event('medusa-loaded'));\n  }\n\n};\nconst {\n  pathname\n} = window.location;\n\nif (!pathname.includes('/login') && !pathname.includes('/apibuilder')) {\n  const configLoaded = event => {\n    const {\n      general,\n      layout\n    } = event.detail;\n    MEDUSA.config.general = { ...MEDUSA.config.general,\n      ...general\n    };\n    const themeSpinner = layout.themeName === 'dark' ? '-dark' : '';\n    MEDUSA.config.layout = { ...MEDUSA.config.layout,\n      ...layout,\n      themeSpinner,\n      loading: '<img src=\"images/loading16' + themeSpinner + '.gif\" height=\"16\" width=\"16\" />'\n    };\n    jquery__WEBPACK_IMPORTED_MODULE_0___default()(document).ready(UTIL.init);\n  };\n\n  window.addEventListener('medusa-config-loaded', configLoaded, {\n    once: true\n  });\n}\n\n//# sourceURL=webpack://slim/./src/index.js?");

/***/ })

},
/******/ __webpack_require__ => { // webpackRuntimeModules
/******/ var __webpack_exec__ = (moduleId) => (__webpack_require__(__webpack_require__.s = moduleId))
/******/ __webpack_require__.O(0, ["medusa-runtime","vendors~date-fns"], () => (__webpack_exec__("./src/index.js")));
/******/ var __webpack_exports__ = __webpack_require__.O();
/******/ }
]);
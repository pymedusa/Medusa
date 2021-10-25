/*
 * ATTENTION: The "eval" devtool has been used (maybe by default in mode: "development").
 * This devtool is neither made for production nor for readable output files.
 * It uses "eval()" calls to create a separate source file in the browser devtools.
 * If you are trying to read the output file, select a different devtool (https://webpack.js.org/configuration/devtool/)
 * or disable the default devtool with "devtool: false".
 * If you are looking for production-ready output files, see mode: "production" (https://webpack.js.org/configuration/mode/).
 */
(self["webpackChunkslim"] = self["webpackChunkslim"] || []).push([["src_components_log-reporter_vue"],{

/***/ "./node_modules/babel-loader/lib/index.js??clonedRuleSet-1[0].rules[0]!./node_modules/vue-loader/lib/index.js??vue-loader-options!./src/components/log-reporter.vue?vue&type=script&lang=js&":
/*!***************************************************************************************************************************************************************************************************!*\
  !*** ./node_modules/babel-loader/lib/index.js??clonedRuleSet-1[0].rules[0]!./node_modules/vue-loader/lib/index.js??vue-loader-options!./src/components/log-reporter.vue?vue&type=script&lang=js& ***!
  \***************************************************************************************************************************************************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
eval("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   \"default\": () => (__WEBPACK_DEFAULT_EXPORT__)\n/* harmony export */ });\n/* harmony import */ var vuex__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! vuex */ \"./node_modules/vuex/dist/vuex.esm.js\");\n/* harmony import */ var _api__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ../api */ \"./src/api.js\");\n//\n//\n//\n//\n//\n//\n//\n//\n//\n//\n//\n//\n//\n//\n//\n\n\n/* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = ({\n  name: 'log-reporter',\n  props: {\n    level: {\n      type: String,\n      default: 'ERROR'\n    }\n  },\n\n  data() {\n    return {\n      logs: []\n    };\n  },\n\n  mounted() {\n    this.getLogs();\n  },\n\n  computed: { ...(0,vuex__WEBPACK_IMPORTED_MODULE_1__.mapState)({\n      loggingLevels: state => state.config.general.logs.loggingLevels\n    }),\n\n    header() {\n      const {\n        loggingLevels,\n        $route\n      } = this;\n\n      if (Number($route.query.level) === loggingLevels.warning) {\n        return 'Warning Logs';\n      }\n\n      return 'Error Logs';\n    }\n\n  },\n  methods: {\n    async getLogs() {\n      const {\n        level\n      } = this;\n\n      try {\n        const {\n          data\n        } = await _api__WEBPACK_IMPORTED_MODULE_0__.api.get('logreporter', {\n          params: {\n            level\n          }\n        });\n        this.logs = data;\n      } catch (error) {\n        this.$snotify.error(`Error while trying to get logs with level ${level}`, 'Error');\n      }\n    }\n\n  }\n});\n\n//# sourceURL=webpack://slim/./src/components/log-reporter.vue?./node_modules/babel-loader/lib/index.js??clonedRuleSet-1%5B0%5D.rules%5B0%5D!./node_modules/vue-loader/lib/index.js??vue-loader-options");

/***/ }),

/***/ "./src/components/log-reporter.vue":
/*!*****************************************!*\
  !*** ./src/components/log-reporter.vue ***!
  \*****************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
eval("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   \"default\": () => (__WEBPACK_DEFAULT_EXPORT__)\n/* harmony export */ });\n/* harmony import */ var _log_reporter_vue_vue_type_template_id_8d3e674c___WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ./log-reporter.vue?vue&type=template&id=8d3e674c& */ \"./src/components/log-reporter.vue?vue&type=template&id=8d3e674c&\");\n/* harmony import */ var _log_reporter_vue_vue_type_script_lang_js___WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ./log-reporter.vue?vue&type=script&lang=js& */ \"./src/components/log-reporter.vue?vue&type=script&lang=js&\");\n/* harmony import */ var _node_modules_vue_loader_lib_runtime_componentNormalizer_js__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! !../../node_modules/vue-loader/lib/runtime/componentNormalizer.js */ \"./node_modules/vue-loader/lib/runtime/componentNormalizer.js\");\n\n\n\n\n\n/* normalize component */\n;\nvar component = (0,_node_modules_vue_loader_lib_runtime_componentNormalizer_js__WEBPACK_IMPORTED_MODULE_2__.default)(\n  _log_reporter_vue_vue_type_script_lang_js___WEBPACK_IMPORTED_MODULE_1__.default,\n  _log_reporter_vue_vue_type_template_id_8d3e674c___WEBPACK_IMPORTED_MODULE_0__.render,\n  _log_reporter_vue_vue_type_template_id_8d3e674c___WEBPACK_IMPORTED_MODULE_0__.staticRenderFns,\n  false,\n  null,\n  null,\n  null\n  \n)\n\n/* hot reload */\nif (false) { var api; }\ncomponent.options.__file = \"src/components/log-reporter.vue\"\n/* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (component.exports);\n\n//# sourceURL=webpack://slim/./src/components/log-reporter.vue?");

/***/ }),

/***/ "./src/components/log-reporter.vue?vue&type=script&lang=js&":
/*!******************************************************************!*\
  !*** ./src/components/log-reporter.vue?vue&type=script&lang=js& ***!
  \******************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
eval("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   \"default\": () => (__WEBPACK_DEFAULT_EXPORT__)\n/* harmony export */ });\n/* harmony import */ var _node_modules_babel_loader_lib_index_js_clonedRuleSet_1_0_rules_0_node_modules_vue_loader_lib_index_js_vue_loader_options_log_reporter_vue_vue_type_script_lang_js___WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! -!../../node_modules/babel-loader/lib/index.js??clonedRuleSet-1[0].rules[0]!../../node_modules/vue-loader/lib/index.js??vue-loader-options!./log-reporter.vue?vue&type=script&lang=js& */ \"./node_modules/babel-loader/lib/index.js??clonedRuleSet-1[0].rules[0]!./node_modules/vue-loader/lib/index.js??vue-loader-options!./src/components/log-reporter.vue?vue&type=script&lang=js&\");\n /* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (_node_modules_babel_loader_lib_index_js_clonedRuleSet_1_0_rules_0_node_modules_vue_loader_lib_index_js_vue_loader_options_log_reporter_vue_vue_type_script_lang_js___WEBPACK_IMPORTED_MODULE_0__.default); \n\n//# sourceURL=webpack://slim/./src/components/log-reporter.vue?");

/***/ }),

/***/ "./src/components/log-reporter.vue?vue&type=template&id=8d3e674c&":
/*!************************************************************************!*\
  !*** ./src/components/log-reporter.vue?vue&type=template&id=8d3e674c& ***!
  \************************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
eval("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   \"render\": () => (/* reexport safe */ _node_modules_vue_loader_lib_loaders_templateLoader_js_vue_loader_options_node_modules_vue_loader_lib_index_js_vue_loader_options_log_reporter_vue_vue_type_template_id_8d3e674c___WEBPACK_IMPORTED_MODULE_0__.render),\n/* harmony export */   \"staticRenderFns\": () => (/* reexport safe */ _node_modules_vue_loader_lib_loaders_templateLoader_js_vue_loader_options_node_modules_vue_loader_lib_index_js_vue_loader_options_log_reporter_vue_vue_type_template_id_8d3e674c___WEBPACK_IMPORTED_MODULE_0__.staticRenderFns)\n/* harmony export */ });\n/* harmony import */ var _node_modules_vue_loader_lib_loaders_templateLoader_js_vue_loader_options_node_modules_vue_loader_lib_index_js_vue_loader_options_log_reporter_vue_vue_type_template_id_8d3e674c___WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! -!../../node_modules/vue-loader/lib/loaders/templateLoader.js??vue-loader-options!../../node_modules/vue-loader/lib/index.js??vue-loader-options!./log-reporter.vue?vue&type=template&id=8d3e674c& */ \"./node_modules/vue-loader/lib/loaders/templateLoader.js??vue-loader-options!./node_modules/vue-loader/lib/index.js??vue-loader-options!./src/components/log-reporter.vue?vue&type=template&id=8d3e674c&\");\n\n\n//# sourceURL=webpack://slim/./src/components/log-reporter.vue?");

/***/ }),

/***/ "./node_modules/vue-loader/lib/loaders/templateLoader.js??vue-loader-options!./node_modules/vue-loader/lib/index.js??vue-loader-options!./src/components/log-reporter.vue?vue&type=template&id=8d3e674c&":
/*!***************************************************************************************************************************************************************************************************************!*\
  !*** ./node_modules/vue-loader/lib/loaders/templateLoader.js??vue-loader-options!./node_modules/vue-loader/lib/index.js??vue-loader-options!./src/components/log-reporter.vue?vue&type=template&id=8d3e674c& ***!
  \***************************************************************************************************************************************************************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
eval("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   \"render\": () => (/* binding */ render),\n/* harmony export */   \"staticRenderFns\": () => (/* binding */ staticRenderFns)\n/* harmony export */ });\nvar render = function() {\n  var _vm = this\n  var _h = _vm.$createElement\n  var _c = _vm._self._c || _h\n  return _vm._m(0)\n}\nvar staticRenderFns = [\n  function() {\n    var _vm = this\n    var _h = _vm.$createElement\n    var _c = _vm._self._c || _h\n    return _c(\"div\", { staticClass: \"row\" }, [\n      _c(\"div\", { staticClass: \"col-md-12\" }, [\n        _c(\n          \"pre\",\n          { pre: true },\n          [\n            _vm._v(\"            \"),\n            [\n              _vm._v(\"\\n                \"),\n              _c(\"span\", { pre: true, attrs: { \"v-for\": \"log in logs\" } }, [\n                _vm._v(\"{{log}}\")\n              ]),\n              _vm._v(\"\\n            \")\n            ],\n            _vm._v(\"\\n            \"),\n            _c(\"span\", { pre: true, attrs: { \"v-else\": \"\" } }, [\n              _vm._v(\n                \"\\n                There are no events to display.\\n            \"\n              )\n            ]),\n            _vm._v(\"\\n         \")\n          ],\n          2\n        )\n      ])\n    ])\n  }\n]\nrender._withStripped = true\n\n\n\n//# sourceURL=webpack://slim/./src/components/log-reporter.vue?./node_modules/vue-loader/lib/loaders/templateLoader.js??vue-loader-options!./node_modules/vue-loader/lib/index.js??vue-loader-options");

/***/ })

}]);
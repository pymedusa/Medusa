/*
 * ATTENTION: The "eval" devtool has been used (maybe by default in mode: "development").
 * This devtool is not neither made for production nor for readable output files.
 * It uses "eval()" calls to create a separate source file in the browser devtools.
 * If you are trying to read the output file, select a different devtool (https://webpack.js.org/configuration/devtool/)
 * or disable the default devtool with "devtool: false".
 * If you are looking for production-ready output files, see mode: "production" (https://webpack.js.org/configuration/mode/).
 */
(self["webpackChunkslim"] = self["webpackChunkslim"] || []).push([["app"],{

/***/ "./src/app.js":
/*!********************!*\
  !*** ./src/app.js ***!
  \********************/
/*! namespace exports */
/*! export default [provided] [no usage info] [missing usage info prevents renaming] */
/*! other exports [not provided] [no usage info] */
/*! runtime requirements: __webpack_require__, __webpack_exports__, __webpack_require__.r, __webpack_require__.d, __webpack_require__.* */
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
eval("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   \"default\": () => __WEBPACK_DEFAULT_EXPORT__\n/* harmony export */ });\n/* harmony import */ var vue__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(/*! vue */ \"./node_modules/vue/dist/vue.esm.js\");\n/* harmony import */ var _global_vue_shim__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ./global-vue-shim */ \"./src/global-vue-shim.js\");\n/* harmony import */ var _router__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ./router */ \"./src/router/index.js\");\n/* harmony import */ var _store__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! ./store */ \"./src/store/index.js\");\n/* harmony import */ var vuex__WEBPACK_IMPORTED_MODULE_5__ = __webpack_require__(/*! vuex */ \"./node_modules/vuex/dist/vuex.esm.js\");\n/* harmony import */ var _utils_core__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! ./utils/core */ \"./src/utils/core.js\");\n\n\n\n\n\n\nvue__WEBPACK_IMPORTED_MODULE_4__.default.config.devtools = true;\nvue__WEBPACK_IMPORTED_MODULE_4__.default.config.performance = true;\n(0,_global_vue_shim__WEBPACK_IMPORTED_MODULE_0__.registerPlugins)(); // @TODO: Remove this before v1.0.0\n\n(0,_global_vue_shim__WEBPACK_IMPORTED_MODULE_0__.registerGlobalComponents)();\nconst app = new vue__WEBPACK_IMPORTED_MODULE_4__.default({\n  name: 'app',\n  router: _router__WEBPACK_IMPORTED_MODULE_1__.default,\n  store: _store__WEBPACK_IMPORTED_MODULE_2__.default,\n\n  data() {\n    return {\n      globalLoading: false,\n      pageComponent: false\n    };\n  },\n\n  computed: { ...(0,vuex__WEBPACK_IMPORTED_MODULE_5__.mapState)({\n      showsLoading: state => state.shows.loading\n    })\n  },\n\n  mounted() {\n    const {\n      getShows,\n      setLoadingDisplay,\n      setLoadingFinished\n    } = this;\n\n    if (_utils_core__WEBPACK_IMPORTED_MODULE_3__.isDevelopment) {\n      console.log('App Mounted!');\n    }\n\n    if (!window.location.pathname.includes('/login')) {\n      const {\n        $store\n      } = this;\n      Promise.all([$store.dispatch('login', {\n        username: window.username\n      }), $store.dispatch('getConfig'), $store.dispatch('getStats')]).then(([_, config]) => {\n        if (_utils_core__WEBPACK_IMPORTED_MODULE_3__.isDevelopment) {\n          console.log('App Loaded!');\n        } // Legacy - send config.general to jQuery (received by index.js)\n\n\n        const event = new CustomEvent('medusa-config-loaded', {\n          detail: {\n            general: config.general,\n            layout: config.layout\n          }\n        });\n        window.dispatchEvent(event);\n      }).catch(error => {\n        console.debug(error);\n        alert('Unable to connect to Medusa!'); // eslint-disable-line no-alert\n      });\n    } // Let's bootstrap the app with essential data.\n\n\n    getShows().then(() => {\n      console.log('Finished loading all shows.');\n      setTimeout(() => {\n        setLoadingFinished(true);\n        setLoadingDisplay(false);\n      }, 2000);\n    });\n  },\n\n  methods: { ...(0,vuex__WEBPACK_IMPORTED_MODULE_5__.mapActions)({\n      getShows: 'getShows'\n    }),\n    ...(0,vuex__WEBPACK_IMPORTED_MODULE_5__.mapMutations)(['setLoadingDisplay', 'setLoadingFinished'])\n  }\n}).$mount('#vue-wrap');\n/* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (app);\n\n//# sourceURL=webpack://slim/./src/app.js?");

/***/ })

},
0,[["./src/app.js","vendors","medusa-runtime","vendors~date-fns"]]]);
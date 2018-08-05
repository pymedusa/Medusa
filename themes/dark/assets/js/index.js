/******/ (function(modules) { // webpackBootstrap
/******/ 	// install a JSONP callback for chunk loading
/******/ 	function webpackJsonpCallback(data) {
/******/ 		var chunkIds = data[0];
/******/ 		var moreModules = data[1];
/******/ 		var executeModules = data[2];
/******/
/******/ 		// add "moreModules" to the modules object,
/******/ 		// then flag all "chunkIds" as loaded and fire callback
/******/ 		var moduleId, chunkId, i = 0, resolves = [];
/******/ 		for(;i < chunkIds.length; i++) {
/******/ 			chunkId = chunkIds[i];
/******/ 			if(installedChunks[chunkId]) {
/******/ 				resolves.push(installedChunks[chunkId][0]);
/******/ 			}
/******/ 			installedChunks[chunkId] = 0;
/******/ 		}
/******/ 		for(moduleId in moreModules) {
/******/ 			if(Object.prototype.hasOwnProperty.call(moreModules, moduleId)) {
/******/ 				modules[moduleId] = moreModules[moduleId];
/******/ 			}
/******/ 		}
/******/ 		if(parentJsonpFunction) parentJsonpFunction(data);
/******/
/******/ 		while(resolves.length) {
/******/ 			resolves.shift()();
/******/ 		}
/******/
/******/ 		// add entry modules from loaded chunk to deferred list
/******/ 		deferredModules.push.apply(deferredModules, executeModules || []);
/******/
/******/ 		// run deferred modules when all chunks ready
/******/ 		return checkDeferredModules();
/******/ 	};
/******/ 	function checkDeferredModules() {
/******/ 		var result;
/******/ 		for(var i = 0; i < deferredModules.length; i++) {
/******/ 			var deferredModule = deferredModules[i];
/******/ 			var fulfilled = true;
/******/ 			for(var j = 1; j < deferredModule.length; j++) {
/******/ 				var depId = deferredModule[j];
/******/ 				if(installedChunks[depId] !== 0) fulfilled = false;
/******/ 			}
/******/ 			if(fulfilled) {
/******/ 				deferredModules.splice(i--, 1);
/******/ 				result = __webpack_require__(__webpack_require__.s = deferredModule[0]);
/******/ 			}
/******/ 		}
/******/ 		return result;
/******/ 	}
/******/
/******/ 	// The module cache
/******/ 	var installedModules = {};
/******/
/******/ 	// object to store loaded and loading chunks
/******/ 	// undefined = chunk not loaded, null = chunk preloaded/prefetched
/******/ 	// Promise = chunk loading, 0 = chunk loaded
/******/ 	var installedChunks = {
/******/ 		"index": 0
/******/ 	};
/******/
/******/ 	var deferredModules = [];
/******/
/******/ 	// The require function
/******/ 	function __webpack_require__(moduleId) {
/******/
/******/ 		// Check if module is in cache
/******/ 		if(installedModules[moduleId]) {
/******/ 			return installedModules[moduleId].exports;
/******/ 		}
/******/ 		// Create a new module (and put it into the cache)
/******/ 		var module = installedModules[moduleId] = {
/******/ 			i: moduleId,
/******/ 			l: false,
/******/ 			exports: {}
/******/ 		};
/******/
/******/ 		// Execute the module function
/******/ 		modules[moduleId].call(module.exports, module, module.exports, __webpack_require__);
/******/
/******/ 		// Flag the module as loaded
/******/ 		module.l = true;
/******/
/******/ 		// Return the exports of the module
/******/ 		return module.exports;
/******/ 	}
/******/
/******/
/******/ 	// expose the modules object (__webpack_modules__)
/******/ 	__webpack_require__.m = modules;
/******/
/******/ 	// expose the module cache
/******/ 	__webpack_require__.c = installedModules;
/******/
/******/ 	// define getter function for harmony exports
/******/ 	__webpack_require__.d = function(exports, name, getter) {
/******/ 		if(!__webpack_require__.o(exports, name)) {
/******/ 			Object.defineProperty(exports, name, { enumerable: true, get: getter });
/******/ 		}
/******/ 	};
/******/
/******/ 	// define __esModule on exports
/******/ 	__webpack_require__.r = function(exports) {
/******/ 		if(typeof Symbol !== 'undefined' && Symbol.toStringTag) {
/******/ 			Object.defineProperty(exports, Symbol.toStringTag, { value: 'Module' });
/******/ 		}
/******/ 		Object.defineProperty(exports, '__esModule', { value: true });
/******/ 	};
/******/
/******/ 	// create a fake namespace object
/******/ 	// mode & 1: value is a module id, require it
/******/ 	// mode & 2: merge all properties of value into the ns
/******/ 	// mode & 4: return value when already ns object
/******/ 	// mode & 8|1: behave like require
/******/ 	__webpack_require__.t = function(value, mode) {
/******/ 		if(mode & 1) value = __webpack_require__(value);
/******/ 		if(mode & 8) return value;
/******/ 		if((mode & 4) && typeof value === 'object' && value && value.__esModule) return value;
/******/ 		var ns = Object.create(null);
/******/ 		__webpack_require__.r(ns);
/******/ 		Object.defineProperty(ns, 'default', { enumerable: true, value: value });
/******/ 		if(mode & 2 && typeof value != 'string') for(var key in value) __webpack_require__.d(ns, key, function(key) { return value[key]; }.bind(null, key));
/******/ 		return ns;
/******/ 	};
/******/
/******/ 	// getDefaultExport function for compatibility with non-harmony modules
/******/ 	__webpack_require__.n = function(module) {
/******/ 		var getter = module && module.__esModule ?
/******/ 			function getDefault() { return module['default']; } :
/******/ 			function getModuleExports() { return module; };
/******/ 		__webpack_require__.d(getter, 'a', getter);
/******/ 		return getter;
/******/ 	};
/******/
/******/ 	// Object.prototype.hasOwnProperty.call
/******/ 	__webpack_require__.o = function(object, property) { return Object.prototype.hasOwnProperty.call(object, property); };
/******/
/******/ 	// __webpack_public_path__
/******/ 	__webpack_require__.p = "";
/******/
/******/ 	var jsonpArray = window["webpackJsonp"] = window["webpackJsonp"] || [];
/******/ 	var oldJsonpFunction = jsonpArray.push.bind(jsonpArray);
/******/ 	jsonpArray.push = webpackJsonpCallback;
/******/ 	jsonpArray = jsonpArray.slice();
/******/ 	for(var i = 0; i < jsonpArray.length; i++) webpackJsonpCallback(jsonpArray[i]);
/******/ 	var parentJsonpFunction = oldJsonpFunction;
/******/
/******/
/******/ 	// add entry module to deferred list
/******/ 	deferredModules.push(["./static/js/index.js","vendors"]);
/******/ 	// run deferred modules when ready
/******/ 	return checkDeferredModules();
/******/ })
/************************************************************************/
/******/ ({

/***/ "./static/js/index.js":
/*!****************************!*\
  !*** ./static/js/index.js ***!
  \****************************/
/*! no static exports found */
/***/ (function(module, exports, __webpack_require__) {

"use strict";
eval("\n\nvar _jquery = __webpack_require__(/*! jquery */ \"./node_modules/jquery/dist/jquery.js\");\n\nvar _jquery2 = _interopRequireDefault(_jquery);\n\nvar _vue = __webpack_require__(/*! vue */ \"./node_modules/vue/dist/vue.esm.js\");\n\nvar _vue2 = _interopRequireDefault(_vue);\n\nvar _vuex = __webpack_require__(/*! vuex */ \"./node_modules/vuex/dist/vuex.esm.js\");\n\nvar _vuex2 = _interopRequireDefault(_vuex);\n\nvar _vueMeta = __webpack_require__(/*! vue-meta */ \"./node_modules/vue-meta/lib/vue-meta.js\");\n\nvar _vueMeta2 = _interopRequireDefault(_vueMeta);\n\nvar _vueRouter = __webpack_require__(/*! vue-router */ \"./node_modules/vue-router/dist/vue-router.esm.js\");\n\nvar _vueRouter2 = _interopRequireDefault(_vueRouter);\n\nvar _vueNativeWebsocket = __webpack_require__(/*! vue-native-websocket */ \"./node_modules/vue-native-websocket/dist/build.js\");\n\nvar _vueNativeWebsocket2 = _interopRequireDefault(_vueNativeWebsocket);\n\nvar _vueAsyncComputed = __webpack_require__(/*! vue-async-computed */ \"./node_modules/vue-async-computed/dist/vue-async-computed.js\");\n\nvar _vueAsyncComputed2 = _interopRequireDefault(_vueAsyncComputed);\n\nvar _vueJsToggleButton = __webpack_require__(/*! vue-js-toggle-button */ \"./node_modules/vue-js-toggle-button/dist/index.js\");\n\nvar _vueJsToggleButton2 = _interopRequireDefault(_vueJsToggleButton);\n\nvar _vueSnotify = __webpack_require__(/*! vue-snotify */ \"./node_modules/vue-snotify/vue-snotify.esm.js\");\n\nvar _vueSnotify2 = _interopRequireDefault(_vueSnotify);\n\nvar _axios = __webpack_require__(/*! axios */ \"./node_modules/axios/index.js\");\n\nvar _axios2 = _interopRequireDefault(_axios);\n\nvar _store = __webpack_require__(/*! ./store */ \"./static/js/store/index.js\");\n\nvar _store2 = _interopRequireDefault(_store);\n\nvar _router = __webpack_require__(/*! ./router */ \"./static/js/router.js\");\n\nvar _router2 = _interopRequireDefault(_router);\n\nvar _api = __webpack_require__(/*! ./api */ \"./static/js/api.js\");\n\nvar _templates = __webpack_require__(/*! ./templates */ \"./static/js/templates/index.js\");\n\nfunction _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }\n\nif (window) {\n    // Adding libs to window so mako files can use them\n    window.Vue = _vue2.default;\n    window.Vuex = _vuex2.default;\n    window.VueMeta = _vueMeta2.default;\n    window.VueRouter = _vueRouter2.default;\n    window.VueNativeSock = _vueNativeWebsocket2.default;\n    window.AsyncComputed = _vueAsyncComputed2.default;\n    window.ToggleButton = _vueJsToggleButton2.default;\n    window.Snotify = _vueSnotify2.default;\n    window.axios = _axios2.default;\n    window.store = _store2.default;\n    window.router = _router2.default;\n    window.apiRoute = _api.apiRoute;\n    window.apiv1 = _api.apiv1;\n    window.api = _api.api;\n\n    window.MEDUSA = {\n        common: {},\n        config: {},\n        home: {},\n        manage: {},\n        history: {},\n        errorlogs: {},\n        schedule: {},\n        addShows: {}\n    };\n    window.webRoot = _api.webRoot;\n    window.apiKey = _api.apiKey;\n    window.apiRoot = _api.webRoot + '/api/v2/';\n\n    // Push pages that load via a vue file but still use `el` for mounting\n    window.components = [];\n    window.components.push(_templates.AppHeader);\n    window.components.push(_templates.AppLink);\n    window.components.push(_templates.Asset);\n    window.components.push(_templates.Backstretch);\n    window.components.push(_templates.DisplayShow);\n    window.components.push(_templates.FileBrowser);\n    window.components.push(_templates.LanguageSelect);\n    window.components.push(_templates.NamePattern);\n    window.components.push(_templates.PlotInfo);\n    window.components.push(_templates.RootDirs);\n    window.components.push(_templates.ScrollButtons);\n    window.components.push(_templates.SelectList);\n    window.components.push(_templates.ShowSelector);\n}\nvar UTIL = {\n    exec: function exec(controller, action) {\n        var ns = MEDUSA;\n        action = action === undefined ? 'init' : action;\n\n        if (controller !== '' && ns[controller] && typeof ns[controller][action] === 'function') {\n            ns[controller][action]();\n        }\n    },\n    init: function init() {\n        if (typeof startVue === 'function') {\n            // eslint-disable-line no-undef\n            startVue(); // eslint-disable-line no-undef\n        } else {\n            (0, _jquery2.default)('[v-cloak]').removeAttr('v-cloak');\n        }\n\n        var _document = document,\n            body = _document.body;\n\n        (0, _jquery2.default)('[asset]').each(function () {\n            var asset = (0, _jquery2.default)(this).attr('asset');\n            var series = (0, _jquery2.default)(this).attr('series');\n            var path = apiRoot + 'series/' + series + '/asset/' + asset + '?api_key=' + _api.apiKey;\n            if (this.tagName.toLowerCase() === 'img') {\n                var defaultPath = (0, _jquery2.default)(this).attr('src');\n                if ((0, _jquery2.default)(this).attr('lazy') === 'on') {\n                    (0, _jquery2.default)(this).attr('data-original', path);\n                } else {\n                    (0, _jquery2.default)(this).attr('src', path);\n                }\n                (0, _jquery2.default)(this).attr('onerror', 'this.src = \"' + defaultPath + '\"; return false;');\n            }\n            if (this.tagName.toLowerCase() === 'a') {\n                (0, _jquery2.default)(this).attr('href', path);\n            }\n        });\n        var controller = body.getAttribute('data-controller');\n        var action = body.getAttribute('data-action');\n\n        UTIL.exec('common'); // Load common\n        UTIL.exec(controller); // Load MEDUSA[controller]\n        UTIL.exec(controller, action); // Load MEDUSA[controller][action]\n\n        window.dispatchEvent(new Event('medusa-loaded'));\n    }\n};\n\n_jquery2.default.fn.extend({\n    addRemoveWarningClass: function addRemoveWarningClass(_) {\n        if (_) {\n            return (0, _jquery2.default)(this).removeClass('warning');\n        }\n        return (0, _jquery2.default)(this).addClass('warning');\n    }\n});\n\nif (!document.location.pathname.includes('/login')) {\n    _api.api.get('config/main').then(function (response) {\n        log.setDefaultLevel('trace');\n        _jquery2.default.extend(MEDUSA.config, response.data);\n        MEDUSA.config.themeSpinner = MEDUSA.config.themeName === 'dark' ? '-dark' : '';\n        MEDUSA.config.loading = '<img src=\"images/loading16' + MEDUSA.config.themeSpinner + '.gif\" height=\"16\" width=\"16\" />';\n\n        if (navigator.userAgent.indexOf('PhantomJS') === -1) {\n            (0, _jquery2.default)(document).ready(UTIL.init);\n        }\n\n        MEDUSA.config.indexers.indexerIdToName = function (indexerId) {\n            if (!indexerId) {\n                return '';\n            }\n            return Object.keys(MEDUSA.config.indexers.config.indexers).filter(function (indexer) {\n                // eslint-disable-line array-callback-return\n                if (MEDUSA.config.indexers.config.indexers[indexer].id === parseInt(indexerId, 10)) {\n                    return MEDUSA.config.indexers.config.indexers[indexer].name;\n                }\n            })[0];\n        };\n\n        MEDUSA.config.indexers.nameToIndexerId = function (name) {\n            if (!name) {\n                return '';\n            }\n            return MEDUSA.config.indexers.config.indexers[name];\n        };\n    }).catch(function (error) {\n        log.error(error);\n        alert('Unable to connect to Medusa!'); // eslint-disable-line no-alert\n    });\n}\n\n//# sourceURL=webpack:///./static/js/index.js?");

/***/ })

/******/ });
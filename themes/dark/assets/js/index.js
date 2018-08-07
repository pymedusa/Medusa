(window["webpackJsonp"] = window["webpackJsonp"] || []).push([["index"],{

/***/ "./src/index.js":
/*!**********************!*\
  !*** ./src/index.js ***!
  \**********************/
/*! no static exports found */
/***/ (function(module, exports, __webpack_require__) {

"use strict";
eval("\n\nvar _jquery = __webpack_require__(/*! jquery */ \"./node_modules/jquery/dist/jquery.js\");\n\nvar _jquery2 = _interopRequireDefault(_jquery);\n\n__webpack_require__(/*! bootstrap */ \"./node_modules/bootstrap/dist/js/npm.js\");\n\n__webpack_require__(/*! bootstrap/dist/css/bootstrap.css */ \"./node_modules/bootstrap/dist/css/bootstrap.css\");\n\nvar _vue = __webpack_require__(/*! vue */ \"./node_modules/vue/dist/vue.esm.js\");\n\nvar _vue2 = _interopRequireDefault(_vue);\n\nvar _vuex = __webpack_require__(/*! vuex */ \"./node_modules/vuex/dist/vuex.esm.js\");\n\nvar _vuex2 = _interopRequireDefault(_vuex);\n\nvar _vueMeta = __webpack_require__(/*! vue-meta */ \"./node_modules/vue-meta/lib/vue-meta.js\");\n\nvar _vueMeta2 = _interopRequireDefault(_vueMeta);\n\nvar _vueRouter = __webpack_require__(/*! vue-router */ \"./node_modules/vue-router/dist/vue-router.esm.js\");\n\nvar _vueRouter2 = _interopRequireDefault(_vueRouter);\n\nvar _vueNativeWebsocket = __webpack_require__(/*! vue-native-websocket */ \"./node_modules/vue-native-websocket/dist/build.js\");\n\nvar _vueNativeWebsocket2 = _interopRequireDefault(_vueNativeWebsocket);\n\nvar _vueAsyncComputed = __webpack_require__(/*! vue-async-computed */ \"./node_modules/vue-async-computed/dist/vue-async-computed.js\");\n\nvar _vueAsyncComputed2 = _interopRequireDefault(_vueAsyncComputed);\n\nvar _vueJsToggleButton = __webpack_require__(/*! vue-js-toggle-button */ \"./node_modules/vue-js-toggle-button/dist/index.js\");\n\nvar _vueJsToggleButton2 = _interopRequireDefault(_vueJsToggleButton);\n\nvar _vueSnotify = __webpack_require__(/*! vue-snotify */ \"./node_modules/vue-snotify/vue-snotify.esm.js\");\n\nvar _vueSnotify2 = _interopRequireDefault(_vueSnotify);\n\nvar _axios = __webpack_require__(/*! axios */ \"./node_modules/axios/index.js\");\n\nvar _axios2 = _interopRequireDefault(_axios);\n\nvar _debounce = __webpack_require__(/*! lodash/debounce */ \"./node_modules/lodash/debounce.js\");\n\nvar _debounce2 = _interopRequireDefault(_debounce);\n\nvar _store = __webpack_require__(/*! ./store */ \"./src/store/index.js\");\n\nvar _store2 = _interopRequireDefault(_store);\n\nvar _router = __webpack_require__(/*! ./router */ \"./src/router.js\");\n\nvar _router2 = _interopRequireDefault(_router);\n\nvar _utils = __webpack_require__(/*! ./utils */ \"./src/utils.js\");\n\nvar _api = __webpack_require__(/*! ./api */ \"./src/api.js\");\n\nvar _components = __webpack_require__(/*! ./components */ \"./src/components/index.js\");\n\nfunction _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }\n\n// eslint-disable-line import/no-unassigned-import\nif (window) {\n    window.isDevelopment = _utils.isDevelopment;\n\n    // Adding libs to window so mako files can use them\n    window.$ = _jquery2.default;\n    window.jQuery = _jquery2.default;\n    window.Vue = _vue2.default;\n    window.Vuex = _vuex2.default;\n    window.VueMeta = _vueMeta2.default;\n    window.VueRouter = _vueRouter2.default;\n    window.VueNativeSock = _vueNativeWebsocket2.default;\n    window.AsyncComputed = _vueAsyncComputed2.default;\n    window.ToggleButton = _vueJsToggleButton2.default;\n    window.Snotify = _vueSnotify2.default;\n    window.axios = _axios2.default;\n    window._ = { debounce: _debounce2.default };\n    window.store = _store2.default;\n    window.router = _router2.default;\n    window.apiRoute = _api.apiRoute;\n    window.apiv1 = _api.apiv1;\n    window.api = _api.api;\n\n    window.MEDUSA = {\n        common: {},\n        config: {},\n        home: {},\n        manage: {},\n        history: {},\n        errorlogs: {},\n        schedule: {},\n        addShows: {}\n    };\n    window.webRoot = _api.webRoot;\n    window.apiKey = _api.apiKey;\n    window.apiRoot = _api.webRoot + '/api/v2/';\n\n    // Push pages that load via a vue file but still use `el` for mounting\n    window.components = [];\n    window.components.push(_components.AnidbReleaseGroupUi);\n    window.components.push(_components.AppHeader);\n    window.components.push(_components.AppLink);\n    window.components.push(_components.Asset);\n    window.components.push(_components.Backstretch);\n    window.components.push(_components.DisplayShow);\n    window.components.push(_components.FileBrowser);\n    window.components.push(_components.LanguageSelect);\n    window.components.push(_components.NamePattern);\n    window.components.push(_components.PlotInfo);\n    window.components.push(_components.RootDirs);\n    window.components.push(_components.ScrollButtons);\n    window.components.push(_components.SelectList);\n    window.components.push(_components.ShowSelector);\n} // eslint-disable-line import/no-unassigned-import\n\nvar UTIL = {\n    exec: function exec(controller, action) {\n        var ns = MEDUSA;\n        action = action === undefined ? 'init' : action;\n\n        if (controller !== '' && ns[controller] && typeof ns[controller][action] === 'function') {\n            ns[controller][action]();\n        }\n    },\n    init: function init() {\n        if (typeof startVue === 'function') {\n            // eslint-disable-line no-undef\n            startVue(); // eslint-disable-line no-undef\n        } else {\n            (0, _jquery2.default)('[v-cloak]').removeAttr('v-cloak');\n        }\n\n        var _document = document,\n            body = _document.body;\n\n        (0, _jquery2.default)('[asset]').each(function () {\n            var asset = (0, _jquery2.default)(this).attr('asset');\n            var series = (0, _jquery2.default)(this).attr('series');\n            var path = apiRoot + 'series/' + series + '/asset/' + asset + '?api_key=' + _api.apiKey;\n            if (this.tagName.toLowerCase() === 'img') {\n                var defaultPath = (0, _jquery2.default)(this).attr('src');\n                if ((0, _jquery2.default)(this).attr('lazy') === 'on') {\n                    (0, _jquery2.default)(this).attr('data-original', path);\n                } else {\n                    (0, _jquery2.default)(this).attr('src', path);\n                }\n                (0, _jquery2.default)(this).attr('onerror', 'this.src = \"' + defaultPath + '\"; return false;');\n            }\n            if (this.tagName.toLowerCase() === 'a') {\n                (0, _jquery2.default)(this).attr('href', path);\n            }\n        });\n        var controller = body.getAttribute('data-controller');\n        var action = body.getAttribute('data-action');\n\n        UTIL.exec('common'); // Load common\n        UTIL.exec(controller); // Load MEDUSA[controller]\n        UTIL.exec(controller, action); // Load MEDUSA[controller][action]\n\n        window.dispatchEvent(new Event('medusa-loaded'));\n    }\n};\n\n_jquery2.default.fn.extend({\n    addRemoveWarningClass: function addRemoveWarningClass(_) {\n        if (_) {\n            return (0, _jquery2.default)(this).removeClass('warning');\n        }\n        return (0, _jquery2.default)(this).addClass('warning');\n    }\n});\n\n// @FIXME: Workaround just for the time being!\nvar log = {\n    setDefaultLevel: function setDefaultLevel() {},\n    log: console.log,\n    info: console.info,\n    error: console.error,\n    debug: console.debug\n};\n\nif (!document.location.pathname.includes('/login')) {\n    _api.api.get('config/main').then(function (response) {\n        log.setDefaultLevel('trace');\n        _jquery2.default.extend(MEDUSA.config, response.data);\n        MEDUSA.config.themeSpinner = MEDUSA.config.themeName === 'dark' ? '-dark' : '';\n        MEDUSA.config.loading = '<img src=\"images/loading16' + MEDUSA.config.themeSpinner + '.gif\" height=\"16\" width=\"16\" />';\n\n        if (navigator.userAgent.indexOf('PhantomJS') === -1) {\n            (0, _jquery2.default)(document).ready(UTIL.init);\n        }\n\n        MEDUSA.config.indexers.indexerIdToName = function (indexerId) {\n            if (!indexerId) {\n                return '';\n            }\n            return Object.keys(MEDUSA.config.indexers.config.indexers).filter(function (indexer) {\n                // eslint-disable-line array-callback-return\n                if (MEDUSA.config.indexers.config.indexers[indexer].id === parseInt(indexerId, 10)) {\n                    return MEDUSA.config.indexers.config.indexers[indexer].name;\n                }\n            })[0];\n        };\n\n        MEDUSA.config.indexers.nameToIndexerId = function (name) {\n            if (!name) {\n                return '';\n            }\n            return MEDUSA.config.indexers.config.indexers[name];\n        };\n    }).catch(function (error) {\n        log.error(error);\n        alert('Unable to connect to Medusa!'); // eslint-disable-line no-alert\n    });\n}\n\n//# sourceURL=webpack:///./src/index.js?");

/***/ })

},[["./src/index.js","vendors"]]]);
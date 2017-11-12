(function e(t,n,r){function s(o,u){if(!n[o]){if(!t[o]){var a=typeof require=="function"&&require;if(!u&&a)return a(o,!0);if(i)return i(o,!0);var f=new Error("Cannot find module '"+o+"'");throw f.code="MODULE_NOT_FOUND",f}var l=n[o]={exports:{}};t[o][0].call(l.exports,function(e){var n=t[o][1][e];return s(n?n:e)},l,l.exports,e,t,n,r)}return n[o].exports}var i=typeof require=="function"&&require;for(var o=0;o<r.length;o++)s(r[o]);return s})({1:[function(require,module,exports){
module.exports = require('./lib/axios');
},{"./lib/axios":3}],2:[function(require,module,exports){
(function (process){
'use strict';

var utils = require('./../utils');
var settle = require('./../core/settle');
var buildURL = require('./../helpers/buildURL');
var parseHeaders = require('./../helpers/parseHeaders');
var isURLSameOrigin = require('./../helpers/isURLSameOrigin');
var createError = require('../core/createError');
var btoa = (typeof window !== 'undefined' && window.btoa && window.btoa.bind(window)) || require('./../helpers/btoa');

module.exports = function xhrAdapter(config) {
  return new Promise(function dispatchXhrRequest(resolve, reject) {
    var requestData = config.data;
    var requestHeaders = config.headers;

    if (utils.isFormData(requestData)) {
      delete requestHeaders['Content-Type']; // Let the browser set it
    }

    var request = new XMLHttpRequest();
    var loadEvent = 'onreadystatechange';
    var xDomain = false;

    // For IE 8/9 CORS support
    // Only supports POST and GET calls and doesn't returns the response headers.
    // DON'T do this for testing b/c XMLHttpRequest is mocked, not XDomainRequest.
    if (process.env.NODE_ENV !== 'test' &&
        typeof window !== 'undefined' &&
        window.XDomainRequest && !('withCredentials' in request) &&
        !isURLSameOrigin(config.url)) {
      request = new window.XDomainRequest();
      loadEvent = 'onload';
      xDomain = true;
      request.onprogress = function handleProgress() {};
      request.ontimeout = function handleTimeout() {};
    }

    // HTTP basic authentication
    if (config.auth) {
      var username = config.auth.username || '';
      var password = config.auth.password || '';
      requestHeaders.Authorization = 'Basic ' + btoa(username + ':' + password);
    }

    request.open(config.method.toUpperCase(), buildURL(config.url, config.params, config.paramsSerializer), true);

    // Set the request timeout in MS
    request.timeout = config.timeout;

    // Listen for ready state
    request[loadEvent] = function handleLoad() {
      if (!request || (request.readyState !== 4 && !xDomain)) {
        return;
      }

      // The request errored out and we didn't get a response, this will be
      // handled by onerror instead
      // With one exception: request that using file: protocol, most browsers
      // will return status as 0 even though it's a successful request
      if (request.status === 0 && !(request.responseURL && request.responseURL.indexOf('file:') === 0)) {
        return;
      }

      // Prepare the response
      var responseHeaders = 'getAllResponseHeaders' in request ? parseHeaders(request.getAllResponseHeaders()) : null;
      var responseData = !config.responseType || config.responseType === 'text' ? request.responseText : request.response;
      var response = {
        data: responseData,
        // IE sends 1223 instead of 204 (https://github.com/axios/axios/issues/201)
        status: request.status === 1223 ? 204 : request.status,
        statusText: request.status === 1223 ? 'No Content' : request.statusText,
        headers: responseHeaders,
        config: config,
        request: request
      };

      settle(resolve, reject, response);

      // Clean up request
      request = null;
    };

    // Handle low level network errors
    request.onerror = function handleError() {
      // Real errors are hidden from us by the browser
      // onerror should only fire if it's a network error
      reject(createError('Network Error', config, null, request));

      // Clean up request
      request = null;
    };

    // Handle timeout
    request.ontimeout = function handleTimeout() {
      reject(createError('timeout of ' + config.timeout + 'ms exceeded', config, 'ECONNABORTED',
        request));

      // Clean up request
      request = null;
    };

    // Add xsrf header
    // This is only done if running in a standard browser environment.
    // Specifically not if we're in a web worker, or react-native.
    if (utils.isStandardBrowserEnv()) {
      var cookies = require('./../helpers/cookies');

      // Add xsrf header
      var xsrfValue = (config.withCredentials || isURLSameOrigin(config.url)) && config.xsrfCookieName ?
          cookies.read(config.xsrfCookieName) :
          undefined;

      if (xsrfValue) {
        requestHeaders[config.xsrfHeaderName] = xsrfValue;
      }
    }

    // Add headers to the request
    if ('setRequestHeader' in request) {
      utils.forEach(requestHeaders, function setRequestHeader(val, key) {
        if (typeof requestData === 'undefined' && key.toLowerCase() === 'content-type') {
          // Remove Content-Type if data is undefined
          delete requestHeaders[key];
        } else {
          // Otherwise add header to the request
          request.setRequestHeader(key, val);
        }
      });
    }

    // Add withCredentials to request if needed
    if (config.withCredentials) {
      request.withCredentials = true;
    }

    // Add responseType to request if needed
    if (config.responseType) {
      try {
        request.responseType = config.responseType;
      } catch (e) {
        // Expected DOMException thrown by browsers not compatible XMLHttpRequest Level 2.
        // But, this can be suppressed for 'json' type as it can be parsed by default 'transformResponse' function.
        if (config.responseType !== 'json') {
          throw e;
        }
      }
    }

    // Handle progress if needed
    if (typeof config.onDownloadProgress === 'function') {
      request.addEventListener('progress', config.onDownloadProgress);
    }

    // Not all browsers support upload events
    if (typeof config.onUploadProgress === 'function' && request.upload) {
      request.upload.addEventListener('progress', config.onUploadProgress);
    }

    if (config.cancelToken) {
      // Handle cancellation
      config.cancelToken.promise.then(function onCanceled(cancel) {
        if (!request) {
          return;
        }

        request.abort();
        reject(cancel);
        // Clean up request
        request = null;
      });
    }

    if (requestData === undefined) {
      requestData = null;
    }

    // Send the request
    request.send(requestData);
  });
};

}).call(this,require('_process'))
},{"../core/createError":9,"./../core/settle":12,"./../helpers/btoa":16,"./../helpers/buildURL":17,"./../helpers/cookies":19,"./../helpers/isURLSameOrigin":21,"./../helpers/parseHeaders":23,"./../utils":25,"_process":27}],3:[function(require,module,exports){
'use strict';

var utils = require('./utils');
var bind = require('./helpers/bind');
var Axios = require('./core/Axios');
var defaults = require('./defaults');

/**
 * Create an instance of Axios
 *
 * @param {Object} defaultConfig The default config for the instance
 * @return {Axios} A new instance of Axios
 */
function createInstance(defaultConfig) {
  var context = new Axios(defaultConfig);
  var instance = bind(Axios.prototype.request, context);

  // Copy axios.prototype to instance
  utils.extend(instance, Axios.prototype, context);

  // Copy context to instance
  utils.extend(instance, context);

  return instance;
}

// Create the default instance to be exported
var axios = createInstance(defaults);

// Expose Axios class to allow class inheritance
axios.Axios = Axios;

// Factory for creating new instances
axios.create = function create(instanceConfig) {
  return createInstance(utils.merge(defaults, instanceConfig));
};

// Expose Cancel & CancelToken
axios.Cancel = require('./cancel/Cancel');
axios.CancelToken = require('./cancel/CancelToken');
axios.isCancel = require('./cancel/isCancel');

// Expose all/spread
axios.all = function all(promises) {
  return Promise.all(promises);
};
axios.spread = require('./helpers/spread');

module.exports = axios;

// Allow use of default import syntax in TypeScript
module.exports.default = axios;

},{"./cancel/Cancel":4,"./cancel/CancelToken":5,"./cancel/isCancel":6,"./core/Axios":7,"./defaults":14,"./helpers/bind":15,"./helpers/spread":24,"./utils":25}],4:[function(require,module,exports){
'use strict';

/**
 * A `Cancel` is an object that is thrown when an operation is canceled.
 *
 * @class
 * @param {string=} message The message.
 */
function Cancel(message) {
  this.message = message;
}

Cancel.prototype.toString = function toString() {
  return 'Cancel' + (this.message ? ': ' + this.message : '');
};

Cancel.prototype.__CANCEL__ = true;

module.exports = Cancel;

},{}],5:[function(require,module,exports){
'use strict';

var Cancel = require('./Cancel');

/**
 * A `CancelToken` is an object that can be used to request cancellation of an operation.
 *
 * @class
 * @param {Function} executor The executor function.
 */
function CancelToken(executor) {
  if (typeof executor !== 'function') {
    throw new TypeError('executor must be a function.');
  }

  var resolvePromise;
  this.promise = new Promise(function promiseExecutor(resolve) {
    resolvePromise = resolve;
  });

  var token = this;
  executor(function cancel(message) {
    if (token.reason) {
      // Cancellation has already been requested
      return;
    }

    token.reason = new Cancel(message);
    resolvePromise(token.reason);
  });
}

/**
 * Throws a `Cancel` if cancellation has been requested.
 */
CancelToken.prototype.throwIfRequested = function throwIfRequested() {
  if (this.reason) {
    throw this.reason;
  }
};

/**
 * Returns an object that contains a new `CancelToken` and a function that, when called,
 * cancels the `CancelToken`.
 */
CancelToken.source = function source() {
  var cancel;
  var token = new CancelToken(function executor(c) {
    cancel = c;
  });
  return {
    token: token,
    cancel: cancel
  };
};

module.exports = CancelToken;

},{"./Cancel":4}],6:[function(require,module,exports){
'use strict';

module.exports = function isCancel(value) {
  return !!(value && value.__CANCEL__);
};

},{}],7:[function(require,module,exports){
'use strict';

var defaults = require('./../defaults');
var utils = require('./../utils');
var InterceptorManager = require('./InterceptorManager');
var dispatchRequest = require('./dispatchRequest');

/**
 * Create a new instance of Axios
 *
 * @param {Object} instanceConfig The default config for the instance
 */
function Axios(instanceConfig) {
  this.defaults = instanceConfig;
  this.interceptors = {
    request: new InterceptorManager(),
    response: new InterceptorManager()
  };
}

/**
 * Dispatch a request
 *
 * @param {Object} config The config specific for this request (merged with this.defaults)
 */
Axios.prototype.request = function request(config) {
  /*eslint no-param-reassign:0*/
  // Allow for axios('example/url'[, config]) a la fetch API
  if (typeof config === 'string') {
    config = utils.merge({
      url: arguments[0]
    }, arguments[1]);
  }

  config = utils.merge(defaults, this.defaults, { method: 'get' }, config);
  config.method = config.method.toLowerCase();

  // Hook up interceptors middleware
  var chain = [dispatchRequest, undefined];
  var promise = Promise.resolve(config);

  this.interceptors.request.forEach(function unshiftRequestInterceptors(interceptor) {
    chain.unshift(interceptor.fulfilled, interceptor.rejected);
  });

  this.interceptors.response.forEach(function pushResponseInterceptors(interceptor) {
    chain.push(interceptor.fulfilled, interceptor.rejected);
  });

  while (chain.length) {
    promise = promise.then(chain.shift(), chain.shift());
  }

  return promise;
};

// Provide aliases for supported request methods
utils.forEach(['delete', 'get', 'head', 'options'], function forEachMethodNoData(method) {
  /*eslint func-names:0*/
  Axios.prototype[method] = function(url, config) {
    return this.request(utils.merge(config || {}, {
      method: method,
      url: url
    }));
  };
});

utils.forEach(['post', 'put', 'patch'], function forEachMethodWithData(method) {
  /*eslint func-names:0*/
  Axios.prototype[method] = function(url, data, config) {
    return this.request(utils.merge(config || {}, {
      method: method,
      url: url,
      data: data
    }));
  };
});

module.exports = Axios;

},{"./../defaults":14,"./../utils":25,"./InterceptorManager":8,"./dispatchRequest":10}],8:[function(require,module,exports){
'use strict';

var utils = require('./../utils');

function InterceptorManager() {
  this.handlers = [];
}

/**
 * Add a new interceptor to the stack
 *
 * @param {Function} fulfilled The function to handle `then` for a `Promise`
 * @param {Function} rejected The function to handle `reject` for a `Promise`
 *
 * @return {Number} An ID used to remove interceptor later
 */
InterceptorManager.prototype.use = function use(fulfilled, rejected) {
  this.handlers.push({
    fulfilled: fulfilled,
    rejected: rejected
  });
  return this.handlers.length - 1;
};

/**
 * Remove an interceptor from the stack
 *
 * @param {Number} id The ID that was returned by `use`
 */
InterceptorManager.prototype.eject = function eject(id) {
  if (this.handlers[id]) {
    this.handlers[id] = null;
  }
};

/**
 * Iterate over all the registered interceptors
 *
 * This method is particularly useful for skipping over any
 * interceptors that may have become `null` calling `eject`.
 *
 * @param {Function} fn The function to call for each interceptor
 */
InterceptorManager.prototype.forEach = function forEach(fn) {
  utils.forEach(this.handlers, function forEachHandler(h) {
    if (h !== null) {
      fn(h);
    }
  });
};

module.exports = InterceptorManager;

},{"./../utils":25}],9:[function(require,module,exports){
'use strict';

var enhanceError = require('./enhanceError');

/**
 * Create an Error with the specified message, config, error code, request and response.
 *
 * @param {string} message The error message.
 * @param {Object} config The config.
 * @param {string} [code] The error code (for example, 'ECONNABORTED').
 * @param {Object} [request] The request.
 * @param {Object} [response] The response.
 * @returns {Error} The created error.
 */
module.exports = function createError(message, config, code, request, response) {
  var error = new Error(message);
  return enhanceError(error, config, code, request, response);
};

},{"./enhanceError":11}],10:[function(require,module,exports){
'use strict';

var utils = require('./../utils');
var transformData = require('./transformData');
var isCancel = require('../cancel/isCancel');
var defaults = require('../defaults');
var isAbsoluteURL = require('./../helpers/isAbsoluteURL');
var combineURLs = require('./../helpers/combineURLs');

/**
 * Throws a `Cancel` if cancellation has been requested.
 */
function throwIfCancellationRequested(config) {
  if (config.cancelToken) {
    config.cancelToken.throwIfRequested();
  }
}

/**
 * Dispatch a request to the server using the configured adapter.
 *
 * @param {object} config The config that is to be used for the request
 * @returns {Promise} The Promise to be fulfilled
 */
module.exports = function dispatchRequest(config) {
  throwIfCancellationRequested(config);

  // Support baseURL config
  if (config.baseURL && !isAbsoluteURL(config.url)) {
    config.url = combineURLs(config.baseURL, config.url);
  }

  // Ensure headers exist
  config.headers = config.headers || {};

  // Transform request data
  config.data = transformData(
    config.data,
    config.headers,
    config.transformRequest
  );

  // Flatten headers
  config.headers = utils.merge(
    config.headers.common || {},
    config.headers[config.method] || {},
    config.headers || {}
  );

  utils.forEach(
    ['delete', 'get', 'head', 'post', 'put', 'patch', 'common'],
    function cleanHeaderConfig(method) {
      delete config.headers[method];
    }
  );

  var adapter = config.adapter || defaults.adapter;

  return adapter(config).then(function onAdapterResolution(response) {
    throwIfCancellationRequested(config);

    // Transform response data
    response.data = transformData(
      response.data,
      response.headers,
      config.transformResponse
    );

    return response;
  }, function onAdapterRejection(reason) {
    if (!isCancel(reason)) {
      throwIfCancellationRequested(config);

      // Transform response data
      if (reason && reason.response) {
        reason.response.data = transformData(
          reason.response.data,
          reason.response.headers,
          config.transformResponse
        );
      }
    }

    return Promise.reject(reason);
  });
};

},{"../cancel/isCancel":6,"../defaults":14,"./../helpers/combineURLs":18,"./../helpers/isAbsoluteURL":20,"./../utils":25,"./transformData":13}],11:[function(require,module,exports){
'use strict';

/**
 * Update an Error with the specified config, error code, and response.
 *
 * @param {Error} error The error to update.
 * @param {Object} config The config.
 * @param {string} [code] The error code (for example, 'ECONNABORTED').
 * @param {Object} [request] The request.
 * @param {Object} [response] The response.
 * @returns {Error} The error.
 */
module.exports = function enhanceError(error, config, code, request, response) {
  error.config = config;
  if (code) {
    error.code = code;
  }
  error.request = request;
  error.response = response;
  return error;
};

},{}],12:[function(require,module,exports){
'use strict';

var createError = require('./createError');

/**
 * Resolve or reject a Promise based on response status.
 *
 * @param {Function} resolve A function that resolves the promise.
 * @param {Function} reject A function that rejects the promise.
 * @param {object} response The response.
 */
module.exports = function settle(resolve, reject, response) {
  var validateStatus = response.config.validateStatus;
  // Note: status is not exposed by XDomainRequest
  if (!response.status || !validateStatus || validateStatus(response.status)) {
    resolve(response);
  } else {
    reject(createError(
      'Request failed with status code ' + response.status,
      response.config,
      null,
      response.request,
      response
    ));
  }
};

},{"./createError":9}],13:[function(require,module,exports){
'use strict';

var utils = require('./../utils');

/**
 * Transform the data for a request or a response
 *
 * @param {Object|String} data The data to be transformed
 * @param {Array} headers The headers for the request or response
 * @param {Array|Function} fns A single function or Array of functions
 * @returns {*} The resulting transformed data
 */
module.exports = function transformData(data, headers, fns) {
  /*eslint no-param-reassign:0*/
  utils.forEach(fns, function transform(fn) {
    data = fn(data, headers);
  });

  return data;
};

},{"./../utils":25}],14:[function(require,module,exports){
(function (process){
'use strict';

var utils = require('./utils');
var normalizeHeaderName = require('./helpers/normalizeHeaderName');

var DEFAULT_CONTENT_TYPE = {
  'Content-Type': 'application/x-www-form-urlencoded'
};

function setContentTypeIfUnset(headers, value) {
  if (!utils.isUndefined(headers) && utils.isUndefined(headers['Content-Type'])) {
    headers['Content-Type'] = value;
  }
}

function getDefaultAdapter() {
  var adapter;
  if (typeof XMLHttpRequest !== 'undefined') {
    // For browsers use XHR adapter
    adapter = require('./adapters/xhr');
  } else if (typeof process !== 'undefined') {
    // For node use HTTP adapter
    adapter = require('./adapters/http');
  }
  return adapter;
}

var defaults = {
  adapter: getDefaultAdapter(),

  transformRequest: [function transformRequest(data, headers) {
    normalizeHeaderName(headers, 'Content-Type');
    if (utils.isFormData(data) ||
      utils.isArrayBuffer(data) ||
      utils.isBuffer(data) ||
      utils.isStream(data) ||
      utils.isFile(data) ||
      utils.isBlob(data)
    ) {
      return data;
    }
    if (utils.isArrayBufferView(data)) {
      return data.buffer;
    }
    if (utils.isURLSearchParams(data)) {
      setContentTypeIfUnset(headers, 'application/x-www-form-urlencoded;charset=utf-8');
      return data.toString();
    }
    if (utils.isObject(data)) {
      setContentTypeIfUnset(headers, 'application/json;charset=utf-8');
      return JSON.stringify(data);
    }
    return data;
  }],

  transformResponse: [function transformResponse(data) {
    /*eslint no-param-reassign:0*/
    if (typeof data === 'string') {
      try {
        data = JSON.parse(data);
      } catch (e) { /* Ignore */ }
    }
    return data;
  }],

  timeout: 0,

  xsrfCookieName: 'XSRF-TOKEN',
  xsrfHeaderName: 'X-XSRF-TOKEN',

  maxContentLength: -1,

  validateStatus: function validateStatus(status) {
    return status >= 200 && status < 300;
  }
};

defaults.headers = {
  common: {
    'Accept': 'application/json, text/plain, */*'
  }
};

utils.forEach(['delete', 'get', 'head'], function forEachMethodNoData(method) {
  defaults.headers[method] = {};
});

utils.forEach(['post', 'put', 'patch'], function forEachMethodWithData(method) {
  defaults.headers[method] = utils.merge(DEFAULT_CONTENT_TYPE);
});

module.exports = defaults;

}).call(this,require('_process'))
},{"./adapters/http":2,"./adapters/xhr":2,"./helpers/normalizeHeaderName":22,"./utils":25,"_process":27}],15:[function(require,module,exports){
'use strict';

module.exports = function bind(fn, thisArg) {
  return function wrap() {
    var args = new Array(arguments.length);
    for (var i = 0; i < args.length; i++) {
      args[i] = arguments[i];
    }
    return fn.apply(thisArg, args);
  };
};

},{}],16:[function(require,module,exports){
'use strict';

// btoa polyfill for IE<10 courtesy https://github.com/davidchambers/Base64.js

var chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=';

function E() {
  this.message = 'String contains an invalid character';
}
E.prototype = new Error;
E.prototype.code = 5;
E.prototype.name = 'InvalidCharacterError';

function btoa(input) {
  var str = String(input);
  var output = '';
  for (
    // initialize result and counter
    var block, charCode, idx = 0, map = chars;
    // if the next str index does not exist:
    //   change the mapping table to "="
    //   check if d has no fractional digits
    str.charAt(idx | 0) || (map = '=', idx % 1);
    // "8 - idx % 1 * 8" generates the sequence 2, 4, 6, 8
    output += map.charAt(63 & block >> 8 - idx % 1 * 8)
  ) {
    charCode = str.charCodeAt(idx += 3 / 4);
    if (charCode > 0xFF) {
      throw new E();
    }
    block = block << 8 | charCode;
  }
  return output;
}

module.exports = btoa;

},{}],17:[function(require,module,exports){
'use strict';

var utils = require('./../utils');

function encode(val) {
  return encodeURIComponent(val).
    replace(/%40/gi, '@').
    replace(/%3A/gi, ':').
    replace(/%24/g, '$').
    replace(/%2C/gi, ',').
    replace(/%20/g, '+').
    replace(/%5B/gi, '[').
    replace(/%5D/gi, ']');
}

/**
 * Build a URL by appending params to the end
 *
 * @param {string} url The base of the url (e.g., http://www.google.com)
 * @param {object} [params] The params to be appended
 * @returns {string} The formatted url
 */
module.exports = function buildURL(url, params, paramsSerializer) {
  /*eslint no-param-reassign:0*/
  if (!params) {
    return url;
  }

  var serializedParams;
  if (paramsSerializer) {
    serializedParams = paramsSerializer(params);
  } else if (utils.isURLSearchParams(params)) {
    serializedParams = params.toString();
  } else {
    var parts = [];

    utils.forEach(params, function serialize(val, key) {
      if (val === null || typeof val === 'undefined') {
        return;
      }

      if (utils.isArray(val)) {
        key = key + '[]';
      }

      if (!utils.isArray(val)) {
        val = [val];
      }

      utils.forEach(val, function parseValue(v) {
        if (utils.isDate(v)) {
          v = v.toISOString();
        } else if (utils.isObject(v)) {
          v = JSON.stringify(v);
        }
        parts.push(encode(key) + '=' + encode(v));
      });
    });

    serializedParams = parts.join('&');
  }

  if (serializedParams) {
    url += (url.indexOf('?') === -1 ? '?' : '&') + serializedParams;
  }

  return url;
};

},{"./../utils":25}],18:[function(require,module,exports){
'use strict';

/**
 * Creates a new URL by combining the specified URLs
 *
 * @param {string} baseURL The base URL
 * @param {string} relativeURL The relative URL
 * @returns {string} The combined URL
 */
module.exports = function combineURLs(baseURL, relativeURL) {
  return relativeURL
    ? baseURL.replace(/\/+$/, '') + '/' + relativeURL.replace(/^\/+/, '')
    : baseURL;
};

},{}],19:[function(require,module,exports){
'use strict';

var utils = require('./../utils');

module.exports = (
  utils.isStandardBrowserEnv() ?

  // Standard browser envs support document.cookie
  (function standardBrowserEnv() {
    return {
      write: function write(name, value, expires, path, domain, secure) {
        var cookie = [];
        cookie.push(name + '=' + encodeURIComponent(value));

        if (utils.isNumber(expires)) {
          cookie.push('expires=' + new Date(expires).toGMTString());
        }

        if (utils.isString(path)) {
          cookie.push('path=' + path);
        }

        if (utils.isString(domain)) {
          cookie.push('domain=' + domain);
        }

        if (secure === true) {
          cookie.push('secure');
        }

        document.cookie = cookie.join('; ');
      },

      read: function read(name) {
        var match = document.cookie.match(new RegExp('(^|;\\s*)(' + name + ')=([^;]*)'));
        return (match ? decodeURIComponent(match[3]) : null);
      },

      remove: function remove(name) {
        this.write(name, '', Date.now() - 86400000);
      }
    };
  })() :

  // Non standard browser env (web workers, react-native) lack needed support.
  (function nonStandardBrowserEnv() {
    return {
      write: function write() {},
      read: function read() { return null; },
      remove: function remove() {}
    };
  })()
);

},{"./../utils":25}],20:[function(require,module,exports){
'use strict';

/**
 * Determines whether the specified URL is absolute
 *
 * @param {string} url The URL to test
 * @returns {boolean} True if the specified URL is absolute, otherwise false
 */
module.exports = function isAbsoluteURL(url) {
  // A URL is considered absolute if it begins with "<scheme>://" or "//" (protocol-relative URL).
  // RFC 3986 defines scheme name as a sequence of characters beginning with a letter and followed
  // by any combination of letters, digits, plus, period, or hyphen.
  return /^([a-z][a-z\d\+\-\.]*:)?\/\//i.test(url);
};

},{}],21:[function(require,module,exports){
'use strict';

var utils = require('./../utils');

module.exports = (
  utils.isStandardBrowserEnv() ?

  // Standard browser envs have full support of the APIs needed to test
  // whether the request URL is of the same origin as current location.
  (function standardBrowserEnv() {
    var msie = /(msie|trident)/i.test(navigator.userAgent);
    var urlParsingNode = document.createElement('a');
    var originURL;

    /**
    * Parse a URL to discover it's components
    *
    * @param {String} url The URL to be parsed
    * @returns {Object}
    */
    function resolveURL(url) {
      var href = url;

      if (msie) {
        // IE needs attribute set twice to normalize properties
        urlParsingNode.setAttribute('href', href);
        href = urlParsingNode.href;
      }

      urlParsingNode.setAttribute('href', href);

      // urlParsingNode provides the UrlUtils interface - http://url.spec.whatwg.org/#urlutils
      return {
        href: urlParsingNode.href,
        protocol: urlParsingNode.protocol ? urlParsingNode.protocol.replace(/:$/, '') : '',
        host: urlParsingNode.host,
        search: urlParsingNode.search ? urlParsingNode.search.replace(/^\?/, '') : '',
        hash: urlParsingNode.hash ? urlParsingNode.hash.replace(/^#/, '') : '',
        hostname: urlParsingNode.hostname,
        port: urlParsingNode.port,
        pathname: (urlParsingNode.pathname.charAt(0) === '/') ?
                  urlParsingNode.pathname :
                  '/' + urlParsingNode.pathname
      };
    }

    originURL = resolveURL(window.location.href);

    /**
    * Determine if a URL shares the same origin as the current location
    *
    * @param {String} requestURL The URL to test
    * @returns {boolean} True if URL shares the same origin, otherwise false
    */
    return function isURLSameOrigin(requestURL) {
      var parsed = (utils.isString(requestURL)) ? resolveURL(requestURL) : requestURL;
      return (parsed.protocol === originURL.protocol &&
            parsed.host === originURL.host);
    };
  })() :

  // Non standard browser envs (web workers, react-native) lack needed support.
  (function nonStandardBrowserEnv() {
    return function isURLSameOrigin() {
      return true;
    };
  })()
);

},{"./../utils":25}],22:[function(require,module,exports){
'use strict';

var utils = require('../utils');

module.exports = function normalizeHeaderName(headers, normalizedName) {
  utils.forEach(headers, function processHeader(value, name) {
    if (name !== normalizedName && name.toUpperCase() === normalizedName.toUpperCase()) {
      headers[normalizedName] = value;
      delete headers[name];
    }
  });
};

},{"../utils":25}],23:[function(require,module,exports){
'use strict';

var utils = require('./../utils');

// Headers whose duplicates are ignored by node
// c.f. https://nodejs.org/api/http.html#http_message_headers
var ignoreDuplicateOf = [
  'age', 'authorization', 'content-length', 'content-type', 'etag',
  'expires', 'from', 'host', 'if-modified-since', 'if-unmodified-since',
  'last-modified', 'location', 'max-forwards', 'proxy-authorization',
  'referer', 'retry-after', 'user-agent'
];

/**
 * Parse headers into an object
 *
 * ```
 * Date: Wed, 27 Aug 2014 08:58:49 GMT
 * Content-Type: application/json
 * Connection: keep-alive
 * Transfer-Encoding: chunked
 * ```
 *
 * @param {String} headers Headers needing to be parsed
 * @returns {Object} Headers parsed into an object
 */
module.exports = function parseHeaders(headers) {
  var parsed = {};
  var key;
  var val;
  var i;

  if (!headers) { return parsed; }

  utils.forEach(headers.split('\n'), function parser(line) {
    i = line.indexOf(':');
    key = utils.trim(line.substr(0, i)).toLowerCase();
    val = utils.trim(line.substr(i + 1));

    if (key) {
      if (parsed[key] && ignoreDuplicateOf.indexOf(key) >= 0) {
        return;
      }
      if (key === 'set-cookie') {
        parsed[key] = (parsed[key] ? parsed[key] : []).concat([val]);
      } else {
        parsed[key] = parsed[key] ? parsed[key] + ', ' + val : val;
      }
    }
  });

  return parsed;
};

},{"./../utils":25}],24:[function(require,module,exports){
'use strict';

/**
 * Syntactic sugar for invoking a function and expanding an array for arguments.
 *
 * Common use case would be to use `Function.prototype.apply`.
 *
 *  ```js
 *  function f(x, y, z) {}
 *  var args = [1, 2, 3];
 *  f.apply(null, args);
 *  ```
 *
 * With `spread` this example can be re-written.
 *
 *  ```js
 *  spread(function(x, y, z) {})([1, 2, 3]);
 *  ```
 *
 * @param {Function} callback
 * @returns {Function}
 */
module.exports = function spread(callback) {
  return function wrap(arr) {
    return callback.apply(null, arr);
  };
};

},{}],25:[function(require,module,exports){
'use strict';

var bind = require('./helpers/bind');
var isBuffer = require('is-buffer');

/*global toString:true*/

// utils is a library of generic helper functions non-specific to axios

var toString = Object.prototype.toString;

/**
 * Determine if a value is an Array
 *
 * @param {Object} val The value to test
 * @returns {boolean} True if value is an Array, otherwise false
 */
function isArray(val) {
  return toString.call(val) === '[object Array]';
}

/**
 * Determine if a value is an ArrayBuffer
 *
 * @param {Object} val The value to test
 * @returns {boolean} True if value is an ArrayBuffer, otherwise false
 */
function isArrayBuffer(val) {
  return toString.call(val) === '[object ArrayBuffer]';
}

/**
 * Determine if a value is a FormData
 *
 * @param {Object} val The value to test
 * @returns {boolean} True if value is an FormData, otherwise false
 */
function isFormData(val) {
  return (typeof FormData !== 'undefined') && (val instanceof FormData);
}

/**
 * Determine if a value is a view on an ArrayBuffer
 *
 * @param {Object} val The value to test
 * @returns {boolean} True if value is a view on an ArrayBuffer, otherwise false
 */
function isArrayBufferView(val) {
  var result;
  if ((typeof ArrayBuffer !== 'undefined') && (ArrayBuffer.isView)) {
    result = ArrayBuffer.isView(val);
  } else {
    result = (val) && (val.buffer) && (val.buffer instanceof ArrayBuffer);
  }
  return result;
}

/**
 * Determine if a value is a String
 *
 * @param {Object} val The value to test
 * @returns {boolean} True if value is a String, otherwise false
 */
function isString(val) {
  return typeof val === 'string';
}

/**
 * Determine if a value is a Number
 *
 * @param {Object} val The value to test
 * @returns {boolean} True if value is a Number, otherwise false
 */
function isNumber(val) {
  return typeof val === 'number';
}

/**
 * Determine if a value is undefined
 *
 * @param {Object} val The value to test
 * @returns {boolean} True if the value is undefined, otherwise false
 */
function isUndefined(val) {
  return typeof val === 'undefined';
}

/**
 * Determine if a value is an Object
 *
 * @param {Object} val The value to test
 * @returns {boolean} True if value is an Object, otherwise false
 */
function isObject(val) {
  return val !== null && typeof val === 'object';
}

/**
 * Determine if a value is a Date
 *
 * @param {Object} val The value to test
 * @returns {boolean} True if value is a Date, otherwise false
 */
function isDate(val) {
  return toString.call(val) === '[object Date]';
}

/**
 * Determine if a value is a File
 *
 * @param {Object} val The value to test
 * @returns {boolean} True if value is a File, otherwise false
 */
function isFile(val) {
  return toString.call(val) === '[object File]';
}

/**
 * Determine if a value is a Blob
 *
 * @param {Object} val The value to test
 * @returns {boolean} True if value is a Blob, otherwise false
 */
function isBlob(val) {
  return toString.call(val) === '[object Blob]';
}

/**
 * Determine if a value is a Function
 *
 * @param {Object} val The value to test
 * @returns {boolean} True if value is a Function, otherwise false
 */
function isFunction(val) {
  return toString.call(val) === '[object Function]';
}

/**
 * Determine if a value is a Stream
 *
 * @param {Object} val The value to test
 * @returns {boolean} True if value is a Stream, otherwise false
 */
function isStream(val) {
  return isObject(val) && isFunction(val.pipe);
}

/**
 * Determine if a value is a URLSearchParams object
 *
 * @param {Object} val The value to test
 * @returns {boolean} True if value is a URLSearchParams object, otherwise false
 */
function isURLSearchParams(val) {
  return typeof URLSearchParams !== 'undefined' && val instanceof URLSearchParams;
}

/**
 * Trim excess whitespace off the beginning and end of a string
 *
 * @param {String} str The String to trim
 * @returns {String} The String freed of excess whitespace
 */
function trim(str) {
  return str.replace(/^\s*/, '').replace(/\s*$/, '');
}

/**
 * Determine if we're running in a standard browser environment
 *
 * This allows axios to run in a web worker, and react-native.
 * Both environments support XMLHttpRequest, but not fully standard globals.
 *
 * web workers:
 *  typeof window -> undefined
 *  typeof document -> undefined
 *
 * react-native:
 *  navigator.product -> 'ReactNative'
 */
function isStandardBrowserEnv() {
  if (typeof navigator !== 'undefined' && navigator.product === 'ReactNative') {
    return false;
  }
  return (
    typeof window !== 'undefined' &&
    typeof document !== 'undefined'
  );
}

/**
 * Iterate over an Array or an Object invoking a function for each item.
 *
 * If `obj` is an Array callback will be called passing
 * the value, index, and complete array for each item.
 *
 * If 'obj' is an Object callback will be called passing
 * the value, key, and complete object for each property.
 *
 * @param {Object|Array} obj The object to iterate
 * @param {Function} fn The callback to invoke for each item
 */
function forEach(obj, fn) {
  // Don't bother if no value provided
  if (obj === null || typeof obj === 'undefined') {
    return;
  }

  // Force an array if not already something iterable
  if (typeof obj !== 'object') {
    /*eslint no-param-reassign:0*/
    obj = [obj];
  }

  if (isArray(obj)) {
    // Iterate over array values
    for (var i = 0, l = obj.length; i < l; i++) {
      fn.call(null, obj[i], i, obj);
    }
  } else {
    // Iterate over object keys
    for (var key in obj) {
      if (Object.prototype.hasOwnProperty.call(obj, key)) {
        fn.call(null, obj[key], key, obj);
      }
    }
  }
}

/**
 * Accepts varargs expecting each argument to be an object, then
 * immutably merges the properties of each object and returns result.
 *
 * When multiple objects contain the same key the later object in
 * the arguments list will take precedence.
 *
 * Example:
 *
 * ```js
 * var result = merge({foo: 123}, {foo: 456});
 * console.log(result.foo); // outputs 456
 * ```
 *
 * @param {Object} obj1 Object to merge
 * @returns {Object} Result of all merge properties
 */
function merge(/* obj1, obj2, obj3, ... */) {
  var result = {};
  function assignValue(val, key) {
    if (typeof result[key] === 'object' && typeof val === 'object') {
      result[key] = merge(result[key], val);
    } else {
      result[key] = val;
    }
  }

  for (var i = 0, l = arguments.length; i < l; i++) {
    forEach(arguments[i], assignValue);
  }
  return result;
}

/**
 * Extends object a by mutably adding to it the properties of object b.
 *
 * @param {Object} a The object to be extended
 * @param {Object} b The object to copy properties from
 * @param {Object} thisArg The object to bind function to
 * @return {Object} The resulting value of object a
 */
function extend(a, b, thisArg) {
  forEach(b, function assignValue(val, key) {
    if (thisArg && typeof val === 'function') {
      a[key] = bind(val, thisArg);
    } else {
      a[key] = val;
    }
  });
  return a;
}

module.exports = {
  isArray: isArray,
  isArrayBuffer: isArrayBuffer,
  isBuffer: isBuffer,
  isFormData: isFormData,
  isArrayBufferView: isArrayBufferView,
  isString: isString,
  isNumber: isNumber,
  isObject: isObject,
  isUndefined: isUndefined,
  isDate: isDate,
  isFile: isFile,
  isBlob: isBlob,
  isFunction: isFunction,
  isStream: isStream,
  isURLSearchParams: isURLSearchParams,
  isStandardBrowserEnv: isStandardBrowserEnv,
  forEach: forEach,
  merge: merge,
  extend: extend,
  trim: trim
};

},{"./helpers/bind":15,"is-buffer":26}],26:[function(require,module,exports){
/*!
 * Determine if an object is a Buffer
 *
 * @author   Feross Aboukhadijeh <https://feross.org>
 * @license  MIT
 */

// The _isBuffer check is for Safari 5-7 support, because it's missing
// Object.prototype.constructor. Remove this eventually
module.exports = function (obj) {
  return obj != null && (isBuffer(obj) || isSlowBuffer(obj) || !!obj._isBuffer)
}

function isBuffer (obj) {
  return !!obj.constructor && typeof obj.constructor.isBuffer === 'function' && obj.constructor.isBuffer(obj)
}

// For Node v0.10 support. Remove this eventually.
function isSlowBuffer (obj) {
  return typeof obj.readFloatLE === 'function' && typeof obj.slice === 'function' && isBuffer(obj.slice(0, 0))
}

},{}],27:[function(require,module,exports){
// shim for using process in browser
var process = module.exports = {};

// cached from whatever global is present so that test runners that stub it
// don't break things.  But we need to wrap it in a try catch in case it is
// wrapped in strict mode code which doesn't define any globals.  It's inside a
// function because try/catches deoptimize in certain engines.

var cachedSetTimeout;
var cachedClearTimeout;

function defaultSetTimout() {
    throw new Error('setTimeout has not been defined');
}
function defaultClearTimeout () {
    throw new Error('clearTimeout has not been defined');
}
(function () {
    try {
        if (typeof setTimeout === 'function') {
            cachedSetTimeout = setTimeout;
        } else {
            cachedSetTimeout = defaultSetTimout;
        }
    } catch (e) {
        cachedSetTimeout = defaultSetTimout;
    }
    try {
        if (typeof clearTimeout === 'function') {
            cachedClearTimeout = clearTimeout;
        } else {
            cachedClearTimeout = defaultClearTimeout;
        }
    } catch (e) {
        cachedClearTimeout = defaultClearTimeout;
    }
} ())
function runTimeout(fun) {
    if (cachedSetTimeout === setTimeout) {
        //normal enviroments in sane situations
        return setTimeout(fun, 0);
    }
    // if setTimeout wasn't available but was latter defined
    if ((cachedSetTimeout === defaultSetTimout || !cachedSetTimeout) && setTimeout) {
        cachedSetTimeout = setTimeout;
        return setTimeout(fun, 0);
    }
    try {
        // when when somebody has screwed with setTimeout but no I.E. maddness
        return cachedSetTimeout(fun, 0);
    } catch(e){
        try {
            // When we are in I.E. but the script has been evaled so I.E. doesn't trust the global object when called normally
            return cachedSetTimeout.call(null, fun, 0);
        } catch(e){
            // same as above but when it's a version of I.E. that must have the global object for 'this', hopfully our context correct otherwise it will throw a global error
            return cachedSetTimeout.call(this, fun, 0);
        }
    }


}
function runClearTimeout(marker) {
    if (cachedClearTimeout === clearTimeout) {
        //normal enviroments in sane situations
        return clearTimeout(marker);
    }
    // if clearTimeout wasn't available but was latter defined
    if ((cachedClearTimeout === defaultClearTimeout || !cachedClearTimeout) && clearTimeout) {
        cachedClearTimeout = clearTimeout;
        return clearTimeout(marker);
    }
    try {
        // when when somebody has screwed with setTimeout but no I.E. maddness
        return cachedClearTimeout(marker);
    } catch (e){
        try {
            // When we are in I.E. but the script has been evaled so I.E. doesn't  trust the global object when called normally
            return cachedClearTimeout.call(null, marker);
        } catch (e){
            // same as above but when it's a version of I.E. that must have the global object for 'this', hopfully our context correct otherwise it will throw a global error.
            // Some versions of I.E. have different rules for clearTimeout vs setTimeout
            return cachedClearTimeout.call(this, marker);
        }
    }



}
var queue = [];
var draining = false;
var currentQueue;
var queueIndex = -1;

function cleanUpNextTick() {
    if (!draining || !currentQueue) {
        return;
    }
    draining = false;
    if (currentQueue.length) {
        queue = currentQueue.concat(queue);
    } else {
        queueIndex = -1;
    }
    if (queue.length) {
        drainQueue();
    }
}

function drainQueue() {
    if (draining) {
        return;
    }
    var timeout = runTimeout(cleanUpNextTick);
    draining = true;

    var len = queue.length;
    while(len) {
        currentQueue = queue;
        queue = [];
        while (++queueIndex < len) {
            if (currentQueue) {
                currentQueue[queueIndex].run();
            }
        }
        queueIndex = -1;
        len = queue.length;
    }
    currentQueue = null;
    draining = false;
    runClearTimeout(timeout);
}

process.nextTick = function (fun) {
    var args = new Array(arguments.length - 1);
    if (arguments.length > 1) {
        for (var i = 1; i < arguments.length; i++) {
            args[i - 1] = arguments[i];
        }
    }
    queue.push(new Item(fun, args));
    if (queue.length === 1 && !draining) {
        runTimeout(drainQueue);
    }
};

// v8 likes predictible objects
function Item(fun, array) {
    this.fun = fun;
    this.array = array;
}
Item.prototype.run = function () {
    this.fun.apply(null, this.array);
};
process.title = 'browser';
process.browser = true;
process.env = {};
process.argv = [];
process.version = ''; // empty string to avoid regexp issues
process.versions = {};

function noop() {}

process.on = noop;
process.addListener = noop;
process.once = noop;
process.off = noop;
process.removeListener = noop;
process.removeAllListeners = noop;
process.emit = noop;
process.prependListener = noop;
process.prependOnceListener = noop;

process.listeners = function (name) { return [] }

process.binding = function (name) {
    throw new Error('process.binding is not supported');
};

process.cwd = function () { return '/' };
process.chdir = function (dir) {
    throw new Error('process.chdir is not supported');
};
process.umask = function() { return 0; };

},{}],28:[function(require,module,exports){
const axios = require('axios');

const baseUrl = $('body').attr('api-root');
const idToken = $('body').attr('api-key');

const api = axios.create({
    baseURL: baseUrl,
    timeout: 10000,
    headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        'X-Api-Key': idToken
    }
});

module.exports = api;

},{"axios":1}],29:[function(require,module,exports){
const MEDUSA = require('../core');

MEDUSA.config.notifications = function () {
    // eslint-disable-line max-lines
    $('#testGrowl').on('click', function () {
        const growl = {};
        growl.host = $.trim($('#growl_host').val());
        growl.password = $.trim($('#growl_password').val());
        if (!growl.host) {
            $('#testGrowl-result').html('Please fill out the necessary fields above.');
            $('#growl_host').addClass('warning');
            return;
        }
        $('#growl_host').removeClass('warning');
        $(this).prop('disabled', true);
        $('#testGrowl-result').html(MEDUSA.config.loading);
        $.get('home/testGrowl', {
            host: growl.host,
            password: growl.password
        }).done(data => {
            $('#testGrowl-result').html(data);
            $('#testGrowl').prop('disabled', false);
        });
    });

    $('#testProwl').on('click', function () {
        const prowl = {};
        prowl.api = $.trim($('#prowl_api').val());
        prowl.priority = $('#prowl_priority').val();
        if (!prowl.api) {
            $('#testProwl-result').html('Please fill out the necessary fields above.');
            $('#prowl_api').addClass('warning');
            return;
        }
        $('#prowl_api').removeClass('warning');
        $(this).prop('disabled', true);
        $('#testProwl-result').html(MEDUSA.config.loading);
        $.get('home/testProwl', {
            prowl_api: prowl.api, // eslint-disable-line camelcase
            prowl_priority: prowl.priority // eslint-disable-line camelcase
        }).done(data => {
            $('#testProwl-result').html(data);
            $('#testProwl').prop('disabled', false);
        });
    });

    $('#testKODI').on('click', function () {
        const kodi = {};
        kodi.host = $.trim($('#kodi_host').val());
        kodi.username = $.trim($('#kodi_username').val());
        kodi.password = $.trim($('#kodi_password').val());
        if (!kodi.host) {
            $('#testKODI-result').html('Please fill out the necessary fields above.');
            $('#kodi_host').addClass('warning');
            return;
        }
        $('#kodi_host').removeClass('warning');
        $(this).prop('disabled', true);
        $('#testKODI-result').html(MEDUSA.config.loading);
        $.get('home/testKODI', {
            host: kodi.host,
            username: kodi.username,
            password: kodi.password
        }).done(data => {
            $('#testKODI-result').html(data);
            $('#testKODI').prop('disabled', false);
        });
    });

    $('#testPHT').on('click', function () {
        const plex = {};
        plex.client = {};
        plex.client.host = $.trim($('#plex_client_host').val());
        plex.client.username = $.trim($('#plex_client_username').val());
        plex.client.password = $.trim($('#plex_client_password').val());
        if (!plex.client.host) {
            $('#testPHT-result').html('Please fill out the necessary fields above.');
            $('#plex_client_host').addClass('warning');
            return;
        }
        $('#plex_client_host').removeClass('warning');
        $(this).prop('disabled', true);
        $('#testPHT-result').html(MEDUSA.config.loading);
        $.get('home/testPHT', {
            host: plex.client.host,
            username: plex.client.username,
            password: plex.client.password
        }).done(data => {
            $('#testPHT-result').html(data);
            $('#testPHT').prop('disabled', false);
        });
    });

    $('#testPMS').on('click', function () {
        const plex = {};
        plex.server = {};
        plex.server.host = $.trim($('#plex_server_host').val());
        plex.server.username = $.trim($('#plex_server_username').val());
        plex.server.password = $.trim($('#plex_server_password').val());
        plex.server.token = $.trim($('#plex_server_token').val());
        if (!plex.server.host) {
            $('#testPMS-result').html('Please fill out the necessary fields above.');
            $('#plex_server_host').addClass('warning');
            return;
        }
        $('#plex_server_host').removeClass('warning');
        $(this).prop('disabled', true);
        $('#testPMS-result').html(MEDUSA.config.loading);
        $.get('home/testPMS', {
            host: plex.server.host,
            username: plex.server.username,
            password: plex.server.password,
            plex_server_token: plex.server.token // eslint-disable-line camelcase
        }).done(data => {
            $('#testPMS-result').html(data);
            $('#testPMS').prop('disabled', false);
        });
    });

    $('#testEMBY').on('click', function () {
        const emby = {};
        emby.host = $('#emby_host').val();
        emby.apikey = $('#emby_apikey').val();
        if (!emby.host || !emby.apikey) {
            $('#testEMBY-result').html('Please fill out the necessary fields above.');
            $('#emby_host').addRemoveWarningClass(emby.host);
            $('#emby_apikey').addRemoveWarningClass(emby.apikey);
            return;
        }
        $('#emby_host,#emby_apikey').removeClass('warning');
        $(this).prop('disabled', true);
        $('#testEMBY-result').html(MEDUSA.config.loading);
        $.get('home/testEMBY', {
            host: emby.host,
            emby_apikey: emby.apikey // eslint-disable-line camelcase
        }).done(data => {
            $('#testEMBY-result').html(data);
            $('#testEMBY').prop('disabled', false);
        });
    });

    $('#testBoxcar2').on('click', function () {
        const boxcar2 = {};
        boxcar2.accesstoken = $.trim($('#boxcar2_accesstoken').val());
        if (!boxcar2.accesstoken) {
            $('#testBoxcar2-result').html('Please fill out the necessary fields above.');
            $('#boxcar2_accesstoken').addClass('warning');
            return;
        }
        $('#boxcar2_accesstoken').removeClass('warning');
        $(this).prop('disabled', true);
        $('#testBoxcar2-result').html(MEDUSA.config.loading);
        $.get('home/testBoxcar2', {
            accesstoken: boxcar2.accesstoken
        }).done(data => {
            $('#testBoxcar2-result').html(data);
            $('#testBoxcar2').prop('disabled', false);
        });
    });

    $('#testPushover').on('click', function () {
        const pushover = {};
        pushover.userkey = $('#pushover_userkey').val();
        pushover.apikey = $('#pushover_apikey').val();
        if (!pushover.userkey || !pushover.apikey) {
            $('#testPushover-result').html('Please fill out the necessary fields above.');
            $('#pushover_userkey').addRemoveWarningClass(pushover.userkey);
            $('#pushover_apikey').addRemoveWarningClass(pushover.apikey);
            return;
        }
        $('#pushover_userkey,#pushover_apikey').removeClass('warning');
        $(this).prop('disabled', true);
        $('#testPushover-result').html(MEDUSA.config.loading);
        $.get('home/testPushover', {
            userKey: pushover.userkey,
            apiKey: pushover.apikey
        }).done(data => {
            $('#testPushover-result').html(data);
            $('#testPushover').prop('disabled', false);
        });
    });

    $('#testLibnotify').on('click', () => {
        $('#testLibnotify-result').html(MEDUSA.config.loading);
        $.get('home/testLibnotify', data => {
            $('#testLibnotify-result').html(data);
        });
    });

    $('#twitterStep1').on('click', () => {
        $('#testTwitter-result').html(MEDUSA.config.loading);
        $.get('home/twitterStep1', data => {
            window.open(data);
        }).done(() => {
            $('#testTwitter-result').html('<b>Step1:</b> Confirm Authorization');
        });
    });

    $('#twitterStep2').on('click', () => {
        const twitter = {};
        twitter.key = $.trim($('#twitter_key').val());
        $('#twitter_key').addRemoveWarningClass(twitter.key);
        if (twitter.key) {
            $('#testTwitter-result').html(MEDUSA.config.loading);
            $.get('home/twitterStep2', {
                key: twitter.key
            }, data => {
                $('#testTwitter-result').html(data);
            });
        }
        $('#testTwitter-result').html('Please fill out the necessary fields above.');
    });

    $('#testTwitter').on('click', () => {
        $.get('home/testTwitter', data => {
            $('#testTwitter-result').html(data);
        });
    });

    $('#settingsNMJ').on('click', () => {
        const nmj = {};
        if ($('#nmj_host').val()) {
            $('#testNMJ-result').html(MEDUSA.config.loading);
            nmj.host = $('#nmj_host').val();

            $.get('home/settingsNMJ', {
                host: nmj.host
            }, data => {
                if (data === null) {
                    $('#nmj_database').removeAttr('readonly');
                    $('#nmj_mount').removeAttr('readonly');
                }
                const JSONData = $.parseJSON(data);
                $('#testNMJ-result').html(JSONData.message);
                $('#nmj_database').val(JSONData.database);
                $('#nmj_mount').val(JSONData.mount);

                if (JSONData.database) {
                    $('#nmj_database').prop('readonly', true);
                } else {
                    $('#nmj_database').removeAttr('readonly');
                }
                if (JSONData.mount) {
                    $('#nmj_mount').prop('readonly', true);
                } else {
                    $('#nmj_mount').removeAttr('readonly');
                }
            });
        }
        alert('Please fill in the Popcorn IP address'); // eslint-disable-line no-alert
        $('#nmj_host').focus();
    });

    $('#testNMJ').on('click', function () {
        const nmj = {};
        nmj.host = $.trim($('#nmj_host').val());
        nmj.database = $('#nmj_database').val();
        nmj.mount = $('#nmj_mount').val();
        if (nmj.host) {
            $('#nmj_host').removeClass('warning');
            $(this).prop('disabled', true);
            $('#testNMJ-result').html(MEDUSA.config.loading);
            $.get('home/testNMJ', {
                host: nmj.host,
                database: nmj.database,
                mount: nmj.mount
            }).done(data => {
                $('#testNMJ-result').html(data);
                $('#testNMJ').prop('disabled', false);
            });
        }
        $('#testNMJ-result').html('Please fill out the necessary fields above.');
        $('#nmj_host').addClass('warning');
    });

    $('#settingsNMJv2').on('click', () => {
        const nmjv2 = {};
        if ($('#nmjv2_host').val()) {
            $('#testNMJv2-result').html(MEDUSA.config.loading);
            nmjv2.host = $('#nmjv2_host').val();
            nmjv2.dbloc = '';
            const radios = document.getElementsByName('nmjv2_dbloc');
            for (let i = 0, len = radios.length; i < len; i++) {
                if (radios[i].checked) {
                    nmjv2.dbloc = radios[i].value;
                    break;
                }
            }

            nmjv2.dbinstance = $('#NMJv2db_instance').val();
            $.get('home/settingsNMJv2', {
                host: nmjv2.host,
                dbloc: nmjv2.dbloc,
                instance: nmjv2.dbinstance
            }, data => {
                if (data === null) {
                    $('#nmjv2_database').removeAttr('readonly');
                }
                const JSONData = $.parseJSON(data);
                $('#testNMJv2-result').html(JSONData.message);
                $('#nmjv2_database').val(JSONData.database);

                if (JSONData.database) {
                    $('#nmjv2_database').prop('readonly', true);
                } else {
                    $('#nmjv2_database').removeAttr('readonly');
                }
            });
        }
        alert('Please fill in the Popcorn IP address'); // eslint-disable-line no-alert
        $('#nmjv2_host').focus();
    });

    $('#testNMJv2').on('click', function () {
        const nmjv2 = {};
        nmjv2.host = $.trim($('#nmjv2_host').val());
        if (nmjv2.host) {
            $('#nmjv2_host').removeClass('warning');
            $(this).prop('disabled', true);
            $('#testNMJv2-result').html(MEDUSA.config.loading);
            $.get('home/testNMJv2', {
                host: nmjv2.host
            }).done(data => {
                $('#testNMJv2-result').html(data);
                $('#testNMJv2').prop('disabled', false);
            });
        }
        $('#testNMJv2-result').html('Please fill out the necessary fields above.');
        $('#nmjv2_host').addClass('warning');
    });

    $('#testFreeMobile').on('click', function () {
        const freemobile = {};
        freemobile.id = $.trim($('#freemobile_id').val());
        freemobile.apikey = $.trim($('#freemobile_apikey').val());
        if (!freemobile.id || !freemobile.apikey) {
            $('#testFreeMobile-result').html('Please fill out the necessary fields above.');
            if (freemobile.id) {
                $('#freemobile_id').removeClass('warning');
            } else {
                $('#freemobile_id').addClass('warning');
            }
            if (freemobile.apikey) {
                $('#freemobile_apikey').removeClass('warning');
            } else {
                $('#freemobile_apikey').addClass('warning');
            }
            return;
        }
        $('#freemobile_id,#freemobile_apikey').removeClass('warning');
        $(this).prop('disabled', true);
        $('#testFreeMobile-result').html(MEDUSA.config.loading);
        $.get('home/testFreeMobile', {
            freemobile_id: freemobile.id, // eslint-disable-line camelcase
            freemobile_apikey: freemobile.apikey // eslint-disable-line camelcase
        }).done(data => {
            $('#testFreeMobile-result').html(data);
            $('#testFreeMobile').prop('disabled', false);
        });
    });

    $('#testTelegram').on('click', function () {
        const telegram = {};
        telegram.id = $.trim($('#telegram_id').val());
        telegram.apikey = $.trim($('#telegram_apikey').val());
        if (!telegram.id || !telegram.apikey) {
            $('#testTelegram-result').html('Please fill out the necessary fields above.');
            $('#telegram_id').addRemoveWarningClass(telegram.id);
            $('#telegram_apikey').addRemoveWarningClass(telegram.apikey);
            return;
        }
        $('#telegram_id,#telegram_apikey').removeClass('warning');
        $(this).prop('disabled', true);
        $('#testTelegram-result').html(MEDUSA.config.loading);
        $.get('home/testTelegram', {
            telegram_id: telegram.id, // eslint-disable-line camelcase
            telegram_apikey: telegram.apikey // eslint-disable-line camelcase
        }).done(data => {
            $('#testTelegram-result').html(data);
            $('#testTelegram').prop('disabled', false);
        });
    });

    $('#testSlack').on('click', function () {
        const slack = {};
        slack.webhook = $.trim($('#slack_webhook').val());

        if (!slack.webhook) {
            $('#testSlack-result').html('Please fill out the necessary fields above.');
            $('#slack_webhook').addRemoveWarningClass(slack.webhook);
            return;
        }
        $('#slack_webhook').removeClass('warning');
        $(this).prop('disabled', true);
        $('#testSlack-result').html(MEDUSA.config.loading);
        $.get('home/testslack', {
            slack_webhook: slack.webhook // eslint-disable-line camelcase
        }).done(data => {
            $('#testSlack-result').html(data);
            $('#testSlack').prop('disabled', false);
        });
    });

    $('#TraktGetPin').on('click', () => {
        window.open($('#trakt_pin_url').val(), 'popUp', 'toolbar=no, scrollbars=no, resizable=no, top=200, left=200, width=650, height=550');
        $('#trakt_pin').prop('disabled', false);
    });

    $('#trakt_pin').on('keyup change', () => {
        if ($('#trakt_pin').val().length === 0) {
            $('#TraktGetPin').removeClass('hide');
            $('#authTrakt').addClass('hide');
        } else {
            $('#TraktGetPin').addClass('hide');
            $('#authTrakt').removeClass('hide');
        }
    });

    $('#authTrakt').on('click', () => {
        const trakt = {};
        trakt.pin = $('#trakt_pin').val();
        if (trakt.pin.length !== 0) {
            $.get('home/getTraktToken', {
                trakt_pin: trakt.pin // eslint-disable-line camelcase
            }).done(data => {
                $('#testTrakt-result').html(data);
                $('#authTrakt').addClass('hide');
                $('#trakt_pin').prop('disabled', true);
                $('#trakt_pin').val('');
                $('#TraktGetPin').removeClass('hide');
            });
        }
    });

    $('#testTrakt').on('click', function () {
        const trakt = {};
        trakt.username = $.trim($('#trakt_username').val());
        trakt.trendingBlacklist = $.trim($('#trakt_blacklist_name').val());
        if (!trakt.username) {
            $('#testTrakt-result').html('Please fill out the necessary fields above.');
            $('#trakt_username').addRemoveWarningClass(trakt.username);
            return;
        }

        if (/\s/g.test(trakt.trendingBlacklist)) {
            $('#testTrakt-result').html('Check blacklist name; the value needs to be a trakt slug');
            $('#trakt_blacklist_name').addClass('warning');
            return;
        }
        $('#trakt_username').removeClass('warning');
        $('#trakt_blacklist_name').removeClass('warning');
        $(this).prop('disabled', true);
        $('#testTrakt-result').html(MEDUSA.config.loading);
        $.get('home/testTrakt', {
            username: trakt.username,
            blacklist_name: trakt.trendingBlacklist // eslint-disable-line camelcase
        }).done(data => {
            $('#testTrakt-result').html(data);
            $('#testTrakt').prop('disabled', false);
        });
    });

    $('#forceSync').on('click', () => {
        $('#testTrakt-result').html(MEDUSA.config.loading);
        $.getJSON('home/forceTraktSync', data => {
            $('#testTrakt-result').html(data.result);
        });
    });

    $('#testEmail').on('click', () => {
        const tls = $('#email_tls').attr('checked') === undefined ? 0 : 1;
        const user = $('#email_user').val().trim();
        const pwd = $('#email_password').val();
        const status = $('#testEmail-result');

        status.html(MEDUSA.config.loading);
        let host = $('#email_host').val();
        host = host.length > 0 ? host : null;

        let port = $('#email_port').val();
        port = port.length > 0 ? port : null;

        let from = $('#email_from').val();
        from = from.length > 0 ? from : 'root@localhost';

        let err = '';
        if (host === null) {
            err += '<li style="color: red;">You must specify an SMTP hostname!</li>';
        }
        if (port === null) {
            err += '<li style="color: red;">You must specify an SMTP port!</li>';
        } else if (port.match(/^\d+$/) === null || parseInt(port, 10) > 65535) {
            err += '<li style="color: red;">SMTP port must be between 0 and 65535!</li>';
        }
        if (err.length > 0) {
            err = '<ol>' + err + '</ol>';
            status.html(err);
        } else {
            const to = prompt('Enter an email address to send the test to:', null); // eslint-disable-line no-alert
            if (to === null || to.length === 0 || to.match(/.*@.*/) === null) {
                status.html('<p style="color: red;">You must provide a recipient email address!</p>');
            } else {
                $.get('home/testEmail', {
                    host,
                    port,
                    smtp_from: from, // eslint-disable-line camelcase
                    use_tls: tls, // eslint-disable-line camelcase
                    user,
                    pwd,
                    to
                }, msg => {
                    $('#testEmail-result').html(msg);
                });
            }
        }
    });

    $('#testNMA').on('click', function () {
        const nma = {};
        nma.api = $.trim($('#nma_api').val());
        nma.priority = $('#nma_priority').val();
        if (!nma.api) {
            $('#testNMA-result').html('Please fill out the necessary fields above.');
            $('#nma_api').addClass('warning');
            return;
        }
        $('#nma_api').removeClass('warning');
        $(this).prop('disabled', true);
        $('#testNMA-result').html(MEDUSA.config.loading);
        $.get('home/testNMA', {
            nma_api: nma.api, // eslint-disable-line camelcase
            nma_priority: nma.priority // eslint-disable-line camelcase
        }).done(data => {
            $('#testNMA-result').html(data);
            $('#testNMA').prop('disabled', false);
        });
    });

    $('#testPushalot').on('click', function () {
        const pushalot = {};
        pushalot.authToken = $.trim($('#pushalot_authorizationtoken').val());
        if (!pushalot.authToken) {
            $('#testPushalot-result').html('Please fill out the necessary fields above.');
            $('#pushalot_authorizationtoken').addClass('warning');
            return;
        }
        $('#pushalot_authorizationtoken').removeClass('warning');
        $(this).prop('disabled', true);
        $('#testPushalot-result').html(MEDUSA.config.loading);
        $.get('home/testPushalot', {
            authorizationToken: pushalot.authToken
        }).done(data => {
            $('#testPushalot-result').html(data);
            $('#testPushalot').prop('disabled', false);
        });
    });

    $('#testPushbullet').on('click', function () {
        const pushbullet = {};
        pushbullet.api = $.trim($('#pushbullet_api').val());
        if (!pushbullet.api) {
            $('#testPushbullet-result').html('Please fill out the necessary fields above.');
            $('#pushbullet_api').addClass('warning');
            return;
        }
        $('#pushbullet_api').removeClass('warning');
        $(this).prop('disabled', true);
        $('#testPushbullet-result').html(MEDUSA.config.loading);
        $.get('home/testPushbullet', {
            api: pushbullet.api
        }).done(data => {
            $('#testPushbullet-result').html(data);
            $('#testPushbullet').prop('disabled', false);
        });
    });

    const getPushbulletDevices = msg => {
        const pushbullet = {};
        pushbullet.api = $('#pushbullet_api').val();

        if (msg) {
            $('#testPushbullet-result').html(MEDUSA.config.loading);
        }

        if (!pushbullet.api) {
            $('#testPushbullet-result').html('You didn\'t supply a Pushbullet api key');
            $('#pushbullet_api').focus();
            return false;
        }

        $.get('home/getPushbulletDevices', {
            api: pushbullet.api
        }, data => {
            pushbullet.devices = $.parseJSON(data).devices;
            pushbullet.currentDevice = $('#pushbullet_device').val();
            $('#pushbullet_device_list').html('');
            for (let i = 0, len = pushbullet.devices.length; i < len; i++) {
                if (pushbullet.devices[i].active === true) {
                    if (pushbullet.currentDevice === pushbullet.devices[i].iden) {
                        $('#pushbullet_device_list').append('<option value="' + pushbullet.devices[i].iden + '" selected>' + pushbullet.devices[i].nickname + '</option>');
                    } else {
                        $('#pushbullet_device_list').append('<option value="' + pushbullet.devices[i].iden + '">' + pushbullet.devices[i].nickname + '</option>');
                    }
                }
            }
            $('#pushbullet_device_list').prepend('<option value="" ' + (pushbullet.currentDevice === '' ? 'selected' : '') + '>All devices</option>');
            if (msg) {
                $('#testPushbullet-result').html(msg);
            }
        });

        $('#pushbullet_device_list').on('change', () => {
            $('#pushbullet_device').val($('#pushbullet_device_list').val());
            $('#testPushbullet-result').html(`Don't forget to save your new pushbullet settings.`);
        });
    };

    $('#getPushbulletDevices').on('click', () => {
        getPushbulletDevices('Device list updated. Please choose a device to push to.');
    });

    // We have to call this function on dom ready to create the devices select
    getPushbulletDevices();

    $('#email_show').on('change', () => {
        const key = parseInt($('#email_show').val(), 10);
        $.getJSON('home/loadShowNotifyLists', data => {
            if (data._size > 0) {
                $('#email_show_list').val(key >= 0 ? data[key.toString()].list : '');
            }
        });
    });
    $('#prowl_show').on('change', () => {
        const key = parseInt($('#prowl_show').val(), 10);
        $.getJSON('home/loadShowNotifyLists', data => {
            if (data._size > 0) {
                $('#prowl_show_list').val(key >= 0 ? data[key.toString()].prowl_notify_list : '');
            }
        });
    });

    const loadShowNotifyLists = () => {
        $.getJSON('home/loadShowNotifyLists', list => {
            let html;
            let s;
            if (list._size === 0) {
                return;
            }

            // Convert the 'list' object to a js array of objects so that we can sort it
            const _list = [];
            for (s in list) {
                if (s.charAt(0) !== '_') {
                    _list.push(list[s]);
                }
            }
            const sortedList = _list.sort((a, b) => {
                if (a.name < b.name) {
                    return -1;
                }
                if (a.name > b.name) {
                    return 1;
                }
                return 0;
            });
            html = '<option value="-1">-- Select --</option>';
            for (s in sortedList) {
                if (sortedList[s].id && sortedList[s].name) {
                    html += '<option value="' + sortedList[s].id + '">' + $('<div/>').text(sortedList[s].name).html() + '</option>';
                }
            }
            $('#email_show').html(html);
            $('#email_show_list').val('');

            $('#prowl_show').html(html);
            $('#prowl_show_list').val('');
        });
    };
    // Load the per show notify lists everytime this page is loaded
    loadShowNotifyLists();

    // Update the internal data struct anytime settings are saved to the server
    $('#email_show').on('notify', loadShowNotifyLists);
    $('#prowl_show').on('notify', loadShowNotifyLists);

    $('#email_show_save').on('click', () => {
        $.post('home/saveShowNotifyList', {
            show: $('#email_show').val(),
            emails: $('#email_show_list').val()
        }, loadShowNotifyLists);
    });
    $('#prowl_show_save').on('click', () => {
        $.post('home/saveShowNotifyList', {
            show: $('#prowl_show').val(),
            prowlAPIs: $('#prowl_show_list').val()
        }, () => {
            // Reload the per show notify lists to reflect changes
            loadShowNotifyLists();
        });
    });

    // Show instructions for plex when enabled
    $('#use_plex_server').on('click', function () {
        if ($(this).is(':checked')) {
            $('.plexinfo').removeClass('hide');
        } else {
            $('.plexinfo').addClass('hide');
        }
    });
};

},{"../core":30}],30:[function(require,module,exports){
const api = require('./api');

// eslint-disable-line max-lines
// @TODO Move these into common.ini when possible,
//       currently we can't do that as browser.js and a few others need it before this is loaded
const topImageHtml = '<img src="images/top.gif" width="31" height="11" alt="Jump to top" />'; // eslint-disable-line no-unused-vars
const apiRoot = $('body').attr('api-root');
const apiKey = $('body').attr('api-key');

const MEDUSA = {
    common: {},
    config: {},
    home: {},
    manage: {},
    history: {},
    errorlogs: {},
    schedule: {},
    addShows: {}
};

const UTIL = {
    exec(controller, action) {
        const ns = MEDUSA;
        action = action === undefined ? 'init' : action;

        if (controller !== '' && ns[controller] && typeof ns[controller][action] === 'function') {
            ns[controller][action]();
        }
    },
    init() {
        if (typeof startVue === 'function') {
            // eslint-disable-line no-undef
            startVue(); // eslint-disable-line no-undef
        } else {
            $('[v-cloak]').removeAttr('v-cloak');
        }

        const body = document.body;
        $('[asset]').each(function () {
            const asset = $(this).attr('asset');
            const series = $(this).attr('series');
            const path = apiRoot + 'series/' + series + '/asset/' + asset + '?api_key=' + apiKey;
            if (this.tagName.toLowerCase() === 'img') {
                if ($(this).attr('lazy') === 'on') {
                    $(this).attr('data-original', path);
                } else {
                    $(this).attr('src', path);
                }
            }
            if (this.tagName.toLowerCase() === 'a') {
                $(this).attr('href', path);
            }
        });
        const controller = body.getAttribute('data-controller');
        const action = body.getAttribute('data-action');

        UTIL.exec('common');
        UTIL.exec(controller);
        UTIL.exec(controller, action);
    }
};

$.extend({
    isMeta(pyVar, result) {
        const reg = new RegExp(result.length > 1 ? result.join('|') : result);

        if (typeof pyVar === 'object' && Object.keys(pyVar).length === 1) {
            return reg.test(MEDUSA.config[Object.keys(pyVar)[0]][pyVar[Object.keys(pyVar)[0]]]);
        }
        if (pyVar.match('medusa')) {
            pyVar.split('.')[1].toLowerCase().replace(/(_\w)/g, m => m[1].toUpperCase());
        }
        return reg.test(MEDUSA.config[pyVar]);
    }
});

$.fn.extend({
    addRemoveWarningClass(_) {
        if (_) {
            return $(this).removeClass('warning');
        }
        return $(this).addClass('warning');
    }
});

const triggerConfigLoaded = function () {
    // Create the event.
    const event = new CustomEvent('build', { detail: 'medusa config loaded' });
    event.initEvent('build', true, true);
    // Trigger the event.
    document.dispatchEvent(event);
};

if (!document.location.pathname.endsWith('/login/')) {
    api.get('config/main').then(response => {
        log.setDefaultLevel('trace');
        $.extend(MEDUSA.config, response.data);
        MEDUSA.config.themeSpinner = MEDUSA.config.themeName === 'dark' ? '-dark' : '';
        MEDUSA.config.loading = '<img src="images/loading16' + MEDUSA.config.themeSpinner + '.gif" height="16" width="16" />';

        if (navigator.userAgent.indexOf('PhantomJS') === -1) {
            $(document).ready(UTIL.init);
        }
        triggerConfigLoaded();
    }).catch(err => {
        log.error(err);
        alert('Unable to connect to Medusa!'); // eslint-disable-line no-alert
    });
}

module.exports = MEDUSA;

},{"./api":28}]},{},[29]);

//# sourceMappingURL=notifications.js.map

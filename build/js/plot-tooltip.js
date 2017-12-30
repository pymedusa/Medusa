!function e(t,r,n){function o(s,a){if(!r[s]){if(!t[s]){var u="function"==typeof require&&require;if(!a&&u)return u(s,!0);if(i)return i(s,!0);var c=new Error("Cannot find module '"+s+"'");throw c.code="MODULE_NOT_FOUND",c}var f=r[s]={exports:{}};t[s][0].call(f.exports,function(e){var r=t[s][1][e];return o(r||e)},f,f.exports,e,t,r,n)}return r[s].exports}for(var i="function"==typeof require&&require,s=0;s<n.length;s++)o(n[s]);return o}({1:[function(e,t,r){t.exports=e("./lib/axios")},{"./lib/axios":3}],2:[function(e,t,r){(function(r){"use strict";var n=e("./../utils"),o=e("./../core/settle"),i=e("./../helpers/buildURL"),s=e("./../helpers/parseHeaders"),a=e("./../helpers/isURLSameOrigin"),u=e("../core/createError"),c="undefined"!=typeof window&&window.btoa&&window.btoa.bind(window)||e("./../helpers/btoa");t.exports=function(t){return new Promise(function(f,l){var p=t.data,d=t.headers;n.isFormData(p)&&delete d["Content-Type"];var h=new XMLHttpRequest,m="onreadystatechange",y=!1;if("test"===r.env.NODE_ENV||"undefined"==typeof window||!window.XDomainRequest||"withCredentials"in h||a(t.url)||(h=new window.XDomainRequest,m="onload",y=!0,h.onprogress=function(){},h.ontimeout=function(){}),t.auth){var g=t.auth.username||"",v=t.auth.password||"";d.Authorization="Basic "+c(g+":"+v)}if(h.open(t.method.toUpperCase(),i(t.url,t.params,t.paramsSerializer),!0),h.timeout=t.timeout,h[m]=function(){if(h&&(4===h.readyState||y)&&(0!==h.status||h.responseURL&&0===h.responseURL.indexOf("file:"))){var e="getAllResponseHeaders"in h?s(h.getAllResponseHeaders()):null,r={data:t.responseType&&"text"!==t.responseType?h.response:h.responseText,status:1223===h.status?204:h.status,statusText:1223===h.status?"No Content":h.statusText,headers:e,config:t,request:h};o(f,l,r),h=null}},h.onerror=function(){l(u("Network Error",t,null,h)),h=null},h.ontimeout=function(){l(u("timeout of "+t.timeout+"ms exceeded",t,"ECONNABORTED",h)),h=null},n.isStandardBrowserEnv()){var w=e("./../helpers/cookies"),x=(t.withCredentials||a(t.url))&&t.xsrfCookieName?w.read(t.xsrfCookieName):void 0;x&&(d[t.xsrfHeaderName]=x)}if("setRequestHeader"in h&&n.forEach(d,function(e,t){void 0===p&&"content-type"===t.toLowerCase()?delete d[t]:h.setRequestHeader(t,e)}),t.withCredentials&&(h.withCredentials=!0),t.responseType)try{h.responseType=t.responseType}catch(e){if("json"!==t.responseType)throw e}"function"==typeof t.onDownloadProgress&&h.addEventListener("progress",t.onDownloadProgress),"function"==typeof t.onUploadProgress&&h.upload&&h.upload.addEventListener("progress",t.onUploadProgress),t.cancelToken&&t.cancelToken.promise.then(function(e){h&&(h.abort(),l(e),h=null)}),void 0===p&&(p=null),h.send(p)})}}).call(this,e("_process"))},{"../core/createError":9,"./../core/settle":12,"./../helpers/btoa":16,"./../helpers/buildURL":17,"./../helpers/cookies":19,"./../helpers/isURLSameOrigin":21,"./../helpers/parseHeaders":23,"./../utils":25,_process:27}],3:[function(e,t,r){"use strict";var n=e("./utils"),o=e("./helpers/bind"),i=e("./core/Axios"),s=e("./defaults");function a(e){var t=new i(e),r=o(i.prototype.request,t);return n.extend(r,i.prototype,t),n.extend(r,t),r}var u=a(s);u.Axios=i,u.create=function(e){return a(n.merge(s,e))},u.Cancel=e("./cancel/Cancel"),u.CancelToken=e("./cancel/CancelToken"),u.isCancel=e("./cancel/isCancel"),u.all=function(e){return Promise.all(e)},u.spread=e("./helpers/spread"),t.exports=u,t.exports.default=u},{"./cancel/Cancel":4,"./cancel/CancelToken":5,"./cancel/isCancel":6,"./core/Axios":7,"./defaults":14,"./helpers/bind":15,"./helpers/spread":24,"./utils":25}],4:[function(e,t,r){"use strict";function n(e){this.message=e}n.prototype.toString=function(){return"Cancel"+(this.message?": "+this.message:"")},n.prototype.__CANCEL__=!0,t.exports=n},{}],5:[function(e,t,r){"use strict";var n=e("./Cancel");function o(e){if("function"!=typeof e)throw new TypeError("executor must be a function.");var t;this.promise=new Promise(function(e){t=e});var r=this;e(function(e){r.reason||(r.reason=new n(e),t(r.reason))})}o.prototype.throwIfRequested=function(){if(this.reason)throw this.reason},o.source=function(){var e;return{token:new o(function(t){e=t}),cancel:e}},t.exports=o},{"./Cancel":4}],6:[function(e,t,r){"use strict";t.exports=function(e){return!(!e||!e.__CANCEL__)}},{}],7:[function(e,t,r){"use strict";var n=e("./../defaults"),o=e("./../utils"),i=e("./InterceptorManager"),s=e("./dispatchRequest");function a(e){this.defaults=e,this.interceptors={request:new i,response:new i}}a.prototype.request=function(e){"string"==typeof e&&(e=o.merge({url:arguments[0]},arguments[1])),(e=o.merge(n,this.defaults,{method:"get"},e)).method=e.method.toLowerCase();var t=[s,void 0],r=Promise.resolve(e);for(this.interceptors.request.forEach(function(e){t.unshift(e.fulfilled,e.rejected)}),this.interceptors.response.forEach(function(e){t.push(e.fulfilled,e.rejected)});t.length;)r=r.then(t.shift(),t.shift());return r},o.forEach(["delete","get","head","options"],function(e){a.prototype[e]=function(t,r){return this.request(o.merge(r||{},{method:e,url:t}))}}),o.forEach(["post","put","patch"],function(e){a.prototype[e]=function(t,r,n){return this.request(o.merge(n||{},{method:e,url:t,data:r}))}}),t.exports=a},{"./../defaults":14,"./../utils":25,"./InterceptorManager":8,"./dispatchRequest":10}],8:[function(e,t,r){"use strict";var n=e("./../utils");function o(){this.handlers=[]}o.prototype.use=function(e,t){return this.handlers.push({fulfilled:e,rejected:t}),this.handlers.length-1},o.prototype.eject=function(e){this.handlers[e]&&(this.handlers[e]=null)},o.prototype.forEach=function(e){n.forEach(this.handlers,function(t){null!==t&&e(t)})},t.exports=o},{"./../utils":25}],9:[function(e,t,r){"use strict";var n=e("./enhanceError");t.exports=function(e,t,r,o,i){var s=new Error(e);return n(s,t,r,o,i)}},{"./enhanceError":11}],10:[function(e,t,r){"use strict";var n=e("./../utils"),o=e("./transformData"),i=e("../cancel/isCancel"),s=e("../defaults"),a=e("./../helpers/isAbsoluteURL"),u=e("./../helpers/combineURLs");function c(e){e.cancelToken&&e.cancelToken.throwIfRequested()}t.exports=function(e){c(e),e.baseURL&&!a(e.url)&&(e.url=u(e.baseURL,e.url)),e.headers=e.headers||{},e.data=o(e.data,e.headers,e.transformRequest),e.headers=n.merge(e.headers.common||{},e.headers[e.method]||{},e.headers||{}),n.forEach(["delete","get","head","post","put","patch","common"],function(t){delete e.headers[t]});return(e.adapter||s.adapter)(e).then(function(t){return c(e),t.data=o(t.data,t.headers,e.transformResponse),t},function(t){return i(t)||(c(e),t&&t.response&&(t.response.data=o(t.response.data,t.response.headers,e.transformResponse))),Promise.reject(t)})}},{"../cancel/isCancel":6,"../defaults":14,"./../helpers/combineURLs":18,"./../helpers/isAbsoluteURL":20,"./../utils":25,"./transformData":13}],11:[function(e,t,r){"use strict";t.exports=function(e,t,r,n,o){return e.config=t,r&&(e.code=r),e.request=n,e.response=o,e}},{}],12:[function(e,t,r){"use strict";var n=e("./createError");t.exports=function(e,t,r){var o=r.config.validateStatus;r.status&&o&&!o(r.status)?t(n("Request failed with status code "+r.status,r.config,null,r.request,r)):e(r)}},{"./createError":9}],13:[function(e,t,r){"use strict";var n=e("./../utils");t.exports=function(e,t,r){return n.forEach(r,function(r){e=r(e,t)}),e}},{"./../utils":25}],14:[function(e,t,r){(function(r){"use strict";var n=e("./utils"),o=e("./helpers/normalizeHeaderName"),i={"Content-Type":"application/x-www-form-urlencoded"};function s(e,t){!n.isUndefined(e)&&n.isUndefined(e["Content-Type"])&&(e["Content-Type"]=t)}var a={adapter:function(){var t;return"undefined"!=typeof XMLHttpRequest?t=e("./adapters/xhr"):void 0!==r&&(t=e("./adapters/http")),t}(),transformRequest:[function(e,t){return o(t,"Content-Type"),n.isFormData(e)||n.isArrayBuffer(e)||n.isBuffer(e)||n.isStream(e)||n.isFile(e)||n.isBlob(e)?e:n.isArrayBufferView(e)?e.buffer:n.isURLSearchParams(e)?(s(t,"application/x-www-form-urlencoded;charset=utf-8"),e.toString()):n.isObject(e)?(s(t,"application/json;charset=utf-8"),JSON.stringify(e)):e}],transformResponse:[function(e){if("string"==typeof e)try{e=JSON.parse(e)}catch(e){}return e}],timeout:0,xsrfCookieName:"XSRF-TOKEN",xsrfHeaderName:"X-XSRF-TOKEN",maxContentLength:-1,validateStatus:function(e){return e>=200&&e<300}};a.headers={common:{Accept:"application/json, text/plain, */*"}},n.forEach(["delete","get","head"],function(e){a.headers[e]={}}),n.forEach(["post","put","patch"],function(e){a.headers[e]=n.merge(i)}),t.exports=a}).call(this,e("_process"))},{"./adapters/http":2,"./adapters/xhr":2,"./helpers/normalizeHeaderName":22,"./utils":25,_process:27}],15:[function(e,t,r){"use strict";t.exports=function(e,t){return function(){for(var r=new Array(arguments.length),n=0;n<r.length;n++)r[n]=arguments[n];return e.apply(t,r)}}},{}],16:[function(e,t,r){"use strict";var n="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=";function o(){this.message="String contains an invalid character"}(o.prototype=new Error).code=5,o.prototype.name="InvalidCharacterError";t.exports=function(e){for(var t,r,i=String(e),s="",a=0,u=n;i.charAt(0|a)||(u="=",a%1);s+=u.charAt(63&t>>8-a%1*8)){if((r=i.charCodeAt(a+=.75))>255)throw new o;t=t<<8|r}return s}},{}],17:[function(e,t,r){"use strict";var n=e("./../utils");function o(e){return encodeURIComponent(e).replace(/%40/gi,"@").replace(/%3A/gi,":").replace(/%24/g,"$").replace(/%2C/gi,",").replace(/%20/g,"+").replace(/%5B/gi,"[").replace(/%5D/gi,"]")}t.exports=function(e,t,r){if(!t)return e;var i;if(r)i=r(t);else if(n.isURLSearchParams(t))i=t.toString();else{var s=[];n.forEach(t,function(e,t){null!==e&&void 0!==e&&(n.isArray(e)&&(t+="[]"),n.isArray(e)||(e=[e]),n.forEach(e,function(e){n.isDate(e)?e=e.toISOString():n.isObject(e)&&(e=JSON.stringify(e)),s.push(o(t)+"="+o(e))}))}),i=s.join("&")}return i&&(e+=(-1===e.indexOf("?")?"?":"&")+i),e}},{"./../utils":25}],18:[function(e,t,r){"use strict";t.exports=function(e,t){return t?e.replace(/\/+$/,"")+"/"+t.replace(/^\/+/,""):e}},{}],19:[function(e,t,r){"use strict";var n=e("./../utils");t.exports=n.isStandardBrowserEnv()?{write:function(e,t,r,o,i,s){var a=[];a.push(e+"="+encodeURIComponent(t)),n.isNumber(r)&&a.push("expires="+new Date(r).toGMTString()),n.isString(o)&&a.push("path="+o),n.isString(i)&&a.push("domain="+i),!0===s&&a.push("secure"),document.cookie=a.join("; ")},read:function(e){var t=document.cookie.match(new RegExp("(^|;\\s*)("+e+")=([^;]*)"));return t?decodeURIComponent(t[3]):null},remove:function(e){this.write(e,"",Date.now()-864e5)}}:{write:function(){},read:function(){return null},remove:function(){}}},{"./../utils":25}],20:[function(e,t,r){"use strict";t.exports=function(e){return/^([a-z][a-z\d\+\-\.]*:)?\/\//i.test(e)}},{}],21:[function(e,t,r){"use strict";var n=e("./../utils");t.exports=n.isStandardBrowserEnv()?function(){var e,t=/(msie|trident)/i.test(navigator.userAgent),r=document.createElement("a");function o(e){var n=e;return t&&(r.setAttribute("href",n),n=r.href),r.setAttribute("href",n),{href:r.href,protocol:r.protocol?r.protocol.replace(/:$/,""):"",host:r.host,search:r.search?r.search.replace(/^\?/,""):"",hash:r.hash?r.hash.replace(/^#/,""):"",hostname:r.hostname,port:r.port,pathname:"/"===r.pathname.charAt(0)?r.pathname:"/"+r.pathname}}return e=o(window.location.href),function(t){var r=n.isString(t)?o(t):t;return r.protocol===e.protocol&&r.host===e.host}}():function(){return!0}},{"./../utils":25}],22:[function(e,t,r){"use strict";var n=e("../utils");t.exports=function(e,t){n.forEach(e,function(r,n){n!==t&&n.toUpperCase()===t.toUpperCase()&&(e[t]=r,delete e[n])})}},{"../utils":25}],23:[function(e,t,r){"use strict";var n=e("./../utils"),o=["age","authorization","content-length","content-type","etag","expires","from","host","if-modified-since","if-unmodified-since","last-modified","location","max-forwards","proxy-authorization","referer","retry-after","user-agent"];t.exports=function(e){var t,r,i,s={};return e?(n.forEach(e.split("\n"),function(e){if(i=e.indexOf(":"),t=n.trim(e.substr(0,i)).toLowerCase(),r=n.trim(e.substr(i+1)),t){if(s[t]&&o.indexOf(t)>=0)return;s[t]="set-cookie"===t?(s[t]?s[t]:[]).concat([r]):s[t]?s[t]+", "+r:r}}),s):s}},{"./../utils":25}],24:[function(e,t,r){"use strict";t.exports=function(e){return function(t){return e.apply(null,t)}}},{}],25:[function(e,t,r){"use strict";var n=e("./helpers/bind"),o=e("is-buffer"),i=Object.prototype.toString;function s(e){return"[object Array]"===i.call(e)}function a(e){return null!==e&&"object"==typeof e}function u(e){return"[object Function]"===i.call(e)}function c(e,t){if(null!==e&&void 0!==e)if("object"!=typeof e&&(e=[e]),s(e))for(var r=0,n=e.length;r<n;r++)t.call(null,e[r],r,e);else for(var o in e)Object.prototype.hasOwnProperty.call(e,o)&&t.call(null,e[o],o,e)}function f(){var e={};function t(t,r){"object"==typeof e[r]&&"object"==typeof t?e[r]=f(e[r],t):e[r]=t}for(var r=0,n=arguments.length;r<n;r++)c(arguments[r],t);return e}t.exports={isArray:s,isArrayBuffer:function(e){return"[object ArrayBuffer]"===i.call(e)},isBuffer:o,isFormData:function(e){return"undefined"!=typeof FormData&&e instanceof FormData},isArrayBufferView:function(e){return"undefined"!=typeof ArrayBuffer&&ArrayBuffer.isView?ArrayBuffer.isView(e):e&&e.buffer&&e.buffer instanceof ArrayBuffer},isString:function(e){return"string"==typeof e},isNumber:function(e){return"number"==typeof e},isObject:a,isUndefined:function(e){return void 0===e},isDate:function(e){return"[object Date]"===i.call(e)},isFile:function(e){return"[object File]"===i.call(e)},isBlob:function(e){return"[object Blob]"===i.call(e)},isFunction:u,isStream:function(e){return a(e)&&u(e.pipe)},isURLSearchParams:function(e){return"undefined"!=typeof URLSearchParams&&e instanceof URLSearchParams},isStandardBrowserEnv:function(){return("undefined"==typeof navigator||"ReactNative"!==navigator.product)&&"undefined"!=typeof window&&"undefined"!=typeof document},forEach:c,merge:f,extend:function(e,t,r){return c(t,function(t,o){e[o]=r&&"function"==typeof t?n(t,r):t}),e},trim:function(e){return e.replace(/^\s*/,"").replace(/\s*$/,"")}}},{"./helpers/bind":15,"is-buffer":26}],26:[function(e,t,r){t.exports=function(e){return null!=e&&(n(e)||(t=e,"function"==typeof t.readFloatLE&&"function"==typeof t.slice&&n(t.slice(0,0)))||!!e._isBuffer);var t};function n(e){return!!e.constructor&&"function"==typeof e.constructor.isBuffer&&e.constructor.isBuffer(e)}},{}],27:[function(e,t,r){var n,o,i=t.exports={};function s(){throw new Error("setTimeout has not been defined")}function a(){throw new Error("clearTimeout has not been defined")}!function(){try{n="function"==typeof setTimeout?setTimeout:s}catch(e){n=s}try{o="function"==typeof clearTimeout?clearTimeout:a}catch(e){o=a}}();function u(e){if(n===setTimeout)return setTimeout(e,0);if((n===s||!n)&&setTimeout)return n=setTimeout,setTimeout(e,0);try{return n(e,0)}catch(t){try{return n.call(null,e,0)}catch(t){return n.call(this,e,0)}}}var c,f=[],l=!1,p=-1;function d(){l&&c&&(l=!1,c.length?f=c.concat(f):p=-1,f.length&&h())}function h(){if(!l){var e=u(d);l=!0;for(var t=f.length;t;){for(c=f,f=[];++p<t;)c&&c[p].run();p=-1,t=f.length}c=null,l=!1,function(e){if(o===clearTimeout)return clearTimeout(e);if((o===a||!o)&&clearTimeout)return o=clearTimeout,clearTimeout(e);try{o(e)}catch(t){try{return o.call(null,e)}catch(t){return o.call(this,e)}}}(e)}}i.nextTick=function(e){var t=new Array(arguments.length-1);if(arguments.length>1)for(var r=1;r<arguments.length;r++)t[r-1]=arguments[r];f.push(new m(e,t)),1!==f.length||l||u(h)};function m(e,t){this.fun=e,this.array=t}m.prototype.run=function(){this.fun.apply(null,this.array)},i.title="browser",i.browser=!0,i.env={},i.argv=[],i.version="",i.versions={};function y(){}i.on=y,i.addListener=y,i.once=y,i.off=y,i.removeListener=y,i.removeAllListeners=y,i.emit=y,i.prependListener=y,i.prependOnceListener=y,i.listeners=function(e){return[]},i.binding=function(e){throw new Error("process.binding is not supported")},i.cwd=function(){return"/"},i.chdir=function(e){throw new Error("process.chdir is not supported")},i.umask=function(){return 0}},{}],28:[function(e,t,r){const n=e("axios"),o=$("body").attr("api-root"),i=$("body").attr("api-key"),s=n.create({baseURL:o,timeout:1e4,headers:{Accept:"application/json","Content-Type":"application/json","X-Api-Key":i}});t.exports=s},{axios:1}],29:[function(e,t,r){const n=e("./api");$(()=>{$(".plotInfo").each(function(){const e=$(this).attr("id").match(/^plot_info_([\da-z]+)_(\d+)_(\d+)$/);$(this).qtip({content:{text:(t,r)=>(n.get("series/"+e[1]+"/episode/s"+e[2]+"e"+e[3]+"/description").then(e=>{r.set("content.text",e.data)},e=>{r.set("content.text","Error while loading plot: "+e.status+": "+e.statusText)}),"Loading...")},show:{solo:!0},position:{my:"left center",adjust:{y:-10,x:2}},style:{tip:{corner:!0,method:"polygon"},classes:"qtip-rounded qtip-shadow ui-tooltip-sb"}})})})},{"./api":28}]},{},[29]);
//# sourceMappingURL=plot-tooltip.js.map

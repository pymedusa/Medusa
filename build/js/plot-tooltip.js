(function e(t,n,r){function s(o,u){if(!n[o]){if(!t[o]){var a=typeof require=="function"&&require;if(!u&&a)return a(o,!0);if(i)return i(o,!0);var f=new Error("Cannot find module '"+o+"'");throw f.code="MODULE_NOT_FOUND",f}var l=n[o]={exports:{}};t[o][0].call(l.exports,function(e){var n=t[o][1][e];return s(n?n:e)},l,l.exports,e,t,n,r)}return n[o].exports}var i=typeof require=="function"&&require;for(var o=0;o<r.length;o++)s(r[o]);return s})({1:[function(require,module,exports){
const baseUrl = $('body').attr('api-root');
const idToken = $('body').attr('api-key');

const api = axios.create({
    baseURL: baseUrl,
    timeout: 10000,
    headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-Api-Key': idToken
    }
});

module.exports = api;

},{}],2:[function(require,module,exports){
const api = require('./api');

$(() => {
    $('.plotInfo').each(function () {
        const match = $(this).attr('id').match(/^plot_info_([\da-z]+)_(\d+)_(\d+)$/);
        // http://localhost:8081/api/v2/series/tvdb83462/episode/s01e01/description?api_key=xxx
        $(this).qtip({
            content: {
                text(event, qt) {
                    api.get('series/' + match[1] + '/episode/s' + match[2] + 'e' + match[3] + '/description').then(response => {
                        // Set the tooltip content upon successful retrieval
                        qt.set('content.text', response.data);
                    }, xhr => {
                        // Upon failure... set the tooltip content to the status and error value
                        qt.set('content.text', 'Error while loading plot: ' + xhr.status + ': ' + xhr.statusText);
                    });
                    return 'Loading...';
                }
            },
            show: {
                solo: true
            },
            position: {
                my: 'left center',
                adjust: {
                    y: -10,
                    x: 2
                }
            },
            style: {
                tip: {
                    corner: true,
                    method: 'polygon'
                },
                classes: 'qtip-rounded qtip-shadow ui-tooltip-sb'
            }
        });
    });
});

},{"./api":1}]},{},[2]);

//# sourceMappingURL=plot-tooltip.js.map

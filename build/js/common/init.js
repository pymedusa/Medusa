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
const MEDUSA = require('../core');

const apiKey = $('body').attr('api-key');

MEDUSA.common.init = function () {
    // Import underscore.string using it's mixin export.
    _.mixin(s.exports());

    const backstretchOffset = () => {
        let offset = '90px';
        if ($('#sub-menu-container').length === 0) {
            offset = '50px';
        }
        if ($(window).width() < 1280) {
            offset = '50px';
        }
        return offset;
    };

    // Background Fanart Functions
    if (MEDUSA.config.fanartBackground) {
        const seriesId = $('#series-id').attr('value');
        if (seriesId) {
            const apiRoot = $('body').attr('api-root');
            const path = apiRoot + 'series/' + $('#series-slug').attr('value') + '/asset/fanart?api_key=' + apiKey;
            $.backstretch(path);
            $('.backstretch').css('top', backstretchOffset());
            $('.backstretch').css('opacity', MEDUSA.config.fanartBackgroundOpacity).fadeIn(500);
        }
    }

    /**
     * Make an attempt to detect if there are currently scroll bars visible for divs with the horizontal-scroll class.
     *
     * If scroll bars are visible the fixed left and right buttons become visible on that page.
     */
    const initHorizontalScroll = function () {
        const scrollDiv = $('div.horizontal-scroll').get();
        if (scrollDiv.length === 0) {
            return;
        }

        const scrollbarVisible = scrollDiv.map(el => {
            return el.scrollWidth > el.clientWidth;
        }).indexOf(true);

        if (scrollbarVisible >= 0) {
            $('.scroll-wrapper.left').addClass('show');
            $('.scroll-wrapper.right').addClass('show');
        } else {
            $('.scroll-wrapper.left').removeClass('show');
            $('.scroll-wrapper.right').removeClass('show');
        }
    };

    initHorizontalScroll();

    $(window).on('resize', () => {
        $('.backstretch').css('top', backstretchOffset());
        initHorizontalScroll();
    });

    // Scroll Functions
    function scrollTo(dest) {
        $('html, body').animate({ scrollTop: $(dest).offset().top }, 500, 'linear');
    }

    $('#scroll-left').on('click', e => {
        e.preventDefault();
        $('div.horizontal-scroll').animate({
            scrollLeft: '-=153'
        }, 1000, 'easeOutQuad');
    });

    $('#scroll-right').on('click', e => {
        e.preventDefault();
        $('div.horizontal-scroll').animate({
            scrollLeft: '+=153'
        }, 1000, 'easeOutQuad');
    });

    $(document).on('scroll', () => {
        if ($(window).scrollTop() > 100) {
            $('.scroll-wrapper.top').addClass('show');
        } else {
            $('.scroll-wrapper.top').removeClass('show');
        }
    });

    $('.scroll-wrapper.top').on('click', () => {
        scrollTo($('body'));
    });

    // Scroll to Anchor
    $('a[href^="#season"]').on('click', e => {
        e.preventDefault();
        scrollTo($('a[name="' + $(this).attr('href').replace('#', '') + '"]'));
    });

    // Hover Dropdown for Nav
    $('ul.nav li.dropdown').hover(function () {
        $(this).find('.dropdown-menu').stop(true, true).delay(200).fadeIn(500);
    }, function () {
        $(this).find('.dropdown-menu').stop(true, true).delay(200).fadeOut(500);
    });

    // Function to change luminance of #000000 color - used in triggerhighlighting
    const colorLuminance = (hex, lum) => {
        hex = String(hex).replace(/[^0-9a-f]/gi, '');
        if (hex.length < 6) {
            hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2];
        }
        lum = lum || 0;
        let rgb = '#';
        let c;
        let i;
        for (i = 0; i < 3; i++) {
            c = parseInt(hex.substr(i * 2, 2), 16);
            c = Math.round(Math.min(Math.max(0, c + c * lum), 255)).toString(16);
            rgb += ('00' + c).substr(c.length);
        }
        return rgb;
    };

    // Function to convert rgb(0,0,0) into #000000
    const rgb2hex = rgb => {
        rgb = rgb.match(/^rgb\((\d+),\s*(\d+),\s*(\d+)\)$/);
        function hex(x) {
            return ('0' + parseInt(x, 10).toString(16)).slice(-2);
        }
        return '#' + hex(rgb[1]) + hex(rgb[2]) + hex(rgb[3]);
    };

    let revertBackgroundColor; // Used to revert back to original background-color after highlight
    $('.triggerhighlight').on('mouseover', event => {
        // Fetch the original background-color to revert back to
        revertBackgroundColor = rgb2hex($(event.currentTarget).parent().css('background-color'));
        // Setting highlight background-color
        $(this).parent().find('.triggerhighlight').css('background-color', colorLuminance(revertBackgroundColor, -0.15));
    }).on('mouseout', () => {
        // Reverting back to original background-color
        $(this).parent().find('.triggerhighlight').css('background-color', revertBackgroundColor);
    });

    $.rootDirCheck = function () {
        if ($('#rootDirs option:selected').length === 0) {
            $('button[data-add-show]').prop('disabled', true);
            if (!$('#configure_show_options').is(':checked')) {
                $('#configure_show_options').prop('checked', true);
                $('#content_configure_show_options').fadeIn('fast', 'linear');
            }
            if ($('#rootDirAlert').length === 0) {
                $('#content-row').before('<div id="rootDirAlert"><div class="text-center">' + '<div class="alert alert-danger upgrade-notification hidden-print role="alert">' + '<strong>ERROR!</strong> Unable to add recommended shows.  Please set a default directory first.' + '</div></div></div>');
            } else {
                $('#rootDirAlert').show();
            }
        } else {
            $('#rootDirAlert').hide();
            $('button[data-add-show]').prop('disabled', false);
        }
    };

    $.confirm.options = {
        confirmButton: 'Yes',
        cancelButton: 'Cancel',
        dialogClass: 'modal-dialog',
        post: false,
        confirm(e) {
            location.href = e[0].href;
        }
    };

    $('a.shutdown').confirm({
        title: 'Shutdown',
        text: 'Are you sure you want to shutdown Medusa?'
    });

    $('a.restart').confirm({
        title: 'Restart',
        text: 'Are you sure you want to restart Medusa?'
    });

    $('a.removeshow').confirm({
        title: 'Remove Show',
        text: 'Are you sure you want to remove <span class="footerhighlight">' + $('#showtitle').data('showname') + '</span> from the database?<br><br><input type="checkbox" id="deleteFiles"> <span class="red-text">Check to delete files as well. IRREVERSIBLE</span></input>',
        confirm(e) {
            location.href = e[0].href + (document.getElementById('deleteFiles').checked ? '&full=1' : '');
        }
    });

    $('a.clearhistory').confirm({
        title: 'Clear History',
        text: 'Are you sure you want to clear all download history?'
    });

    $('a.trimhistory').confirm({
        title: 'Trim History',
        text: 'Are you sure you want to trim all download history older than 30 days?'
    });

    $('a.submiterrors').confirm({
        title: 'Submit Errors',
        text: 'Are you sure you want to submit these errors ?<br><br><span class="red-text">Make sure Medusa is updated and trigger<br> this error with debug enabled before submitting</span>'
    });

    $('#config-components').tabs({
        activate: (event, ui) => {
            let lastOpenedPanel = $(this).data('lastOpenedPanel');

            if (!lastOpenedPanel) {
                lastOpenedPanel = $(ui.oldPanel);
            }

            if (!$(this).data('topPositionTab')) {
                $(this).data('topPositionTab', $(ui.newPanel).position().top);
            }

            // Dont use the builtin fx effects. This will fade in/out both tabs, we dont want that
            // Fadein the new tab yourself
            $(ui.newPanel).hide().fadeIn(0);

            if (lastOpenedPanel) {
                // 1. Show the previous opened tab by removing the jQuery UI class
                // 2. Make the tab temporary position:absolute so the two tabs will overlap
                // 3. Set topposition so they will overlap if you go from tab 1 to tab 0
                // 4. Remove position:absolute after animation
                lastOpenedPanel.toggleClass('ui-tabs-hide').css('position', 'absolute').css('top', $(this).data('topPositionTab') + 'px').fadeOut(0, function () {
                    $(this).css('position', '');
                });
            }

            // Saving the last tab has been opened
            $(this).data('lastOpenedPanel', $(ui.newPanel));
        }
    });

    // @TODO Replace this with a real touchscreen check
    // hack alert: if we don't have a touchscreen, and we are already hovering the mouse, then click should link instead of toggle
    if ((navigator.maxTouchPoints || 0) < 2) {
        $('.dropdown-toggle').on('click', function () {
            const $this = $(this);
            if ($this.attr('aria-expanded') === 'true') {
                window.location.href = $('base').attr('href') + $this.attr('href');
            }
        });
    }

    if (MEDUSA.config.fuzzyDating) {
        $.timeago.settings.allowFuture = true;
        $.timeago.settings.strings = {
            prefixAgo: null,
            prefixFromNow: 'In ',
            suffixAgo: 'ago',
            suffixFromNow: '',
            seconds: 'a few seconds',
            minute: 'a minute',
            minutes: '%d minutes',
            hour: 'an hour',
            hours: '%d hours',
            day: 'a day',
            days: '%d days',
            month: 'a month',
            months: '%d months',
            year: 'a year',
            years: '%d years',
            wordSeparator: ' ',
            numbers: []
        };
        $('[datetime]').timeago();
    }

    $(document.body).on('click', 'a[data-no-redirect]', function (e) {
        e.preventDefault();
        $.get($(this).attr('href'));
        return false;
    });

    $(document.body).on('click', '.bulkCheck', function () {
        const bulkCheck = this;
        const whichBulkCheck = $(bulkCheck).attr('id');

        $('.' + whichBulkCheck + ':visible').each(function () {
            $(this).prop('checked', $(bulkCheck).prop('checked'));
        });
    });

    $('.enabler').each(function () {
        if (!$(this).prop('checked')) {
            $('#content_' + $(this).attr('id')).hide();
        }
    });

    $('.enabler').on('click', function () {
        if ($(this).prop('checked')) {
            $('#content_' + $(this).attr('id')).fadeIn('fast', 'linear');
        } else {
            $('#content_' + $(this).attr('id')).fadeOut('fast', 'linear');
        }
    });

    $('.addQTip').each(function () {
        $(this).css({
            'cursor': 'help', // eslint-disable-line quote-props
            'text-shadow': '0px 0px 0.5px #666'
        });

        const my = $(this).data('qtip-my') || 'left center';
        const at = $(this).data('qtip-at') || 'middle right';

        $(this).qtip({
            show: {
                solo: true
            },
            position: {
                my,
                at
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
};

},{"../core":3}],3:[function(require,module,exports){
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

},{"./api":1}]},{},[2]);

//# sourceMappingURL=init.js.map

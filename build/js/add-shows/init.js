(function e(t,n,r){function s(o,u){if(!n[o]){if(!t[o]){var a=typeof require=="function"&&require;if(!u&&a)return a(o,!0);if(i)return i(o,!0);var f=new Error("Cannot find module '"+o+"'");throw f.code="MODULE_NOT_FOUND",f}var l=n[o]={exports:{}};t[o][0].call(l.exports,function(e){var n=t[o][1][e];return s(n?n:e)},l,l.exports,e,t,n,r)}return n[o].exports}var i=typeof require=="function"&&require;for(var o=0;o<r.length;o++)s(r[o]);return s})({1:[function(require,module,exports){
const MEDUSA = require('../core');
MEDUSA.addShows.init = function () {
    $('#tabs').tabs({
        collapsible: true,
        selected: MEDUSA.config.sortArticle ? -1 : 0
    });

    var imgLazyLoad = new LazyLoad({
        // example of options object -> see options section
        threshold: 500
    });

    $.initRemoteShowGrid = function () {
        // Set defaults on page load
        imgLazyLoad.update();
        imgLazyLoad.handleScroll();
        $('#showsort').val('original');
        $('#showsortdirection').val('asc');

        $('#showsort').on('change', function () {
            var sortCriteria;
            switch (this.value) {
                case 'original':
                    sortCriteria = 'original-order';
                    break;
                case 'rating':
                    /* randomise, else the rating_votes can already
                     * have sorted leaving this with nothing to do.
                     */
                    $('#container').isotope({ sortBy: 'random' });
                    sortCriteria = 'rating';
                    break;
                case 'rating_votes':
                    sortCriteria = ['rating', 'votes'];
                    break;
                case 'votes':
                    sortCriteria = 'votes';
                    break;
                default:
                    sortCriteria = 'name';
                    break;
            }
            $('#container').isotope({
                sortBy: sortCriteria
            });
        });

        $('#rootDirs').on('change', function () {
            $.rootDirCheck();
        });

        $('#showsortdirection').on('change', function () {
            $('#container').isotope({
                sortAscending: this.value === 'asc'
            });
        });

        $('#container').isotope({
            sortBy: 'original-order',
            layoutMode: 'fitRows',
            getSortData: {
                name: function (itemElem) {
                    var name = $(itemElem).attr('data-name') || '';
                    return (MEDUSA.config.sortArticle ? name : name.replace(/^((?:The|A|An)\s)/i, '')).toLowerCase();
                },
                rating: '[data-rating] parseInt',
                votes: '[data-votes] parseInt'
            }
        }).on('layoutComplete arrangeComplete removeComplete', function () {
            imgLazyLoad.update();
            imgLazyLoad.handleScroll();
        });
    };

    $.fn.loadRemoteShows = function (path, loadingTxt, errorTxt) {
        $(this).html('<img id="searchingAnim" src="images/loading32' + MEDUSA.config.themeSpinner + '.gif" height="32" width="32" />&nbsp;' + loadingTxt);
        $(this).load(path + ' #container', function (response, status) {
            if (status === 'error') {
                $(this).empty().html(errorTxt);
            } else {
                $.initRemoteShowGrid();
                imgLazyLoad.update();
                imgLazyLoad.handleScroll();
            }
        });
    };

    /*
     * Blacklist a show by indexer and indexer_id
     */
    $.initBlackListShowById = function () {
        $(document.body).on('click', 'button[data-blacklist-show]', function (e) {
            e.preventDefault();

            if ($(this).is(':disabled')) {
                return false;
            }

            $(this).html('Blacklisted').prop('disabled', true);
            $(this).parent().find('button[data-add-show]').prop('disabled', true);

            $.get('addShows/addShowToBlacklist?indexer_id=' + $(this).attr('data-indexer-id'));
            return false;
        });
    };

    /*
     * Adds show by indexer and indexer_id with a number of optional parameters
     * The show can be added as an anime show by providing the data attribute: data-isanime="1"
     */
    $.initAddShowById = function () {
        $(document.body).on('click', 'button[data-add-show]', function (e) {
            e.preventDefault();

            if ($(this).is(':disabled')) {
                return false;
            }

            $(this).html('Added').prop('disabled', true);
            $(this).parent().find('button[data-blacklist-show]').prop('disabled', true);

            var anyQualArray = [];
            var bestQualArray = [];
            $('#allowed_qualities option:selected').each(function (i, d) {
                anyQualArray.push($(d).val());
            });
            $('#preferred_qualities option:selected').each(function (i, d) {
                bestQualArray.push($(d).val());
            });

            // If we are going to add an anime, let's by default configure it as one
            var anime = $('#anime').prop('checked');
            var configureShowOptions = $('#configure_show_options').prop('checked');

            $.get('addShows/addShowByID?indexer_id=' + $(this).attr('data-indexer-id'), {
                root_dir: $('#rootDirs option:selected').val(), // eslint-disable-line camelcase
                configure_show_options: configureShowOptions, // eslint-disable-line camelcase
                indexer: $(this).attr('data-indexer'),
                show_name: $(this).attr('data-show-name'), // eslint-disable-line camelcase
                quality_preset: $('#qualityPreset').val(), // eslint-disable-line camelcase
                default_status: $('#statusSelect').val(), // eslint-disable-line camelcase
                any_qualities: anyQualArray.join(','), // eslint-disable-line camelcase
                best_qualities: bestQualArray.join(','), // eslint-disable-line camelcase
                default_flatten_folders: $('#flatten_folders').prop('checked'), // eslint-disable-line camelcase
                subtitles: $('#subtitles').prop('checked'),
                anime: anime,
                scene: $('#scene').prop('checked'),
                default_status_after: $('#statusSelectAfter').val() // eslint-disable-line camelcase
            });
            return false;
        });

        $('#saveDefaultsButton').on('click', function () {
            var anyQualArray = [];
            var bestQualArray = [];
            $('#allowed_qualities option:selected').each(function (i, d) {
                anyQualArray.push($(d).val());
            });
            $('#preferred_qualities option:selected').each(function (i, d) {
                bestQualArray.push($(d).val());
            });

            $.get('config/general/saveAddShowDefaults', {
                defaultStatus: $('#statusSelect').val(),
                allowed_qualities: anyQualArray.join(','), // eslint-disable-line camelcase
                preferred_qualities: bestQualArray.join(','), // eslint-disable-line camelcase
                defaultFlattenFolders: $('#flatten_folders').prop('checked'),
                subtitles: $('#subtitles').prop('checked'),
                anime: $('#anime').prop('checked'),
                scene: $('#scene').prop('checked'),
                defaultStatusAfter: $('#statusSelectAfter').val()
            });

            $(this).prop('disabled', true);
            new PNotify({ // eslint-disable-line no-new
                title: 'Saved Defaults',
                text: 'Your "add show" defaults have been set to your current selections.',
                shadow: false
            });
        });

        $('#statusSelect, #qualityPreset, #flatten_folders, #allowed_qualities, #preferred_qualities, #subtitles, #scene, #anime, #statusSelectAfter').on('change', function () {
            $('#saveDefaultsButton').prop('disabled', false);
        });

        $('#qualityPreset').on('change', function () {
            // fix issue #181 - force re-render to correct the height of the outer div
            $('span.prev').click();
            $('span.next').click();
        });
    };
    $.updateBlackWhiteList = function (showName) {
        $('#white').children().remove();
        $('#black').children().remove();
        $('#pool').children().remove();

        if ($('#anime').prop('checked') && showName) {
            $('#blackwhitelist').show();
            if (showName) {
                $.getJSON('home/fetch_releasegroups', {
                    show_name: showName // eslint-disable-line camelcase
                }, function (data) {
                    if (data.result === 'success') {
                        $.each(data.groups, function (i, group) {
                            var option = $('<option>');
                            option.prop('value', group.name);
                            option.html(group.name + ' | ' + group.rating + ' | ' + group.range);
                            option.appendTo('#pool');
                        });
                    }
                });
            }
        } else {
            $('#blackwhitelist').hide();
        }
    };
};

},{"../core":2}],2:[function(require,module,exports){
// eslint-disable-line max-lines
// @TODO Move these into common.ini when possible,
//       currently we can't do that as browser.js and a few others need it before this is loaded
var topImageHtml = '<img src="images/top.gif" width="31" height="11" alt="Jump to top" />'; // eslint-disable-line no-unused-vars
var apiRoot = $('body').attr('api-root');
var apiKey = $('body').attr('api-key');

var MEDUSA = {
    common: {},
    config: {},
    home: {},
    manage: {},
    history: {},
    errorlogs: {},
    schedule: {},
    addShows: {}
};

var UTIL = {
    exec: function (controller, action) {
        var ns = MEDUSA;
        action = action === undefined ? 'init' : action;

        if (controller !== '' && ns[controller] && typeof ns[controller][action] === 'function') {
            ns[controller][action]();
        }
    },
    init: function () {
        if (typeof startVue === 'function') {
            // eslint-disable-line no-undef
            startVue(); // eslint-disable-line no-undef
        } else {
            $('[v-cloak]').removeAttr('v-cloak');
        }

        var body = document.body;
        $('[asset]').each(function () {
            let asset = $(this).attr('asset');
            let series = $(this).attr('series');
            let path = apiRoot + 'series/' + series + '/asset/' + asset + '?api_key=' + apiKey;
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
        var controller = body.getAttribute('data-controller');
        var action = body.getAttribute('data-action');

        UTIL.exec('common');
        UTIL.exec(controller);
        UTIL.exec(controller, action);
    }
};

$.extend({
    isMeta: function (pyVar, result) {
        // eslint-disable-line no-unused-vars
        var reg = new RegExp(result.length > 1 ? result.join('|') : result);

        if (typeof pyVar === 'object' && Object.keys(pyVar).length === 1) {
            return reg.test(MEDUSA.config[Object.keys(pyVar)[0]][pyVar[Object.keys(pyVar)[0]]]);
        }
        if (pyVar.match('medusa')) {
            pyVar.split('.')[1].toLowerCase().replace(/(_\w)/g, function (m) {
                return m[1].toUpperCase();
            });
        }
        return reg.test(MEDUSA.config[pyVar]);
    }
});

$.fn.extend({
    addRemoveWarningClass: function (_) {
        if (_) {
            return $(this).removeClass('warning');
        }
        return $(this).addClass('warning');
    }
});

var triggerConfigLoaded = function () {
    // Create the event.
    var event = new CustomEvent('build', { detail: 'medusa config loaded' });
    event.initEvent('build', true, true);
    // Trigger the event.
    document.dispatchEvent(event);
};

if (!document.location.pathname.endsWith('/login/')) {
    api.get('config/main').then(function (response) {
        log.setDefaultLevel('trace');
        $.extend(MEDUSA.config, response.data);
        MEDUSA.config.themeSpinner = MEDUSA.config.themeName === 'dark' ? '-dark' : '';
        MEDUSA.config.loading = '<img src="images/loading16' + MEDUSA.config.themeSpinner + '.gif" height="16" width="16" />';

        if (navigator.userAgent.indexOf('PhantomJS') === -1) {
            $(document).ready(UTIL.init);
        }
        triggerConfigLoaded();
    }).catch(function (err) {
        log.error(err);
        alert('Unable to connect to Medusa!'); // eslint-disable-line no-alert
    });
}

module.exports = MEDUSA;

},{}]},{},[1]);

//# sourceMappingURL=init.js.map

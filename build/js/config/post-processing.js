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
MEDUSA.config.postProcessing = function () {
    // eslint-disable-line max-lines
    $('#config-components').tabs();
    $('#tv_download_dir').fileBrowser({
        title: 'Select TV Download Directory'
    });

    // http://stackoverflow.com/questions/2219924/idiomatic-jquery-delayed-event-only-after-a-short-pause-in-typing-e-g-timew
    var typewatch = function () {
        var timer = 0;
        return function (callback, ms) {
            clearTimeout(timer);
            timer = setTimeout(callback, ms);
        };
    }();

    function isRarSupported() {
        $.get('config/postProcessing/isRarSupported', function (data) {
            if (data !== 'supported') {
                $('#unpack').qtip('option', {
                    'content.text': 'Unrar Executable not found.',
                    'style.classes': 'qtip-rounded qtip-shadow qtip-red'
                });
                $('#unpack').qtip('toggle', true);
                $('#unpack').css('background-color', '#FFFFDD');
            }
        });
    }

    function fillExamples() {
        var example = {};

        example.pattern = $('#naming_pattern').val();
        example.multi = $('#naming_multi_ep :selected').val();
        example.animeType = $('input[name="naming_anime"]:checked').val();

        $.get('config/postProcessing/testNaming', {
            pattern: example.pattern,
            anime_type: 3 // eslint-disable-line camelcase
        }, function (data) {
            if (data) {
                $('#naming_example').text(data + '.ext');
                $('#naming_example_div').show();
            } else {
                $('#naming_example_div').hide();
            }
        });

        $.get('config/postProcessing/testNaming', {
            pattern: example.pattern,
            multi: example.multi,
            anime_type: 3 // eslint-disable-line camelcase
        }, function (data) {
            if (data) {
                $('#naming_example_multi').text(data + '.ext');
                $('#naming_example_multi_div').show();
            } else {
                $('#naming_example_multi_div').hide();
            }
        });

        $.get('config/postProcessing/isNamingValid', {
            pattern: example.pattern,
            multi: example.multi,
            anime_type: example.animeType // eslint-disable-line camelcase
        }, function (data) {
            if (data === 'invalid') {
                $('#naming_pattern').qtip('option', {
                    'content.text': 'This pattern is invalid.',
                    'style.classes': 'qtip-rounded qtip-shadow qtip-red'
                });
                $('#naming_pattern').qtip('toggle', true);
                $('#naming_pattern').css('background-color', '#FFDDDD');
            } else if (data === 'seasonfolders') {
                $('#naming_pattern').qtip('option', {
                    'content.text': 'This pattern would be invalid without the folders, using it will force "Flatten" off for all shows.',
                    'style.classes': 'qtip-rounded qtip-shadow qtip-red'
                });
                $('#naming_pattern').qtip('toggle', true);
                $('#naming_pattern').css('background-color', '#FFFFDD');
            } else {
                $('#naming_pattern').qtip('option', {
                    'content.text': 'This pattern is valid.',
                    'style.classes': 'qtip-rounded qtip-shadow qtip-green'
                });
                $('#naming_pattern').qtip('toggle', false);
                $('#naming_pattern').css('background-color', '#FFFFFF');
            }
        });
    }

    function fillAbdExamples() {
        var pattern = $('#naming_abd_pattern').val();

        $.get('config/postProcessing/testNaming', {
            pattern: pattern,
            abd: 'True'
        }, function (data) {
            if (data) {
                $('#naming_abd_example').text(data + '.ext');
                $('#naming_abd_example_div').show();
            } else {
                $('#naming_abd_example_div').hide();
            }
        });

        $.get('config/postProcessing/isNamingValid', {
            pattern: pattern,
            abd: 'True'
        }, function (data) {
            if (data === 'invalid') {
                $('#naming_abd_pattern').qtip('option', {
                    'content.text': 'This pattern is invalid.',
                    'style.classes': 'qtip-rounded qtip-shadow qtip-red'
                });
                $('#naming_abd_pattern').qtip('toggle', true);
                $('#naming_abd_pattern').css('background-color', '#FFDDDD');
            } else if (data === 'seasonfolders') {
                $('#naming_abd_pattern').qtip('option', {
                    'content.text': 'This pattern would be invalid without the folders, using it will force "Flatten" off for all shows.',
                    'style.classes': 'qtip-rounded qtip-shadow qtip-red'
                });
                $('#naming_abd_pattern').qtip('toggle', true);
                $('#naming_abd_pattern').css('background-color', '#FFFFDD');
            } else {
                $('#naming_abd_pattern').qtip('option', {
                    'content.text': 'This pattern is valid.',
                    'style.classes': 'qtip-rounded qtip-shadow qtip-green'
                });
                $('#naming_abd_pattern').qtip('toggle', false);
                $('#naming_abd_pattern').css('background-color', '#FFFFFF');
            }
        });
    }

    function fillSportsExamples() {
        var pattern = $('#naming_sports_pattern').val();

        $.get('config/postProcessing/testNaming', {
            pattern: pattern,
            sports: 'True' // @TODO does this actually need to be a string or can it be a boolean?
        }, function (data) {
            if (data) {
                $('#naming_sports_example').text(data + '.ext');
                $('#naming_sports_example_div').show();
            } else {
                $('#naming_sports_example_div').hide();
            }
        });

        $.get('config/postProcessing/isNamingValid', {
            pattern: pattern,
            sports: 'True' // @TODO does this actually need to be a string or can it be a boolean?
        }, function (data) {
            if (data === 'invalid') {
                $('#naming_sports_pattern').qtip('option', {
                    'content.text': 'This pattern is invalid.',
                    'style.classes': 'qtip-rounded qtip-shadow qtip-red'
                });
                $('#naming_sports_pattern').qtip('toggle', true);
                $('#naming_sports_pattern').css('background-color', '#FFDDDD');
            } else if (data === 'seasonfolders') {
                $('#naming_sports_pattern').qtip('option', {
                    'content.text': 'This pattern would be invalid without the folders, using it will force "Flatten" off for all shows.',
                    'style.classes': 'qtip-rounded qtip-shadow qtip-red'
                });
                $('#naming_sports_pattern').qtip('toggle', true);
                $('#naming_sports_pattern').css('background-color', '#FFFFDD');
            } else {
                $('#naming_sports_pattern').qtip('option', {
                    'content.text': 'This pattern is valid.',
                    'style.classes': 'qtip-rounded qtip-shadow qtip-green'
                });
                $('#naming_sports_pattern').qtip('toggle', false);
                $('#naming_sports_pattern').css('background-color', '#FFFFFF');
            }
        });
    }

    function fillAnimeExamples() {
        var example = {};
        example.pattern = $('#naming_anime_pattern').val();
        example.multi = $('#naming_anime_multi_ep :selected').val();
        example.animeType = $('input[name="naming_anime"]:checked').val();

        $.get('config/postProcessing/testNaming', {
            pattern: example.pattern,
            anime_type: example.animeType // eslint-disable-line camelcase
        }, function (data) {
            if (data) {
                $('#naming_example_anime').text(data + '.ext');
                $('#naming_example_anime_div').show();
            } else {
                $('#naming_example_anime_div').hide();
            }
        });

        $.get('config/postProcessing/testNaming', {
            pattern: example.pattern,
            multi: example.multi,
            anime_type: example.animeType // eslint-disable-line camelcase
        }, function (data) {
            if (data) {
                $('#naming_example_multi_anime').text(data + '.ext');
                $('#naming_example_multi_anime_div').show();
            } else {
                $('#naming_example_multi_anime_div').hide();
            }
        });

        $.get('config/postProcessing/isNamingValid', {
            pattern: example.pattern,
            multi: example.multi,
            anime_type: example.animeType // eslint-disable-line camelcase
        }, function (data) {
            if (data === 'invalid') {
                $('#naming_pattern').qtip('option', {
                    'content.text': 'This pattern is invalid.',
                    'style.classes': 'qtip-rounded qtip-shadow qtip-red'
                });
                $('#naming_pattern').qtip('toggle', true);
                $('#naming_pattern').css('background-color', '#FFDDDD');
            } else if (data === 'seasonfolders') {
                $('#naming_pattern').qtip('option', {
                    'content.text': 'This pattern would be invalid without the folders, using it will force "Flatten" off for all shows.',
                    'style.classes': 'qtip-rounded qtip-shadow qtip-red'
                });
                $('#naming_pattern').qtip('toggle', true);
                $('#naming_pattern').css('background-color', '#FFFFDD');
            } else {
                $('#naming_pattern').qtip('option', {
                    'content.text': 'This pattern is valid.',
                    'style.classes': 'qtip-rounded qtip-shadow qtip-green'
                });
                $('#naming_pattern').qtip('toggle', false);
                $('#naming_pattern').css('background-color', '#FFFFFF');
            }
        });
    }

    // @TODO all of these setup funcitons should be able to be rolled into a generic function

    function setupNaming() {
        // if it is a custom selection then show the text box
        if ($('#name_presets :selected').val().toLowerCase() === 'custom...') {
            $('#naming_custom').show();
        } else {
            $('#naming_custom').hide();
            $('#naming_pattern').val($('#name_presets :selected').attr('id'));
        }
        fillExamples();
    }

    function setupAbdNaming() {
        // if it is a custom selection then show the text box
        if ($('#name_abd_presets :selected').val().toLowerCase() === 'custom...') {
            $('#naming_abd_custom').show();
        } else {
            $('#naming_abd_custom').hide();
            $('#naming_abd_pattern').val($('#name_abd_presets :selected').attr('id'));
        }
        fillAbdExamples();
    }

    function setupSportsNaming() {
        // if it is a custom selection then show the text box
        if ($('#name_sports_presets :selected').val().toLowerCase() === 'custom...') {
            $('#naming_sports_custom').show();
        } else {
            $('#naming_sports_custom').hide();
            $('#naming_sports_pattern').val($('#name_sports_presets :selected').attr('id'));
        }
        fillSportsExamples();
    }

    function setupAnimeNaming() {
        // if it is a custom selection then show the text box
        if ($('#name_anime_presets :selected').val().toLowerCase() === 'custom...') {
            $('#naming_anime_custom').show();
        } else {
            $('#naming_anime_custom').hide();
            $('#naming_anime_pattern').val($('#name_anime_presets :selected').attr('id'));
        }
        fillAnimeExamples();
    }

    $('#unpack').on('change', function () {
        if (this.checked) {
            isRarSupported();
        } else {
            $('#unpack').qtip('toggle', false);
        }
    });

    // @TODO all of these on change funcitons should be able to be rolled into a generic jQuery function or maybe we could
    //       move all of the setup functions into these handlers?

    $('#name_presets').on('change', function () {
        setupNaming();
    });

    $('#name_abd_presets').on('change', function () {
        setupAbdNaming();
    });

    $('#naming_custom_abd').on('change', function () {
        setupAbdNaming();
    });

    $('#name_sports_presets').on('change', function () {
        setupSportsNaming();
    });

    $('#naming_custom_sports').on('change', function () {
        setupSportsNaming();
    });

    $('#name_anime_presets').on('change', function () {
        setupAnimeNaming();
    });

    $('#naming_custom_anime').on('change', function () {
        setupAnimeNaming();
    });

    $('input[name="naming_anime"]').on('click', function () {
        setupAnimeNaming();
    });

    // @TODO We might be able to change these from typewatch to _ debounce like we've done on the log page
    //       The main reason for doing this would be to use only open source stuff that's still being maintained

    $('#naming_multi_ep').on('change', fillExamples);
    $('#naming_pattern').on('focusout', fillExamples);
    $('#naming_pattern').on('keyup', function () {
        typewatch(function () {
            fillExamples();
        }, 500);
    });

    $('#naming_anime_multi_ep').on('change', fillAnimeExamples);
    $('#naming_anime_pattern').on('focusout', fillAnimeExamples);
    $('#naming_anime_pattern').on('keyup', function () {
        typewatch(function () {
            fillAnimeExamples();
        }, 500);
    });

    $('#naming_abd_pattern').on('focusout', fillExamples);
    $('#naming_abd_pattern').on('keyup', function () {
        typewatch(function () {
            fillAbdExamples();
        }, 500);
    });

    $('#naming_sports_pattern').on('focusout', fillExamples);
    $('#naming_sports_pattern').on('keyup', function () {
        typewatch(function () {
            fillSportsExamples();
        }, 500);
    });

    $('#naming_anime_pattern').on('focusout', fillExamples);
    $('#naming_anime_pattern').on('keyup', function () {
        typewatch(function () {
            fillAnimeExamples();
        }, 500);
    });

    $('#show_naming_key').on('click', function () {
        $('#naming_key').toggle();
    });
    $('#show_naming_abd_key').on('click', function () {
        $('#naming_abd_key').toggle();
    });
    $('#show_naming_sports_key').on('click', function () {
        $('#naming_sports_key').toggle();
    });
    $('#show_naming_anime_key').on('click', function () {
        $('#naming_anime_key').toggle();
    });
    $('#do_custom').on('click', function () {
        $('#naming_pattern').val($('#name_presets :selected').attr('id'));
        $('#naming_custom').show();
        $('#naming_pattern').focus();
    });

    // @TODO We should see if these can be added with the on click or if we need to even call them on load
    setupNaming();
    setupAbdNaming();
    setupSportsNaming();
    setupAnimeNaming();

    // -- start of metadata options div toggle code --
    $('#metadataType').on('change keyup', function () {
        $(this).showHideMetadata();
    });

    $.fn.showHideMetadata = function () {
        $('.metadataDiv').each(function () {
            var targetName = $(this).attr('id');
            var selectedTarget = $('#metadataType :selected').val();

            if (selectedTarget === targetName) {
                $(this).show();
            } else {
                $(this).hide();
            }
        });
    };
    // initialize to show the div
    $(this).showHideMetadata();
    // -- end of metadata options div toggle code --

    $('.metadata_checkbox').on('click', function () {
        $(this).refreshMetadataConfig(false);
    });

    $.fn.refreshMetadataConfig = function (first) {
        var curMost = 0;
        var curMostProvider = '';

        $('.metadataDiv').each(function () {
            // eslint-disable-line complexity
            var generatorName = $(this).attr('id');

            var configArray = [];
            var showMetadata = $('#' + generatorName + '_show_metadata').prop('checked');
            var episodeMetadata = $('#' + generatorName + '_episode_metadata').prop('checked');
            var fanart = $('#' + generatorName + '_fanart').prop('checked');
            var poster = $('#' + generatorName + '_poster').prop('checked');
            var banner = $('#' + generatorName + '_banner').prop('checked');
            var episodeThumbnails = $('#' + generatorName + '_episode_thumbnails').prop('checked');
            var seasonPosters = $('#' + generatorName + '_season_posters').prop('checked');
            var seasonBanners = $('#' + generatorName + '_season_banners').prop('checked');
            var seasonAllPoster = $('#' + generatorName + '_season_all_poster').prop('checked');
            var seasonAllBanner = $('#' + generatorName + '_season_all_banner').prop('checked');

            configArray.push(showMetadata ? '1' : '0');
            configArray.push(episodeMetadata ? '1' : '0');
            configArray.push(fanart ? '1' : '0');
            configArray.push(poster ? '1' : '0');
            configArray.push(banner ? '1' : '0');
            configArray.push(episodeThumbnails ? '1' : '0');
            configArray.push(seasonPosters ? '1' : '0');
            configArray.push(seasonBanners ? '1' : '0');
            configArray.push(seasonAllPoster ? '1' : '0');
            configArray.push(seasonAllBanner ? '1' : '0');

            var curNumber = 0;
            for (var i = 0, len = configArray.length; i < len; i++) {
                curNumber += parseInt(configArray[i], 10);
            }
            if (curNumber > curMost) {
                curMost = curNumber;
                curMostProvider = generatorName;
            }

            $('#' + generatorName + '_eg_show_metadata').prop('class', showMetadata ? 'enabled' : 'disabled');
            $('#' + generatorName + '_eg_episode_metadata').prop('class', episodeMetadata ? 'enabled' : 'disabled');
            $('#' + generatorName + '_eg_fanart').prop('class', fanart ? 'enabled' : 'disabled');
            $('#' + generatorName + '_eg_poster').prop('class', poster ? 'enabled' : 'disabled');
            $('#' + generatorName + '_eg_banner').prop('class', banner ? 'enabled' : 'disabled');
            $('#' + generatorName + '_eg_episode_thumbnails').prop('class', episodeThumbnails ? 'enabled' : 'disabled');
            $('#' + generatorName + '_eg_season_posters').prop('class', seasonPosters ? 'enabled' : 'disabled');
            $('#' + generatorName + '_eg_season_banners').prop('class', seasonBanners ? 'enabled' : 'disabled');
            $('#' + generatorName + '_eg_season_all_poster').prop('class', seasonAllPoster ? 'enabled' : 'disabled');
            $('#' + generatorName + '_eg_season_all_banner').prop('class', seasonAllBanner ? 'enabled' : 'disabled');
            $('#' + generatorName + '_data').val(configArray.join('|'));
        });

        if (curMostProvider !== '' && first) {
            $('#metadataType option[value=' + curMostProvider + ']').prop('selected', true);
            $(this).showHideMetadata();
        }
    };

    $(this).refreshMetadataConfig(true);
    $('img[title]').qtip({
        position: {
            at: 'bottom center',
            my: 'top right'
        },
        style: {
            tip: {
                corner: true,
                method: 'polygon'
            },
            classes: 'qtip-shadow qtip-dark'
        }
    });
    $('i[title]').qtip({
        position: {
            at: 'top center',
            my: 'bottom center'
        },
        style: {
            tip: {
                corner: true,
                method: 'polygon'
            },
            classes: 'qtip-rounded qtip-shadow ui-tooltip-sb'
        }
    });
    $('.custom-pattern,#unpack').qtip({
        content: 'validating...',
        show: {
            event: false,
            ready: false
        },
        hide: false,
        position: {
            at: 'center left',
            my: 'center right'
        },
        style: {
            tip: {
                corner: true,
                method: 'polygon'
            },
            classes: 'qtip-rounded qtip-shadow qtip-red'
        }
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

//# sourceMappingURL=post-processing.js.map

(function e(t,n,r){function s(o,u){if(!n[o]){if(!t[o]){var a=typeof require=="function"&&require;if(!u&&a)return a(o,!0);if(i)return i(o,!0);var f=new Error("Cannot find module '"+o+"'");throw f.code="MODULE_NOT_FOUND",f}var l=n[o]={exports:{}};t[o][0].call(l.exports,function(e){var n=t[o][1][e];return s(n?n:e)},l,l.exports,e,t,n,r)}return n[o].exports}var i=typeof require=="function"&&require;for(var o=0;o<r.length;o++)s(r[o]);return s})({1:[function(require,module,exports){
const MEDUSA = require('./core');

const startAjaxEpisodeSubtitles = function () {
    const searchTypesList = ['.epSubtitlesSearch', '.epSubtitlesSearchPP', '.epRedownloadSubtitle', '.epSearch', '.epRetry', '.epManualSearch'];
    const subtitlesResultModal = $('#manualSubtitleSearchModal');
    const subtitlesMulti = MEDUSA.config.subtitlesMulti;
    const loadingSpinner = 'images/loading32' + MEDUSA.config.themeSpinner + '.gif';
    let subtitlesTd;
    let selectedEpisode;

    const disableAllSearches = () => {
        // Disables all other searches while manual searching for subtitles
        $.each(searchTypesList, (index, searchTypes) => {
            $(searchTypes).css({
                'pointer-events': 'none'
            });
        });
    };

    const enableAllSearches = () => {
        // Enabled all other searches while manual searching for subtitles
        $.each(searchTypesList, (index, searchTypes) => {
            $(searchTypes).css({
                'pointer-events': 'auto'
            });
        });
    };

    const changeImage = (imageTR, srcData, altData, titleData, heightData, emptyLink) => {
        // eslint-disable-line max-params
        if (emptyLink === true) {
            imageTR.find('img').remove();
        }
        imageTR.append($('<img/>').prop({
            src: srcData,
            alt: altData,
            title: titleData,
            width: 16,
            height: heightData
        }));
    };

    subtitlesResultModal.on('hidden.bs.modal', () => {
        // If user close manual subtitle search modal, enable again all searches
        enableAllSearches();
    });

    $.ajaxEpSubtitlesSearch = function () {
        const searchSubtitles = () => {
            disableAllSearches();
            changeImage(selectedEpisode, loadingSpinner, 'loading', 'loading', 16, true);
            let url = selectedEpisode.prop('href');
            // If manual search, replace handler
            url = url.replace('searchEpisodeSubtitles', 'manual_search_subtitles');
            $.getJSON(url, data => {
                // Delete existing rows in the modal
                const existingRows = $('#subtitle_results tr').length;
                if (existingRows > 1) {
                    for (let x = existingRows - 1; x > 0; x--) {
                        $('#subtitle_results tr').eq(x).remove();
                    }
                }
                // Add the release to the modal title
                $('h4#manualSubtitleSearchModalTitle.modal-title').text(data.release);
                if (data.result === 'success') {
                    $.each(data.subtitles, (index, subtitle) => {
                        // For each subtitle found create the row string and append to the modal
                        const provider = '<img src="images/subtitles/' + subtitle.provider + '.png" width="16" height="16" style="vertical-align:middle;"/>';
                        const flag = '<img src="images/subtitles/flags/' + subtitle.lang + '.png" width="16" height="11"/>';
                        let missingGuess = '';
                        for (let i = 0; i < subtitle.missing_guess.length; i++) {
                            let value = subtitle.missing_guess[i];
                            if (missingGuess) {
                                missingGuess += ', ';
                            }
                            value = value.charAt(0).toUpperCase() + value.slice(1);
                            missingGuess += value.replace(/(_[a-z])/g, $1 => $1.toUpperCase().replace('_', ' '));
                        }
                        const subtitleName = subtitle.filename.substring(0, 99);
                        let subtitleScore = subtitle.score;
                        // If hash match, don't show missingGuess
                        if (subtitle.sub_score >= subtitle.max_score) {
                            missingGuess = '';
                        }
                        // If perfect match, add a checkmark next to subtitle filename
                        let checkmark = '';
                        if (subtitle.sub_score >= subtitle.min_score) {
                            checkmark = '<img src="images/save.png" width="16" height="16"/>';
                        }
                        const subtitleLink = '<a href="#" id="pickSub" title="Download subtitle: ' + subtitle.filename + '" subtitleID="subtitleid-' + subtitle.id + '">' + subtitleName + checkmark + '</a>';
                        // Make subtitle score always between 0 and 10
                        if (subtitleScore > 10) {
                            subtitleScore = 10;
                        } else if (subtitleScore < 0) {
                            subtitleScore = 0;
                        }
                        const row = '<tr style="font-size: 95%;">' + '<td style="white-space:nowrap;">' + provider + ' ' + subtitle.provider + '</td>' + '<td>' + flag + '</td>' + '<td title="' + subtitle.sub_score + '/' + subtitle.min_score + '"> ' + subtitleScore + '</td>' + '<td class="tvShow"> ' + subtitleLink + '</td>' + '<td>' + missingGuess + '</td>' + '</tr>';
                        $('#subtitle_results').append(row);
                        // Allow the modal to be resizable
                        $('.modal-content').resizable({
                            alsoResize: '.modal-body'
                        });
                        // Allow the modal to be draggable
                        $('.modal-dialog').draggable({
                            cancel: '.text'
                        });
                        // After all rows are added, show the modal with results found
                        subtitlesResultModal.modal('show');
                    });
                }
                // Add back the CC icon as we are not searching anymore
                changeImage(selectedEpisode, 'images/closed_captioning.png', 'Search subtitles', 'Search subtitles', 16, true);
                enableAllSearches();
            });
            return false;
        };

        const forcedSearch = () => {
            disableAllSearches();
            changeImage(selectedEpisode, loadingSpinner, 'loading', 'loading', 16, true);
            const url = selectedEpisode.prop('href');
            $.getJSON(url, data => {
                if (data.result.toLowerCase() === 'success') {
                    // Clear and update the subtitles column with new informations
                    const subtitles = data.subtitles.split(',');
                    subtitlesTd.empty();
                    $.each(subtitles, (index, language) => {
                        if (language !== '') {
                            if (index !== subtitles.length - 1) {
                                // eslint-disable-line no-negated-condition
                                changeImage(subtitlesTd, '', language, language, 11, true);
                            } else {
                                changeImage(subtitlesTd, 'images/subtitles/flags/' + language + '.png', language, language, 11, true);
                            }
                        }
                    });
                }
                // Add back the CC icon as we are not searching anymore
                changeImage(selectedEpisode, 'images/closed_captioning.png', 'Search subtitles', 'Search subtitles', 16, true);
                enableAllSearches();
            });
            return false;
        };

        $('.epSubtitlesSearch').on('click', function (e) {
            // This is for the page 'displayShow.mako'
            e.preventDefault();
            selectedEpisode = $(this);
            subtitlesTd = selectedEpisode.parent().siblings('.col-subtitles');
            // Ask user if he want to manual search subs or automatic search
            $('#askmanualSubtitleSearchModal').modal('show');
        });

        $('.epSubtitlesSearchPP').on('click', function (e) {
            // This is for the page 'manage_subtitleMissedPP.mako'
            e.preventDefault();
            selectedEpisode = $(this);
            subtitlesTd = selectedEpisode.parent().siblings('.col-search');
            searchSubtitles();
        });

        // @TODO: move this to a more specific selector
        $(document).on('click', '#pickSub', function (e) {
            e.preventDefault();
            const subtitlePicked = $(this);
            changeImage(subtitlePicked, loadingSpinner, 'loading', 'loading', 16, true);
            let subtitleID = subtitlePicked.attr('subtitleID');
            // Remove 'subtitleid-' so we know the actual ID
            subtitleID = subtitleID.replace('subtitleid-', '');
            let url = selectedEpisode.prop('href');
            url = url.replace('searchEpisodeSubtitles', 'manual_search_subtitles');
            // Append the ID param that 'manual_search_subtitles' expect when picking subtitles
            url += '&picked_id=' + encodeURIComponent(subtitleID);
            $.getJSON(url, data => {
                // If user click to close the window before subtitle download finishes, show again the modal
                if (subtitlesResultModal.is(':visible') === false) {
                    subtitlesResultModal.modal('show');
                }
                if (data.result === 'success') {
                    const language = data.subtitles;
                    changeImage(subtitlePicked, 'images/yes16.png', 'subtitle saved', 'subtitle saved', 16, true);
                    if ($('table#releasesPP').length > 0) {
                        // Removes the release as we downloaded the subtitle
                        // Only applied to manage_subtitleMissedPP.mako
                        selectedEpisode.parent().parent().remove();
                    } else {
                        // Update the subtitles column with new informations
                        if (subtitlesMulti === true) {
                            // eslint-disable-line no-lonely-if
                            const lang = language;
                            let hasLang = false;
                            subtitlesTd.children().children().each(function () {
                                // Check if user already have this subtitle language
                                if ($(this).attr('alt').indexOf(lang) !== -1) {
                                    hasLang = true;
                                }
                            });
                            // Only add language flag if user doesn't have this subtitle language
                            if (hasLang === false) {
                                changeImage(subtitlesTd, 'images/subtitles/flags/' + language + '.png', language, language, 11, false);
                            }
                        } else {
                            changeImage(subtitlesTd, 'images/subtitles/flags/unknown.png', language, language, 11, false);
                        }
                    }
                } else {
                    changeImage(subtitlePicked, 'images/no16.png', 'subtitle not saved', 'subtitle not saved', 16, true);
                }
            });
        });

        $('#askmanualSubtitleSearchModal .btn').on('click', function () {
            if ($(this).text().toLowerCase() === 'manual') {
                // Call manual search
                searchSubtitles();
            } else {
                // Call auto search
                forcedSearch();
            }
        });
    };

    $.fn.ajaxEpMergeSubtitles = function () {
        $('.epMergeSubtitles').on('click', function () {
            const subtitlesMergeLink = $(this);
            changeImage(subtitlesMergeLink, loadingSpinner, 'loading', 'loading', 16, true);
            $.getJSON($(this).attr('href'), () => {
                // Don't allow other merges
                subtitlesMergeLink.remove();
            });
            return false;
        });
    };

    $.ajaxEpRedownloadSubtitle = function () {
        $('.epRedownloadSubtitle').on('click', function (e) {
            e.preventDefault();
            selectedEpisode = $(this);
            $('#confirmSubtitleReDownloadModal').modal('show');
        });

        const redownloadSubtitles = () => {
            disableAllSearches();
            const url = selectedEpisode.prop('href');
            const downloading = 'Re-downloading subtitle';
            const failed = 'Re-downloaded subtitle failed';
            const downloaded = 'Re-downloaded subtitle succeeded';
            changeImage(selectedEpisode, loadingSpinner, downloading, downloading, 16, true);
            $.getJSON(url, data => {
                if (data.result.toLowerCase() === 'success' && data.new_subtitles.length > 0) {
                    changeImage(selectedEpisode, 'images/save.png', downloaded, downloaded, 16, true);
                } else {
                    changeImage(selectedEpisode, 'images/no16.png', failed, failed, 16, true);
                }
            });
            enableAllSearches();
            return false;
        };

        $('#confirmSubtitleReDownloadModal .btn.btn-success').on('click', () => {
            redownloadSubtitles();
        });
    };
};

module.exports = startAjaxEpisodeSubtitles;

},{"./core":3}],2:[function(require,module,exports){
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

},{}],3:[function(require,module,exports){
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

},{"./api":2}]},{},[1]);

//# sourceMappingURL=ajax-episode-subtitles.js.map

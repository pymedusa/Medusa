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

},{"./api":2}],4:[function(require,module,exports){
const MEDUSA = require('../core');
const startAjaxEpisodeSubtitles = require('../ajax-episode-subtitles');

MEDUSA.home.displayShow = function () {
    // eslint-disable-line max-lines
    // Adjust the summary background position and size on page load and resize
    const moveSummaryBackground = () => {
        const height = $('#summary').height() + 10;
        const top = $('#summary').offset().top + 5;
        $('#summaryBackground').height(height);
        $('#summaryBackground').offset({ top, left: 0 });
        $('#summaryBackground').show();
    };

    const movecheckboxControlsBackground = () => {
        const height = $('#checkboxControls').height() + 10;
        const top = $('#checkboxControls').offset().top - 3;
        $('#checkboxControlsBackground').height(height);
        $('#checkboxControlsBackground').offset({ top, left: 0 });
        $('#checkboxControlsBackground').show();
    };

    $('.imdbPlot').on('click', function () {
        $(this).prev('span').toggle();
        if ($(this).html() === '..show less') {
            $(this).html('..show more');
        } else {
            $(this).html('..show less');
        }
        moveSummaryBackground();
        movecheckboxControlsBackground();
    });

    $(window).on('resize', () => {
        moveSummaryBackground();
        movecheckboxControlsBackground();
    });

    $(() => {
        moveSummaryBackground();
        movecheckboxControlsBackground();
    });

    $.ajaxEpSearch({
        colorRow: true
    });

    startAjaxEpisodeSubtitles();
    $.ajaxEpSubtitlesSearch();
    $.ajaxEpRedownloadSubtitle();

    $('#seasonJump').on('change', function () {
        const id = $('#seasonJump option:selected').val();
        if (id && id !== 'jump') {
            const season = $('#seasonJump option:selected').data('season');
            $('html,body').animate({ scrollTop: $('[name ="' + id.substring(1) + '"]').offset().top - 50 }, 'slow');
            $('#collapseSeason-' + season).collapse('show');
            location.hash = id;
        }
        $(this).val('jump');
    });

    $('#prevShow').on('click', () => {
        $('#select-show option:selected').prev('option').prop('selected', true);
        $('#select-show').change();
    });

    $('#nextShow').on('click', () => {
        $('#select-show option:selected').next('option').prop('selected', true);
        $('#select-show').change();
    });

    $('#changeStatus').on('click', () => {
        const epArr = [];

        $('.epCheck').each(function () {
            if (this.checked === true) {
                epArr.push($(this).attr('id'));
            }
        });

        if (epArr.length === 0) {
            return false;
        }

        window.location.href = $('base').attr('href') + 'home/setStatus?show=' + $('#series-id').attr('value') + '&eps=' + epArr.join('|') + '&status=' + $('#statusSelect').val();
    });

    $('.seasonCheck').on('click', function () {
        const seasCheck = this;
        const seasNo = $(seasCheck).attr('id');

        $('#collapseSeason-' + seasNo).collapse('show');
        $('.epCheck:visible').each(function () {
            const epParts = $(this).attr('id').split('x');
            if (epParts[0] === seasNo) {
                this.checked = seasCheck.checked;
            }
        });
    });

    let lastCheck = null;
    $('.epCheck').on('click', function (event) {
        if (!lastCheck || !event.shiftKey) {
            lastCheck = this;
            return;
        }

        const check = this;
        let found = 0;

        $('.epCheck').each(function () {
            if (found === 1) {
                this.checked = lastCheck.checked;
            }

            if (found === 1) {
                return false;
            }

            if (this === check || this === lastCheck) {
                found++;
            }
        });
    });

    // Selects all visible episode checkboxes.
    $('.seriesCheck').on('click', () => {
        $('.epCheck:visible').each(function () {
            this.checked = true;
        });
        $('.seasonCheck:visible').each(function () {
            this.checked = true;
        });
    });

    // Clears all visible episode checkboxes and the season selectors
    $('.clearAll').on('click', () => {
        $('.epCheck:visible').each(function () {
            this.checked = false;
        });
        $('.seasonCheck:visible').each(function () {
            this.checked = false;
        });
    });

    // Handle the show selection dropbox
    $('#select-show').on('change', function () {
        const val = $(this).val();
        if (val === 0) {
            return;
        }
        window.location.href = $('base').attr('href') + 'home/displayShow?show=' + val;
    });

    // Show/Hide different types of rows when the checkboxes are changed
    $('#checkboxControls input').on('change', function () {
        const whichClass = $(this).attr('id');
        $(this).showHideRows(whichClass);
    });

    // Initially show/hide all the rows according to the checkboxes
    $('#checkboxControls input').each(function () {
        const status = $(this).prop('checked');
        $('tr.' + $(this).attr('id')).each(function () {
            if (status) {
                $(this).show();
            } else {
                $(this).hide();
            }
        });
    });

    $.fn.showHideRows = function (whichClass) {
        const status = $('#checkboxControls > input, #' + whichClass).prop('checked');
        $('tr.' + whichClass).each(function () {
            if (status) {
                $(this).show();
            } else {
                $(this).hide();
            }
        });

        // Hide season headers with no episodes under them
        $('tr.seasonheader').each(function () {
            const seasonNo = $(this).attr('id');
            let numRows = 0;
            $('tr.' + seasonNo + ' :visible').each(() => {
                numRows++;
            });
            if (numRows === 0) {
                $(this).hide();
                $('#' + seasonNo + '-cols').hide();
            } else {
                $(this).show();
                $('#' + seasonNo + '-cols').show();
            }
        });
    };

    const setEpisodeSceneNumbering = (forSeason, forEpisode, sceneSeason, sceneEpisode) => {
        const showId = $('#series-id').val();
        const indexer = $('#indexer').val();

        if (sceneSeason === '') {
            sceneSeason = null;
        }
        if (sceneEpisode === '') {
            sceneEpisode = null;
        }

        $.getJSON('home/setSceneNumbering', {
            show: showId,
            indexer,
            forSeason,
            forEpisode,
            sceneSeason,
            sceneEpisode
        }, data => {
            // Set the values we get back
            if (data.sceneSeason === null || data.sceneEpisode === null) {
                $('#sceneSeasonXEpisode_' + showId + '_' + forSeason + '_' + forEpisode).val('');
            } else {
                $('#sceneSeasonXEpisode_' + showId + '_' + forSeason + '_' + forEpisode).val(data.sceneSeason + 'x' + data.sceneEpisode);
            }
            if (!data.success) {
                if (data.errorMessage) {
                    alert(data.errorMessage); // eslint-disable-line no-alert
                } else {
                    alert('Update failed.'); // eslint-disable-line no-alert
                }
            }
        });
    };

    const setAbsoluteSceneNumbering = (forAbsolute, sceneAbsolute) => {
        const showId = $('#series-id').val();
        const indexer = $('#indexer').val();

        if (sceneAbsolute === '') {
            sceneAbsolute = null;
        }

        $.getJSON('home/setSceneNumbering', {
            show: showId,
            indexer,
            forAbsolute,
            sceneAbsolute
        }, data => {
            // Set the values we get back
            if (data.sceneAbsolute === null) {
                $('#sceneAbsolute_' + showId + '_' + forAbsolute).val('');
            } else {
                $('#sceneAbsolute_' + showId + '_' + forAbsolute).val(data.sceneAbsolute);
            }

            if (!data.success) {
                if (data.errorMessage) {
                    alert(data.errorMessage); // eslint-disable-line no-alert
                } else {
                    alert('Update failed.'); // eslint-disable-line no-alert
                }
            }
        });
    };

    const setInputValidInvalid = (valid, el) => {
        if (valid) {
            $(el).css({
                'background-color': '#90EE90', // Green
                color: '#FFF',
                'font-weight': 'bold'
            });
            return true;
        }
        $(el).css({
            'background-color': '#FF0000', // Red
            color: '#FFF!important',
            'font-weight': 'bold'
        });
        return false;
    };

    $('.sceneSeasonXEpisode').on('change', function () {
        // Strip non-numeric characters
        const value = $(this).val();
        $(this).val(value.replace(/[^0-9xX]*/g, ''));
        const forSeason = $(this).attr('data-for-season');
        const forEpisode = $(this).attr('data-for-episode');

        // If empty reset the field
        if (value === '') {
            setEpisodeSceneNumbering(forSeason, forEpisode, null, null);
            return;
        }

        const m = $(this).val().match(/^(\d+)x(\d+)$/i);
        const onlyEpisode = $(this).val().match(/^(\d+)$/i);
        let sceneSeason = null;
        let sceneEpisode = null;
        let isValid = false;
        if (m) {
            sceneSeason = m[1];
            sceneEpisode = m[2];
            isValid = setInputValidInvalid(true, $(this));
        } else if (onlyEpisode) {
            // For example when '5' is filled in instead of '1x5', asume it's the first season
            sceneSeason = forSeason;
            sceneEpisode = onlyEpisode[1];
            isValid = setInputValidInvalid(true, $(this));
        } else {
            isValid = setInputValidInvalid(false, $(this));
        }

        if (isValid) {
            setEpisodeSceneNumbering(forSeason, forEpisode, sceneSeason, sceneEpisode);
        }
    });

    $('.sceneAbsolute').on('change', function () {
        // Strip non-numeric characters
        $(this).val($(this).val().replace(/[^0-9xX]*/g, ''));
        const forAbsolute = $(this).attr('data-for-absolute');

        const m = $(this).val().match(/^(\d{1,3})$/i);
        let sceneAbsolute = null;
        if (m) {
            sceneAbsolute = m[1];
        }
        setAbsoluteSceneNumbering(forAbsolute, sceneAbsolute);
    });

    $.fn.generateStars = function () {
        return this.each((i, e) => {
            $(e).html($('<span/>').width($(e).text() * 12));
        });
    };

    $('.imdbstars').generateStars();

    $('#showTable, #animeTable').tablesorter({
        widgets: ['saveSort', 'stickyHeaders', 'columnSelector'],
        widgetOptions: {
            columnSelector_saveColumns: true, // eslint-disable-line camelcase
            columnSelector_layout: '<label><input type="checkbox">{name}</label>', // eslint-disable-line camelcase
            columnSelector_mediaquery: false, // eslint-disable-line camelcase
            columnSelector_cssChecked: 'checked' // eslint-disable-line camelcase
        }
    });

    $('#popover').popover({
        placement: 'bottom',
        html: true,
        content: '<div id="popover-target"></div>'
    }).on('shown.bs.popover', () => {
        $.tablesorter.columnSelector.attachTo($('#showTable, #animeTable'), '#popover-target');
    });

    // Moved and rewritten this from displayShow. This changes the button when clicked for collapsing/expanding the
    // Season to Show Episodes or Hide Episodes.
    $(() => {
        $('.collapse.toggle').on('hide.bs.collapse', function () {
            const reg = /collapseSeason-([0-9]+)/g;
            const result = reg.exec(this.id);
            $('#showseason-' + result[1]).text('Show Episodes');
            $('#season-' + result[1] + '-cols').addClass('shadow');
        });
        $('.collapse.toggle').on('show.bs.collapse', function () {
            const reg = /collapseSeason-([0-9]+)/g;
            const result = reg.exec(this.id);
            $('#showseason-' + result[1]).text('Hide Episodes');
            $('#season-' + result[1] + '-cols').removeClass('shadow');
        });
    });

    // Set the season exception based on using the get_xem_numbering_for_show() for animes if available in data.xemNumbering,
    // or else try to map using just the data.season_exceptions.
    function setSeasonSceneException(data) {
        $.each(data.seasonExceptions, (season, nameExceptions) => {
            let foundInXem = false;
            // Check if it is a season name exception, we don't handle the show name exceptions here
            if (season >= 0) {
                // Loop through the xem mapping, and check if there is a xem_season, that needs to show the season name exception
                $.each(data.xemNumbering, (indexerSeason, xemSeason) => {
                    if (xemSeason === parseInt(season, 10)) {
                        foundInXem = true;
                        $('<img>', {
                            id: 'xem-exception-season-' + xemSeason,
                            alt: '[xem]',
                            height: '16',
                            width: '16',
                            src: 'images/xem.png',
                            title: nameExceptions.join(', ')
                        }).appendTo('[data-season=' + indexerSeason + ']');
                    }
                });

                // This is not a xem season exception, let's set the exceptions as a medusa exception
                if (!foundInXem) {
                    $('<img>', {
                        id: 'xem-exception-season-' + season,
                        alt: '[medusa]',
                        height: '16',
                        width: '16',
                        src: 'images/ico/favicon-16.png',
                        title: nameExceptions.join(', ')
                    }).appendTo('[data-season=' + season + ']');
                }
            }
        });
    }

    // @TODO: OMG: This is just a basic json, in future it should be based on the CRUD route.
    // Get the season exceptions and the xem season mappings.
    $.getJSON('home/getSeasonSceneExceptions', {
        indexer: $('input#indexer').val(),
        indexer_id: $('input#series-id').val() // eslint-disable-line camelcase
    }, data => {
        setSeasonSceneException(data);
    });

    //
    // href="home/toggleDisplayShowSpecials/?show=${show.indexerid}"
    $('.display-specials a').on('click', function () {
        api.patch('config/main', {
            layout: {
                show: {
                    specials: $(this).text() !== 'Hide'
                }
            }
        }).then(response => {
            log.info(response.data);
            window.location.reload();
        }).catch(err => {
            log.error(err.data);
        });
    });
};

},{"../ajax-episode-subtitles":1,"../core":3}]},{},[4]);

//# sourceMappingURL=display-show.js.map

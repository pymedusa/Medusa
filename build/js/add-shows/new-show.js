(function e(t,n,r){function s(o,u){if(!n[o]){if(!t[o]){var a=typeof require=="function"&&require;if(!u&&a)return a(o,!0);if(i)return i(o,!0);var f=new Error("Cannot find module '"+o+"'");throw f.code="MODULE_NOT_FOUND",f}var l=n[o]={exports:{}};t[o][0].call(l.exports,function(e){var n=t[o][1][e];return s(n?n:e)},l,l.exports,e,t,n,r)}return n[o].exports}var i=typeof require=="function"&&require;for(var o=0;o<r.length;o++)s(r[o]);return s})({1:[function(require,module,exports){
const MEDUSA = require('../core');
MEDUSA.addShows.newShow = function () {
    function updateSampleText() {
        // if something's selected then we have some behavior to figure out

        var showName;
        var sepChar;
        // if they've picked a radio button then use that
        if ($('input:radio[name=whichSeries]:checked').length !== 0) {
            showName = $('input:radio[name=whichSeries]:checked').val().split('|')[4];
        } else if ($('input:hidden[name=whichSeries]').length !== 0 && $('input:hidden[name=whichSeries]').val().length !== 0) {
            // if we provided a show in the hidden field, use that
            showName = $('#providedName').val();
        } else {
            showName = '';
        }
        $.updateBlackWhiteList(showName);
        var sampleText = 'Adding show <b>' + showName + '</b> into <b>';

        // if we have a root dir selected, figure out the path
        if ($('#rootDirs option:selected').length !== 0) {
            var rootDirectoryText = $('#rootDirs option:selected').val();
            if (rootDirectoryText.indexOf('/') >= 0) {
                sepChar = '/';
            } else if (rootDirectoryText.indexOf('\\') >= 0) {
                sepChar = '\\';
            } else {
                sepChar = '';
            }

            if (rootDirectoryText.substr(sampleText.length - 1) !== sepChar) {
                rootDirectoryText += sepChar;
            }
            rootDirectoryText += '<i>||</i>' + sepChar;

            sampleText += rootDirectoryText;
        } else if ($('#fullShowPath').length !== 0 && $('#fullShowPath').val().length !== 0) {
            sampleText += $('#fullShowPath').val();
        } else {
            sampleText += 'unknown dir.';
        }

        sampleText += '</b>';

        // if we have a show name then sanitize and use it for the dir name
        if (showName.length > 0) {
            $.get('addShows/sanitizeFileName', {
                name: showName
            }, function (data) {
                $('#displayText').html(sampleText.replace('||', data));
            });
            // if not then it's unknown
        } else {
            $('#displayText').html(sampleText.replace('||', '??'));
        }

        // also toggle the add show button
        if (($('#rootDirs option:selected').length !== 0 || $('#fullShowPath').length !== 0 && $('#fullShowPath').val().length !== 0) && // eslint-disable-line no-mixed-operators
        $('input:radio[name=whichSeries]:checked').length !== 0 || // eslint-disable-line no-mixed-operators
        $('input:hidden[name=whichSeries]').length !== 0 && $('input:hidden[name=whichSeries]').val().length !== 0) {
            $('#addShowButton').prop('disabled', false);
        } else {
            $('#addShowButton').prop('disabled', true);
        }
    }

    var searchRequestXhr = null;
    function searchIndexers() {
        if ($('#nameToSearch').val().length === 0) {
            return;
        }

        if (searchRequestXhr) {
            searchRequestXhr.abort();
        }

        var searchingFor = $('#nameToSearch').val().trim() + ' on ' + $('#providedIndexer option:selected').text() + ' in ' + $('#indexerLangSelect').val();
        $('#searchResults').empty().html('<img id="searchingAnim" src="images/loading32' + MEDUSA.config.themeSpinner + '.gif" height="32" width="32" /> searching ' + searchingFor + '...');

        searchRequestXhr = $.ajax({
            url: 'addShows/searchIndexersForShowName',
            data: {
                search_term: $('#nameToSearch').val().trim(), // eslint-disable-line camelcase
                lang: $('#indexerLangSelect').val(),
                indexer: $('#providedIndexer').val()
            },
            timeout: parseInt($('#indexer_timeout').val(), 10) * 1000,
            dataType: 'json',
            error: function () {
                $('#searchResults').empty().html('search timed out, try again or try another indexer');
            }
        }).done(function (data) {
            var firstResult = true;
            var resultStr = '<fieldset>\n<legend class="legendStep">Search Results:</legend>\n';
            var checked = '';

            if (data.results.length === 0) {
                resultStr += '<b>No results found, try a different search.</b>';
            } else {
                $.each(data.results, function (index, obj) {
                    if (firstResult) {
                        checked = ' checked';
                        firstResult = false;
                    } else {
                        checked = '';
                    }

                    var whichSeries = obj.join('|');

                    resultStr += '<input type="radio" id="whichSeries" name="whichSeries" value="' + whichSeries.replace(/"/g, '') + '"' + checked + ' /> ';
                    if (data.langid && data.langid !== '' && obj[1] === 1) {
                        // For now only add the language id to the tvdb url, as the others might have different routes.
                        resultStr += '<a href="' + MEDUSA.config.anonRedirect + obj[2] + obj[3] + '&lid=' + data.langid + '" onclick="window.open(this.href, \'_blank\'); return false;" ><b>' + obj[4] + '</b></a>';
                    } else {
                        resultStr += '<a href="' + MEDUSA.config.anonRedirect + obj[2] + obj[3] + '" onclick="window.open(this.href, \'_blank\'); return false;" ><b>' + obj[4] + '</b></a>';
                    }

                    if (obj[5] !== null) {
                        var startDate = new Date(obj[5]);
                        var today = new Date();
                        if (startDate > today) {
                            resultStr += ' (will debut on ' + obj[5] + ')';
                        } else {
                            resultStr += ' (started on ' + obj[5] + ')';
                        }
                    }

                    if (obj[0] !== null) {
                        resultStr += ' [' + obj[0] + ']';
                    }

                    resultStr += '<br>';
                });
                resultStr += '</ul>';
            }
            resultStr += '</fieldset>';
            $('#searchResults').html(resultStr);
            updateSampleText();
            myform.loadsection(0); // eslint-disable-line no-use-before-define
        });
    }

    $('#searchName').on('click', function () {
        searchIndexers();
    });

    if ($('#nameToSearch').length !== 0 && $('#nameToSearch').val().length !== 0) {
        $('#searchName').click();
    }

    $('#addShowButton').click(function () {
        // if they haven't picked a show don't let them submit
        if (!$('input:radio[name="whichSeries"]:checked').val() && $('input:hidden[name="whichSeries"]').val().length !== 0) {
            alert('You must choose a show to continue'); // eslint-disable-line no-alert
            return false;
        }
        generateBlackWhiteList(); // eslint-disable-line no-undef
        $('#addShowForm').submit();
    });

    $('#skipShowButton').click(function () {
        $('#skipShow').val('1');
        $('#addShowForm').submit();
    });

    $('#qualityPreset').on('change', function () {
        myform.loadsection(2); // eslint-disable-line no-use-before-define
    });

    /* jQuery Form to Form Wizard- (c) Dynamic Drive (www.dynamicdrive.com)
    *  This notice MUST stay intact for legal use
    *  Visit http://www.dynamicdrive.com/ for this script and 100s more. */

    function goToStep(num) {
        $('.step').each(function () {
            if ($.data(this, 'section') + 1 === num) {
                $(this).click();
            }
        });
    }

    $('#nameToSearch').focus();

    // @TODO we need to move to real forms instead of this
    var myform = new formtowizard({ // eslint-disable-line new-cap, no-undef
        formid: 'addShowForm',
        revealfx: ['slide', 500],
        oninit: function () {
            updateSampleText();
            if ($('input:hidden[name=whichSeries]').length !== 0 && $('#fullShowPath').length !== 0) {
                goToStep(3);
            }
        }
    });

    $('#rootDirText').change(updateSampleText);
    $('#searchResults').on('change', '#whichSeries', updateSampleText);

    $('#nameToSearch').keyup(function (event) {
        if (event.keyCode === 13) {
            $('#searchName').click();
        }
    });

    $('#anime').change(function () {
        updateSampleText();
        myform.loadsection(2);
    });

    $('#rootDirs').on('change', function () {
        updateSampleText();
    });
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

//# sourceMappingURL=new-show.js.map

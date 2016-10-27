MEDUSA.addShows.newShow = function() {
    function updateSampleText() {
        // if something's selected then we have some behavior to figure out

        var showName;
        var sepChar;
        // if they've picked a radio button then use that
        if ($('input:radio[name=whichSeries]:checked').length !== 0) {
            showName = $('input:radio[name=whichSeries]:checked').val().split('|')[4];
        } else if ($('input:hidden[name=whichSeries]').length !== 0 && $('input:hidden[name=whichSeries]').val().length !== 0) { // if we provided a show in the hidden field, use that
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
            }, function(data) {
                $('#displayText').html(sampleText.replace('||', data));
            });
        // if not then it's unknown
        } else {
            $('#displayText').html(sampleText.replace('||', '??'));
        }

        // also toggle the add show button
        if (
            ($('#rootDirs option:selected').length !== 0 ||
            ($('#fullShowPath').length !== 0 && $('#fullShowPath').val().length !== 0)) && // eslint-disable-line no-mixed-operators
            ($('input:radio[name=whichSeries]:checked').length !== 0) || // eslint-disable-line no-mixed-operators
            ($('input:hidden[name=whichSeries]').length !== 0 && $('input:hidden[name=whichSeries]').val().length !== 0)
        ) {
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
            error: function() {
                $('#searchResults').empty().html('search timed out, try again or try another indexer');
            },
            success: function(data) {
                var firstResult = true;
                var resultStr = '<fieldset>\n<legend class="legendStep">Search Results:</legend>\n';
                var checked = '';

                if (data.results.length === 0) {
                    resultStr += '<b>No results found, try a different search.</b>';
                } else {
                    $.each(data.results, function(index, obj) {
                        if (firstResult) {
                            checked = ' checked';
                            firstResult = false;
                        } else {
                            checked = '';
                        }

                        var whichSeries = obj.join('|');

                        resultStr += '<input type="radio" id="whichSeries" name="whichSeries" value="' + whichSeries.replace(/"/g, '') + '"' + checked + ' /> ';
                        if (data.langid && data.langid !== '') {
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
            }
        });
    }

    $('#searchName').on('click', function() {
        searchIndexers();
    });

    if ($('#nameToSearch').length !== 0 && $('#nameToSearch').val().length !== 0) {
        $('#searchName').click();
    }

    $('#addShowButton').click(function() {
        // if they haven't picked a show don't let them submit
        if (!$('input:radio[name="whichSeries"]:checked').val() && $('input:hidden[name="whichSeries"]').val().length !== 0) {
            alert('You must choose a show to continue'); // eslint-disable-line no-alert
            return false;
        }
        generateBlackWhiteList(); // eslint-disable-line no-undef
        $('#addShowForm').submit();
    });

    $('#skipShowButton').click(function() {
        $('#skipShow').val('1');
        $('#addShowForm').submit();
    });

    $('#qualityPreset').on('change', function() {
        myform.loadsection(2); // eslint-disable-line no-use-before-define
    });

    /* jQuery Form to Form Wizard- (c) Dynamic Drive (www.dynamicdrive.com)
    *  This notice MUST stay intact for legal use
    *  Visit http://www.dynamicdrive.com/ for this script and 100s more. */

    function goToStep(num) {
        $('.step').each(function() {
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
        oninit: function() {
            updateSampleText();
            if ($('input:hidden[name=whichSeries]').length !== 0 && $('#fullShowPath').length !== 0) {
                goToStep(3);
            }
        }
    });

    $('#rootDirText').change(updateSampleText);
    $('#searchResults').on('change', '#whichSeries', updateSampleText);

    $('#nameToSearch').keyup(function(event) {
        if (event.keyCode === 13) {
            $('#searchName').click();
        }
    });

    $('#anime').change(function() {
        updateSampleText();
        myform.loadsection(2);
    });
};

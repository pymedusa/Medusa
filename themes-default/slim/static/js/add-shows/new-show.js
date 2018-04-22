MEDUSA.addShows.newShow = function() {
    function updateSampleText() {
        // If something's selected then we have some behavior to figure out

        let showName;
        let sepChar;
        // If they've picked a radio button then use that
        if ($('input:radio[name=whichSeries]:checked').length !== 0) {
            showName = $('input:radio[name=whichSeries]:checked').val().split('|')[4];
        } else if ($('input:hidden[name=whichSeries]').length !== 0 && $('input:hidden[name=whichSeries]').val().length !== 0) { // If we provided a show in the hidden field, use that
            showName = $('#providedName').val();
        } else {
            showName = '';
        }
        $.updateBlackWhiteList(showName);
        let sampleText = 'Adding show <b>' + showName + '</b> into <b>';

        // If we have a root dir selected, figure out the path
        if ($('#rootDirs option:selected').length !== 0) {
            let rootDirectoryText = $('#rootDirs option:selected').val();
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

        // If we have a show name then sanitize and use it for the dir name
        if (showName.length > 0) {
            $.get('addShows/sanitizeFileName', {
                name: showName
            }, data => {
                $('#displayText').html(sampleText.replace('||', data));
            });
        // If not then it's unknown
        } else {
            $('#displayText').html(sampleText.replace('||', '??'));
        }

        // Also toggle the add show button
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

    let searchRequestXhr = null;
    function searchIndexers() {
        if ($('#nameToSearch').val().length === 0) {
            return;
        }

        if (searchRequestXhr) {
            searchRequestXhr.abort();
        }

        const searchingFor = $('#nameToSearch').val().trim() + ' on ' + $('#providedIndexer option:selected').text() + ' in ' + $('#indexerLangSelect').val();
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
            error() {
                $('#searchResults').empty().html('search timed out, try again or try another indexer');
            }
        }).done(data => {
            let firstResult = true;
            let resultStr = '<fieldset>\n<legend class="legendStep">Search Results:</legend>\n';
            let checked = '';

            if (data.results.length === 0) {
                resultStr += '<b>No results found, try a different search.</b>';
            } else {
                $.each(data.results, (index, obj) => {
                    if (firstResult) {
                        checked = ' checked';
                        firstResult = false;
                    } else {
                        checked = '';
                    }

                    const whichSeries = obj.join('|');

                    resultStr += '<input type="radio" id="whichSeries" name="whichSeries" value="' + whichSeries.replace(/"/g, '') + '"' + checked + ' /> ';
                    if (data.langid && data.langid !== '' && obj[1] === 1) { // For now only add the language id to the tvdb url, as the others might have different routes.
                        resultStr += '<a href="' + MEDUSA.config.anonRedirect + obj[2] + obj[3] + '&lid=' + data.langid + '" onclick="window.open(this.href, \'_blank\'); return false;" ><b>' + obj[4] + '</b></a>';
                    } else {
                        resultStr += '<a href="' + MEDUSA.config.anonRedirect + obj[2] + obj[3] + '" onclick="window.open(this.href, \'_blank\'); return false;" ><b>' + obj[4] + '</b></a>';
                    }

                    if (obj[5] !== null) {
                        const startDate = new Date(obj[5]);
                        const today = new Date();
                        if (startDate > today) {
                            resultStr += ' (will debut on ' + obj[5] + ' on ' + obj[6] + ')';
                        } else {
                            resultStr += ' (started on ' + obj[5] + ' on ' + obj[6] + ')';
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

    $('#searchName').on('click', () => {
        searchIndexers();
    });

    if ($('#nameToSearch').length !== 0 && $('#nameToSearch').val().length !== 0) {
        $('#searchName').click();
    }

    $('#addShowButton').click(() => {
        // If they haven't picked a show don't let them submit
        if (!$('input:radio[name="whichSeries"]:checked').val() && $('input:hidden[name="whichSeries"]').val().length === 0) {
            alert('You must choose a show to continue'); // eslint-disable-line no-alert
            return false;
        }
        generateBlackWhiteList(); // eslint-disable-line no-undef
        $('#addShowForm').submit();
    });

    $('#skipShowButton').click(() => {
        $('#skipShow').val('1');
        $('#addShowForm').submit();
    });

    /* JQuery Form to Form Wizard- (c) Dynamic Drive (www.dynamicdrive.com)
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
    const myform = new formtowizard({ // eslint-disable-line new-cap, no-undef
        formid: 'addShowForm',
        revealfx: ['slide', 500],
        oninit() {
            updateSampleText();
            if ($('input:hidden[name=whichSeries]').length !== 0 && $('#fullShowPath').length !== 0) {
                goToStep(3);
            }
        }
    });

    $('#rootDirText').change(updateSampleText);
    $('#searchResults').on('change', '#whichSeries', updateSampleText);

    $('#nameToSearch').keyup(event => {
        if (event.keyCode === 13) {
            $('#searchName').click();
        }
    });

    $('#anime').change(() => {
        updateSampleText();
        myform.loadsection(2);
    });

    $(document.body).on('change', 'select[name="quality_preset"]', () => {
        setTimeout(() => myform.loadsection(2), 100);
    });

    $('#rootDirs').on('change', () => {
        updateSampleText();
    });
};

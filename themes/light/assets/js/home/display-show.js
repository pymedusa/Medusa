MEDUSA.home.displayShow = function() { // eslint-disable-line max-lines
    $('.imdbPlot').on('click', function() {
        $(this).prev('span').toggle();
        if ($(this).html() === '..show less') {
            $(this).html('..show more');
        } else {
            $(this).html('..show less');
        }
        moveSummaryBackground();
        movecheckboxControlsBackground();
    });

    // Adjust the summary background position and size on page load and resize
    function moveSummaryBackground() {
        const height = $('#summary').height() + 10;
        const top = $('#summary').offset().top + 5;
        $('#summaryBackground').height(height);
        $('#summaryBackground').offset({ top, left: 0 });
        $('#summaryBackground').show();
    }

    function movecheckboxControlsBackground() {
        const height = $('#checkboxControls').height() + 10;
        const top = $('#checkboxControls').offset().top - 3;
        $('#checkboxControlsBackground').height(height);
        $('#checkboxControlsBackground').offset({ top, left: 0 });
        $('#checkboxControlsBackground').show();
    }

    $(window).resize(() => {
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

    startAjaxEpisodeSubtitles(); // eslint-disable-line no-undef
    $.ajaxEpSubtitlesSearch();
    $.ajaxEpRedownloadSubtitle();

    $('#seasonJump').on('change', function() {
        const id = $('#seasonJump option:selected').val();
        if (id && id !== 'jump') {
            const season = $('#seasonJump option:selected').data('season');
            $('html,body').animate({ scrollTop: $('[name="' + id.substring(1) + '"]').offset().top - 100 }, 'slow');
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

        $('.epCheck').each(function() {
            if (this.checked === true) {
                epArr.push($(this).attr('id'));
            }
        });

        if (epArr.length === 0) {
            return false;
        }

        window.location.href = $('base').attr('href') + 'home/setStatus?' +
            'indexername=' + $('#indexer-name').attr('value') +
            '&seriesid=' + $('#series-id').attr('value') +
            '&eps=' + epArr.join('|') +
            '&status=' + $('#statusSelect').val();
    });

    $('.seasonCheck').on('click', function() {
        const seasCheck = this;
        const seasNo = $(seasCheck).attr('id');

        $('#collapseSeason-' + seasNo).collapse('show');
        $('.epCheck:visible').each(function() {
            const epParts = $(this).attr('id').split('x');
            if (epParts[0] === seasNo) {
                this.checked = seasCheck.checked;
            }
        });
    });

    let lastCheck = null;
    $('.epCheck').on('click', function(event) {
        if (!lastCheck || !event.shiftKey) {
            lastCheck = this;
            return;
        }

        const check = this;
        let found = 0;

        $('.epCheck').each(function() {
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
        $('.epCheck:visible').each(function() {
            this.checked = true;
        });
        $('.seasonCheck:visible').each(function() {
            this.checked = true;
        });
    });

    // Clears all visible episode checkboxes and the season selectors
    $('.clearAll').on('click', () => {
        $('.epCheck:visible').each(function() {
            this.checked = false;
        });
        $('.seasonCheck:visible').each(function() {
            this.checked = false;
        });
    });

    // Handle the show selection dropbox
    $('#select-show').on('change', evt => {
        const selectedOption = evt.currentTarget.selectedOptions[0];
        const indexerName = $(selectedOption).attr('data-indexer-name');
        const seriesId = $(selectedOption).attr('data-series-id');
        if (seriesId === 0 || !indexerName) {
            return;
        }
        window.location.href = $('base').attr('href') + 'home/displayShow?indexername=' + indexerName + '&seriesid=' + seriesId;
    });

    // Show/hide different types of rows when the checkboxes are changed
    $('#checkboxControls input').on('change', function() {
        const whichClass = $(this).attr('id');
        $(this).showHideRows(whichClass);
    });

    // Initially show/hide all the rows according to the checkboxes
    $('#checkboxControls input').each(function() {
        const status = $(this).prop('checked');
        $('tr.' + $(this).attr('id')).each(function() {
            if (status) {
                $(this).show();
            } else {
                $(this).hide();
            }
        });
    });

    $.fn.showHideRows = function(whichClass) {
        const status = $('#checkboxControls > input, #' + whichClass).prop('checked');
        $('tr.' + whichClass).each(function() {
            if (status) {
                $(this).show();
            } else {
                $(this).hide();
            }
        });

        // Hide season headers with no episodes under them
        $('tr.seasonheader').each(function() {
            let numRows = 0;
            const seasonNo = $(this).attr('id');
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

    function setEpisodeSceneNumbering(forSeason, forEpisode, sceneSeason, sceneEpisode) {
        const indexerName = $('#indexer-name').val();
        const seriesId = $('#series-id').val();

        if (sceneSeason === '') {
            sceneSeason = null;
        }
        if (sceneEpisode === '') {
            sceneEpisode = null;
        }

        $.getJSON('home/setSceneNumbering', {
            indexername: indexerName,
            seriesid: seriesId,
            forSeason,
            forEpisode,
            sceneSeason,
            sceneEpisode
        }, data => {
            // Set the values we get back
            if (data.sceneSeason === null || data.sceneEpisode === null) {
                $('#sceneSeasonXEpisode_' + seriesId + '_' + forSeason + '_' + forEpisode).val('');
            } else {
                $('#sceneSeasonXEpisode_' + seriesId + '_' + forSeason + '_' + forEpisode).val(data.sceneSeason + 'x' + data.sceneEpisode);
            }
            if (!data.success) {
                if (data.errorMessage) {
                    alert(data.errorMessage); // eslint-disable-line no-alert
                } else {
                    alert('Update failed.'); // eslint-disable-line no-alert
                }
            }
        });
    }

    function setAbsoluteSceneNumbering(forAbsolute, sceneAbsolute) {
        const indexerName = $('#indexer-name').val();
        const seriesId = $('#series-id').val();

        if (sceneAbsolute === '') {
            sceneAbsolute = null;
        }

        $.getJSON('home/setSceneNumbering', {
            indexername: indexerName,
            seriesid: seriesId,
            forAbsolute,
            sceneAbsolute
        }, data => {
            // Set the values we get back
            if (data.sceneAbsolute === null) {
                $('#sceneAbsolute_' + seriesId + '_' + forAbsolute).val('');
            } else {
                $('#sceneAbsolute_' + seriesId + '_' + forAbsolute).val(data.sceneAbsolute);
            }

            if (!data.success) {
                if (data.errorMessage) {
                    alert(data.errorMessage); // eslint-disable-line no-alert
                } else {
                    alert('Update failed.'); // eslint-disable-line no-alert
                }
            }
        });
    }

    function setInputValidInvalid(valid, el) {
        if (valid) {
            $(el).css({
                'background-color': '#90EE90', // Green
                'color': '#FFF', // eslint-disable-line quote-props
                'font-weight': 'bold'
            });
            return true;
        }
        $(el).css({
            'background-color': '#FF0000', // Red
            'color': '#FFF!important', // eslint-disable-line quote-props
            'font-weight': 'bold'
        });
        return false;
    }

    $('.sceneSeasonXEpisode').on('change', function() {
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

    $('.sceneAbsolute').on('change', function() {
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

    $.fn.generateStars = function() {
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
        html: true, // Required if content has HTML
        content: '<div id="popover-target"></div>'
    }).on('shown.bs.popover', () => { // Bootstrap popover event triggered when the popover opens
        $.tablesorter.columnSelector.attachTo($('#showTable, #animeTable'), '#popover-target');
    });

    // Moved and rewritten this from displayShow. This changes the button when clicked for collapsing/expanding the
    // Season to Show Episodes or Hide Episodes.
    $(() => {
        $('.collapse.toggle').on('hide.bs.collapse', function() {
            const reg = /collapseSeason-(\d+)/g;
            const result = reg.exec(this.id);
            $('#showseason-' + result[1]).text('Show Episodes');
            $('#season-' + result[1] + '-cols').addClass('shadow');
        });
        $('.collapse.toggle').on('show.bs.collapse', function() {
            const reg = /collapseSeason-(\d+)/g;
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
        indexername: $('#indexer-name').val(),
        seriesid: $('#series-id').val() // eslint-disable-line camelcase
    }, data => {
        setSeasonSceneException(data);
    });

    $('.display-specials a').on('click', function() {
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

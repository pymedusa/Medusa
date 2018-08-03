<script>
import { api } from '../api';
import AppLink from './app-link.vue';
import PlotInfo from './plot-info.vue';

module.exports = {
    name: 'displayShow',
    template: '#display-show-template',
    components: {
        AppLink,
        PlotInfo
    },
    data() {
        return {};
    },
    mounted() {
        const {
            moveSummaryBackground,
            movecheckboxControlsBackground,
            setQuality,
            setEpisodeSceneNumbering,
            setAbsoluteSceneNumbering,
            setInputValidInvalid,
            setSeasonSceneException,
            showHideRows
        } = this;

        $(window).on('resize', () => {
            moveSummaryBackground();
            movecheckboxControlsBackground();
        });

        window.addEventListener('load', () => {
            // Adjust the summary background position and size
            window.dispatchEvent(new Event('resize'));

            $.ajaxEpSearch({
                colorRow: true
            });

            startAjaxEpisodeSubtitles(); // eslint-disable-line no-undef
            $.ajaxEpSubtitlesSearch();
            $.ajaxEpRedownloadSubtitle();
        });

        $(document.body).on('click', '.imdbPlot', event => {
            const $target = $(event.currentTarget);
            $target.prev('span').toggle();
            if ($target.html() === '..show less') {
                $target.html('..show more');
            } else {
                $target.html('..show less');
            }
            moveSummaryBackground();
            movecheckboxControlsBackground();
        });

        $(document.body).on('change', '#seasonJump', event => {
            const id = $('#seasonJump option:selected').val();
            if (id && id !== 'jump') {
                const season = $('#seasonJump option:selected').data('season');
                $('html,body').animate({ scrollTop: $('[name="' + id.substring(1) + '"]').offset().top - 100 }, 'slow');
                $('#collapseSeason-' + season).collapse('show');
                location.hash = id;
            }
            $(event.currentTarget).val('jump');
        });

        $(document.body).on('click', '#changeStatus', () => {
            const epArr = [];
            const status = $('#statusSelect').val();
            const quality = $('#qualitySelect').val();
            const seriesSlug = $('#series-slug').val();

            $('.epCheck').each((index, element) => {
                if (element.checked === true) {
                    epArr.push($(element).attr('id'));
                }
            });

            if (epArr.length === 0) {
                return false;
            }

            if (quality) {
                setQuality(quality, seriesSlug, epArr);
            }

            if (status) {
                window.location.href = $('base').attr('href') + 'home/setStatus?' +
                    'indexername=' + $('#indexer-name').attr('value') +
                    '&seriesid=' + $('#series-id').attr('value') +
                    '&eps=' + epArr.join('|') +
                    '&status=' + status;
            }
        });

        $(document.body).on('click', '.seasonCheck', event => {
            const seasCheck = event.currentTarget;
            const seasNo = $(seasCheck).attr('id');

            $('#collapseSeason-' + seasNo).collapse('show');
            const seasonIdentifier = 's' + seasNo;
            $('.epCheck:visible').each((index, element) => {
                const epParts = $(element).attr('id').split('e');
                if (epParts[0] === seasonIdentifier) {
                    element.checked = seasCheck.checked;
                }
            });
        });

        let lastCheck = null;
        $(document.body).on('click', '.epCheck', event => {
            const target = event.currentTarget;
            if (!lastCheck || !event.shiftKey) {
                lastCheck = target;
                return;
            }

            const check = target;
            let found = 0;

            $('.epCheck').each((index, element) => {
                if (found === 1) {
                    element.checked = lastCheck.checked;
                }

                if (found === 2) {
                    return false;
                }

                if (element === check || element === lastCheck) {
                    found++;
                }
            });
        });

        // Selects all visible episode checkboxes.
        $(document.body).on('click', '.seriesCheck', () => {
            $('.epCheck:visible').each((index, element) => {
                element.checked = true;
            });
            $('.seasonCheck:visible').each((index, element) => {
                element.checked = true;
            });
        });

        // Clears all visible episode checkboxes and the season selectors
        $(document.body).on('click', '.clearAll', () => {
            $('.epCheck:visible').each((index, element) => {
                element.checked = false;
            });
            $('.seasonCheck:visible').each((index, element) => {
                element.checked = false;
            });
        });

        // Show/hide different types of rows when the checkboxes are changed
        $(document.body).on('change', '#checkboxControls input', event => {
            const whichClass = $(event.currentTarget).attr('id');
            showHideRows(whichClass);
        });

        // Initially show/hide all the rows according to the checkboxes
        $('#checkboxControls input').each((index, element) => {
            const status = $(element).prop('checked');
            $('tr.' + $(element).attr('id')).each((index, tableRow) => {
                if (status) {
                    $(tableRow).show();
                } else {
                    $(tableRow).hide();
                }
            });
        });

        $(document.body).on('change', '.sceneSeasonXEpisode', event => {
            const target = event.currentTarget;
            // Strip non-numeric characters
            const value = $(target).val();
            $(target).val(value.replace(/[^0-9xX]*/g, ''));
            const forSeason = $(target).attr('data-for-season');
            const forEpisode = $(target).attr('data-for-episode');

            // If empty reset the field
            if (value === '') {
                setEpisodeSceneNumbering(forSeason, forEpisode, null, null);
                return;
            }

            const m = $(target).val().match(/^(\d+)x(\d+)$/i);
            const onlyEpisode = $(target).val().match(/^(\d+)$/i);
            let sceneSeason = null;
            let sceneEpisode = null;
            let isValid = false;
            if (m) {
                sceneSeason = m[1];
                sceneEpisode = m[2];
                isValid = setInputValidInvalid(true, $(target));
            } else if (onlyEpisode) {
                // For example when '5' is filled in instead of '1x5', asume it's the first season
                sceneSeason = forSeason;
                sceneEpisode = onlyEpisode[1];
                isValid = setInputValidInvalid(true, $(target));
            } else {
                isValid = setInputValidInvalid(false, $(target));
            }

            if (isValid) {
                setEpisodeSceneNumbering(forSeason, forEpisode, sceneSeason, sceneEpisode);
            }
        });

        $(document.body).on('change', '.sceneAbsolute', event => {
            const target = event.currentTarget;
            // Strip non-numeric characters
            $(target).val($(target).val().replace(/[^0-9xX]*/g, ''));
            const forAbsolute = $(target).attr('data-for-absolute');

            const m = $(target).val().match(/^(\d{1,3})$/i);
            let sceneAbsolute = null;
            if (m) {
                sceneAbsolute = m[1];
            }
            setAbsoluteSceneNumbering(forAbsolute, sceneAbsolute);
        });

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

        // Generate IMDB stars
        $('.imdbstars').each((index, element) => {
            $(element).html($('<span/>').width($(element).text() * 12));
        });
        attachImdbTooltip(); // eslint-disable-line no-undef

        // @TODO: OMG: This is just a basic json, in future it should be based on the CRUD route.
        // Get the season exceptions and the xem season mappings.
        $.getJSON('home/getSeasonSceneExceptions', {
            indexername: $('#indexer-name').val(),
            seriesid: $('#series-id').val() // eslint-disable-line camelcase
        }, data => {
            setSeasonSceneException(data);
        });

        $(document.body).on('click', '.display-specials a', event => {
            api.patch('config/main', {
                layout: {
                    show: {
                        specials: $(event.currentTarget).text() !== 'Hide'
                    }
                }
            }).then(response => {
                log.info(response.data);
                window.location.reload();
            }).catch(error => {
                log.error(error.data);
            });
        });
    },
    methods: {
        // Adjust the summary background position and size on page load and resize
        moveSummaryBackground() {
            const height = $('#summary').height() + 10;
            const top = $('#summary').offset().top + 5;
            $('#summaryBackground').height(height);
            $('#summaryBackground').offset({ top, left: 0 });
            $('#summaryBackground').show();
        },
        movecheckboxControlsBackground() {
            const height = $('#checkboxControls').height() + 10;
            const top = $('#checkboxControls').offset().top - 3;
            $('#checkboxControlsBackground').height(height);
            $('#checkboxControlsBackground').offset({ top, left: 0 });
            $('#checkboxControlsBackground').show();
        },
        setQuality(quality, seriesSlug, episodes) {
            const patchData = {};
            episodes.forEach(episode => {
                patchData[episode] = { quality: parseInt(quality, 10) };
            });

            api.patch('series/' + seriesSlug + '/episodes', patchData).then(response => {
                log.info(response.data);
                window.location.reload();
            }).catch(error => {
                log.error(error.data);
            });
        },
        setEpisodeSceneNumbering(forSeason, forEpisode, sceneSeason, sceneEpisode) {
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
        },
        setAbsoluteSceneNumbering(forAbsolute, sceneAbsolute) {
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
        },
        setInputValidInvalid(valid, el) {
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
        },
        // Set the season exception based on using the get_xem_numbering_for_show() for animes if available in data.xemNumbering,
        // or else try to map using just the data.season_exceptions.
        setSeasonSceneException(data) {
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
        },
        showHideRows(whichClass) {
            const status = $('#checkboxControls > input, #' + whichClass).prop('checked');
            $('tr.' + whichClass).each((index, element) => {
                if (status) {
                    $(element).show();
                } else {
                    $(element).hide();
                }
            });

            // Hide season headers with no episodes under them
            $('tr.seasonheader').each((index, element) => {
                let numRows = 0;
                const seasonNo = $(element).attr('id');
                $('tr.' + seasonNo + ' :visible').each(() => {
                    numRows++;
                });
                if (numRows === 0) {
                    $(element).hide();
                    $('#' + seasonNo + '-cols').hide();
                } else {
                    $(element).show();
                    $('#' + seasonNo + '-cols').show();
                }
            });
        }
    }
};
</script>

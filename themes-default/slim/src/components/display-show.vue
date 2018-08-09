<script>
import $ from 'jquery';
import { mapState, mapGetters } from 'vuex';
import { api } from '../api';
import AppLink from './app-link.vue';
import PlotInfo from './plot-info.vue';

export default {
    name: 'displayShow',
    template: '#display-show-template',
    components: {
        AppLink,
        PlotInfo
    },
    data() {
        return {};
    },
    computed: {
        ...mapState({
            shows: state => state.shows.shows
        }),
        ...mapGetters([
            'getShowById'
        ]),
        indexer() {
            return this.$route.query.indexername;
        },
        id() {
            return this.$route.query.seriesid;
        },
        show() {
            const { indexer, id, getShowById, shows, $store } = this;
            const { defaults } = $store.state;

            if (shows.length === 0 || !indexer || !id) {
                return defaults.show;
            }

            const show = getShowById({ indexer, id });
            if (!show) {
                return defaults.show;
            }

            return show;
        }
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
            const target = event.currentTarget;
            $(target).prev('span').toggle();
            if (target.innerHTML === '..show less') {
                target.innerHTML = '..show more';
            } else {
                target.innerHTML = '..show less';
            }
            moveSummaryBackground();
            movecheckboxControlsBackground();
        });

        $(document.body).on('change', '#seasonJump', event => {
            const element = event.currentTarget;
            const selectedOption = element.options[element.selectedIndex];
            const id = selectedOption.value;
            if (id && id !== 'jump') {
                const { season } = selectedOption.dataset;
                const seasonHeader = document.querySelector('[name="' + id.substring(1) + '"]');
                $('html,body').animate({ scrollTop: $(seasonHeader).offset().top - 100 }, 'slow');
                $(`#collapseSeason-${season}`).collapse('show');
                location.hash = id;
            }
            element.value = 'jump';
        });

        $(document.body).on('click', '#changeStatus', () => {
            const epArr = [];
            const status = document.querySelector('#statusSelect').value;
            const quality = document.querySelector('#qualitySelect').value;
            const showSlug = document.querySelector('#series-slug').value;

            document.querySelectorAll('.epCheck').forEach(element => {
                if (element.checked === true) {
                    epArr.push(element.getAttribute('id'));
                }
            });

            if (epArr.length === 0) {
                return false;
            }

            if (quality) {
                setQuality(quality, showSlug, epArr);
            }

            if (status) {
                const base = document.getElementsByTagName('base')[0].getAttribute('href');
                const indexerName = document.querySelector('#indexer-name').value;
                const seriesId = document.querySelector('#series-id').value;
                window.location.href = `${base}home/setStatus?` +
                    `indexername=${indexerName}&seriesid=${seriesId}` +
                    `&eps=${epArr.join('|')}&status=${status}`;
            }
        });

        $(document.body).on('click', '.seasonCheck', event => {
            const seasCheck = event.currentTarget;
            const seasNo = seasCheck.getAttribute('id');

            $(`#collapseSeason-${seasNo}`).collapse('show');
            const seasonIdentifier = `s${seasNo}`;
            // eslint-disable-next-line jquery/no-each, jquery/no-sizzle
            $('.epCheck:visible').each((index, element) => {
                const epParts = element.getAttribute('id').split('e');
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

            document.querySelectorAll('.epCheck').forEach(element => {
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
            // eslint-disable-next-line jquery/no-each, jquery/no-sizzle
            $('.epCheck:visible').each((index, element) => {
                element.checked = true;
            });
            // eslint-disable-next-line jquery/no-each, jquery/no-sizzle
            $('.seasonCheck:visible').each((index, element) => {
                element.checked = true;
            });
        });

        // Clears all visible episode checkboxes and the season selectors
        $(document.body).on('click', '.clearAll', () => {
            // eslint-disable-next-line jquery/no-each, jquery/no-sizzle
            $('.epCheck:visible').each((index, element) => {
                element.checked = false;
            });
            // eslint-disable-next-line jquery/no-each, jquery/no-sizzle
            $('.seasonCheck:visible').each((index, element) => {
                element.checked = false;
            });
        });

        // Show/hide different types of rows when the checkboxes are changed
        $(document.body).on('change', '#checkboxControls input', event => {
            const whichClass = event.currentTarget.getAttribute('id');
            showHideRows(whichClass);
        });

        // Initially show/hide all the rows according to the checkboxes
        document.querySelectorAll('#checkboxControls input').forEach(element => {
            const status = element.checked;
            const id = element.getAttribute('id');
            document.querySelectorAll(`tr.${id}`).forEach(tableRow => {
                if (status) {
                    $(tableRow).show(); // eslint-disable-line jquery/no-show
                } else {
                    $(tableRow).hide(); // eslint-disable-line jquery/no-hide
                }
            });
        });

        $(document.body).on('change', '.sceneSeasonXEpisode', event => {
            const target = event.currentTarget;
            // Strip non-numeric characters
            const { value } = target;
            target.value = value.replace(/[^0-9xX]*/g, '');
            const { forSeason, forEpisode } = target.dataset;

            // If empty reset the field
            if (value === '') {
                setEpisodeSceneNumbering(forSeason, forEpisode, null, null);
                return;
            }

            const m = target.value.match(/^(\d+)x(\d+)$/i);
            const onlyEpisode = target.value.match(/^(\d+)$/i);
            let sceneSeason = null;
            let sceneEpisode = null;
            let isValid = false;
            if (m) {
                sceneSeason = m[1];
                sceneEpisode = m[2];
                isValid = setInputValidInvalid(true, target);
            } else if (onlyEpisode) {
                // For example when '5' is filled in instead of '1x5', asume it's the first season
                sceneSeason = forSeason;
                sceneEpisode = onlyEpisode[1];
                isValid = setInputValidInvalid(true, target);
            } else {
                isValid = setInputValidInvalid(false, target);
            }

            if (isValid) {
                setEpisodeSceneNumbering(forSeason, forEpisode, sceneSeason, sceneEpisode);
            }
        });

        $(document.body).on('change', '.sceneAbsolute', event => {
            const target = event.currentTarget;
            // Strip non-numeric characters
            target.value = target.value.replace(/[^0-9xX]*/g, '');
            const { forAbsolute } = target.dataset;

            const m = target.value.match(/^(\d{1,3})$/i);
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
            document.querySelector(`#showseason-${result[1]}`).textContent = 'Show Episodes';
            $('#season-' + result[1] + '-cols').addClass('shadow');
        });
        $('.collapse.toggle').on('show.bs.collapse', function() {
            const reg = /collapseSeason-(\d+)/g;
            const result = reg.exec(this.id);
            document.querySelector(`#showseason-${result[1]}`).textContent = 'Hide Episodes';
            $('#season-' + result[1] + '-cols').removeClass('shadow');
        });

        // Generate IMDB stars
        document.querySelectorAll('.imdbstars').forEach(element => {
            const rating = document.createElement('span');
            rating.style.width = `${element.textContent * 12}px`;
            element.innerHTML = rating.outerHTML;
        });
        // From rating-tooltip.js
        attachImdbTooltip(); // eslint-disable-line no-undef

        // @TODO: OMG: This is just a basic json, in future it should be based on the CRUD route.
        // Get the season exceptions and the xem season mappings.
        $.getJSON('home/getSeasonSceneExceptions', {
            indexername: document.querySelector('#indexer-name').value,
            seriesid: document.querySelector('#series-id').value
        }, data => {
            setSeasonSceneException(data);
        });

        $(document.body).on('click', '.display-specials a', event => {
            api.patch('config/main', {
                layout: {
                    show: {
                        specials: event.currentTarget.textContent !== 'Hide'
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
        setQuality(quality, showSlug, episodes) {
            const patchData = {};
            episodes.forEach(episode => {
                patchData[episode] = { quality: parseInt(quality, 10) };
            });

            api.patch('series/' + showSlug + '/episodes', patchData).then(response => {
                log.info(response.data);
                window.location.reload();
            }).catch(error => {
                log.error(error.data);
            });
        },
        setEpisodeSceneNumbering(forSeason, forEpisode, sceneSeason, sceneEpisode) {
            const indexerName = document.querySelector('#indexer-name').value;
            const seriesId = document.querySelector('#series-id').value;

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
                const element = document.querySelector(`#sceneSeasonXEpisode_${seriesId}_${forSeason}_${forEpisode}`);
                if (data.sceneSeason === null || data.sceneEpisode === null) {
                    element.value = '';
                } else {
                    const { sceneSeason, sceneEpisode } = data;
                    element.value = `${sceneSeason}x${sceneEpisode}`;
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
            const indexerName = document.querySelector('#indexer-name').value;
            const seriesId = document.querySelector('#series-id').value;

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
                const element = document.querySelector(`#sceneAbsolute_${seriesId}_${forAbsolute}`);
                if (data.sceneAbsolute === null) {
                    element.value = '';
                } else {
                    element.value = data.sceneAbsolute;
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
            const { seasonExceptions, xemNumbering } = data;
            for (const [season, nameExceptions] of Object.entries(seasonExceptions)) {
                let foundInXem = false;
                // Check if it is a season name exception, we don't handle the show name exceptions here
                if (season >= 0) {
                    // Loop through the xem mapping, and check if there is a xem_season, that needs to show the season name exception
                    for (const [indexerSeason, xemSeason] of Object.entries(xemNumbering)) {
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
                    }

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
            }
        },
        showHideRows(whichClass) {
            const status = $(`#checkboxControls > input, #${whichClass}`)[0].checked;
            document.querySelectorAll(`tr.${whichClass}`).forEach(element => {
                if (status) {
                    $(element).show(); // eslint-disable-line jquery/no-show
                } else {
                    $(element).hide(); // eslint-disable-line jquery/no-hide
                }
            });

            // Hide season headers with no episodes under them
            document.querySelectorAll('tr.seasonheader').forEach(element => {
                let numRows = 0;
                const seasonNo = element.getAttribute('id');
                // eslint-disable-next-line jquery/no-each, jquery/no-sizzle
                $(`tr.${seasonNo} :visible`).each(() => {
                    numRows++;
                });
                if (numRows === 0) {
                    $(element).hide();
                    $('#' + seasonNo + '-cols').hide(); // eslint-disable-line jquery/no-hide
                } else {
                    $(element).show();
                    $('#' + seasonNo + '-cols').show(); // eslint-disable-line jquery/no-show
                }
            });
        }
    }
};
</script>

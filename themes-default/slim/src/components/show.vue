<script>
import { isVisible } from 'is-visible';
import { scrollTo } from 'vue-scrollto';
import { mapState, mapGetters } from 'vuex';
import { api, apiRoute } from '../api';
import { AppLink, PlotInfo } from './helpers';

export default {
    name: 'show',
    template: '#show-template',
    components: {
        AppLink,
        PlotInfo
    },
    metaInfo() {
        if (!this.show || !this.show.title) {
            return {
                title: 'Medusa'
            };
        }
        const { title } = this.show;
        return {
            title,
            titleTemplate: '%s | Medusa'
        };
    },
    props: {
        /**
         * Show id
         */
        showId: {
            type: Number
        },
        /**
         * Show indexer
         */
        showIndexer: {
            type: String
        }
    },
    data() {
        return {
            jumpToSeason: 'jump',
            show: {
                airs: null,
                akas: null,
                cache: null,
                classification: null,
                config: {
                    airByDate: null,
                    aliases: null,
                    anime: null,
                    defaultEpisodeStatus: null,
                    dvdOrder: null,
                    location: null,
                    paused: null,
                    qualities: null,
                    release: null,
                    scene: null,
                    seasonFolders: null,
                    sports: null,
                    subtitlesEnabled: null,
                    airdateOffset: null
                },
                countries: null,
                country_codes: null, // eslint-disable-line camelcase
                genres: null,
                id: {
                    tvdb: null,
                    slug: null
                },
                indexer: null,
                language: null,
                network: null,
                nextAirDate: null,
                plot: null,
                rating: {
                    imdb: {
                        rating: null,
                        votes: null
                    }
                },
                runtime: null,
                showType: null,
                status: null,
                title: null,
                type: null,
                year: {}
            },
            shows: []
        };
    },
    computed: {
        ...mapState({
            stateShows: state => state.shows.shows,
            indexerConfig: state => state.config.indexers.config.indexers
        }),
        ...mapGetters([
            'getShowById'
        ]),
        indexer() {
            return this.showIndexer || this.$route.query.indexername;
        },
        id() {
            return this.showId || this.$route.query.seriesid;
        },
        showIndexerUrl() {
            const { show, indexerConfig } = this;
            const id = show.id[show.indexer];
            const indexerUrl = indexerConfig[show.indexer].showUrl;

            return `${indexerUrl}${id}`;
        }
    },
    mounted() {
        const {
            setQuality,
            setEpisodeSceneNumbering,
            setAbsoluteSceneNumbering,
            setInputValidInvalid,
            getSeasonSceneExceptions,
            showHideRows
        } = this;

        this.$watch('show', () => {
            this.$nextTick(() => this.reflowLayout());
        });

        ['load', 'resize'].map(event => {
            return window.addEventListener(event, () => {
                this.reflowLayout();
            });
        });

        window.addEventListener('load', () => {
            $.ajaxEpSearch({
                colorRow: true
            });

            startAjaxEpisodeSubtitles(); // eslint-disable-line no-undef
            $.ajaxEpSubtitlesSearch();
            $.ajaxEpRedownloadSubtitle();
        });

        $(document.body).on('click', '#changeStatus', () => {
            const epArr = [];
            const status = $('#statusSelect').val();
            const quality = $('#qualitySelect').val();
            const showSlug = $('#series-slug').val();

            $('.epCheck').each((index, element) => {
                if (element.checked === true) {
                    epArr.push($(element).attr('id'));
                }
            });

            if (epArr.length === 0) {
                return false;
            }

            if (quality) {
                setQuality(quality, showSlug, epArr);
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

        // Selects all visible episode checkboxes
        document.addEventListener('click', event => {
            if (event.target && event.target.className.includes('seriesCheck')) {
                [...document.querySelectorAll('.epCheck, .seasonCheck')].filter(isVisible).forEach(element => {
                    element.checked = true;
                });
            }
        });

        // Clears all visible episode checkboxes and the season selectors
        document.addEventListener('click', event => {
            if (event.target && event.target.className.includes('clearAll')) {
                [...document.querySelectorAll('.epCheck, .seasonCheck')].filter(isVisible).forEach(element => {
                    element.checked = false;
                });
            }
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

        // Changes the button when clicked for collapsing/expanding the season to show/hide episodes
        document.querySelectorAll('.collapse.toggle').forEach(element => {
            element.addEventListener('hide.bs.collapse', () => {
                // On hide
                const reg = /collapseSeason-(\d+)/g;
                const result = reg.exec(this.id);
                $('#showseason-' + result[1]).text('Show Episodes');
                $('#season-' + result[1] + '-cols').addClass('shadow');
            });
            element.addEventListener('show.bs.collapse', () => {
                // On show
                const reg = /collapseSeason-(\d+)/g;
                const result = reg.exec(this.id);
                $('#showseason-' + result[1]).text('Hide Episodes');
                $('#season-' + result[1] + '-cols').removeClass('shadow');
            });
        });

        // Get the season exceptions and the xem season mappings.
        getSeasonSceneExceptions();

        $(document.body).on('click', '.display-specials a', event => {
            api.patch('config/main', {
                layout: {
                    show: {
                        specials: $(event.currentTarget).text() !== 'Hide'
                    }
                }
            }).then(response => {
                console.info(response.data);
                window.location.reload();
            }).catch(error => {
                console.error(error.data);
            });
        });
    },
    methods: {
        /**
         * Attaches imdb tool tip,
         * moves summary background and checkbox controls
         */
        reflowLayout() {
            console.debug('Reflowing layout');

            this.$nextTick(() => {
                this.moveSummaryBackground();
                this.movecheckboxControlsBackground();
            });

            attachImdbTooltip(); // eslint-disable-line no-undef
        },
        /**
         * Adjust the summary background position and size on page load and resize
         */
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
                console.info(response.data);
                window.location.reload();
            }).catch(error => {
                console.error(error.data);
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
        // @TODO: OMG: This is just a basic json, in future it should be based on the CRUD route.
        // Get the season exceptions and the xem season mappings.
        getSeasonSceneExceptions() {
            const { indexer, id } = this;

            if (!indexer || !id) {
                console.warn('Unable to get season scene exceptions: Unknown series identifier');
                return;
            }

            apiRoute.get('home/getSeasonSceneExceptions', {
                params: {
                    indexername: indexer,
                    seriesid: id
                }
            }).then(response => {
                this.setSeasonSceneExceptions(response.data);
            }).catch(error => {
                console.error('Error getting season scene exceptions', error);
            });
        },
        // Set the season exception based on using the get_xem_numbering_for_show() for animes if available in data.xemNumbering,
        // or else try to map using just the data.season_exceptions.
        setSeasonSceneExceptions(data) {
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
        },
        toggleSpecials() {
            this.$store.dispatch('setConfig', {
                layout: {
                    show: {
                        specials: !this.config.layout.show.specials
                    }
                }
            });
        },
        reverse(array) {
            return array ? array.slice().reverse() : [];
        },
        dedupeGenres(genres) {
            return genres ? [...new Set(genres.slice(0).map(genre => genre.replace('-', ' ')))] : [];
        },
        getShow() {
            const { indexer, id, getShowById, shows, $store } = this;
            const { defaults } = $store.state;

            // Added the log, to see when this computed is accessed.
            console.log(`getting show info for: ${id}`);

            if (shows.length === 0 || !indexer || !id) {
                return defaults.show;
            }

            const show = getShowById({ indexer, id });
            if (!show) {
                return defaults.show;
            }

            // Not detailed
            // Retreive episode and season summary information
            if (!show.seasons) {
                $store.dispatch('getShow', { id, indexer, detailed: true });
                return getShowById({ indexer, id });
            }

            this.show = show;
        }
    },
    watch: {
        jumpToSeason(season) {
            // Don't jump until an option is selected
            if (season !== 'jump') {
                console.debug(`Jumping to ${season}`);

                scrollTo(season, 100, {
                    container: 'body',
                    easing: 'ease-in',
                    offset: -100
                });

                // Update URL hash
                location.hash = season;

                // Reset jump
                this.jumpToSeason = 'jump';
            }
        },
        stateShows: {
            handler: function(after, before) { // eslint-disable-line object-shorthand, no-unused-vars
                this.shows = after;

                if (after.filter(show => show.id[this.indexer] === Number(this.id)).length > 0) {
                    this.getShow();
                }
            },
            deep: true
        }
    }
};
</script>

<style>

</style>

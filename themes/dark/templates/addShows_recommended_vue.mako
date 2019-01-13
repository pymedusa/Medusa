<%inherit file="/layouts/main.mako"/>
<%block name="scripts">
<script>
const IMDB = 10;
const ANIDB = 11;
const TRAKT = 12;
window.app = {};
window.app = new Vue({
    store,
    router,
    el: '#vue-wrap',
    data() {
        const externals = {
            IMDB: 10,
            ANIDB: 11,
            TRAKT: 12
        };
        const sortOptions = [
            { text: 'Name', value: 'name' },
            { text: 'Original', value: 'original' },
            { text: 'Votes', value: 'votes' },
            { text: '% Rating', value: 'rating' },
            { text: '% Rating > Votes', value: 'rating_votes' },
        ]
        const sortDirectionOptions = [
            { text: 'Ascending', value: 'asc'},
            { text: 'Descending', value: 'desc'},
        ]
        return {
            externals,
            sortOptions,
            sortDirectionOptions,
            sortOptionsValue: 'original',
            sortDirectionOptionsValue: 'desc',
            configLoaded: false,
            rootDirs: [],
            enableShowOptions: false,
            selectedShowOptions: {
                subtitles: null,
                status: null,
                statusAfter: null,
                seasonFolders: null,
                anime: null,
                scene: null,
                release: {
                    blacklist: [],
                    whitelist: []
                },
                quality: {
                    allowed: [],
                    preferred: []
                }
            },
            options: [
                { text: 'Anidb', value: externals.ANIDB },
                { text: 'IMDB', value: externals.IMDB },
                { text: 'Trakt', value: externals.TRAKT },
                { text: 'all', value: -1 }
            ],
            selectedList: 11,
            shows: [],
            // trakt thing
            removedFromMedusa: [],
            
            // Isotope stuff
            selected: null,
            option: {
                getSortData: {
                    id: 'seriesId',
                    title: function(itemElem) {
                        return itemElem.title.toLowerCase();
                    },
                    rating: 'rating',
                    votes: 'votes'
                },
                sortBy : 'votes',
                layoutMode: 'fitRows',
                sortAscending: false
            },
            imgLazyLoad: new LazyLoad({
                // Example of options object -> see options section
                threshold: 500
            }),
            
        };
    },
    created() {
        const { $store, imgLazyLoad } = this;
        $store.dispatch('getRecommendedShows').then(() =>{
            this.$nextTick(() => {
                // This is needed for now.
                imgLazyLoad.update();
                imgLazyLoad.handleScroll();
            });
        })
    },
    mounted() {
        // jquery

        // init
        $('#tabs').tabs({
            collapsible: true,
            selected: (MEDUSA.config.sortArticle ? -1 : 0)
        });

        $.initRemoteShowGrid = function() {
            // Set defaults on page load
            imgLazyLoad.update();
            imgLazyLoad.handleScroll();
            $('#showsort').val('original');
            $('#showsortdirection').val('asc');

            // Sorts the shows (Original, name, votes, etc.)
            // Remove! Moved to vue.
            $('#showsort').on('change', function() {
                let sortCriteria;
                switch (this.value) {
                    case 'original':
                        sortCriteria = 'original-order';
                        break;
                    case 'rating':
                        /* Randomise, else the rating_votes can already
                        * have sorted leaving this with nothing to do.
                        */
                        $('#container').isotope({ sortBy: 'random' });
                        sortCriteria = 'rating';
                        break;
                    case 'rating_votes':
                        sortCriteria = ['rating', 'votes'];
                        break;
                    case 'votes':
                        sortCriteria = 'votes';
                        break;
                    default:
                        sortCriteria = 'name';
                        break;
                }
                $('#container').isotope({
                    sortBy: sortCriteria
                });
            });

            $(document.body).on('change', '#rootDirs', () => {
                $.rootDirCheck();
            });

            $('#showsortdirection').on('change', function() {
                $('#container').isotope({
                    sortAscending: (this.value === 'asc')
                });
            });

            $('#container').isotope({
                sortBy: 'original-order',
                layoutMode: 'fitRows',
                getSortData: {
                    name(itemElem) {
                        const name = $(itemElem).attr('data-name') || '';
                        return (MEDUSA.config.sortArticle ? name : name.replace(/^((?:The|A|An)\s)/i, '')).toLowerCase();
                    },
                    rating: '[data-rating] parseInt',
                    votes: '[data-votes] parseInt'
                }
            }).on('layoutComplete arrangeComplete removeComplete', () => {
                imgLazyLoad.update();
                imgLazyLoad.handleScroll();
            });
        };

        /*
        * Blacklist a show by series id.
        * Used by trakt.
        * @TODO: convert to vue method
        */
        $.initBlackListShowById = function() {
            $(document.body).on('click', 'button[data-blacklist-show]', function(e) {
                e.preventDefault();

                if ($(this).is(':disabled')) {
                    return false;
                }

                $(this).html('Blacklisted').prop('disabled', true);
                $(this).parent().find('button[data-add-show]').prop('disabled', true);

                $.get('addShows/addShowToBlacklist?seriesid=' + $(this).attr('data-indexer-id'));
                return false;
            });
        };

        $.updateBlackWhiteList = function(showName) {
            $('#white').children().remove();
            $('#black').children().remove();
            $('#pool').children().remove();

            if ($('#anime').prop('checked') && showName) {
                $('#blackwhitelist').show();
                if (showName) {
                    $.getJSON('home/fetch_releasegroups', {
                        series_name: showName // eslint-disable-line camelcase
                    }, data => {
                        if (data.result === 'success') {
                            $.each(data.groups, (i, group) => {
                                const option = $('<option>');
                                option.prop('value', group.name);
                                option.html(group.name + ' | ' + group.rating + ' | ' + group.range);
                                option.appendTo('#pool');
                            });
                        }
                    });
                }
            } else {
                $('#blackwhitelist').hide();
            }
        };

        $.rootDirCheck = function() {
            if ($('#rootDirs option:selected').length === 0) {
                $('button[data-add-show]').prop('disabled', true);
                if (!$('#configure_show_options').is(':checked')) {
                    $('#configure_show_options').prop('checked', true);
                    $('#content_configure_show_options').fadeIn('fast', 'linear');
                }
                if ($('#rootDirAlert').length === 0) {
                    $('#content-row').before('<div id="rootDirAlert"><div class="text-center">' +
                    '<div class="alert alert-danger upgrade-notification hidden-print role="alert">' +
                    '<strong>ERROR!</strong> Unable to add recommended shows.  Please set a default directory first.' +
                    '</div></div></div>');
                } else {
                    $('#rootDirAlert').show();
                }
            } else {
                $('#rootDirAlert').hide();
                $('button[data-add-show]').prop('disabled', false);
            }
        };
        
        // recommended shows
        // Initialise combos for dirty page refreshes
        $('#showsort').val('original');
        $('#showsortdirection').val('asc');

        // Isotope for trakt recommended shows.
        // Remove!
        const $container = [$('#container')];
        $.each($container, function() {
            this.isotope({
                itemSelector: '.trakt_show',
                sortBy: 'original-order',
                layoutMode: 'fitRows',
                getSortData: {
                    name(itemElem) {
                        const name = $(itemElem).attr('data-name') || '';
                        return (MEDUSA.config.sortArticle ? name : name.replace(/^(The|A|An)\s/i, '')).toLowerCase(); // eslint-disable-line no-undef
                    },
                    rating: '[data-rating] parseInt',
                    votes: '[data-votes] parseInt'
                }
            });
        });

        // Move to vue.
        $('#showsort').on('change', function() {
            let sortCriteria;
            switch (this.value) {
                case 'original':
                    sortCriteria = 'original-order';
                    break;
                case 'rating':
                    /* Randomise, else the rating_votes can already
                    * have sorted leaving this with nothing to do.
                    */
                    $('#container').isotope({ sortBy: 'random' });
                    sortCriteria = 'rating';
                    break;
                case 'rating_votes':
                    sortCriteria = ['rating', 'votes'];
                    break;
                case 'votes':
                    sortCriteria = 'votes';
                    break;
                default:
                    sortCriteria = 'name';
                    break;
            }
            $('#container').isotope({
                sortBy: sortCriteria
            });
        });

        $('#showsortdirection').on('change', function() {
            $('#container').isotope({
                sortAscending: (this.value === 'asc')
            });
        });
        
        // trending shows
        // Cleanest way of not showing the black/whitelist, when there isn't a show to show it for
        // Cleanest way of not showing the black/whitelist, when there isn't a show to show it for
        // $.updateBlackWhiteList(undefined);
        // $('#trendingShows').loadRemoteShows(
        //     'addShows/getTrendingShows/?traktList=' + $('#traktList').val(),
        //     'Loading trending shows...',
        //     'Trakt timed out, refresh page to try again'
        // );

        // $('#traktlistselection').on('change', e => {
        //     const traktList = e.target.value;
        //     window.history.replaceState({}, document.title, 'addShows/trendingShows/?traktList=' + traktList);
        //     // Update the jquery tab hrefs, when switching trakt list.
        //     $('#trakt-tab-1').attr('href', document.location.href.split('=')[0] + '=' + e.target.value);
        //     $('#trakt-tab-2').attr('href', document.location.href.split('=')[0] + '=' + e.target.value);
        //     $('#trendingShows').loadRemoteShows(
        //         'addShows/getTrendingShows/?traktList=' + traktList,
        //         'Loading trending shows...',
        //         'Trakt timed out, refresh page to try again'
        //     );
        //     $('h1.header').text('Trakt ' + $('option[value="' + e.target.value + '"]')[0].innerText);
        // });

        // $.initAddShowById();
        // $.initBlackListShowById();
        // $.rootDirCheck();

        // // popular shows
        // $.initRemoteShowGrid();
        // $.rootDirCheck();


        // The real vue stuff
        // This is used to wait for the config to be loaded by the store.
        this.$once('loaded', () => {
            const { stateShows, shows } = this;

            // Map the state values to local data.
            this.shows = stateShows;
            this.configLoaded = true;
        });


    },
    computed: {
        stateShows() {
            const { $store } = this;
            // @omg, I need to use recommended.recommended here, but don't know why?
            return $store.state.recommended.shows;
        },
        filteredShowsByList() {
            const { shows, selectedList, imgLazyLoad } = this;

            if (selectedList === -1) {
                return shows;
            }

            this.$nextTick(() => {
                // This is needed for now.
                imgLazyLoad.update();
                imgLazyLoad.handleScroll();
            });
            return shows.filter(show => show.source === selectedList);
        }
    },
    methods: {
        changeRecommendedList() {
            const { $store, shows } = this;

        },
        containerClass(show) {
            let classes = 'recommended-container default-poster show-row';
            const { removedFromMedusa } = this;
            if (show.showInLibrary || removedFromMedusa.includes(show.mappedSeriesId)) {
                classes += ' show-in-list';
            }
            return classes;
        },
        isotopeLayout(evt) {
            console.log('isotope Layout loaded');
            imgLazyLoad.update();
            imgLazyLoad.handleScroll();
        },
        addShowById(show, indexer) {
            console.log('adding show by id');
            const { enableShowOptions, selectedShowOptions, $store } = this;
            const { mappedIndexerName, mappedSeriesId } = show
            const selectedIndexer = this.$refs[indexer][0].selectedOptions[0].value;            
            debugger;
            let showId = { [mappedIndexerName]: mappedSeriesId };
            if (Object.keys(show.externals).length !== 0 && show.externals[selectedIndexer + '_id']) {
                showId = { [selectedIndexer]: show.externals[selectedIndexer + '_id'] };
            }
            
            options = { id: showId };

            if (enableShowOptions) {
                options = Object.assign({}, options, { options: selectedShowOptions });
            }

            $store.dispatch('addShow', options).then(() => {
                this.$snotify.success(
                    'Added new show to library',
                    'Saved',
                    { timeout: 20000 }
                );
                show.showInLibrary = true;
                debugger;
            }).catch(() => {
                this.$snotify.error(
                    'Error while trying to add new show',
                    'Error'
                );
            });

        },
        updateOptions(options) {
            // Update seleted options from add-show-options.vue @change event.
            const { anime, scene, seasonFolders, status, subtitles, statusAfter, seasonFolder, release, quality } = options;
            const { blacklist, whitelist } = release;
            const { allowed, preferred } = quality;

            this.selectedShowOptions.subtitles = subtitles;
            this.selectedShowOptions.status = status;
            this.selectedShowOptions.statusAfter = statusAfter;
            this.selectedShowOptions.seasonFolders = seasonFolders;
            this.selectedShowOptions.anime = anime;
            this.selectedShowOptions.scene = scene;
            this.selectedShowOptions.release.blacklist = blacklist;
            this.selectedShowOptions.release.whitelist = whitelist;
            this.selectedShowOptions.quality.allowed = allowed;
            this.selectedShowOptions.quality.preferred = preferred;
        },
        sort() {
            const mapped = {
                original: 'original-order',
                rating: 'rating',
                votes: 'votes',
                name: 'title',
                rating_votes: ['rating', 'votes']
            }
            const { option: isotopeOptions, sortOptionsValue } = this;
            this.option.sortBy = mapped[sortOptionsValue];
            this.$refs.filteredShows.arrange(isotopeOptions);
        },
        sortDirection() {
            const { option: isotopeOptions, sortDirectionOptionsValue } = this;
            this.option.sortAscending = sortDirectionOptionsValue === 'asc';
            this.$refs.filteredShows.arrange(isotopeOptions);
        },
        addByExternalIndexer(show) {
            const { externals } = show;
            if (show.source === 11) {
                return [{text: 'Tvdb', value: 'tvdb_id'}]
            }
            
            let options = [];
            for (external in externals) {
                if (['tvdb_id', 'tmdb_id', 'tvmaze_id'].includes(external)) {
                    const externalName = external.split('_')[0];
                    options.push({text: externalName, value: externalName})
                }
            }

            return options;
        }
    }
});
</script>
</%block>
<%block name="content">

<h1 class="header">{{ $route.meta.header }}</h1>

<div id="recommended-shows-lists" class="row">
    <div class="col-md-12">
        <config-template label-for="recommended-lists" label="Select a list">
            <select id="recommended-lists" name="recommended-lists" v-model="selectedList" class="form-control" @change="changeRecommendedList">
                <option v-for="option in options" v-bind:value="option.value">
                    {{ option.text }}
                </option>
            </select>
        </config-template>
    </div>
</div>

<div id="recommended-shows-options" class="row">
    <div class="col-md-12">
        <config-toggle-slider v-model="enableShowOptions" label="Pass Default show options" id="default_show_options" ></config-toggle-slider>

        <add-show-options v-show="enableShowOptions" enable-anime-options @change="updateOptions"></add-show-options>

        <div class="show-option">
            <span>Sort By:</span>
            <select name="showsort" id="showsort" v-model="sortOptionsValue" class="form-control form-control-inline input-sm" @change="sort">
                <option v-for="option in sortOptions" :value="option.value">{{option.text}}</option>
            </select>
        </div>

        <div class="show-option">
            <span style="margin-left:12px">Sort Order:</span>
            <select name="showsortdirection" id="showsortdirection" v-model="sortDirectionOptionsValue" class="form-control form-control-inline input-sm" @change="sortDirection">
                <option v-for="option in sortDirectionOptions" :value="option.value">{{option.text}}</option>
            </select>
        </div>
    </div>
</div> <!-- row -->

<div id="recommended-shows" class="row">
    <div id="popularShows" class="col-md-12">
        
        <div v-if="false" class="recommended_show" style="width:100%; margin-top:20px">
            <p class="red-text">Fetching of Recommender Data failed.</p>
            <strong>Exception:</strong>
            <p>###Exception here###??</p>
        </div>

        <isotope ref="filteredShows" :list="filteredShowsByList" id="container" class="isoDefault" :options='option' @layout="isotopeLayout($event)">
            <div v-for="show in filteredShowsByList" :key="show.seriesId" :class="containerClass(show)" :data-name="show.title" :data-rating="show.rating" :data-votes="show.votes" :data-anime="show.isAnime">
                <div class="recommended-image">
                    <app-link :href="show.imageHref">
                        <img alt="" class="recommended-image" src="images/poster.png" :data-original="show.imageSrc" height="273px" width="186px"/>
                    </app-link>
                </div>
                <div id="check-overlay"></div>

                <div class="show-title">
                    {{show.title}}
                </div>

                <div class="row">

                    <div name="left" class="col-md-6 col-xs-12">
                        <div class="show-rating">
                            <p>{{show.rating}} <img src="images/heart.png">
                                <div v-if="show.isAnime" id="linkAnime">
                                    <app-link class="recommended-show-url" :href="'https://anidb.net/a' + show.externals.aid">
                                        <img src="images/anidb_inline_refl.png" class="recommended-show-link-inline" alt=""/>
                                    </app-link>
                                </div>
                                <div v-if="show.recommender === 'Trakt Popular'" id="linkAnime">
                                    <a class="recommended-show-url" href="'https://trakt.tv/shows/' + show.seriesId">
                                        <img src="images/trakt.png" class="recommended-show-link-inline" alt=""/>
                                    </a>
                                </div>
                            </p>
                        </div>
                        
                        <div class="show-votes">
                            <i>{{show.votes}} votes</i>
                        </div>

                        
                    </div>
                    
                    <div name="right" class="col-md-6 col-xs-12">
                        <div class="recommendedShowTitleIcons">
                            <button v-if="show.showInLibrary" class="btn-medusa btn-xs">
                                <app-link :href="'home/displayShow?indexername=' + show.mappedIndexerName + '&seriesid=' + show.mappedSeriesId">In List</app-link>
                            </button>
                            
                            <button v-if="removedFromMedusa.includes(show.mappedSeriesId)" class="btn-medusa btn-xs">
                                <app-link :href="'home/displayShow?indexername=' + show.mappedIndexerName + '&seriesid=' + show.mappedSeriesId">Watched</app-link>
                            </button>
                            <!-- if trakt_b and not (cur_show.show_in_list or cur_show.mapped_series_id in removed_from_medusa): -->
                            <button v-if="show.source === externals.TRAKT" :data-indexer-id="show.mappedSeriesId" class="btn-medusa btn-xs" data-blacklist-show>Blacklist</button>
                        </div>
                    </div>
                </div>
                <div class="row" v-if="!show.showInLibrary">
                        <div class="col-md-12" name="addshowoptions">
                                <select :ref="String(show.source) + '-' + String(show.seriesId)" name="addshow" class="rec-show-select">
                                    <option v-for="option in addByExternalIndexer(show)" :value="option.value">{{option.text}}</option>
                                </select>
                                <button class="btn-medusa btn-xs rec-show-button" @click="addShowById(show, String(show.source) + '-' + String(show.seriesId))">
                                    Add
                                </button>
                        </div>
                </div>
            </div>
        </isotope>
    </div> <!-- End of col -->
</div> <!-- End of row -->
</%block>

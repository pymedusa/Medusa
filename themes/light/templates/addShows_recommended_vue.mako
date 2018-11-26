<%inherit file="/layouts/main.mako"/>
<%block name="scripts">
<script>
window.app = {};
window.app = new Vue({
    store,
    router,
    el: '#vue-wrap',
    data() {
        return {
            configLoaded: false,
            rootDirs: [],
            options: [
                { text: 'Anidb', value: 11 },
                { text: 'IMDB', value: 10 },
                { text: 'Trakt', value: 12 },
                { text: 'all', value: -1}
            ],
            selectedList: 11,
            shows: [],
            // trakt thing
            removedFromMedusa: [],
            
            // Isotope stuff
            selected: null,
            option: {
                getSortData: {
                    id: "seriesId"
                },
                sortBy : "seriesId",
                layoutMode: 'fitRows'
            },
            imgLazyLoad: new LazyLoad({
                // Example of options object -> see options section
                threshold: 500
            })
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

        /*
        * Adds show by indexer and indexer_id with a number of optional parameters
        * The show can be added as an anime show by providing the data attribute: data-isanime="1"
        * @TODO: move to vue method. Eventually you want to have this go through the store.
        */
        $.initAddShowById = function() {
            $(document.body).on('click', 'button[data-add-show]', function(e) {
                e.preventDefault();

                if ($(this).is(':disabled')) {
                    return false;
                }

                $(this).html('Added').prop('disabled', true);
                $(this).parent().find('button[data-blacklist-show]').prop('disabled', true);

                const anyQualArray = [];
                const bestQualArray = [];
                $('select[name="allowed_qualities"] option:selected').each((i, d) => {
                    anyQualArray.push($(d).val());
                });
                $('select[name="preferred_qualities"] option:selected').each((i, d) => {
                    bestQualArray.push($(d).val());
                });

                const configureShowOptions = $('#configure_show_options').prop('checked');

                $.get('addShows/addShowByID?indexername=' + $(this).attr('data-indexer') + '&seriesid=' + $(this).attr('data-indexer-id'), {
                    root_dir: $('#rootDirs option:selected').val(), // eslint-disable-line camelcase
                    configure_show_options: configureShowOptions, // eslint-disable-line camelcase
                    show_name: $(this).attr('data-show-name'), // eslint-disable-line camelcase
                    quality_preset: $('select[name="quality_preset"]').val(), // eslint-disable-line camelcase
                    default_status: $('#statusSelect').val(), // eslint-disable-line camelcase
                    any_qualities: anyQualArray.join(','), // eslint-disable-line camelcase
                    best_qualities: bestQualArray.join(','), // eslint-disable-line camelcase
                    season_folders: $('#season_folders').prop('checked'), // eslint-disable-line camelcase
                    subtitles: $('#subtitles').prop('checked'),
                    anime: $('#anime').prop('checked'),
                    scene: $('#scene').prop('checked'),
                    default_status_after: $('#statusSelectAfter').val() // eslint-disable-line camelcase
                });
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
            return $store.state.recommended.recommended.shows;
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
        <div id="tabs">
            <fieldset class="component-group-list">
                <div class="field-pair">
                    <label class="clearfix" for="content_configure_show_options">
                        <span class="component-title">Configure Show Options</span>
                        <span class="component-desc">
                            <input type="checkbox" class="enabler" name="configure_show_options" id="configure_show_options" />
                            <p>Recommended shows will be added using your default options. Use this option if you want to change the options for that show.</p>
                        </span>
                    </label>
                </div>
                <div id="content_configure_show_options">
                    <div class="field-pair">
                        <label class="clearfix" for="configure_show_options">
                            <ul>
                                <li><app-link href="#tabs-1">Manage Directories</app-link></li>
                                <li><app-link href="#tabs-2">Customize Options</app-link></li>
                            </ul>
                            <div id="tabs-1" class="existingtabs">
                                <root-dirs @update="rootDirs = $event"></root-dirs>
                                <br/>
                            </div>
                            <div id="tabs-2" class="existingtabs">
                                <!-- <include file="/inc_addShowOptions.mako"/> -->
                            </div>
                        </label>
                    </div>
                </div>
            </fieldset>
        </div>  <!-- tabs-->


        <div class="show-option">
            <span>Sort By:</span>
            <select id="showsort" class="form-control form-control-inline input-sm">
                <option value="name">Name</option>
                <option value="original">Original</option>
                <option value="votes">Votes</option>
                <option value="rating">% Rating</option>
                <option value="rating_votes" selected="true" >% Rating > Votes</option>
            </select>
        </div>

        <div class="show-option">
            <span style="margin-left:12px">Sort Order:</span>
            <select id="showsortdirection" class="form-control form-control-inline input-sm">
                <option value="asc">Asc</option>
                <option value="desc" selected="true" >Desc</option>
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

        <isotope :list="filteredShowsByList" id="container" class="isoDefault" :options='option' @layout="isotopeLayout($event)">
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

                <div class="clearfix show-attributes">
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
                    <i>{{show.votes}} votes</i>

                    <div class="recommendedShowTitleIcons">
                        <button v-if="show.showInLibrary" class="btn-medusa btn-xs">
                            <app-link :href="'home/displayShow?indexername=' + show.mappedIndexer + '&seriesid=' + show.mappedSeriesId">In List</app-link>
                        </button>
                        
                        <button v-if="!show.showInLibrary" class="btn-medusa btn-xs" data-isanime="1" :data-indexer="show.mappedIndexer"
                            :data-indexer-id="show.mappedSeriesId" :data-show-name="show.title || 'u'" data-add-show>
                            Add
                        </button>

                        <button v-if="removedFromMedusa.includes(show.mappedSeriesId)" class="btn-medusa btn-xs">
                            <app-link :href="'home/displayShow?indexername=' + show.mappedIndexer + '&seriesid=' + show.mappedSeriesId">Watched</app-link>
                        </button>
                        <!-- if trakt_b and not (cur_show.show_in_list or cur_show.mapped_series_id in removed_from_medusa): -->
                        <button :data-indexer-id="show.mappedSeriesId" class="btn-medusa btn-xs" data-blacklist-show>Blacklist</button>
                    </div>
                </div>
            </div>
        </isotope>
    </div> <!-- End of col -->
</div> <!-- End of row -->
</%block>

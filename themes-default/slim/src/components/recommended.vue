<template>
    <div id="recommended-shows">
        <div id="recommended-shows-lists" class="row">
            <div class="col-md-12">
                <config-template label-for="recommended-source" label="Select a Source">
                    <select id="recommended-source" name="recommended-source" v-model="selectedSource" class="form-control">
                        <option v-for="option in sourceOptions" :value="option.value" :key="option.value">
                            {{ option.text }}
                        </option>
                    </select>
                </config-template>
                <config-template label-for="recommended-list" label="Select a list">
                    <select id="recommended-list" name="recommended-list" v-model="selectedList" class="form-control">
                        <option v-for="option in listOptions" :value="option.value" :key="option.value">
                            {{ option.text }}
                        </option>
                    </select>
                </config-template>

            </div>
        </div>

        <div id="recommended-shows-options" class="row">
            <div class="col-md-12">
                <config-toggle-slider v-model="enableShowOptions" label="Pass Default show options" id="default_show_options" />

                <add-show-options v-show="enableShowOptions" enable-anime-options @change="updateOptions" />

                <div class="show-option">
                    <span>Sort By:</span>
                    <select name="showsort" id="showsort" v-model="sortOptionsValue" class="form-control form-control-inline input-sm" @change="sort">
                        <option v-for="option in sortOptions" :value="option.value" :key="option.value">{{option.text}}</option>
                    </select>
                </div>

                <div class="show-option">
                    <span style="margin-left:12px">Sort Order:</span>
                    <select name="showsortdirection" id="showsortdirection" v-model="sortDirectionOptionsValue" class="form-control form-control-inline input-sm" @change="sortDirection">
                        <option v-for="option in sortDirectionOptions" :value="option.value" :key="option.value">{{option.text}}</option>
                    </select>
                </div>

                <div class="show-option">
                    <span style="margin-left:12px">Filter:</span>
                    <input type="text" v-model="filterShows" placeholder="no filter" class="form-control form-control-inline input-sm" @input="filter('filterByText')">
                </div>

            </div>
        </div> <!-- row -->

        <div id="recommended-shows" class="row">
            <div id="popularShows" class="col-md-12">
                <div v-if="selectedSource === externals.TRAKT && traktWarning" class="trakt-auth-container">
                    <font-awesome-icon :icon="['far', 'times-circle']" class="close-container" @click="traktWarning = false" />
                    <span v-if="traktWarning" class="trakt-warning">{{traktWarningMessage}}</span>
                    <button v-if="!showTraktAuthDialog" class="btn-medusa" id="config-trakt" @click="showTraktAuthDialog = true">Config Trakt</button>
                    <trakt-authentication v-if="showTraktAuthDialog" auth-only />
                </div>

                <div v-if="false" class="recommended_show" style="width:100%; margin-top:20px">
                    <p class="red-text">Fetching of Recommender Data failed.</p>
                    <strong>Exception:</strong>
                    <p>###Exception here###??</p>
                </div>

                <isotope ref="filteredShows" :list="filteredShowsByList" id="isotope-container" class="isoDefault" :options="option" @layout="isotopeLayout($event)">
                    <div v-for="show in filteredShowsByList" :key="show.seriesId" :class="containerClass(show)" :data-name="show.title" :data-rating="show.rating" :data-votes="show.votes" :data-anime="show.isAnime">
                        <div class="recommended-image">
                            <app-link :href="show.imageHref">
                                <asset :default-src="show.imageSrc" lazy type="posterThumb" cls="show-image" :link="false" height="273px" :img-width="186" />
                            </app-link>
                        </div>

                        <div id="check-overlay" />

                        <div class="show-title">
                            {{show.title}}
                        </div>

                        <div class="row">

                            <div name="left" class="col-md-6 col-xs-12">
                                <div class="show-rating">
                                    <p>{{show.rating}} <img src="images/heart.png">
                                        <template v-if="show.isAnime" id="linkAnime">
                                            <app-link class="recommended-show-url" :href="`https://anidb.net/a${show.externals.aid}`">
                                                <img src="images/anidb_inline_refl.png" class="recommended-show-link-inline" alt="">
                                            </app-link>
                                        </template>
                                        <template v-if="show.recommender === 'Trakt Popular'" id="linkAnime">
                                            <a class="recommended-show-url" :href="`https://trakt.tv/shows/${show.seriesId}`">
                                                <img src="images/trakt.png" class="recommended-show-link-inline" alt="">
                                            </a>
                                        </template>
                                    </p>
                                </div>

                                <div class="show-votes">
                                    <i>{{show.votes}} votes</i>
                                </div>

                            </div>

                            <div name="right" class="col-md-6 col-xs-12">
                                <div class="recommendedShowTitleIcons">
                                    <button v-if="show.showInLibrary" class="btn-medusa btn-xs">
                                        <app-link :href="`home/displayShow?indexername=${show.mappedIndexerName}&seriesid=${show.mappedSeriesId}`">In List</app-link>
                                    </button>

                                    <button v-if="traktConfig.removedFromMedusa.includes(show.mappedSeriesId)" class="btn-medusa btn-xs">
                                        <app-link :href="`home/displayShow?indexername=${show.mappedIndexerName}&seriesid=${show.mappedSeriesId}`">Watched</app-link>
                                    </button>
                                    <!-- if trakt_b and not (cur_show.show_in_list or cur_show.mapped_series_id in removed_from_medusa): -->
                                    <button :disabled="show.trakt.blacklisted" v-if="show.source === externals.TRAKT" :data-indexer-id="show.mappedSeriesId" class="btn-medusa btn-xs" @click="blacklistTrakt(show)">Blacklist</button>
                                </div>
                            </div>
                        </div>
                        <div class="row" v-if="!show.showInLibrary">
                            <div class="col-md-12" name="addshowoptions">
                                <select :ref="`${show.source}-${show.seriesId}`" name="addshow" class="rec-show-select">
                                    <option v-for="option in externalIndexers(show)" :value="option.value" :key="option.value">{{option.text}}</option>
                                </select>
                                <button :disabled="show.trakt.blacklisted" class="btn-medusa btn-xs rec-show-button" @click="addShow(show, `${show.source}-${show.seriesId}`)">
                                    Add
                                </button>
                            </div>
                        </div>
                    </div>
                </isotope>
            </div> <!-- End of col -->
        </div> <!-- End of row -->
    </div>
</template>

<script>
import LazyLoad from 'vanilla-lazyload';
import { apiRoute } from '../api.js';
import { mapState, mapActions } from 'vuex';
import AddShowOptions from './add-show-options.vue';
import {
    Asset,
    AppLink,
    ConfigTemplate,
    ConfigToggleSlider,
    TraktAuthentication
} from './helpers';
import isotope from 'vueisotope';
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome';


export default {
    name: 'recommended',
    components: {
        Asset,
        AddShowOptions,
        AppLink,
        ConfigTemplate,
        ConfigToggleSlider,
        FontAwesomeIcon,
        TraktAuthentication,
        isotope
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
        ];
        const sortDirectionOptions = [
            { text: 'Ascending', value: 'asc'},
            { text: 'Descending', value: 'desc'},
        ];
        return {
            externals,
            sortOptions,
            sortDirectionOptions,
            sortOptionsValue: 'original',
            sortDirectionOptionsValue: 'desc',
            filterOption: null,
            filterShows: '',
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
            sourceOptions: [
                { text: 'Anidb', value: externals.ANIDB },
                { text: 'IMDB', value: externals.IMDB },
                { text: 'Trakt', value: externals.TRAKT },
                { text: 'all', value: -1 }
            ],
            selectedSource: 11,
            selectedList: '',

            // Isotope stuff
            selected: null,
            option: {
                getSortData: {
                    id: 'seriesId',
                    title: itemElem => {
                        return itemElem.title.toLowerCase();
                    },
                    rating: 'rating',
                    votes: 'votes'
                },
                getFilterData: {
                    filterByText: itemElem => {
                        return itemElem.title.toLowerCase().includes(this.filterShows.toLowerCase());
                    }
                },
                sortBy: 'votes',
                layoutMode: 'fitRows',
                sortAscending: false
            },
            showTraktAuthDialog: false,
            traktWarning: false,
            traktWarningMessage: ''
        };
    },
    created() {
        const { getRecommendedShows, imgLazyLoad } = this;
        getRecommendedShows().then(() => {
            this.$nextTick(() => {
                // This is needed for now.
                imgLazyLoad.update();
                // imgLazyLoad.handleScroll();
            });
        });
    },
    mounted() {
        this.$once('loaded', () => {
            this.configLoaded = true;
        });

        this.$watch('recommendedLists', () =>{
            this.setSelectedList(this.selectedSource);
        });

    },
    computed: {
        ...mapState({
            config: state => state.config,
            trakt: state => state.config.notifiers.trakt,
            recommendedShows: state => state.recommended.shows,
            traktConfig: state => state.recommended.trakt,
            recommendedLists: state => state.config.indexers.main.recommendedLists
        }),
        filteredShowsByList() {
            const { imgLazyLoad, recommendedShows, selectedSource, selectedList } = this;
            let filteredList = null;

            if (selectedSource === -1) {
                return recommendedShows;
            }

            this.$nextTick(() => {
                // This is needed for now.
                imgLazyLoad.update();
                // imgLazyLoad.handleScroll();
            });

            filteredList = recommendedShows.filter(show => show.source === selectedSource);

            if (selectedList) {
                filteredList = recommendedShows.filter(show => show.subcat === selectedList);
            }

            return filteredList;
        },
        imgLazyLoad() {
            console.log('imgLazyLoad object constructud!');
            return new LazyLoad({
                // Example of options object -> see options section
                threshold: 500
            });
        },
        listOptions() {
            const { recommendedLists, selectedSource } = this;
            const sourceLists = recommendedLists[selectedSource] || [];
            return sourceLists.map(list => ({text: list, value: list}))
        }
    },
    methods: {
        ...mapActions({
            getRecommendedShows: 'getRecommendedShows'
        }),
        containerClass(show) {
            let classes = 'recommended-container default-poster show-row';
            // const { removedFromMedusa } = this.traktConfig;
            if (show.showInLibrary) {
                classes += ' show-in-list';
            }
            return classes;
        },
        isotopeLayout() {
            const { imgLazyLoad } = this;

            console.log('isotope Layout loaded');
            imgLazyLoad.update();
            // imgLazyLoad.handleScroll();
        },
        addShow(show, indexer) {
            const selectedOption = this.$refs[indexer][0].selectedOptions[0].value;
            if (selectedOption === 'search') {
                // Route to the add-new-show.vue component, with the show's title.
                this.$router.push({
                    name: 'addNewShow',
                    params: {
                        providedInfo: {
                            showName: show.title
                        }
                    }
                });
                return;
            }
                        
            let showId = null;
            if (Object.keys(show.externals).length !== 0 && show.externals[selectedOption + '_id']) {
                showId = { [selectedOption]: show.externals[selectedOption + '_id'] };
            }
            this.addShowById(showId);
        },
        /**
         * Add by show id.
         */
        async addShowById(showId) {
            const { enableShowOptions, selectedShowOptions } = this;

            const options = {};
            
            if (enableShowOptions) {
                options.options = selectedShowOptions;
            }

            try {
                await api.post('series', { id: showId, options });
                this.$snotify.success(
                    'Adding new show to library',
                    'Saved',
                    { timeout: 20000 }
                );
                show.showInLibrary = true;            
            } catch (error) {
                this.$snotify.error(
                    'Error while trying to add new show',
                    'Error'
                );                
            }
        },
        updateOptions(options) {
            // Update seleted options from add-show-options.vue @change event.
            const { anime, scene, seasonFolders, status, subtitles, statusAfter, release, quality } = options;
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
                rating_votes: ['rating', 'votes'] // eslint-disable-line camelcase
            };
            const { option: isotopeOptions, sortOptionsValue } = this;
            this.option.sortBy = mapped[sortOptionsValue];
            this.$refs.filteredShows.arrange(isotopeOptions);
        },
        filter(key) {
            // const { option: isotopeOptions } = this;
            // this.$refs.filteredShows.arrange(isotopeOptions);
            this.$refs.filteredShows.filter(key);
            this.filterOption = key;
        },
        sortDirection() {
            const { option: isotopeOptions, sortDirectionOptionsValue } = this;
            this.option.sortAscending = sortDirectionOptionsValue === 'asc';
            this.$refs.filteredShows.arrange(isotopeOptions);
        },
        externalIndexers(show) {
            const { externals } = show;
            if (show.isAnime) {
                return [{ text: 'Tvdb', value: 'tvdb_id' }];
            }

            const options = [];
            // Add through the add-new-show.vue component
            options.push({ text: 'search show', value: 'search'});

            for (const external in externals) {
                if (['tvdb_id', 'tmdb_id', 'tvmaze_id'].includes(external)) {
                    const externalName = external.split('_')[0];
                    options.push({ text: externalName, value: externalName });
                }
            }

            return options;
        },
        blacklistTrakt(show) {
            debugger;
            show.trakt.blacklisted = true;
            apiRoute(`addShows/addShowToBlacklist?seriesid=${show.externals.tvdb_id}`);
        },
        setSelectedList(selectedSource) {
            const { recommendedLists, selectedList } = this;
            const listOptions = recommendedLists[selectedSource];
            if (selectedList == '' || !listOptions.includes(selectedList)) {
                this.selectedList = listOptions[0];
            }
        }
    },
    watch: {
        selectedSource(newValue) {
            this.setSelectedList(newValue);
            if (newValue === this.externals.TRAKT) {
                const { trakt } = this;
                if (!trakt.enabled) {
                    this.traktWarning = true;
                    this.traktWarningMessage = 'You havent enabled trakt yet.';
                    return;
                }
                apiRoute('home/testTrakt')
                    .then(result => {
                        if (result.data !== 'Test notice sent successfully to Trakt') {
                            // Ask user if he wants to setup trakt authentication.
                            this.traktWarning = true;
                            this.traktWarningMessage = 'We could not authenticate to trakt. Do you want to set this up now?';
                        }
                    });

            }
        }
    }
};
</script>

<style scoped>
.recommended-image >>> .show-image {
    height: 100%;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
}

.trakt-auth-container {
    padding: 10px;
    border: 1px solid rgb(255 255 255);
    box-shadow: 5px 5px dimgrey;
}

.trakt-auth-container > .close-container {
    position: absolute;
    top: -24px;
    right: 15px;
    color: red;
}

span.trakt-warning {
    margin: 0px 0 14px 0;
    display: block;
    color: red;
}
</style>

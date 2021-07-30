<template>
    <div id="recommended-shows">
        <vue-snotify />
        <div id="recommended-shows-lists" class="row">
            <div class="col-md-12">
                <config-template label-for="recommended-source" label="Select a Source">
                    <select disabled="disabled" v-if="!showsLoaded" class="form-control max-width">
                        <option value="">Loading shows, please wait</option>
                    </select>
                    <select v-else :disabled="!showsLoaded" id="recommended-source" name="recommended-source" v-model="selectedSource" class="form-control max-width">
                        <option v-show="showsLoaded" v-for="option in sourceOptions" :value="option.value" :key="option.value">
                            {{ option.text }}
                        </option>
                    </select>
                </config-template>
                <config-template label-for="recommended-list" label="Select a list">
                    <select :disabled="!showsLoaded" id="recommended-list" name="recommended-list" v-model="selectedList" class="form-control max-width">
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

                <isotope ref="filteredShows" v-if="filteredShowsByList.length" :list="filteredShowsByList" id="isotope-container" class="isoDefault" :options="option" @layout="isotopeLayout">
                    <div v-for="show in filteredShowsByList" :key="show.seriesId" :class="containerClass(show)" :data-name="show.title" :data-rating="show.rating" :data-votes="show.votes" :data-anime="show.isAnime">
                        <div class="recommended-image">
                            <app-link :href="show.imageHref">
                                <asset :default-src="show.imageSrc" lazy type="posterThumb" cls="show-image" :link="false" height="273px" :img-width="186" />
                            </app-link>
                        </div>
                        <div class="tag-container">
                            <ul class="genre-tags">
                                <li v-for="genre in show.genres">{{genre}}</li>
                            </ul>
                        </div>

                        <div class="check-overlay" />
                        <div class="tag-container">
                            <ul class="genre-tags">
                                <li v-for="genre in show.genres">{{genre}}</li>
                            </ul>
                        </div>


                        <div class="show-title">
                            {{show.title}}
                        </div>

                        <div class="row">
                            <div name="left" class="col-md-7 col-xs-12">
                                <div class="show-rating">
                                    <p>{{show.rating.toFixed(1)}} <img src="images/heart.png">
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
                                    <i>x {{show.votes}}</i>
                                </div>

                            </div>

                            <div name="right" class="col-md-5 col-xs-12">
                                <div class="recommendedShowTitleIcons">
                                    <button v-if="traktConfig.removedFromMedusa.includes(show.mappedSeriesId)" class="btn-medusa btn-xs">
                                        <app-link :href="`home/displayShow?indexername=${show.mappedIndexerName}&seriesid=${show.mappedSeriesId}`">Watched</app-link>
                                    </button>
                                    <!-- if trakt_b and not (cur_show.show_in_list or cur_show.mapped_series_id in removed_from_medusa): -->
                                    <button :disabled="show.trakt.blacklisted" v-if="show.source === externals.TRAKT" :data-indexer-id="show.mappedSeriesId" class="btn-medusa btn-xs" @click="blacklistTrakt(show)">Blacklist</button>
                                </div>
                            </div>
                        </div>
                        <div class="row">
                            <div class="col-md-12 addshowoptions">
                                <template v-if="show.showInLibrary">
                                    <button v-if="show.showInLibrary" class="btn-medusa btn-xs">
                                        <app-link :href="`home/displayShow?showslug=${show.showInLibrary}`">Open in library</app-link>
                                    </button>
                                </template>
                                <template v-else>
                                    <select :ref="`${show.source}-${show.seriesId}`" name="addshow" class="rec-show-select">
                                        <option v-for="option in addShowOptions(show)" :value="option.value" :key="option.value">{{option.text}}</option>
                                    </select>
                                    <button :disabled="show.trakt.blacklisted" class="btn-medusa btn-xs rec-show-button" @click="addShow(show, `${show.source}-${show.seriesId}`)">
                                        Search/Add
                                    </button>
                                </template>
                            </div>
                        </div>
                    </div>
                </isotope>
                <div class="align-center" v-if="showsLoaded && filteredShowsByList.length === 0 && selectedSource !== -1">
                    <button class="btn-medusa btn-xs rec-show-button" @click="searchRecommendedShows">
                        Search for new recommended shows from {{sourceToString[selectedSource]}}
                    </button>
                </div>

            </div> <!-- End of col -->
        </div> <!-- End of row -->
    </div>
</template>

<script>
import LazyLoad from 'vanilla-lazyload';
import { api, apiRoute } from '../api.js';
import { mapState, mapActions } from 'vuex';
import AddShowOptions from './add-show-options.vue';
import {
    Asset,
    AppLink,
    ConfigTemplate,
    ConfigToggleSlider,
    TraktAuthentication
} from './helpers';
import Isotope from 'vueisotope';
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
        Isotope
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
        const IMDB = 10;
        const ANIDB = 11;
        const TRAKT = 12;
        const MYANIMELIST = 13;
        const ANILIST = 14;
        const externals = {
            IMDB,
            ANIDB,
            TRAKT,
            MYANIMELIST,
            ANILIST
        };
        const sourceToString = {
            [externals.IMDB]: 'imdb',
            [externals.ANIDB]: 'anidb',
            [externals.TRAKT]: 'trakt',
            [externals.MYANIMELIST]: 'myanimelist',
            [externals.ANILIST]: 'anilist'
        };
        const sortOptions = [
            { text: 'Name', value: 'name' },
            { text: 'Original', value: 'original' },
            { text: 'Votes', value: 'votes' },
            { text: '% Rating', value: 'rating' },
            { text: '% Rating > Votes', value: 'rating_votes' }
        ];
        const sortDirectionOptions = [
            { text: 'Ascending', value: 'asc' },
            { text: 'Descending', value: 'desc' }
        ];
        return {
            externals,
            sourceToString,
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
                { text: 'MyAnimeList', value: externals.MYANIMELIST },
                { text: 'AniList', value: externals.ANILIST },
                { text: 'all', value: -1 }
            ],
            selectedSource: 10,
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
            traktWarningMessage: '',
            showsLoaded: false
        };
    },
    mounted() {
        const { getRecommendedShows } = this;
        getRecommendedShows().then(() => {
            this.showsLoaded = true;
            this.$nextTick(() => {
                this.isotopeLayout();
            });
        });

        this.$once('loaded', () => {
            this.configLoaded = true;
        });

        this.$watch('recommendedLists', () => {
            this.setSelectedList(this.selectedSource);
        });
    },
    computed: {
        ...mapState({
            config: state => state.config,
            trakt: state => state.config.notifiers.trakt,
            recommendedShows: state => state.recommended.shows,
            traktConfig: state => state.recommended.trakt,
            recommendedLists: state => state.recommended.categories,
            queueitems: state => state.queue.queueitems
        }),
        filteredShowsByList() {
            const { imgLazyLoad, recommendedShows, selectedSource, selectedList } = this;
            let filteredList = null;

            if (selectedSource === -1) {
                return recommendedShows;
            }

            filteredList = recommendedShows.filter(show => show.source === selectedSource);

            if (selectedList) {
                filteredList = filteredList.filter(show => show.subcat === selectedList);
            }

            this.$nextTick(() => {
                // This is needed for now.
                imgLazyLoad.update();
            });
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
            return sourceLists.map(list => ({ text: list, value: list }));
        }
    },
    methods: {
        ...mapActions({
            getRecommendedShows: 'getRecommendedShows'
        }),
        containerClass(show) {
            let classes = 'recommended-container default-poster show-row';
            const { traktConfig } = this;
            const { removedFromMedusa } = traktConfig;

            if (show.showInLibrary) {
                classes += ' show-in-list';
            }

            if (removedFromMedusa.includes(show.externals.tvdb_id)) {
                classes += ' removed-from-medusa';
            }
            return classes;
        },
        isotopeLayout() {
            const { imgLazyLoad } = this;

            console.log('isotope Layout loaded');
            imgLazyLoad.update();
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

            if (this.addShowById(showId)) {
                show.showInLibrary = true;
            }
        },
        /**
         * Add by show id.
         * @param {number} showId - Show id.
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
                return true;
            } catch (error) {
                this.$snotify.error(
                    'Error while trying to add new show',
                    'Error'
                );
            }
            return false;
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
            this.$refs.filteredShows.filter(key);
            this.filterOption = key;
        },
        sortDirection() {
            const { option: isotopeOptions, sortDirectionOptionsValue } = this;
            this.option.sortAscending = sortDirectionOptionsValue === 'asc';
            this.$refs.filteredShows.arrange(isotopeOptions);
        },
        addShowOptions(show) {
            const { externals } = show;
            if (show.isAnime) {
                return [{ text: 'Tvdb', value: 'tvdb_id' }];
            }

            const options = [];
            // Add through the add-new-show.vue component
            options.push({ text: 'search show', value: 'search' });

            for (const external in externals) {
                if (['tvdb_id', 'tmdb_id', 'tvmaze_id'].includes(external)) {
                    const externalName = external.split('_')[0];
                    options.push({ text: externalName, value: externalName });
                }
            }

            return options;
        },
        blacklistTrakt(show) {
            show.trakt.blacklisted = true;
            apiRoute(`addShows/addShowToBlacklist?seriesid=${show.externals.tvdb_id}`);
        },
        setSelectedList(selectedSource) {
            const { recommendedLists, selectedList } = this;
            const listOptions = recommendedLists[selectedSource];
            if (!listOptions) {
                return;
            }
            if (selectedList === '' || !listOptions.includes(selectedList)) {
                this.selectedList = listOptions[0];
            }
        },
        async searchRecommendedShows() {
            const { sourceToString, selectedSource } = this;
            const source = sourceToString[selectedSource];
            try {
                await api.post(`recommended/${source}`);
                this.$snotify.success(
                    'Started search for new recommended shows',
                    `Searching ${source}`
                );
            } catch (error) {
                if (error.response.status === 409) {
                    this.$snotify.error(
                        error.response.data.error,
                        'Error'
                    );
                }
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
        },
        queueitems(queueItems) {
            // Check for a new recommended show queue item and refresh results.
            if (queueItems.filter(item => item.name.includes('UPDATE-RECOMMENDED'))) {
                this.getRecommendedShows();
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
    margin: 0 0 14px 0;
    display: block;
    color: red;
}

.tag-container {
    opacity: 0;
    position: absolute;
    top: 3px;
    right: 0;
    -webkit-transition: opacity 0.2s ease-in-out;
    -moz-transition: opacity 0.2s ease-in-out;
    -ms-transition: opacity 0.2s ease-in-out;
    -o-transition: opacity 0.2s ease-in-out;
    transition: opacity 0.2s ease-in-out;
}

.check-overlay:hover,
.recommended-image:hover {
    opacity: 0.9;
}

.check-overlay:hover + .tag-container,
.recommended-image:hover + .tag-container {
    display: block;
    /* transition: opacity 1s ease-in-out; */
    opacity: 0.9;
}

ul.genre-tags {
    margin-right: 2px;
}

ul.genre-tags > li {
    margin-right: 1px;
    margin-bottom: 2px;
    padding: 2px 4px;
    background: rgb(21, 82, 143);
    border-radius: 1px;
    border: 1px solid rgb(17, 17, 17);
    color: rgb(255, 255, 255);
    font: 14px/18px "Open Sans", "Helvetica Neue", Helvetica, Arial, Geneva, sans-serif;
    text-shadow: 0 1px rgb(0 0 0 / 80%);
    float: right;
    list-style: none;
}

select.max-width {
    max-width: 430px;
}
</style>

<template>
    <div id="recommended-shows">
        <vue-snotify />
        <div id="recommended-shows-lists" class="row">
            <div class="col-md-12">
                <config-template label-for="recommended-source" label="Select a Source">
                    <select disabled="disabled" v-if="!showsLoaded" class="form-control max-input350">
                        <option value="">Loading shows, please wait</option>
                    </select>
                    <select v-else :disabled="!showsLoaded" id="recommended-source" name="recommended-source" v-model="selectedSource" class="form-control max-input350">
                        <option v-show="showsLoaded" v-for="option in sourceOptions" :value="option.value" :key="option.value">
                            {{ option.text }}
                        </option>
                    </select>
                </config-template>
                <config-template label-for="recommended-list" label="Select a list">
                    <select :disabled="!showsLoaded" id="recommended-list" name="recommended-list" v-model="selectedList" class="form-control max-input350">
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

                <isotope ref="filteredShows" v-if="showsLoaded && filteredShowsByList.length" :list="filteredShowsByList" id="isotope-container" class="isoDefault" :options="option" @layout="isotopeLayout">
                    <div v-for="show in filteredShowsByList" :key="show.seriesId" :class="containerClass(show)" :data-name="show.title" :data-rating="show.rating" :data-votes="show.votes" :data-anime="show.isAnime">
                        <recommended-poster :show="show" />
                    </div>
                </isotope>

                <div class="align-center" v-if="showsLoaded && filteredShowsByList.length === 0 && selectedSource !== -1">
                    <button class="btn-medusa btn-xs rec-show-button" @click="searchRecommendedShows">
                        Search for new recommended shows from {{sourceToString[selectedSource]}}
                    </button>
                </div>

                <div v-else-if="page[selectedSource] !== -1" class="load-more">
                    <state-switch v-if="loadingShows" state="loading" />
                    <button v-else class="btn-medusa" @click="getMore">Load More</button>
                </div>
            </div> <!-- End of col -->
        </div> <!-- End of row -->
    </div>
</template>

<script>
import LazyLoad from 'vanilla-lazyload';
import { mapState, mapActions } from 'vuex';
import AddShowOptions from './add-show-options.vue';
import {
    ConfigTemplate,
    ConfigToggleSlider,
    StateSwitch,
    TraktAuthentication
} from './helpers';
import RecommendedPoster from './recommended-poster.vue';
import Isotope from 'vueisotope';
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome';

export default {
    name: 'recommended',
    components: {
        AddShowOptions,
        ConfigTemplate,
        ConfigToggleSlider,
        FontAwesomeIcon,
        StateSwitch,
        RecommendedPoster,
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
        const ANILIST = 13;
        const externals = {
            IMDB,
            ANIDB,
            TRAKT,
            ANILIST
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
            sortOptions,
            sortDirectionOptions,
            sortOptionsValue: 'original',
            sortDirectionOptionsValue: 'desc',
            filterOption: null,
            filterShows: '',
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
            showsLoaded: false,
            loadingShows: false
        };
    },
    async mounted() {
        const { getRecommendedShows, getRecommendedShowsOptions, sourceToString } = this;
        const sources = Object.keys(sourceToString);

        await getRecommendedShowsOptions();

        this.loadingShows = true;
        for (const source of sources) {
            try {
                // eslint-disable-next-line no-await-in-loop
                await getRecommendedShows(source);
            } catch {
                this.$snotify.error(
                    `Could not load recommended shows for ${sourceToString[source]}`
                );
            }
        }

        this.showsLoaded = true;
        this.loadingShows = false;

        this.$nextTick(() => {
            this.isotopeLayout();
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
            lastQueueItem: state => state.queue.last,
            sourceToString: state => state.recommended.sourceToString,
            page: state => state.recommended.page,
            client: state => state.auth.client
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
            if (!recommendedLists || !(selectedSource in recommendedLists)) {
                return;
            }
            const sourceLists = recommendedLists[selectedSource] || [];
            return sourceLists.map(list => ({ text: list, value: list }));
        }
    },
    methods: {
        ...mapActions({
            getRecommendedShows: 'getRecommendedShows',
            getRecommendedShowsOptions: 'getRecommendedShowsOptions',
            getMoreShows: 'getMoreShows'
        }),
        containerClass(show) {
            let classes = 'recommended-container default-poster show-row';
            const { traktConfig } = this;
            const { removedFromMedusa } = traktConfig;

            if (show.showInLibrary) {
                classes += ' show-in-list';
            }

            if (removedFromMedusa && removedFromMedusa.includes(show.externals.tvdb_id)) {
                classes += ' removed-from-medusa';
            }
            return classes;
        },
        isotopeLayout() {
            const { imgLazyLoad } = this;

            console.log('isotope Layout loaded');
            imgLazyLoad.update();
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
                await this.client.api.post(`recommended/${source}`);
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
        },
        getMore() {
            this.loadingShows = true;
            this.getMoreShows(this.selectedSource)
                .finally(() => {
                    this.loadingShows = false;
                });
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
                this.client.apiRoute('home/testTrakt')
                    .then(result => {
                        if (result.data !== 'Test notice sent successfully to Trakt') {
                            // Ask user if he wants to setup trakt authentication.
                            this.traktWarning = true;
                            this.traktWarningMessage = 'We could not authenticate to trakt. Do you want to set this up now?';
                        }
                    });
            }
        },
        lastQueueItem(item) {
            const { externals } = this;
            const actions = {
                'UPDATE-RECOMMENDED-IMDB': externals.IMDB,
                'UPDATE-RECOMMENDED-ANIDB': externals.ANIDB,
                'UPDATE-RECOMMENDED-TRAKT': externals.TRAKT,
                'UPDATE-RECOMMENDED-ANILIST': externals.ANILIST
            };
            if (item.name.includes('UPDATE-RECOMMENDED') && item.success) {
                // Now we're getting the first page. But if there are more then 1000 shows in lib,
                // we won't get the updated shows. In future, we should add an option to the pagination
                // where we can request the last page.
                this.$store.commit('resetPage', actions[item.name]);
                this.getRecommendedShows(actions[item.name]);
            }
        }
    }
};
</script>

<style scoped>
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

.load-more {
    display: flex;
    justify-content: center;
}
</style>

<template>
    <div class="new-show-search">
        <div v-if="providedInfo.use">
            Show retrieved from existing metadata:
            <span v-if="providedInfo.indexerId !== 0 && providedInfo.showId !== 0">
                <app-link :href="`${getIndexer(providedInfo.indexerId).showUrl}${providedInfo.showId}`">
                    <b>{{ providedInfo.showName }}</b>
                </app-link>
                <br>
                Show indexer:
                <b>{{ getIndexer(providedInfo.indexerId).name }}</b>
                <img height="16" width="16" :src="`images/${getIndexer(providedInfo.indexerId).icon}`">
            </span>
            <span v-else>
                <b>{{ providedInfo.showName }}</b>
            </span>
        </div>
        <div v-else>
            <div class="row">
                <div class="col-lg-12">
                    <div class="row">
                        <div class="col-lg-12">
                            <div class="row">
                                <div v-if="existingFolder && existingFolder.pathExists" class="col-lg-12">
                                    <span>Show folder found for selected show: <strong>{{existingFolder.path}}</strong></span>
                                </div>
                            </div>

                            <div class="row">
                                <div class="col-lg-12">
                                    <div class="show-add-option">
                                        <input type="text" v-model.trim="nameToSearch" ref="nameToSearch" @keyup.enter="searchIndexers" class="form-control form-control-inline input-sm input350">
                                    </div>

                                    <div class="show-add-option">
                                        <language-select @update-language="indexerLanguage = $event"
                                                         ref="indexerLanguage" :language="general.indexerDefaultLanguage"
                                                         :available="indexers.main.validLanguages.join(',')"
                                                         class="form-control form-control-inline input-sm"
                                        />
                                        <b>*</b>
                                    </div>

                                    <div class="show-add-option">
                                        <select v-model="indexerId" class="form-control form-control-inline input-sm">
                                            <option v-for="option in indexerListOptions" :value="option.value" :key="option.value">
                                                {{ option.text }}
                                            </option>
                                        </select>
                                    </div>

                                    <div class="show-add-option">
                                        <input class="btn-medusa btn-inline" type="button" value="Search" @click="searchIndexers">
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="row">
                        <div class="col-lg-12">
                            <div name="filter-exact-results">
                                <div class="">
                                    <toggle-button :width="45" :height="22" v-model="searchExact" sync />
                                    <p style="display: inline">Filter the results by exact string</p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="row">
                        <div class="col-lg-12">
                            <div style="display: inline-block">
                                <p style="padding: 20px 0;">
                                    <b>*</b> This will only affect the language of the retrieved metadata file contents and episode filenames.<br>
                                    This <b>DOES NOT</b> allow Medusa to download non-english TV episodes!
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="row">
                <div class="col-lg-12">
                    <div v-show="displayStatus === 'searching'">
                        <img :src="spinnerSrc" height="32" width="32">
                        Searching <b>{{ currentSearch.query }}</b>
                        on {{ currentSearch.indexerName }}
                        in {{ currentSearch.languageName }}...
                    </div>
                    <div v-if="displayStatus === 'results'" class="search-results">
                        <legend class="legendStep">Search Results:</legend>
                        <table v-if="filteredSearchResults.length !== 0" class="search-results">
                            <thead>
                                <tr>
                                    <th />
                                    <th>Show Name</th>
                                    <th class="premiere">Premiere</th>
                                    <th class="network">Network</th>
                                    <th class="indexer">Indexer</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="result in filteredSearchResults" :key="result.slug" @click="selectResult(result)" :class="{ selected: selectedShowSlug === result.slug }">
                                    <td class="search-result">
                                        <input v-if="!result.alreadyAdded || fromChangeIndexer" v-model="selectedShowSlug" type="radio" :value="result.slug">
                                        <app-link v-else :href="result.alreadyAdded" title="Show already added - jump to show page">
                                            <img height="16" width="16" src="images/ico/favicon-16.png">
                                        </app-link>
                                    </td>
                                    <td>
                                        <app-link :href="result.indexerShowUrl" title="Go to the show's page on the indexer site">
                                            <b>{{ result.showName }}</b>
                                            <span v-if="String(result.showId) === currentSearch.query"
                                                  v-tooltip.right="'This is an exact match based on the show id'"
                                            >
                                                *
                                            </span>
                                        </app-link>
                                    </td>
                                    <td class="premiere">{{ result.premiereDate }}</td>
                                    <td class="network">{{ result.network }}</td>
                                    <td class="indexer">
                                        {{ result.indexerName }}
                                        <img height="16" width="16" :src="result.indexerIcon">
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                        <div v-else class="no-results">
                            <b>No results found, try a different search.</b>
                        </div>
                    </div>
                </div>
            </div>

        </div>
        <div class="row" v-if="fromChangeIndexer">
            <div class="col-lg-12">
                <button class="btn-medusa" @click="$emit('close')">Close</button>
            </div>
        </div>
    </div>
</template>
<script>
import { mapGetters, mapState } from 'vuex';
import { ToggleButton } from 'vue-js-toggle-button';
import { AppLink, LanguageSelect } from './helpers';
import { VTooltip } from 'v-tooltip';
import ExistingShowDialog from './modals/existing-show-dialog.vue';
import axios from 'axios';

export default {
    name: 'new-show-search',
    components: {
        AppLink,
        ToggleButton,
        LanguageSelect
    },
    directives: {
        tooltip: VTooltip
    },
    props: {
        providedInfo: {
            default() {
                return {
                    use: false,
                    showId: null,
                    showName: '',
                    showDir: '',
                    indexerId: '',
                    indexerLanguage: 'en',
                    unattended: false
                };
            }
        },
        selectedRootDir: String,
        fromChangeIndexer: Boolean
    },
    data() {
        return {
            // Show Search
            searchStatus: '',
            searchResults: [],
            searchExact: false,
            nameToSearch: '',
            indexerId: 0,
            indexerLanguage: null,
            currentSearch: {
                cancel: null,
                query: null,
                indexerName: null,
                languageName: null
            },

            selectedShowSlug: '',
            existingFolder: null
        };
    },
    mounted() {
        setTimeout(() => {
            if (this.$refs.nameToSearch) {
                this.$refs.nameToSearch.focus();

                if (this.nameToSearch) {
                    this.searchIndexers();
                }
            }
        }, 500);

        const { general } = this;
        // Set the indexer to the indexer default.
        if (general.indexerDefault) {
            this.indexerId = general.indexerDefault;
        }

        // Set default indexer language.
        this.indexerLanguage = general.indexerDefaultLanguage;

        // Set the default show name, if provided through show dir or show name.
        this.nameToSearch = this.defaultShowName;
    },
    computed: {
        ...mapState({
            general: state => state.config.general,
            layout: state => state.config.layout,
            indexers: state => state.config.indexers,
            client: state => state.auth.client
        }),
        ...mapGetters(['indexerIdToName']),
        selectedShow() {
            const { filteredSearchResults, selectedShowSlug } = this;
            if (filteredSearchResults.length === 0 || !filteredSearchResults) {
                return null;
            }

            return filteredSearchResults.find(s => s.slug === selectedShowSlug);
        },
        filteredSearchResults() {
            const { nameToSearch, searchExact, searchResults } = this;

            if (searchExact) {
                return searchResults.filter(result => result.showName.toLowerCase().includes(nameToSearch.toLowerCase()));
            }

            // Place results where the showId matches the search query on top.
            searchResults.sort((a, _) => {
                if (nameToSearch === String(a.showId)) {
                    return -1;
                }
                return 1;
            });

            return searchResults;
        },
        spinnerSrc() {
            const { layout } = this;
            const { themeName } = layout;
            const themeSpinner = themeName === 'dark' ? '-dark' : '';
            return 'images/loading32' + themeSpinner + '.gif';
        },
        displayStatus() {
            const { currentSearch } = this;
            if (currentSearch.cancel !== null) {
                return 'searching';
            }

            return 'results';
        },
        indexerListOptions() {
            const { indexers } = this;
            const allIndexers = [{ text: 'All Indexers', value: 0 }];

            const indexerOptions = Object.values(indexers.indexers).map(indexer => ({ value: indexer.id, text: indexer.name }));
            return [...allIndexers, ...indexerOptions];
        },
        defaultShowName() {
            // Moved this logic from add_shows.py.
            const { providedInfo, showBaseName } = this;
            if (providedInfo.showName) {
                return providedInfo.showName;
            }

            if (providedInfo.showDir) {
                // Try to get a show name from the show dir.
                const titleWithoutYear = providedInfo.showDir.replace(/\(?\d{4}\)?/gi, '');
                titleWithoutYear.split(/[/\\]/).pop();
                return showBaseName(titleWithoutYear).trim();
            }

            return '';
        }
    },
    methods: {
        selectResult(result) {
            const { alreadyAdded } = result;
            if (alreadyAdded) {
                return;
            }
            this.selectedShowSlug = result.slug;
        },
        async searchIndexers() {
            const {
                client, currentSearch, general,
                nameToSearch, indexerLanguage,
                indexerId, indexerIdToName, indexers
            } = this;
            const { indexerTimeout } = general;

            if (!nameToSearch) {
                return;
            }

            // Get the language name
            const indexerLanguageSelect = this.$refs.indexerLanguage.$el;
            const indexerLanguageName = indexerLanguageSelect[indexerLanguageSelect.selectedIndex].text;

            const indexerName = indexerId === 0 ? 'All Indexers' : indexerIdToName(indexerId);

            if (currentSearch.cancel) {
                // If a search is currently running, and the new search is the same, don't start a new search
                const sameQuery = nameToSearch === currentSearch.query;
                const sameIndexer = indexerName === currentSearch.indexerName;
                const sameLanguage = indexerLanguageName === currentSearch.languageName;
                if (sameQuery && sameIndexer && sameLanguage) {
                    return;
                }
                // Abort search before starting a new one
                currentSearch.cancel();
                currentSearch.cancel = null;
            }

            currentSearch.query = nameToSearch;
            currentSearch.indexerName = indexerName;
            currentSearch.languageName = indexerLanguageName;

            this.selectedShowSlug = '';
            this.searchResults = [];

            const config = {
                params: {
                    query: nameToSearch,
                    indexerId,
                    language: indexerLanguage
                },
                timeout: indexerTimeout * 1000,
                // An executor function receives a cancel function as a parameter
                cancelToken: new axios.CancelToken(cancel => {
                    currentSearch.cancel = cancel;
                })
            };

            let data = null;
            try {
                const response = await client.api.get('internal/searchIndexersForShowName', config);
                data = response.data;
            } catch (error) {
                if (axios.isCancel(error)) {
                    // Request cancelled
                    return;
                }
                if (error.code === 'ECONNABORTED') {
                    // Request timed out
                    this.searchStatus = 'Search timed out, try again or try another indexer';
                    return;
                }
                // Request failed
                this.searchStatus = 'Search failed with error: ' + error;
                return;
            } finally {
                currentSearch.cancel = null; // eslint-disable-line  require-atomic-updates
            }

            if (!data) {
                return;
            }

            this.searchResults = data.results
                .map(result => {
                    // Unpack result items 0 through 8 (Array)
                    let [
                        indexerName,
                        indexerId,
                        indexerShowUrl,
                        showId,
                        showName,
                        premiereDate,
                        network,
                        sanitizedName,
                        alreadyAdded
                    ] = result;

                    const slug = [indexers.indexers[indexerIdToName(indexerId)].identifier, showId].join('');

                    // Append showId to indexer show url
                    if (indexerName === 'IMDb') {
                        indexerShowUrl += String(showId).padStart(7, '0');
                    } else {
                        indexerShowUrl += showId;
                    }

                    // Discard 'N/A' and '1900-01-01'
                    const filter = string => ['N/A', '1900-01-01'].includes(string) ? '' : string;
                    premiereDate = filter(premiereDate);
                    network = filter(network);

                    const indexerIcon = `images/${indexers.indexers[indexerIdToName(indexerId)].icon}`;

                    alreadyAdded = (() => {
                        if (!alreadyAdded) {
                            return false;
                        }
                        // Extract existing show info
                        const [matchIndexerName, matchShowId] = alreadyAdded;
                        return `home/displayShow?showslug=${matchIndexerName}${matchShowId}`;
                    })();

                    return {
                        slug,
                        indexerName,
                        indexerId,
                        indexerShowUrl,
                        indexerIcon,
                        showId,
                        showName,
                        premiereDate,
                        network,
                        sanitizedName,
                        alreadyAdded
                    };
                });

            this.searchStatus = '';

            this.$nextTick(() => {
                this.$emit('navigate-step', 0);
            });
        },
        /**
         * Helper to get the indexer object.
         * @param {number} indexerId - indexers id
         * @return {string} - The indexers base showUrl.
         */
        getIndexer(indexerId) {
            const { indexers } = this;
            if (!indexerId) {
                return;
            }
            return Object.values(indexers.indexers).find(indexer => indexer.id === indexerId);
        },
        showBaseName(name) {
            const sepChar = (() => {
                if (name.includes('\\')) {
                    return '\\';
                }
                if (name.includes('/')) {
                    return '/';
                }
                return '';
            })();
            return name.split(sepChar).slice(-1)[0];
        },
        async checkFolder() {
            // Check if selected show already has a folder in one of the root dirs.
            // We only check this for the addNewShow route.
            const { client, indexerIdToName, selectedRootDir, selectedShow } = this;

            if (this.$route.name === 'addExistingShows' || !selectedShow || !selectedRootDir) {
                return;
            }

            const { showName } = selectedShow;

            try {
                const response = await client.api.get('internal/checkForExistingFolder', { params: {
                    showdir: '', rootdir: selectedRootDir, title: showName
                } });
                const { data } = response;

                if (data.pathInfo.pathExists) {
                    this.existingFolder = data.pathInfo;
                    if (data.pathInfo.metadata &&
                        selectedShow.indexerId !== data.pathInfo.metadata.indexer &&
                        selectedShow.showId !== data.pathInfo.metadata.seriesId) {
                        this.$modal.show(ExistingShowDialog, {
                            indexerName: indexerIdToName(data.pathInfo.metadata.indexer),
                            eventCallback: param => {
                                if (param.answer === 'yes') {
                                    this.indexerId = data.pathInfo.metadata.indexer;
                                    this.nameToSearch = data.pathInfo.metadata.seriesId;
                                    this.searchIndexers();
                                }
                            }
                        },
                        { height: 'auto' }
                        );
                    }
                }
            } catch (error) {
                this.$snotify.warning('Error while checking for existing folder');
            }
        }
    },
    watch: {
        filteredSearchResults(newResults, oldResults) {
            if (oldResults.length === newResults.length) {
                return;
            }

            // Select the first available result
            const firstAvailableResult = newResults.find(result => !result.alreadyAdded);
            if (firstAvailableResult) {
                this.selectedShowSlug = firstAvailableResult.slug;
            }
        },
        selectedShowSlug(showSlug) {
            const { filteredSearchResults } = this;
            this.checkFolder();
            this.$emit('selected', { result: filteredSearchResults.find(s => s.slug === showSlug) });
        }
    }
};
</script>
<style scoped>
.show-add-option {
    float: left;
    padding-right: 10px;
    line-height: 40px;
}

@media (max-width: 768px) {
    .show-add-option {
        float: none;
    }

    .show-add-option > input.input350 {
        width: 100%;
    }
}
</style>

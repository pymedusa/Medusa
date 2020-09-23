<template>
    <div class="newShowPortal">
        <vue-tabs>
            <v-tab key="add_new_show" title="Add New Show">
                <div id="core-component-group1" class="tab-pane active component-group">
                    <div id="displayText">Adding show <b v-html="showName" /> {{showPathPreposition}} <b v-html="showPath" /></div>
                    <br>

                    <form id="addShowForm" @submit.prevent="">

                        <form-wizard ref="formwizard" class="formwizard" title="" subtitle="" @change="updateFormWizardStep" color="rgb(95, 95, 95)">
                            <template slot="step" slot-scope="props">
                                <div class="step" :class="{disabledstep: !props.tab.active}" @click="navigateStep(props.index)">
                                    Step {{props.index + 1}}<div class="smalltext">{{props.tab.title}}</div>
                                </div>
                            </template>

                            <template slot="finish">
                                <button @click.prevent="submitForm" type="button" :disabled="addButtonDisabled">Add Show</button>
                            </template>

                            <tab-content title="Find a show on selected indexer(s)">
                                <div v-if="providedInfo.use" class="stepDiv">
                                    Show retrieved from existing metadata:
                                    <span v-if="providedInfo.indexerId !== 0 && providedInfo.showId !== 0">
                                        <app-link :href="`${getIndexer(providedInfo.indexerId).showUrl}${providedInfo.showId}`">
                                            <b>{{ providedInfo.showName }}</b>
                                        </app-link>
                                        <br>
                                        Show indexer:
                                        <b>{{ getIndexer(providedInfo.indexerId).name }}</b>
                                        <img height="16" width="16" :src="`images/'${getIndexer(providedInfo.indexerId).icon}`">
                                    </span>
                                    <span v-else>
                                        <b>{{ providedInfo.showName }}</b>
                                    </span>
                                </div>
                                <div v-else class="stepDiv">
                                    <div class="row">
                                        <div class="col-lg-12">
                                            <div class="row">
                                                <div class="col-lg-12 show-add-options">
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
                                                                <input v-if="!result.alreadyAdded" v-model="selectedShowSlug" type="radio" :value="result.slug">
                                                                <app-link v-else :href="result.alreadyAdded" title="Show already added - jump to show page">
                                                                    <img height="16" width="16" src="images/ico/favicon-16.png">
                                                                </app-link>
                                                            </td>
                                                            <td>
                                                                <app-link :href="result.indexerShowUrl" title="Go to the show's page on the indexer site">
                                                                    <b>{{ result.showName }}</b>
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
                            </tab-content>
                            <tab-content title="Pick the parent folder">
                                <div v-if="providedInfo.showDir" class="stepDiv">
                                    Pre-chosen Destination Folder: <b>{{ providedInfo.showDir }}</b><br>
                                </div>
                                <div v-else class="stepDiv">
                                    <root-dirs @update="rootDirsUpdated" />
                                </div>
                            </tab-content>
                            <tab-content title="Customize options">
                                <div class="stepDiv">
                                    <add-show-options v-bind="{showName, enableAnimeOptions}" @change="updateOptions" @refresh="refreshOptionStep" />
                                </div>
                            </tab-content>
                        </form-wizard>
                    </form>
                    <br>
                    <div style="width: 100%; text-align: center;">
                        <input @click.prevent="submitForm" class="btn-medusa" type="button" value="Add Show" :disabled="addButtonDisabled">
                        <!-- <input v-if="skipShowVisible" @click.prevent="submitForm(true);" class="btn-medusa" type="button" value="Skip Show">
                        <p v-if="otherShows.length !== 0"><i>({{ otherShows.length }} more {{ otherShows.length > 1 ? 'shows' : 'show' }} left)</i></p>
                        <p v-else-if="skipShowVisible"><i>(last show)</i></p> -->
                    </div>
                </div>
            </v-tab>
        </vue-tabs>
    </div>
</template>
<script>
import { mapGetters, mapState } from 'vuex';
import { ToggleButton } from 'vue-js-toggle-button';
import RootDirs from './root-dirs.vue';
import { AddShowOptions } from '.';
import { AppLink, LanguageSelect } from './helpers';
import { api } from '../api';
import axios from 'axios';
import { VueTabs, VTab } from 'vue-nav-tabs/dist/vue-tabs.js';
import { FormWizard, TabContent } from 'vue-form-wizard';

export default {
    name: 'new-show',
    components: {
        AddShowOptions,
        AppLink,
        FormWizard,
        TabContent,
        ToggleButton,
        LanguageSelect,
        RootDirs,
        VueTabs,
        VTab
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
                    indexerLanguage: 'en'
                };
            }
        }
    },
    data() {
        return {
            // Vueified jquery formwizard
            formwizard: {
                ref: null,
                currentIndex: 0
            },

            // Show Search
            searchStatus: '',
            searchResults: [],
            searchExact: false,
            nameToSearch: '', //'${json.dumps(default_show_name)},'
            indexerId: 0,
            indexerLanguage: null,
            currentSearch: {
                cancel: null,
                query: null,
                indexerName: null,
                languageName: null
            },

            selectedRootDir: '',
            selectedShowSlug: '',
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
                },
                showLists: []
            }
        };
    },
    mounted() {
        // const init = () => {
        //     this.$watch('formwizard.currentsection', newValue => {
        //         if (newValue === 0 && this.$refs.nameToSearch) {
        //             this.$refs.nameToSearch.focus();
        //         }
        //     });

        setTimeout(() => {
            const { providedInfo, navigateStep } = this;
            const { use, showId, showDir } = providedInfo;
            if (use && showId !== 0 && showDir) {
                navigateStep(2);
            }
        }, 100);

        setTimeout(() => {
            if (this.$refs.nameToSearch) {
                this.$refs.nameToSearch.focus();

                if (this.nameToSearch) {
                    this.searchIndexers();
                }
            }
        }, 500);
        // };

        /* JQuery Form to Form Wizard- (c) Dynamic Drive (www.dynamicdrive.com)
        *  This notice MUST stay intact for legal use
        *  Visit http://www.dynamicdrive.com/ for this script and 100s more. */
        // @TODO: we need to move to real forms instead of this
        // this.formwizard = new formtowizard({ // eslint-disable-line new-cap, no-undef
        //     formid: 'addShowForm',
        //     revealfx: ['slide', 300],
        //     oninit: init
        // });

        const { general } = this;
        // Set the indexer to the indexer default.
        if (general.indexerDefault) {
            this.indexerId = general.indexerDefault;
        }

        // Set default indexer language.
        this.indexerLanguage = general.indexerDefaultLanguage;

        // Set the default show name, if provided through show dir or show name.
        this.nameToSearch = this.defaultShowName;

        // Assign formwizard ref to this.formwizard.ref.
        this.formwizard.ref = this.$refs.formwizard;
    },
    computed: {
        ...mapState({
            general: state => state.config.general,
            layout: state => state.config.layout,
            indexers: state => state.config.indexers
        }),
        ...mapGetters(['indexerIdToName']),
        selectedShow() {
            const { filteredSearchResults, selectedShowSlug } = this;
            if (filteredSearchResults.length === 0 || !filteredSearchResults) {
                return null;
            }

            return filteredSearchResults.find(s => s.slug === selectedShowSlug);
        },
        addButtonDisabled() {
            const { selectedShowSlug, selectedRootDir, providedInfo } = this;
            if (providedInfo.use) {
                return providedInfo.showId === 0;
            }
            return !(providedInfo.showDir || selectedRootDir) || selectedShowSlug === '';
        },
        filteredSearchResults() {
            const { nameToSearch, searchExact, searchResults } = this;

            if (searchExact) {
                return searchResults.filter(result => result.showName.toLowerCase().includes(nameToSearch.toLowerCase()));
            }

            return searchResults;
        },
        // skipShowVisible() {
        //     const { otherShows, providedInfo } = this;
        //     return otherShows.length !== 0 || providedInfo.use || providedInfo.showDir;
        // },
        showName() {
            const { providedInfo, selectedShow } = this;
            // If we provided a show, use that
            if (providedInfo.use && providedInfo.showName) {
                return providedInfo.showName;
            }
            // If they've picked a radio button then use that
            if (selectedShow) {
                return selectedShow.showName;
            }
            // Not selected / not searched
            return '';
        },
        showPath() {
            const {
                selectedRootDir,
                providedInfo,
                selectedShow } = this;

            const appendSepChar = path => {
                const sepChar = (() => {
                    if (path.includes('\\')) {
                        return '\\';
                    }
                    if (path.includes('/')) {
                        return '/';
                    }
                    return '';
                })();
                return path.slice(-1) === sepChar ? path : path + sepChar;
            };

            let showPath = 'unknown dir';
            // If we provided a show path, use that
            if (providedInfo.showDir) {
                showPath = appendSepChar(providedInfo.showDir);
            // If we have a root dir selected, figure out the path
            } else if (selectedRootDir) {
                showPath = appendSepChar(selectedRootDir);
                // If we have a show selected, use the sanitized name
                const dirName = selectedShow ? selectedShow.sanitizedName : '??';
                showPath = appendSepChar(showPath + '<i>' + dirName + '</i>');
            }
            return showPath;
        },
        showPathPreposition() {
            return this.providedInfo.showDir ? 'from' : 'into';
        },
        spinnerSrc() {
            const { layout } = this;
            const { themeName } = layout;
            const themeSpinner = themeName === 'dark' ? '-dark' : '';
            return 'images/loading32' + themeSpinner + '.gif';
        },
        displayStatus() {
            const { currentSearch, searchStatus } = this;
            if (currentSearch.cancel !== null) {
                return 'searching';
            }

            return 'results';
        },
        enableAnimeOptions() {
            const { providedInfo, selectedShow } = this;
            return Boolean((selectedShow && selectedShow.indexerId === 1) || (providedInfo.use && providedInfo.indexerId === 1));
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
                const titleWithoutYear = providedInfo.showDir.replace(/\d{4}/gi, '');
                titleWithoutYear.split(/[/\\]/).pop();
                return showBaseName(titleWithoutYear);
            }

            return '';
        }
    },
    methods: {
        async submitForm() {
            const { addButtonDisabled } = this;

            // If they haven't picked a show or a root dir don't let them submit
            if (addButtonDisabled) {
                this.$snotify.warning('You must choose a show and a parent folder to continue.');
                return;
            }

            // Collect all the needed form data.

            const {
                indexerIdToName,
                indexerLanguage,
                providedInfo,
                selectedRootDir,
                selectedShow,
                selectedShowOptions
            } = this;

            const showId = {};
            const options = {};

            if (providedInfo.use) {
                options.language = providedInfo.indexerLanguage;
                showId[indexerIdToName(providedInfo.indexerId)] = providedInfo.showId;
            } else {
                options.language = indexerLanguage;
                showId[indexerIdToName(selectedShow.indexerId)] = selectedShow.showId;
            }

            if (providedInfo.showDir) {
                options.showDir = providedInfo.showDir;
            } else {
                options.rootDir = selectedRootDir;
            }

            const {
                anime,
                quality,
                release,
                scene,
                seasonFolders,
                status,
                statusAfter,
                subtitles,
                showLists
            } = selectedShowOptions;

            // Show options
            options.status = status;
            options.statusAfter = statusAfter;
            options.subtitles = Boolean(subtitles);
            options.anime = Boolean(anime);
            options.scene = Boolean(scene);
            options.seasonFolders = Boolean(seasonFolders);
            options.quality = quality;
            options.release = release;
            options.showlists = showLists;

            let response = null;
            try {
                const { $router } = this;
                response = await api.post('series', { id: showId, options }, { timeout: 60000 });
                if (response.status === 201) {
                    this.$emit('added', response.data);

                    // If we're not using this component from addExistingShow, route to home.
                    if (this.$route.name === 'addNewShow') {
                        $router.push({ name: 'home' });
                    }
                }
            } catch (error) {
                if (error.includes('409')) {
                    // Show already exists
                    this.$snotify.error(
                        'Show already exists',
                        `Error trying to add show ${Object.keys(showId)[0]}${showId[Object.keys(showId)[0]]}`
                    );
                    this.$emit('error', { message: 'Show already exists' });
                } else {
                    this.$snotify.error(
                        `Error trying to add show ${Object.keys(showId)[0]}${showId[Object.keys(showId)[0]]}`
                    );
                    this.$emit('error', { message: `Error trying to add show ${Object.keys(showId)[0]}${showId[Object.keys(showId)[0]]}` });
                }
            }
        },
        selectResult(result) {
            const { alreadyAdded } = result;
            if (alreadyAdded) {
                return;
            }
            this.selectedShowSlug = result.slug;
        },
        rootDirsUpdated(rootDirs) {
            this.selectedRootDir = rootDirs.length === 0 ? '' : rootDirs.find(rd => rd.selected).path;
        },
        async searchIndexers() {
            const { currentSearch, general, nameToSearch, indexerLanguage, indexerId, indexerIdToName, indexers } = this;
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

            // this.$nextTick(() => this.formwizard.loadsection(0)); // eslint-disable-line no-use-before-define

            let data = null;
            try {
                const response = await api.get('internal/searchIndexersForShowName', config);
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
                    indexerShowUrl += showId;
                    // TheTVDB.com no longer supports that feature
                    // For now only add the languageId id to the tvdb url, as the others might have different routes.
                    /* if (languageId && languageId !== '' && indexerId === 1) {
                        indexerShowUrl += '&lid=' + languageId
                    } */

                    // Discard 'N/A' and '1900-01-01'
                    const filter = string => ['N/A', '1900-01-01'].includes(string) ? '' : string;
                    premiereDate = filter(premiereDate);
                    network = filter(network);

                    const indexerIcon = 'images/' + indexers.indexers[indexerIdToName(indexerId)].icon;

                    alreadyAdded = (() => {
                        if (!alreadyAdded) {
                            return false;
                        }
                        // Extract existing show info
                        const [matchIndexerName, matchShowId] = alreadyAdded;
                        return 'home/displayShow?indexername=' + matchIndexerName + '&seriesid=' + matchShowId;
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

            // this.$nextTick(() => {
            //     this.formwizard.loadsection(0); // eslint-disable-line no-use-before-define
            // });
        },
        /**
         * The formwizard sets a fixed height when the step has been loaded. We need to refresh this on the option
         * page, when showing/hiding the release groups.
         */
        refreshOptionStep() {
            if (this.formwizard.currentStep === 2) {
                this.$nextTick(() => this.formwizard.loadsection(2));
            }
        },
        updateFormWizardStep(_, nextIndex) {
            this.formwizard.currentIndex = nextIndex;
        },
        navigateStep(newIndex) {
            this.formwizard.ref.changeTab(0, newIndex);
        },
        updateOptions(options) {
            // Update seleted options from add-show-options.vue @change event.
            this.selectedShowOptions.subtitles = options.subtitles;
            this.selectedShowOptions.status = options.status;
            this.selectedShowOptions.statusAfter = options.statusAfter;
            this.selectedShowOptions.seasonFolders = options.seasonFolders;
            this.selectedShowOptions.anime = options.anime;
            this.selectedShowOptions.scene = options.scene;
            this.selectedShowOptions.release.blacklist = options.release.blacklist;
            this.selectedShowOptions.release.whitelist = options.release.whitelist;
            this.selectedShowOptions.quality.allowed = options.quality.allowed;
            this.selectedShowOptions.quality.preferred = options.quality.preferred;
            this.selectedShowOptions.showLists = options.showLists;
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
        }
    }
};
</script>
<style scoped>
.formwizard >>> ul.wizard-nav {
    display: flex;
    justify-content: space-around;
    padding-left: 0;
}

ul.wizard-nav > div.step {
    width: 33.3333%;
    display: table-cell;
    font: bold 24px Arial, sans-serif;
    font-style: normal;
    font-variant-ligatures: normal;
    font-variant-caps: normal;
    font-variant-numeric: normal;
    font-variant-east-asian: normal;
    font-weight: bold;
    font-stretch: normal;
    font-size: 24px;
    line-height: normal;
    font-family: Arial, sans-serif;
    border-bottom: 4px solid rgb(87, 68, 43);
    cursor: pointer;
}

.formwizard >>> .wizard-nav .step {
    margin: 12px 0;
    border-bottom: 4px solid rgb(35, 175, 220);
}

.formwizard >>> ul.wizard-nav .disabledstep {
    border-bottom: 4px solid rgb(17, 120, 179);
}

ul.wizard-nav .step .smalltext {
    font-size: 13px;
    font-weight: normal;
    margin-bottom: 12px;
}

.formwizard >>> .wizard-footer-left {
    float: left;
}

.formwizard >>> .wizard-footer-right {
    float: right;
}

.formwizard >>> .wizard-card-footer span {
    padding: 3px 6px;
    cursor: hand;
    cursor: pointer;
    opacity: 0.65;
    /* move to themed */
    color: rgb(255, 255, 255);
    background: rgb(95, 95, 95);
}

.formwizard >>> .wizard-card-footer button {
    border-width: 0;
    /* move to themed */
    background-color: rgb(95, 95, 95);
    border-color: rgb(95, 95, 95); color: white;
}

</style>

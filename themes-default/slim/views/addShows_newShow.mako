<%inherit file="/layouts/main.mako"/>
<%!
    import json

    from medusa import app
    from medusa.indexers.indexer_api import indexerApi
    from medusa.indexers.indexer_config import indexerConfig

    from six import iteritems, text_type
%>
<%block name="scripts">
<script type="text/javascript" src="js/add-show-options.js?${sbPID}"></script>
<script type="text/javascript" src="js/blackwhite.js?${sbPID}"></script>
<%
    valid_indexers = {
        '0': {
            'name': 'All Indexers'
        }
    }
    valid_indexers.update({
        text_type(indexer): {
            'name': config['name'],
            'showUrl': config['show_url'],
            'icon': config['icon'],
            'identifier': config['identifier']
        }
        for indexer, config in iteritems(indexerConfig)
        if config.get('enabled', None)
    })
%>
<script>
window.app = {};
window.app = new Vue({
    store,
    router,
    el: '#vue-wrap',
    data() {
        return {
            // @TODO: Fix Python conversions
            formwizard: null,
            otherShows: ${json.dumps(other_shows)},

            // Show Search
            searchStatus: '',
            firstSearch: false,
            searchResults: [],
            indexers: ${json.dumps(valid_indexers)},
            indexerTimeout: ${app.INDEXER_TIMEOUT},
            validLanguages: ${json.dumps(indexerApi().config['valid_languages'])},
            nameToSearch: ${json.dumps(default_show_name)},
            indexerId: ${provided_indexer or 0},
            indexerLanguage: ${json.dumps(app.INDEXER_DEFAULT_LANGUAGE)},
            currentSearch: {
                cancel: null,
                query: null,
                indexerName: null,
                languageName: null
            },

            // Provided info
            providedInfo: {
                use: ${json.dumps(use_provided_info)},
                showId: ${provided_indexer_id},
                showName: ${json.dumps(provided_indexer_name)},
                showDir: ${json.dumps(provided_show_dir)},
                indexerId: ${provided_indexer},
                indexerLanguage: 'en',
            },

            selectedRootDir: '',
            selectedShowSlug: ''
        };
    },
    mounted() {
        const init = () => {
            this.$watch('formwizard.currentsection', newValue => {
                if (newValue === 0 && this.$refs.nameToSearch) {
                    this.$refs.nameToSearch.focus();
                }
            });

            setTimeout(() => {
                this.updateBlackWhiteList();

                const { providedInfo } = this;
                const { use, showId, showDir } = providedInfo;
                if (use && showId !== 0 && showDir) {
                    this.formwizard.loadsection(2);
                }
            }, 100);

            setTimeout(() => {
                if (this.$refs.nameToSearch) {
                    this.$refs.nameToSearch.focus();

                    if (this.nameToSearch) {
                        this.searchIndexers();
                    }
                }
            }, this.formwizard.setting.revealfx[1]);
        };

        /* JQuery Form to Form Wizard- (c) Dynamic Drive (www.dynamicdrive.com)
        *  This notice MUST stay intact for legal use
        *  Visit http://www.dynamicdrive.com/ for this script and 100s more. */
        // @TODO: we need to move to real forms instead of this
        this.formwizard = new formtowizard({ // eslint-disable-line new-cap, no-undef
            formid: 'addShowForm',
            revealfx: ['slide', 300],
            oninit: init
        });

        $(document.body).on('change', 'select[name="quality_preset"]', () => {
            this.$nextTick(() => this.formwizard.loadsection(2));
        });

        $(document.body).on('change', '#anime', () => {
            this.updateBlackWhiteList();
            this.$nextTick(() => this.formwizard.loadsection(2));
        });
    },
    computed: {
        config() {
            return this.$store.state.config;
        },
        selectedShow() {
            const { searchResults, selectedShowSlug } = this;
            if (searchResults.length === 0 || !selectedShowSlug) return null;
            return searchResults.find(s => s.slug === selectedShowSlug);
        },
        addButtonDisabled() {
            const { selectedShowSlug, selectedRootDir, providedInfo } = this;
            if (providedInfo.use) return providedInfo.showId === 0;
            return !(providedInfo.showDir || selectedRootDir) || selectedShowSlug === '';
        },
        skipShowVisible() {
            const { otherShows, providedInfo } = this;
            return otherShows.length !== 0 || providedInfo.use || providedInfo.showDir;
        },
        showName() {
            const { providedInfo, selectedShow } = this;
            // If we provided a show, use that
            if (providedInfo.use && providedInfo.showName) return providedInfo.showName;
            // If they've picked a radio button then use that
            if (selectedShow !== null) return selectedShow.showName;
            // Not selected / not searched
            return '';
        },
        showPath() {
            const { selectedRootDir, providedInfo, selectedShow } = this;

            const appendSepChar = path => {
                const sepChar = (() => {
                    if (path.includes('\\')) return '\\';
                    if (path.includes('/')) return '/';
                    return '';
                })();
                return path.slice(-1) !== sepChar ? path + sepChar : path;
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
            const { config } = this;
            const { themeName } = config;
            const themeSpinner = themeName === 'dark' ? '-dark' : '';
            return 'images/loading32' + themeSpinner + '.gif';
        },
        displayStatus() {
            const { currentSearch, firstSearch, searchStatus } = this;
            if (currentSearch.cancel !== null) return 'searching';
            if (!firstSearch || searchStatus !== '') return 'status';
            return 'results';
        }
    },
    methods: {
        async submitForm(skipShow) {
            const { currentSearch, addButtonDisabled } = this;

            let formData;

            if (skipShow && skipShow === true) {
                formData = new FormData();
                formData.append('skipShow', 'true');

                if (currentSearch.cancel) {
                    // Abort current search
                    currentSearch.cancel();
                    currentSearch.cancel = null;
                }
            } else {
                // If they haven't picked a show or a root dir don't let them submit
                if (addButtonDisabled) {
                    this.$snotify.warning('You must choose a show and a parent folder to continue.');
                    return;
                }

                // Converts select boxes to command separated values [js/blackwhite.js]
                generateBlackWhiteList(); // eslint-disable-line no-undef

                formData = new FormData(this.$refs.addShowForm);
            }

            this.otherShows.forEach(nextShow => formData.append('other_shows', nextShow));

            const response = await apiRoute.post('addShows/addNewShow', formData);
            const { data } = response;
            const { result, message, redirect, params } = data;

            if (message) {
                if (result === false) {
                    console.log('Error: ' + message);
                } else {
                    console.log('Response: ' + message);
                }
            }
            if (redirect) {
                const baseUrl = apiRoute.defaults.baseURL;
                if (params.length === 0) {
                    window.location.href = baseUrl + redirect;
                    return;
                }

                const form = document.createElement('form');
                form.method = 'POST';
                form.action = baseUrl + redirect;
                form.acceptCharset = 'utf-8';

                params.forEach(param => {
                    const element = document.createElement('input');
                    [ element.name, element.value ] = param; // Unpack
                    form.appendChild(element);
                });

                document.body.appendChild(form);
                form.submit();
            }
        },
        selectResult(result) {
            const { alreadyAdded, identifier } = result;
            if (alreadyAdded) return;
            this.selectedShowSlug = result.slug;
        },
        rootDirsUpdated(rootDirs) {
            this.selectedRootDir = rootDirs.length === 0 ? '' : rootDirs.find(rd => rd.selected).path;
        },
        async searchIndexers() {
            let { currentSearch, nameToSearch, indexerLanguage, indexerId, indexerTimeout, indexers } = this;

            if (!nameToSearch) return;

            // Get the language name
            const indexerLanguageSelect = this.$refs.indexerLanguage.$el;
            const indexerLanguageName = indexerLanguageSelect[indexerLanguageSelect.selectedIndex].text;

            const indexerName = indexers[indexerId].name;

            if (currentSearch.cancel) {
                // If a search is currently running, and the new search is the same, don't start a new search
                const sameQuery = nameToSearch === currentSearch.query;
                const sameIndexer = indexerName == currentSearch.indexerName;
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
                    indexerId: indexerId,
                    language: indexerLanguage
                },
                timeout: indexerTimeout * 1000,
                // An executor function receives a cancel function as a parameter
                cancelToken: new axios.CancelToken(cancel => currentSearch.cancel = cancel)
            };

            this.$nextTick(() => this.formwizard.loadsection(0)); // eslint-disable-line no-use-before-define

            let data = null;
            try {
                const response = await api.get('internal/searchIndexersForShowName', config);
                data = response.data;
            }
            catch (error) {
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
            }
            finally {
                currentSearch.cancel = null;
            }

            if (!data) return;

            const { languageId } = data;
            this.searchResults = data.results
                .map(result => {
                    // Compute whichSeries value (without the 2 last items - sanitizedName and alreadyAdded)
                    whichSeries = result.slice(0, -2).join('|');

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

                    slug = [indexers[indexerId].identifier, showId].join('')

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

                    indexerIcon = 'images/' + indexers[indexerId].icon;

                    alreadyAdded = (() => {
                        if (!alreadyAdded) return false;
                        // Extract existing show info
                        const [ matchIndexerName, matchShowId ] = alreadyAdded;
                        return 'home/displayShow?indexername=' + matchIndexerName + '&seriesid=' + matchShowId;
                    })();

                    return {
                        slug,
                        whichSeries,
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

            // Select the first available result
            const firstAvailableResult = this.searchResults.find(result => !result.alreadyAdded);
            if (firstAvailableResult) {
                this.selectedShowSlug = firstAvailableResult.slug;
            }

            this.searchStatus = '';
            this.firstSearch = true;

            this.$nextTick(() => {
                this.formwizard.loadsection(0); // eslint-disable-line no-use-before-define
            });
        },
        updateBlackWhiteList() {
            // Currently requires jQuery
            if ($ === undefined) return;
            $.updateBlackWhiteList(this.showName);
        }
    }
});
</script>
</%block>
<%block name="content">
<vue-snotify></vue-snotify>
<h1 class="header">{{ $route.meta.header }}</h1>
<div class="newShowPortal">
    <div id="config-components">
        <ul><li><app-link href="#core-component-group1">Add New Show</app-link></li></ul>
        <div id="core-component-group1" class="tab-pane active component-group">
            <div id="displayText">Adding show <b v-html="showName"></b> {{showPathPreposition}} <b v-html="showPath"></b></div>
            <br>
            <form id="addShowForm" ref="addShowForm" method="post" action="addShows/addNewShow" accept-charset="utf-8">
                <fieldset class="sectionwrap">
                    <legend class="legendStep">Find a show on selected indexer(s)</legend>
                    <div v-if="providedInfo.use" class="stepDiv">
                        Show retrieved from existing metadata:
                        <span v-if="providedInfo.indexerId !== 0 && providedInfo.showId !== 0">
                            <app-link :href="indexers[providedInfo.indexerId].showUrl + providedInfo.showId.toString()">
                                <b>{{ providedInfo.showName }}</b>
                            </app-link>
                            <br>
                            Show indexer:
                            <b>{{ indexers[providedInfo.indexerId].name }}</b>
                            <img height="16" width="16" :src="'images/' + indexers[providedInfo.indexerId].icon" />
                        </span>
                        <span v-else>
                            <b>{{ providedInfo.showName }}</b>
                        </span>
                        <input type="hidden" name="indexer_lang" :value="providedInfo.indexerLanguage" />
                        <input type="hidden" name="whichSeries" :value="providedInfo.showId" />
                        <input type="hidden" name="providedIndexer" :value="providedInfo.indexerId" />
                    </div>
                    <div v-else class="stepDiv">
                        <input type="text" v-model.trim="nameToSearch" ref="nameToSearch" @keyup.enter="searchIndexers" class="form-control form-control-inline input-sm input350"/>
                        &nbsp;&nbsp;
                        <language-select @update-language="indexerLanguage = $event" ref="indexerLanguage" name="indexer_lang" :language="indexerLanguage" :available="validLanguages.join(',')" class="form-control form-control-inline input-sm"></language-select>
                        <b>*</b>
                        &nbsp;
                        <select name="providedIndexer" v-model.number="indexerId" class="form-control form-control-inline input-sm">
                            <option v-for="(indexer, indexerId) in indexers" :value="indexerId">{{indexer.name}}</option>
                        </select>
                        &nbsp;
                        <input class="btn-medusa btn-inline" type="button" value="Search" @click="searchIndexers" />

                        <p style="padding: 20px 0;">
                            <b>*</b> This will only affect the language of the retrieved metadata file contents and episode filenames.<br>
                            This <b>DOES NOT</b> allow Medusa to download non-english TV episodes!
                        </p>

                        <div v-show="displayStatus === 'searching'">
                            <img :src="spinnerSrc" height="32" width="32" />
                            Searching <b>{{ currentSearch.query }}</b>
                            on {{ currentSearch.indexerName }}
                            in {{ currentSearch.languageName }}...
                        </div>
                        <div v-show="displayStatus === 'status'" v-html="searchStatus"></div>
                        <div v-if="displayStatus === 'results'" class="search-results">
                            <legend class="legendStep">Search Results:</legend>
                            <table v-if="searchResults.length !== 0" class="search-results">
                                <thead>
                                    <tr>
                                        ## @TODO: Remove the need for the whichSeries value
                                        <th><input v-if="selectedShow !== null" type="hidden" name="whichSeries" :value="selectedShow.whichSeries" /></th>
                                        <th>Show Name</th>
                                        <th class="premiere">Premiere</th>
                                        <th class="network">Network</th>
                                        <th class="indexer">Indexer</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr v-for="result in searchResults" @click="selectResult(result)" :class="{ selected: selectedShowSlug === result.slug }">
                                        <td class="search-result">
                                            <input v-if="!result.alreadyAdded" v-model="selectedShowSlug" type="radio" :value="result.slug" />
                                            <app-link v-else :href="result.alreadyAdded" title="Show already added - jump to show page">
                                                <img height="16" width="16" src="images/ico/favicon-16.png" />
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
                                            <img height="16" width="16" :src="result.indexerIcon" />
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                            <div v-else class="no-results">
                                <b>No results found, try a different search.</b>
                            </div>
                        </div>
                    </div>
                </fieldset>
                <fieldset class="sectionwrap">
                    <legend class="legendStep">Pick the parent folder</legend>
                    <div v-if="providedInfo.showDir" class="stepDiv">
                        Pre-chosen Destination Folder: <b>{{ providedInfo.showDir }}</b><br>
                        <input type="hidden" name="fullShowPath" :value="providedInfo.showDir" /><br>
                    </div>
                    <div v-else class="stepDiv">
                        <root-dirs @update="rootDirsUpdated"></root-dirs>
                    </div>
                </fieldset>
                <fieldset class="sectionwrap">
                    <legend class="legendStep">Customize options</legend>
                    <div class="stepDiv">
                        <%include file="/inc_addShowOptions.mako"/>
                    </div>
                </fieldset>
            </form>
            <br>
            <div style="width: 100%; text-align: center;">
                <input @click.prevent="submitForm" class="btn-medusa" type="button" value="Add Show" :disabled="addButtonDisabled" />
                <input v-if="skipShowVisible" @click.prevent="submitForm(true);" class="btn-medusa" type="button" value="Skip Show" />
                <p v-if="otherShows.length !== 0"><i>({{ otherShows.length }} more {{ otherShows.length > 1 ? 'shows' : 'show' }} left)</i></p>
                <p v-else-if="skipShowVisible"><i>(last show)</i></p>
            </div>
        </div>
    </div>
</div>
</%block>

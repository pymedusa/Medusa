<%inherit file="/layouts/main.mako"/>
<%!
    import json

    from medusa import app
    from medusa.indexers.indexer_api import indexerApi
    from medusa.indexers.indexer_config import indexerConfig

    from six import iteritems, text_type as str
%>
<%block name="scripts">
<script type="text/javascript" src="js/add-show-options.js?${sbPID}"></script>
<script>
window.app = {};
window.app = new Vue({
    store,
    router,
    el: '#vue-wrap',
    data() {
        <% indexers = { str(i): { 'name': v['name'], 'showUrl': v['show_url'] } for i, v in iteritems(indexerConfig) } %>
        return {
            // @FIXME: Python conversions (fix when config is loaded before routes)
            indexers: ${json.dumps(indexers)},
            defaultIndexer: ${app.INDEXER_DEFAULT},

            isLoading: false,
            requestTimeout: 3 * 60 * 1000,
            errorMessage: '',
            rootDirs: [],
            dirList: [],
            promptForSettings: false
        };
    },
    mounted() {
        // Need to delay that a bit
        setTimeout(() => {
            // Hide the black/whitelist, because it can only be used for a single anime show
            $.updateBlackWhiteList(undefined);
        }, 500);
    },
    computed: {
        selectedRootDirs() {
            return this.rootDirs.filter(rd => rd.selected);
        },
        filteredDirList() {
            return this.dirList.filter(dir => !dir.alreadyAdded);
        },
        displayPaths() {
            // Mark the root dir as bold in the path
            const appendSepChar = path => {
                const sepChar = (() => {
                    if (path.includes('\\')) return '\\';
                    if (path.includes('/')) return '/';
                    return '';
                })();
                return path.slice(-1) !== sepChar ? path + sepChar : path;
            };
            return this.filteredDirList
                .map(dir => {
                    const rootDirObj = this.rootDirs.find(rd => dir.path.startsWith(rd.path));
                    if (!rootDirObj) return dir.path;
                    const rootDir = appendSepChar(rootDirObj.path);
                    const rdEndIndex = dir.path.indexOf(rootDir) + rootDir.length;
                    return '<b>' + dir.path.slice(0, rdEndIndex) + '</b>' + dir.path.slice(rdEndIndex);
                });
        },
        showTable() {
            const { isLoading, selectedRootDirs, errorMessage } = this;
            return !isLoading && selectedRootDirs.length !== 0 && errorMessage === '';
        },
        checkAll: {
            get() {
                const selectedDirList = this.filteredDirList.filter(dir => dir.selected);
                if (selectedDirList.length === 0) return false;
                return selectedDirList.length === this.filteredDirList.length;
            },
            set(newValue) {
                this.dirList = this.dirList.map(dir => {
                    dir.selected = newValue;
                    return dir;
                });
            }
        }
    },
    methods: {
        /**
         * Transform root dirs paths array, and select all the paths.
         * @param {string[]} paths - The root dir paths
         */
        rootDirsPathsUpdated(paths) {
            this.rootDirs = paths.map(path => {
                return {
                    selected: true,
                    path
                };
            });
        },
        update() {
            if (this.isLoading) {
                return;
            }

            this.isLoading = true;
            this.errorMessage = '';

            const indices = this.rootDirs
                .reduce((indices, rd, index) => {
                    if (rd.selected) indices.push(index);
                    return indices;
                }, []);
            if (indices.length === 0) {
                this.dirList = [];
                this.isLoading = false;
                return;
            }

            const config = {
                params: {
                    'rootDirs': indices.join(',')
                },
                timeout: this.requestTimeout
            };
            api.get('internal/existingSeries', config).then(response => {
                const { data } = response;
                this.dirList = data
                    .map(dir => {
                        // Pre-select all dirs not already added
                        dir.selected = !dir.alreadyAdded;
                        dir.selectedIndexer = dir.metadata.indexer || this.defaultIndexer;
                        return dir;
                    });
                this.isLoading = false;

                this.$nextTick(() => {
                    $('#addRootDirTable')
                        .tablesorter({
                            widgets: ['zebra'],
                            // This fixes the checkAll checkbox getting unbound because this code changes the innerHTML of the <th>
                            // https://github.com/Mottie/tablesorter/blob/v2.28.1/js/jquery.tablesorter.js#L566
                            headerTemplate: '',
                            headers: {
                                0: { sorter: false },
                                3: { sorter: false }
                            }
                        })
                        // Fixes tablesorter not working after root dirs are refreshed
                        .trigger('updateAll');
                });
            }).catch(error => {
                this.errorMessage = error.message;
                this.dirList = [];
                this.isLoading = false;
            });
        },
        seriesIndexerUrl(curDir) {
            return this.indexers[curDir.metadata.indexer].showUrl + curDir.metadata.seriesId.toString();
        },
        async submitSeriesDirs() {
            const dirList = this.filteredDirList.filter(dir => dir.selected);
            if (dirList.length === 0) return false;

            const formData = new FormData();
            formData.append('promptForSettings', this.promptForSettings);
            dirList.forEach(dir => {
                const originalIndexer = dir.metadata.indexer;
                let seriesId = dir.metadata.seriesId;
                if (originalIndexer !== null && originalIndexer !== dir.selectedIndexer) {
                    seriesId = '';
                }

                const seriesToAdd = [dir.selectedIndexer, dir.path, seriesId, dir.metadata.seriesName]
                    .filter(i => typeof(i) === 'number' || Boolean(i)).join('|');

                formData.append('shows_to_add', encodeURIComponent(seriesToAdd));
            });

            const response = await apiRoute.post('addShows/addExistingShows', formData);
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
        }
    },
    watch: {
        selectedRootDirs() {
            this.update();
        }
    }
});
</script>
</%block>
<%block name="content">
<h1 class="header">{{ $route.meta.header }}</h1>
<div class="newShowPortal">
    <div id="config-components">
        <ul><li><app-link href="#core-component-group1">Add Existing Show</app-link></li></ul>
        <div id="core-component-group1" class="tab-pane active component-group">
            <form id="addShowForm" method="post" action="addShows/addExistingShows" accept-charset="utf-8">
                <div id="tabs">
                    <ul>
                        <li><app-link href="#tabs-1">Manage Directories</app-link></li>
                        <li><app-link href="#tabs-2">Customize Options</app-link></li>
                    </ul>
                    <div id="tabs-1" class="existingtabs">
                        <root-dirs @update:paths="rootDirsPathsUpdated"></root-dirs>
                    </div>
                    <div id="tabs-2" class="existingtabs">
                        <%include file="/inc_addShowOptions.mako"/>
                    </div>
                </div>
                <br>
                <p>Medusa can add existing shows, using the current options, by using locally stored NFO/XML metadata to eliminate user interaction.
                If you would rather have Medusa prompt you to customize each show, then use the checkbox below.</p>
                <p><input type="checkbox" v-model="promptForSettings" id="promptForSettings" /> <label for="promptForSettings">Prompt me to set settings for each show</label></p>
                <hr>
                <p><b>Displaying folders within these directories which aren't already added to Medusa:</b></p>
                <ul id="rootDirStaticList">
                    <li v-for="(rootDir, index) in rootDirs" class="ui-state-default ui-corner-all" @click="rootDirs[index].selected = !rootDirs[index].selected">
                        <input type="checkbox" class="rootDirCheck" v-model="rootDir.selected" :value="rootDir.path" style="cursor: pointer;">
                        <label><b style="cursor: pointer;">{{rootDir.path}}</b></label>
                    </li>
                </ul>
                <br>

                <span v-if="isLoading">
                    <img id="searchingAnim" src="images/loading32.gif" height="32" width="32" /> loading folders...
                </span>
                <template v-else>
                    <span v-if="errorMessage !== ''">
                        <b>Encountered an error while loading folders:</b> {{ errorMessage }}
                    </span>
                    <span v-else-if="selectedRootDirs.length === 0">No folders selected.</span>
                </template>

                <table v-show="showTable" id="addRootDirTable" class="defaultTable tablesorter">
                    <thead>
                        <tr>
                            <th class="col-checkbox"><input type="checkbox" v-model="checkAll" /></th>
                            <th>Directory</th>
                            <th width="20%">Show Name (tvshow.nfo)</th>
                            <th width="20%">Indexer</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="(curDir, curDirIndex) in filteredDirList">
                            <td class="col-checkbox">
                                <input type="checkbox" v-model="curDir.selected" :value="curDir.path" class="seriesDirCheck" />
                            </td>
                            <td>
                                <label @click="curDir.selected = !curDir.selected" v-html="displayPaths[curDirIndex]"></label>
                            </td>
                            <td>
                                <app-link v-if="curDir.metadata.seriesName && curDir.metadata.indexer > 0"
                                          :href="seriesIndexerUrl(curDir)">{{curDir.metadata.seriesName}}</app-link>
                                <span v-else>?</span>
                            </td>
                            <td align="center">
                                <select name="indexer" v-model="curDir.selectedIndexer">
                                    <option :value.number="0">All Indexers</option>
                                    <option v-for="(indexer, indexerId) in indexers" :value.number="indexerId">{{indexer.name}}</option>
                                </select>
                            </td>
                        </tr>
                    </tbody>
                </table>
                <br>
                <br>
                <input class="btn-medusa" type="button" value="Submit" :disabled="isLoading" @click="submitSeriesDirs" />
            </form>
        </div>
    </div>
</div>
</%block>

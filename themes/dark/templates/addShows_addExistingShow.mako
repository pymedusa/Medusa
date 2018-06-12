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
const startVue = () => {
    window.app = new Vue({
        el: '#vue-wrap',
        metaInfo: {
            title: 'Existing Show'
        },
        data() {
            <% indexers = { str(i): { 'name': v['name'], 'showUrl': v['show_url'] } for i, v in iteritems(indexerConfig) } %>
            return {
                // @FIXME: Python conversions (fix when config is loaded before routes)
                indexers: ${json.dumps(indexers)},
                defaultIndexer: ${app.INDEXER_DEFAULT},

                isLoading: false,
                rootDirs: [],
                dirList: [],
                promptForSettings: false
            };
        },
        mounted() {
            // Need to delay that a bit
            this.$nextTick(() => {
                // Hide the black/whitelist, because it can only be used for a single anime show
                $.updateBlackWhiteList(undefined);
            });
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
                return this.filteredDirList
                    .map(dir => {
                        const rootDirObj = this.rootDirs.find(rd => dir.path.startsWith(rd.path));
                        if (!rootDirObj) return dir.path;
                        const rootDir = rootDirObj.path;
                        const pathSep = rootDir.indexOf('\\\\') > -1 ? 2 : 1;
                        const rdEndIndex = dir.path.indexOf(rootDir) + rootDir.length + pathSep;
                        return '<b>' + dir.path.slice(0, rdEndIndex) + '</b>' + dir.path.slice(rdEndIndex);
                    });
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
            rootDirsUpdated(value, data) {
                this.rootDirs = data.map(rd => {
                    return {
                        selected: true,
                        path: rd.path
                    };
                });
            },
            async update() {
                if (this.isLoading) return;

                this.isLoading = true;

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

                const params = { 'rootDirs': indices.join(',') };
                const { data } = await api.get('internal/existingShow', { params });
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
            },
            showIndexerUrl(curDir) {
                return this.indexers[curDir.metadata.indexer].showUrl + curDir.metadata.showId.toString();
            },
            submitShowDirs() {
                const dirArr = this.filteredDirList
                    .reduce((accumlator, dir) => {
                        if (!dir.selected) return accumlator;

                        const originalIndexer = dir.metadata.indexer;
                        let showId = dir.metadata.showId;
                        if (originalIndexer !== null && originalIndexer !== dir.selectedIndexer) {
                            showId = '';
                        }

                        const showToAdd = [dir.selectedIndexer, dir.path, showId, dir.metadata.showName]
                            .filter(i => typeof(i) === 'number' || Boolean(i)).join('|');
                        accumlator.push(encodeURIComponent(showToAdd));
                        return accumlator;
                    }, []);

                if (dirArr.length === 0) return false;

                const promptForSettings = 'promptForSettings=' + (this.promptForSettings ? 'on' : 'off');
                const showToAdd = 'shows_to_add=' + dirArr.join('&shows_to_add=');
                window.location.href = $('base').attr('href') + 'addShows/addExistingShows?' + promptForSettings + '&' + showToAdd;
            }
        },
        watch: {
            selectedRootDirs() {
                this.update();
            }
        }
    });
};
</script>
</%block>
<%block name="content">
<h1 class="header">Existing Show</h1>
<div class="newShowPortal">
    <div id="config-components">
        <ul><li><app-link href="#core-component-group1">Add Existing Show</app-link></li></ul>
        <div id="core-component-group1" class="tab-pane active component-group">
            <form id="addShowForm" method="post" action="addShows/addExistingShows" accept-charset="utf-8">
                <div id="tabs">
                    <ul>
                        <li><app-link href="addShows/existingShows/#tabs-1">Manage Directories</app-link></li>
                        <li><app-link href="addShows/existingShows/#tabs-2">Customize Options</app-link></li>
                    </ul>
                    <div id="tabs-1" class="existingtabs">
                        <root-dirs @update:root-dirs-value="rootDirsUpdated"></root-dirs>
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
                <span v-if="isLoading"><img id="searchingAnim" src="images/loading32.gif" height="32" width="32" /> loading folders...</span>
                <span v-if="!isLoading && selectedRootDirs.length === 0">No folders selected.</span>
                <table v-show="!isLoading && selectedRootDirs.length !== 0" id="addRootDirTable" class="defaultTable tablesorter">
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
                                <input type="checkbox" v-model="curDir.selected" :value="curDir.path" class="showDirCheck" />
                            </td>
                            <td>
                                <label @click="curDir.selected = !curDir.selected" v-html="displayPaths[curDirIndex]"></label>
                            </td>
                            <td>
                                <app-link v-if="curDir.metadata.showName && curDir.metadata.indexer > 0"
                                          :href="showIndexerUrl(curDir)">{{curDir.metadata.showName}}</app-link>
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
                <input class="btn-medusa" type="button" value="Submit" :disabled="isLoading" @click="submitShowDirs" />
            </form>
        </div>
    </div>
</div>
</%block>

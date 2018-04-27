<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import app
    from medusa.indexers.indexer_api import indexerApi
    from medusa.indexers.indexer_config import indexerConfig

    from six import iteritems
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
            // @FIXME: Need this before rendering
            <%
                indexers = ["{0}: {{name: '{1}', showUrl: '{2}'}},".format(indexer, values['name'], values['show_url'])
                            for indexer, values in iteritems(indexerConfig)]
            %>
            return {
                indexers: {
                    ${'\n'.join(indexers)}
                },
                defaultIndexer: ${app.INDEXER_DEFAULT},

                dirList: [],
                selectedRootDirs: [],
                selectedSeriesDirs: [],
                isLoading: false,
                header: 'Existing Show',
                lastRootDirTxt: ''
            };
        },
        mounted() {
            // Need to delay that a bit
            this.$nextTick(() => {
                // Hide the black/whitelist, because it can only be used for a single anime show
                $.updateBlackWhiteList(undefined);
            });

            $(document.body).on('change', '#rootDirText', () => {
                if (this.lastRootDirTxt === $('#rootDirText').val()) {
                    return false;
                }
                this.lastRootDirTxt = $('#rootDirText').val();
                this.selectedRootDirs = this.rootDirs;
                this.loadContent();
            });

            // Trigger Root Dirs to update.
            // @FIXME: This is a workaround until root-dirs is a Vue component.
            if ($('#rootDirText').val() === '') {
                $('#rootDirs').click();
            }

            // this.lastRootDirTxt = $('#rootDirText').val();
            // this.selectedRootDirs = this.rootDirs;
            // this.loadContent();
        },
        computed: {
            rootDirs() {
                if (!this.lastRootDirTxt) return [];
                return this.lastRootDirTxt.split('|').slice(1);
            },
            filteredDirList() {
                return this.dirList.filter(dir => !dir.alreadyAdded);
            },
            checkAll: {
                get() {
                    if (!this.selectedSeriesDirs.length) return false;
                    return this.selectedSeriesDirs.length === this.filteredDirList.length;
                },
                set(newValue) {
                    this.selectedSeriesDirs = newValue ? this.filteredDirList.map(dir => dir.dir) : [];
                }
            }
        },
        methods: {
            async loadContent() {
                if (this.isLoading) return;

                this.isLoading = true;
                if (!this.selectedRootDirs.length) {
                    this.dirList = [];
                    this.isLoading = false;
                    return;
                }

                const data = await $.getJSON('addShows/massAddTable/', {
                    jsonData: JSON.stringify(this.selectedRootDirs)
                });
                this.dirList = data.dirList;
                this.selectedSeriesDirs = this.filteredDirList.map(dir => dir.dir);
                this.isLoading = false;

                this.$nextTick(() => {
                    $('#addRootDirTable').tablesorter({
                        // SortList: [[1,0]],
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
                    .trigger("updateAll");
                });
            },
            submitSeriesDirs() {
                const dirArr = [];
                $('.seriesDirCheck').each((index, element) => {
                    if (element.checked === true) {
                        const originalIndexer = $(element).attr('data-indexer');
                        let seriesId = '|' + $(element).attr('data-series-id');
                        const seriesName = $(element).attr('data-series-name');
                        const seriesDir = $(element).attr('data-series-dir');

                        const indexer = $(element).closest('tr').find('select').val();
                        if (originalIndexer !== indexer || originalIndexer === '0') {
                            seriesId = '';
                        }
                        dirArr.push(encodeURIComponent(indexer + '|' + seriesDir + seriesId + '|' + seriesName));
                    }
                });

                if (dirArr.length === 0) {
                    return false;
                }

                // @FIXME: Restore functionality!
                //window.location.href = $('base').attr('href') + 'addShows/addExistingShows?promptForSettings=' + ($('#promptForSettings').prop('checked') ? 'on' : 'off') + '&shows_to_add=' + dirArr.join('&shows_to_add=');
                console.log($('base').attr('href') + 'addShows/addExistingShows?promptForSettings=' + ($('#promptForSettings').prop('checked') ? 'on' : 'off') + '&shows_to_add=' + dirArr.join('&shows_to_add='));
            }
        },
        watch: {
            selectedRootDirs() {
                this.loadContent();
            }
        }
    });
};
</script>
</%block>
<%block name="content">
<h1 class="header">{{header}}</h1>
<div id="newShowPortal">
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
                        <%include file="/inc_rootDirs.mako"/>
                    </div>
                    <div id="tabs-2" class="existingtabs">
                        <%include file="/inc_addShowOptions.mako"/>
                    </div>
                </div>
                <br>
                <p>Medusa can add existing shows, using the current options, by using locally stored NFO/XML metadata to eliminate user interaction.
                If you would rather have Medusa prompt you to customize each show, then use the checkbox below.</p>
                <p><input type="checkbox" name="promptForSettings" id="promptForSettings" /> <label for="promptForSettings">Prompt me to set settings for each show</label></p>
                <hr>
                <p><b>Displaying folders within these directories which aren't already added to Medusa:</b></p>
                <ul id="rootDirStaticList">
                    <li v-for="rootDir in rootDirs" class="ui-state-default ui-corner-all" @click.self=""> <!-- @FIXME -->
                        <input type="checkbox" class="rootDirCheck" v-model="selectedRootDirs" :value="rootDir" style="cursor: pointer;">
                        <label :for="rootDir"><b style="cursor: pointer;">{{rootDir}}</b></label>
                    </li>
                </ul>
                <br>
                <span v-if="isLoading"><img id="searchingAnim" src="images/loading32.gif" height="32" width="32" /> loading folders...</span>
                <span v-if="!isLoading && Object.keys(dirList).length === 0">No folders selected.</span>
                <table v-show="!isLoading && Object.keys(dirList).length !== 0" id="addRootDirTable" class="defaultTable tablesorter">
                    <thead>
                        <tr>
                            <th class="col-checkbox"><input type="checkbox" v-model="checkAll" /></th>
                            <th>Directory</th>
                            <th width="20%">Show Name (tvshow.nfo)</th>
                            <th width="20%">Indexer</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="curDir in dirList" v-if="!curDir.alreadyAdded">
                            <td class="col-checkbox">
                                <input type="checkbox" v-model="selectedSeriesDirs" :value="curDir.dir" :data-indexer="curDir.existingInfo.indexer || 0"
                                       :data-series-id="curDir.existingInfo.seriesId || 0" :data-series-dir="curDir.dir"
                                       :data-series-name="curDir.existingInfo.seriesName || ''" class="seriesDirCheck" />
                            </td>
                            <td><label :for="curDir.dir" v-html="curDir.displayDir"></label></td>
                            <td>
                                <app-link v-if="curDir.existingInfo.seriesName && curDir.existingInfo.indexer > 0"
                                          :href="indexers[curDir.existingInfo.indexer].showUrl + curDir.existingInfo.seriesId.toString()">{{curDir.existingInfo.seriesName}}</app-link>
                                <span v-else>?</span>
                            </td>
                            <td align="center">
                                <select name="indexer">
                                    <option v-for="(indexer, indexerId) in indexers" :value="indexerId" :selected="parseInt(indexerId, 10) === curDir.existingInfo.indexer || indexerId == defaultIndexer">{{indexer.name}}</option>
                                </select>
                            </td>
                        </tr>
                    </tbody>
                </table>
                <br>
                <br>
                <input class="btn" type="button" value="Submit" id="submitSeriesDirs" :disabled="isLoading" @click="submitSeriesDirs" />
            </form>
        </div>
    </div>
</div>
</%block>

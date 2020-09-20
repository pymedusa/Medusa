<template>
    <div id="new-shows-existing" class="newShowPortal">
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
                            <root-dirs @update:paths="rootDirsPathsUpdated" />
                        </div>
                        <div id="tabs-2" class="existingtabs">
                            <add-show-options disable-release-groups v-bind="{enableAnimeOptions}" @change="updateOptions" />
                        </div>
                    </div>
                    <br>
                    <p>Medusa can add existing shows, using the current options, by using locally stored NFO/XML metadata to eliminate user interaction.
                        If you would rather have Medusa prompt you to customize each show, then use the checkbox below.</p>
                    <p><input type="checkbox" v-model="promptForSettings" id="promptForSettings"> <label for="promptForSettings">Prompt me to set settings for each show</label></p>
                    <hr>
                    <p><b>Displaying folders within these directories which aren't already added to Medusa:</b></p>
                    <ul id="rootDirStaticList">
                        <li v-for="(rootDir, index) in rootDirs" :key="index" class="ui-state-default ui-corner-all" @click="rootDirs[index].selected = !rootDirs[index].selected">
                            <input type="checkbox" class="rootDirCheck" v-model="rootDir.selected" :value="rootDir.path" style="cursor: pointer;">
                            <label><b style="cursor: pointer;">{{rootDir.path}}</b></label>
                        </li>
                    </ul>
                    <br>

                    <span v-if="isLoading">
                        <img id="searchingAnime" src="images/loading32.gif" height="32" width="32"> loading folders...
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
                                <th class="col-checkbox"><input type="checkbox" v-model="checkAll"></th>
                                <th>Directory</th>
                                <th width="20%">Show Name (tvshow.nfo)</th>
                                <th width="20%">Indexer</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr :ref="`curdirindex-${curDirIndex}`" v-for="(curDir, curDirIndex) in filteredDirList" :key="curDirIndex">
                                <td class="col-checkbox">
                                    <input type="checkbox" v-model="curDir.selected" :value="curDir.path" class="seriesDirCheck">
                                </td>
                                <td>
                                    <label @click="curDir.selected = !curDir.selected" v-html="displayPaths[curDirIndex]" />
                                </td>
                                <td>
                                    <app-link v-if="curDir.metadata.seriesName && curDir.metadata.indexer > 0"
                                              :href="seriesIndexerUrl(curDir)">{{curDir.metadata.seriesName}}</app-link>
                                    <span v-else>?</span>
                                </td>
                                <td align="center">
                                    <select name="indexer" v-model="curDir.selectedIndexer">
                                        <option :value="0">All Indexers</option>
                                        <option v-for="indexer in Object.values(indexers.indexers)" :key="indexer.id" :value="indexer.id">{{indexer.name}}</option>
                                    </select>
                                </td>
                                <td align="center" :key="`td${curDirIndex}`">
                                    <button v-if="addShowComponents[`curdirindex-${curDirIndex}`] === undefined" type="button" class="btn-medusa btn-inline" @click="manualAddNewShow($event, curDirIndex)" :key="`add${curDirIndex}`">Add</button>
                                    <button v-else type="button" class="btn-medusa btn-inline" @click="closeAddShowComponent(curDirIndex)" :key="`close${curDirIndex}`">Close</button>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                    <br>
                    <br>
                    <input class="btn-medusa" type="button" value="Submit" :disabled="isLoading" @click="submitSeriesDirs">
                </form>
            </div>
        </div>
    </div>
</template>

<script>
import Vue from 'vue';
import { mapState } from 'vuex';
import RootDirs from './root-dirs.vue';
import { AddShowOptions, NewShow } from '.';
import { AppLink } from './helpers';
import { api, apiRoute } from '../api';

export default {
    components: {
        AddShowOptions,
        AppLink,
        RootDirs
    },
    data() {
        return {
            // @FIXME: Python conversions (fix when config is loaded before routes)
            // indexers: ${json.dumps(indexers)},

            isLoading: false,
            requestTimeout: 3 * 60 * 1000,
            errorMessage: '',
            rootDirs: [],
            dirList: [],
            promptForSettings: false,
            enableAnimeOptions: true,
            presetShowOptions: {
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
            },
            addShowComponents: {} // An array of mounted new-show.vue components.
        };
    },
    computed: {
        ...mapState({
            config: state => state.config.general, // Used by `inc_addShowOptions.mako`
            indexers: state => state.config.indexers,
            indexerDefault: state => state.config.general.indexerDefault
        }),
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
            return this.filteredDirList
                .map(dir => {
                    const rootDirObj = this.rootDirs.find(rd => dir.path.startsWith(rd.path));
                    if (!rootDirObj) {
                        return dir.path;
                    }
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
                if (selectedDirList.length === 0) {
                    return false;
                }
                return selectedDirList.length === this.filteredDirList.length;
            },
            set(newValue) {
                this.dirList = this.dirList.map(dir => {
                    dir.selected = newValue;
                    return dir;
                });
            }
        },
        indexerListOptions() {
            const { indexers } = this;
            const allIndexers = [{ text: 'All Indexers', value: 0 }];

            const indexerOptions = Object.values(indexers.indexers).map(indexer => ({ value: indexer.id, text: indexer.name }));
            return [...allIndexers, ...indexerOptions];
        }
    },
    methods: {
        indexExist(index) {
            return this.addShowComponents[`curdirindex-${index}`] === undefined;
        },
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
            const { indexerDefault } = this;

            if (this.isLoading) {
                return;
            }

            this.isLoading = true;
            this.errorMessage = '';

            const indices = this.rootDirs
                .reduce((indices, rd, index) => {
                    if (rd.selected) {
                        indices.push(index);
                    }
                    return indices;
                }, []);
            if (indices.length === 0) {
                this.dirList = [];
                this.isLoading = false;
                return;
            }

            const config = {
                params: {
                    rootDirs: indices.join(',')
                },
                timeout: this.requestTimeout
            };
            api.get('internal/existingSeries', config).then(response => {
                const { data } = response;
                this.dirList = data
                    .map(dir => {
                        // Pre-select all dirs not already added
                        dir.selected = !dir.alreadyAdded;
                        dir.selectedIndexer = dir.metadata.indexer || indexerDefault;
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
            const { showUrl } = Object.values(this.indexers.indexers).filter(indexer => indexer.id === curDir.metadata.indexer)[0];
            return `${showUrl}${curDir.metadata.seriesId}`;
        },
        async submitSeriesDirs() {
            const dirList = this.filteredDirList.filter(dir => dir.selected);
            if (dirList.length === 0) {
                return false;
            }

            const formData = new FormData();
            formData.append('promptForSettings', this.promptForSettings);
            dirList.forEach(dir => {
                const originalIndexer = dir.metadata.indexer;
                let { seriesId } = dir.metadata;
                if (originalIndexer !== null && originalIndexer !== dir.selectedIndexer) {
                    seriesId = '';
                }

                const seriesToAdd = [dir.selectedIndexer, dir.path, seriesId, dir.metadata.seriesName]
                    .filter(i => typeof (i) === 'number' || Boolean(i)).join('|');

                formData.append('shows_to_add', seriesToAdd);
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
                    [element.name, element.value] = param; // Unpack
                    form.append(element);
                });

                document.body.append(form);
                form.submit();
            }
        },
        updateOptions(options) {
            // Update seleted options from add-show-options.vue @change event.
            this.presetShowOptions.subtitles = options.subtitles;
            this.presetShowOptions.status = options.status;
            this.presetShowOptions.statusAfter = options.statusAfter;
            this.presetShowOptions.seasonFolders = options.seasonFolders;
            this.presetShowOptions.anime = options.anime;
            this.presetShowOptions.scene = options.scene;
            this.presetShowOptions.release.blacklist = options.release.blacklist;
            this.presetShowOptions.release.whitelist = options.release.whitelist;
            this.presetShowOptions.quality.allowed = options.quality.allowed;
            this.presetShowOptions.quality.preferred = options.quality.preferred;
            this.presetShowOptions.showLists = options.showLists;
        },
        /**
         * Mount the new-show.vue component and provide nfo info if available.
         * @param {object} event - Triggered event
         * @param {number} curDirIndex - Index of the looped filteredDirList array.
         */
        manualAddNewShow(event, curDirIndex) {
            const { addShowComponents, filteredDirList } = this;

            const curDir = filteredDirList[curDirIndex];
            const providedInfo = {
                use: false,
                showId: 0,
                showName: '',
                showDir: curDir.path,
                indexerId: 0,
                indexerLanguage: 'en'
            };

            if (curDir.metadata.indexer) {
                providedInfo.indexerId = curDir.metadata.indexer;
            }

            if (curDir.metadata.seriesId) {
                providedInfo.showId = curDir.metadata.seriesId;
            }

            if (curDir.metadata.seriesName) {
                providedInfo.showName = curDir.metadata.seriesName;
            }

            providedInfo.use = Boolean(providedInfo.indexerId !== 0 && providedInfo.showId !== 0 && providedInfo.showName);

            const NewShowClass = Vue.extend(NewShow);
            const instance = new NewShowClass({
                propsData: { providedInfo },
                parent: this
            });

            // Need these, because we want it to span the width of the parent table row.
            const row = document.createElement('tr');
            row.style.columnSpan = 'all';
            const cell = document.createElement('td');
            cell.setAttribute('colspan', '9999');

            const wrapper = document.createElement('div'); // Just used to mount on.
            row.append(cell);
            cell.append(wrapper);
            this.$refs[`curdirindex-${curDirIndex}`][0].after(row);

            instance.$mount(wrapper);
            Vue.set(addShowComponents, `curdirindex-${curDirIndex}`, instance);
        },
        closeAddShowComponent(index) {
            const { addShowComponents } = this;
            addShowComponents[`curdirindex-${index}`].$destroy();
            // Remove the element from the DOM
            addShowComponents[`curdirindex-${index}`].$el.closest('tr').remove();
            Vue.set(addShowComponents, `curdirindex-${index}`, undefined);
        }
    },
    watch: {
        selectedRootDirs() {
            this.update();
        }
    }
};
</script>

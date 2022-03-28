<template>
    <div class="newShowPortal">
        <vue-tabs>
            <v-tab key="add_new_show" title="Add New Show">
                <div id="core-component-group1" class="tab-pane active component-group">
                    <div id="displayText">Adding show <b v-html="showName" /> {{showPathPreposition}} <b v-html="showPath" /></div>
                    <br>

                    <form id="addShowForm" @submit.prevent="">

                        <form-wizard ref="formwizard" class="formwizard" title="" subtitle="" @on-change="updateFormWizardStep" color="rgb(95, 95, 95)">
                            <template slot="step" slot-scope="props">
                                <div class="step" :class="{disabledstep: !props.tab.active}" @click="navigateStep(props.index)">
                                    Step {{props.index + 1}}<div class="smalltext">{{props.tab.title}}</div>
                                </div>
                            </template>

                            <template slot="prev">
                                <button type="button" class="btn-medusa btn-inline">Back</button>
                            </template>

                            <template slot="next">
                                <button type="button" class="btn-medusa btn-inline">Next</button>
                            </template>

                            <template slot="finish">
                                <button @click.prevent="submitForm" type="button" class="btn-medusa btn-inline" :disabled="addButtonDisabled">Add Show</button>
                            </template>

                            <tab-content title="Find a show on selected indexer(s)">
                                <div class="stepDiv">
                                    <new-show-search
                                        ref="newShowSearch"
                                        :provided-info="providedInfo"
                                        :selected-root-dir="selectedRootDir"
                                        @navigate-step="navigateStep"
                                        @selected="selected"
                                    />
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
                                    <add-show-options v-bind="{showName, enableAnimeOptions, presetShowOptions}" @change="updateOptions" @refresh="refreshOptionStep" />
                                </div>
                            </tab-content>
                        </form-wizard>
                    </form>
                    <br>
                    <div style="width: 100%; text-align: center;">
                        <input @click.prevent="submitForm" class="btn-medusa btn-inline"
                               v-show="formwizard.currentIndex !== 2"
                               type="button" value="Add Show" :disabled="addButtonDisabled">
                    </div>
                </div>
            </v-tab>
        </vue-tabs>

        <!-- eslint-disable @sharkykh/vue-extra/component-not-registered -->
        <modal name="existing-show-folder" :height="'auto'" :width="'80%'">
            <transition name="modal">
                <div class="modal-mask">
                    <div class="modal-wrapper">
                        <div class="modal-content">
                            <div class="modal-header">
                                <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
                                <h4 class="modal-title">Show folder exists</h4>
                            </div>
                            <div class="modal-body">
                                <p>The folder for the selected show already exists. And metadata was found.</p>
                                <p v-if="this.existingFolder">The show has previously been added through the indexer {{indexerIdToName(this.existingFolder.indexerId)}}. Do you want to use this indexer?</p>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn-medusa btn-success" data-dismiss="modal" @click="switchIndexer; $modal.hide('existing-show-folder')">Yes</button>
                                <button type="button" class="btn-medusa btn-success" data-dismiss="modal" @click="$modal.hide('existing-show-folder')">No</button>
                            </div>
                        </div>
                    </div>
                </div>
            </transition>
        </modal>

    </div>
</template>
<script>
import { mapGetters, mapState } from 'vuex';
import RootDirs from './root-dirs.vue';
import { AddShowOptions } from '.';
import NewShowSearch from './new-show-search.vue';
import { VueTabs, VTab } from 'vue-nav-tabs/dist/vue-tabs.js';
import { FormWizard, TabContent } from 'vue-form-wizard';

export default {
    name: 'new-show',
    components: {
        AddShowOptions,
        FormWizard,
        TabContent,
        NewShowSearch,
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
                    indexerLanguage: 'en',
                    unattended: false
                };
            }
        },
        presetShowOptions: {
            default() {
                return {
                    use: false,
                    subtitles: null,
                    status: null,
                    statusAfter: null,
                    seasonFolders: null,
                    anime: null,
                    scene: null,
                    showLists: null,
                    release: null,
                    quality: null
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
            selectedRootDir: '',
            selectedShow: null,
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
            },
            addedQueueItem: null,
            existingFolder: null
        };
    },
    mounted() {
        // If switching to the first tab, auto focus on the name field.
        this.$watch('formwizard.currentIndex', newValue => {
            if (newValue === 0 && this.$refs.newShowSearch.$refs.nameToSearch) {
                this.$refs.newShowSearch.$refs.nameToSearch.focus();
            }
        });

        setTimeout(() => {
            const { providedInfo, navigateStep } = this;
            const { use, showId, showDir } = providedInfo;
            if (use && showId !== 0 && showDir) {
                navigateStep(2);
            }
        }, 100);

        // Assign formwizard ref to this.formwizard.ref.
        this.formwizard.ref = this.$refs.formwizard;

        // Check if this.providedInfo.unattended is provided together with the info we need to add a show without prompts.
        if (this.providedInfo.use && this.providedInfo.unattended) {
            this.submitForm();
        }
    },
    computed: {
        ...mapState({
            general: state => state.config.general,
            indexers: state => state.config.indexers,
            client: state => state.auth.client
        }),
        ...mapGetters(['indexerIdToName']),
        addButtonDisabled() {
            const { selectedShowSlug, selectedRootDir, providedInfo } = this;
            if (providedInfo.use) {
                return providedInfo.showId === 0;
            }
            return !(providedInfo.showDir || selectedRootDir) || selectedShowSlug === '';
        },
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
        enableAnimeOptions() {
            const { providedInfo, selectedShow } = this;
            return Boolean(selectedShow || (providedInfo.use && providedInfo.indexerId === 1));
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
                presetShowOptions,
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

            if (presetShowOptions.use) {
                this.selectedShowOptions = presetShowOptions;
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
            options.showLists = showLists;

            let response = null;
            try {
                const { $router } = this;
                response = await this.client.api.post('series', { id: showId, options }, { timeout: 180000 });

                // If we're not using this component from addExistingShow, route to home.
                if (this.$route.name === 'addNewShow') {
                    $router.push({ name: 'home' });
                } else {
                    const { providedInfo } = this;
                    this.$emit('added', { ...response.data, providedInfo });
                }
            } catch (error) {
                this.$snotify.error(
                    `Error trying to add show ${Object.keys(showId)[0]}${showId[Object.keys(showId)[0]]}`
                );
                this.$emit('error', { message: `Error trying to add show ${Object.keys(showId)[0]}${showId[Object.keys(showId)[0]]}` });
                // }
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
            // Update selected options from add-show-options.vue @change event.
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
        selected({ result }) {
            this.selectedShow = result;
            this.selectedShowSlug = result.slug;
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

.show-add-option {
    float: left;
    padding-right: 10px;
    line-height: 40px;
}

</style>

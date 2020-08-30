<template>
    <div id="home">

        <div class="row">
            <div class="col-sm-12 home-header-controls">
                <h2 class="header pull-left">Show List</h2>
                <div class="home-options">
                    <div v-if="selectedRootIndexOptions.length > 1" class="home-filter-option pull-right" id="showRoot">
                        <select :value="stateLayout.selectedRootIndex" name="showRootDir" id="showRootDir" class="form-control form-control-inline input-sm" @change="setStoreLayout({ key: 'selectedRootIndex', value: Number($event.target.selectedOptions[0].value) });">
                            <option v-for="option in selectedRootIndexOptions" :key="option.value" :value="String(option.value)">{{option.text}}</option>
                        </select>
                    </div>
                    <div class="home-filter-option show-option-layout pull-right">
                        <span>Layout: </span>
                        <select v-model="layout" name="layout" class="form-control form-control-inline input-sm show-layout">
                            <option value="poster">Poster</option>
                            <option value="small">Small Poster</option>
                            <option value="banner">Banner</option>
                            <option value="simple">Simple</option>
                        </select>
                    </div>
                </div>
            </div>
        </div>

        <div class="row">
            <div class="col-md-12">
                <!-- Split in tabs -->
                <div id="showTabs" v-if="stateLayout.splitHomeInTabs">
                    <vue-tabs @tab-change="tabChange">
                        <v-tab
                            v-for="showInList in showsInLists"
                            :key="showInList.listTitle"
                            :title="showInList.listTitle"
                        >
                            <template v-if="['banner', 'simple', 'small', 'poster'].includes(layout)">
                                <show-list :id="`${showInList.listTitle.toLowerCase()}TabContent`"
                                           v-bind="{
                                               listTitle: showInList.listTitle, layout, shows: showInList.shows, header: showInList.length > 1
                                           }"
                                />
                            </template>
                        </v-tab>
                    </vue-tabs>
                </div> <!-- #showTabs -->
                <template v-else>
                    <template v-if="['banner', 'simple', 'small', 'poster'].includes(layout)">
                        <draggable tag="ul" v-model="showList" class="list-group" handle=".move-show-list">
                            <li v-for="showInList in showsInLists" :key="showInList.listTitle">
                                <show-list
                                    v-bind="{
                                        listTitle: showInList.listTitle, layout, shows: showInList.shows, header: showInList.length > 1
                                    }"
                                />
                            </li>
                        </draggable>
                    </template>
                </template>

                <!-- No Shows added -->
                <span v-if="showsInLists && showsInLists.filter(list => list.shows.length > 0).length === 0">Please add a show <app-link href="addShows">here</app-link> to get started</span>

            </div>
        </div>
        <backstretch :slug="config.randomShowSlug" />
    </div>
</template>

<script>
import { mapActions, mapGetters, mapState } from 'vuex';
import { AppLink } from './helpers';
import { ShowList } from './show-list';
import { VueTabs, VTab } from 'vue-nav-tabs/dist/vue-tabs.js';
import Draggable from 'vuedraggable';
import Backstretch from './backstretch.vue';

export default {
    name: 'home',
    components: {
        AppLink,
        Backstretch,
        ShowList,
        VueTabs,
        VTab,
        Draggable
    },
    data() {
        return {
            layoutOptions: [
                { value: 'poster', text: 'Poster' },
                { value: 'small', text: 'Small Poster' },
                { value: 'banner', text: 'Banner' },
                { value: 'simple', text: 'Simple' }
            ],
            selectedRootDir: 0
        };
    },
    computed: {
        ...mapState({
            config: state => state.config.general,
            indexers: state => state.config.indexers,
            // Renamed because of the computed property 'layout'.
            stateLayout: state => state.config.layout,
            stats: state => state.stats
        }),
        ...mapGetters({
            showsWithStats: 'showsWithStats',
            showsInLists: 'showsInLists'
        }),
        layout: {
            get() {
                const { stateLayout } = this;
                return stateLayout.home;
            },
            set(layout) {
                const { setLayout } = this;
                const page = 'home';
                setLayout({ page, layout });
            }
        },
        showList: {
            get() {
                const { stateLayout } = this;
                const { show } = stateLayout;
                return show.showListOrder;
            },
            set(value) {
                const { stateLayout, setLayoutShow } = this;
                const mergedShowLayout = { ...stateLayout.show, showListOrder: value };
                setLayoutShow(mergedShowLayout);
            }
        },
        selectedRootIndexOptions() {
            const { config } = this;
            const { rootDirs } = config;
            let mappedRootDirs = rootDirs.slice(1).map((item, idx) => ({ text: item, value: idx }));
            if (mappedRootDirs && mappedRootDirs.length > 1) {
                mappedRootDirs = [...[{ value: -1, text: 'All Folders' }], ...mappedRootDirs];
            }
            return mappedRootDirs;
        }
    },
    methods: {
        ...mapActions({
            setLayout: 'setLayout',
            setConfig: 'setConfig',
            setLayoutShow: 'setLayoutShow',
            setStoreLayout: 'setStoreLayout',
            setLayoutLocal: 'setLayoutLocal',
            getShows: 'getShows',
            getStats: 'getStats'
        }),
        async changePosterSortBy() {
            // Patch new posterSOrtBy value
            const { $snotify, posterSortby, setPosterSortBy } = this;

            try {
                await setPosterSortBy({ section: 'layout', config: { posterSortby } });
            } catch (error) {
                $snotify.error(
                    'Error while trying to change poster sort option',
                    'Error'
                );
            }
        },
        saveSelectedRootDir(value) {
            const { setStoreLayout } = this;
            setStoreLayout({ key: 'selectedRootIndex', value });
        },
        tabChange(tabIndex) {
            const { setLayoutLocal } = this;
            setLayoutLocal({ key: 'currentShowTab', tabIndex });
        }
    },
    mounted() {
        const { getStats } = this;
        getStats('show');
    }
};
</script>

<style scoped>
ul.list-group > li {
    list-style: none;
    margin-bottom: 10px;
}

.home-header-controls {
    display: flex;
}

.home-header-controls > h2 {
    white-space: nowrap;
}

.home-options {
    align-self: flex-end;
    width: 100%;
}

.home-filter-option {
    margin-left: 10px;
    line-height: 40px;
}

@media (max-width: 768px) {
    .show-option {
        width: 100%;
        display: inline-block;
    }

    .show-option-layout > span {
        display: none;
    }
}

</style>

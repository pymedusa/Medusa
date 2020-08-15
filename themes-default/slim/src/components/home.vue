<template>
    <div id="home">
        <div v-if="['banner', 'simple', 'small'].includes(layout)" class="row">
            <div class="col-sm-12">
                <div class="home-filter-option option-filter-name">
                    <input v-model="filterByName" id="filterShowName" class="form-control form-control-inline input-sm input200" type="search" placeholder="Filter Show Name">
                </div>
            </div>
        </div>

        <div class="row">
            <div class="col-sm-12">
                <div class="home-filter-option pull-left" id="showRoot">
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
        </div><!-- end row -->

        <div class="row">
            <div class="col-md-12">
                <!-- Split in tabs -->
                <div id="showTabs" v-if="stateLayout.splitHomeInTabs">
                    <vue-tabs>
                        <v-tab
                            v-for="showList in showLists"
                            :key="showList.listTitle"
                            :title="showList.listTitle"
                        >
                            <template v-if="['banner', 'simple', 'small', 'poster'].includes(layout)">
                                <show-list :id="`${showList.listTitle.toLowerCase()}TabContent`"
                                           v-bind="{
                                               listTitle: showList.listTitle, layout, shows: showList.shows, header: showLists.length > 1
                                           }"
                                />
                            </template>
                        </v-tab>
                    </vue-tabs>
                </div> <!-- #showTabs -->
                <template v-else>
                    <template v-if="['banner', 'simple', 'small', 'poster'].includes(layout)">
                        <draggable tag="ul" v-model="showList" class="list-group" handle=".move-show-list">
                            <li v-for="showList in showLists" :key="showList.listTitle">
                                <show-list
                                    v-bind="{
                                        listTitle: showList.listTitle, layout, shows: showList.shows, header: showLists.length > 1
                                    }"
                                />
                            </li>
                        </draggable>
                    </template>
                </template>
            </div>
        </div>
        <backstretch :slug="config.randomShowSlug" />
    </div>
</template>

<script>
import { mapActions, mapGetters, mapState } from 'vuex';
import { ShowList } from './show-list';
import { VueTabs, VTab } from 'vue-nav-tabs/dist/vue-tabs.js';
import Draggable from 'vuedraggable';
import Backstretch from './backstretch.vue';

export default {
    name: 'home',
    components: {
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
            showsWithStats: 'showsWithStats'
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
        filterByName: {
            get() {
                const { local } = this.stateLayout;
                const { showFilterByName } = local;

                return showFilterByName;
            },
            set(value) {
                const { setLayoutLocal } = this;
                setLayoutLocal({ key: 'showFilterByName', value });
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
                const mergedShowLayout = { ...stateLayout.show, showListOrder: value.map(item => item.value) };
                setLayoutShow(mergedShowLayout);
            }
        },
        showLists() {
            const { config, filterByName, indexers, layout, stateLayout, showList, showsWithStats } = this;
            const { rootDirs } = config;
            const { selectedRootIndex } = stateLayout;
            if (!indexers.indexers) {
                return;
            }

            let shows = null;

            // Filter root dirs
            shows = showsWithStats.filter(show => selectedRootIndex === -1 || show.config.location.includes(rootDirs.slice(1)[selectedRootIndex]));

            // Filter by text for the banner, simple and smallposter layouts.
            // The Poster layout uses vue-isotope and this does not respond well to changes to the `list` property.
            if (layout !== 'poster') {
                shows = shows.filter(show => show.title.toLowerCase().includes(filterByName.toLowerCase()));
            }

            const categorizedShows = showList.filter(listTitle => {
                return listTitle === 'series' || shows.filter(show => show.config.showLists.includes(listTitle.toLowerCase())).length > 0;
            }).map(listTitle => ({ listTitle, shows: shows.filter(show => show.config.showLists.includes(listTitle.toLowerCase())) }));

            // Check for shows that are not in any category anymore
            const uncategorizedShows = shows.filter(show => {
                return show.config.showLists.map(item => {
                    return showList.map(list => list.toLowerCase()).includes(item);
                }).every(item => !item);
            });

            if (uncategorizedShows.length > 0) {
                categorizedShows.push({ listTitle: 'uncategorized', shows: uncategorizedShows });
            }

            return categorizedShows;
        },
        selectedRootIndexOptions() {
            const { config } = this;
            const { rootDirs } = config;
            return [...[{ value: -1, text: 'All Folders' }], ...rootDirs.slice(1).map((item, idx) => ({ text: item, value: idx }))];
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

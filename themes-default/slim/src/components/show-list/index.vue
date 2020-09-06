<template>
    <div>
        <div v-if="layout ==='poster'" class="row poster-ui-controls">
            <!-- Only show the list title when not in tabs & only for the poster layout -->
            <div v-if="!stateLayout.splitHomeInTabs && (showsInLists && showsInLists.length > 1)" class="show-list-title listTitle">
                <button type="button" class="nav-show-list move-show-list">
                    <span class="icon-bar" />
                    <span class="icon-bar" />
                    <span class="icon-bar" />
                </button>
                <h3 class="header">{{listTitle}}</h3>
            </div>
            <div class="col-lg-12">
                <div class="show-option">
                    <input type="search" v-model="filterByName" class="form-control form-control-inline input-sm input200" placeholder="Filter Show Name">
                </div>
                <div class="show-option">
                    <!-- These need to patch apiv2 on change! -->
                    <select v-model="posterUiSortDir" id="postersortdirection" class="form-control form-control-inline input-sm" placeholder="Direction">
                        <option :value="1">Ascending</option>
                        <option :value="0">Descending</option>
                    </select>
                </div>

                <div class="show-option pull-right">
                    <select v-model="posterUiSortBy" id="postersort" class="form-control form-control-inline input-sm" placeholder="Sort By">
                        <option v-for="option in posterSortByOptions" :value="option.value" :key="option.value">
                            {{ option.text }}
                        </option>
                    </select>
                </div>

                <poster-size-slider />
            </div>

        </div>

        <!-- We're still loading -->
        <template v-if="!this.showsLoading.finished && shows.length === 0">
            <state-switch state="loading" :theme="stateLayout.themeName" />
            <span>Loading</span>
        </template>

        <template v-else-if="shows.length >= 1">
            <component :class="[['simple', 'small', 'banner'].includes(layout) ? 'table-layout' : '']" :is="mappedLayout" v-bind="$props" />
        </template>
    </div>
</template>
<script>

import { mapActions, mapGetters, mapState } from 'vuex';
import Banner from './banner.vue';
import Simple from './simple.vue';
import Poster from './poster.vue';
import Smallposter from './smallposter.vue';
import { AppLink, PosterSizeSlider, StateSwitch } from '../helpers';

export default {
    name: 'show-list',
    components: {
        AppLink,
        Banner,
        Simple,
        Poster,
        PosterSizeSlider,
        Smallposter,
        StateSwitch
    },
    props: {
        layout: {
            validator: layout => [
                null,
                '',
                'poster',
                'banner',
                'simple',
                'small'
            ].includes(layout),
            required: true
        },
        shows: {
            type: Array,
            required: true
        },
        listTitle: {
            type: String
        },
        header: {
            type: Boolean
        }
    },
    data() {
        return {
            postSortDirOptions: [
                { value: '0', text: 'Descending' },
                { value: '1', text: 'Ascending' }
            ],
            posterSortByOptions: [
                { text: 'Name', value: 'name' },
                { text: 'Next episode', value: 'date' },
                { text: 'Network', value: 'network' },
                { text: 'Progress', value: 'progress' },
                { text: 'Indexer', value: 'indexer' }
            ]
        };
    },
    computed: {
        ...mapState({
            stateLayout: state => state.config.layout,
            showsLoading: state => state.shows.loading
        }),
        ...mapGetters({
            showsInLists: 'showsInLists'
        }),
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
        mappedLayout() {
            const { layout } = this;
            if (layout === 'small') {
                return 'smallposter';
            }
            return layout;
        },
        posterUiSortBy: {
            get() {
                const { stateLayout } = this;
                const { posterSortby } = stateLayout;
                return posterSortby;
            },
            set(value) {
                const { setPosterSortBy } = this;
                setPosterSortBy({ value });
            }
        },
        posterUiSortDir: {
            get() {
                const { stateLayout } = this;
                const { posterSortdir } = stateLayout;
                return posterSortdir;
            },
            set(value) {
                const { setPosterSortDir } = this;
                setPosterSortDir({ value });
            }
        }
    },
    methods: {
        ...mapActions({
            setPosterSortBy: 'setPosterSortBy',
            setPosterSortDir: 'setPosterSortDir',
            setLayoutLocal: 'setLayoutLocal'
        })
    }
};
</script>
<style scoped>
/* Configure the show-list-title for in the poster layout. */
.show-list-title {
    display: flex;
    float: left;
    margin-top: 6px;
}

button.nav-show-list {
    height: 20px;
}

.show-list-title > h3 {
    margin: 0;
}

/* Configure the show-list-title for in the table layouts. */
.table-layout >>> .show-list-title {
    display: flex;
    float: left;
}

.table-layout >>> button.nav-show-list {
    height: 20px;
}

.table-layout >>> .show-list-title > h3 {
    margin: 0;
}

/** Use this as table styling for all table layouts */
.table-layout >>> .vgt-table {
    width: 100%;
    margin-right: auto;
    margin-left: auto;
    text-align: left;
    border-spacing: 0;
}

.table-layout >>> .vgt-table th,
.table-layout >>> .vgt-table td {
    padding: 4px;
    vertical-align: middle;
}

/* remove extra border from left edge */
.table-layout >>> .vgt-table th:first-child,
.table-layout >>> .vgt-table td:first-child {
    border-left: none;
}

.table-layout >>> .vgt-table th {
    text-align: center;
    border-collapse: collapse;
    font-weight: normal;
}

.table-layout >>> .vgt-table span.break-word {
    word-wrap: break-word;
}

.table-layout >>> .vgt-table thead th.sorting.sorting-asc {
    background-position-x: right;
    background-position-y: bottom;
}

.table-layout >>> .vgt-table thead th.sorting {
    background-repeat: no-repeat;
}

.table-layout >>> .vgt-table thead th {
    padding: 4px;
    cursor: default;
}

.table-layout >>> .vgt-table input.tablesorter-filter {
    width: 98%;
    height: auto;
    -webkit-box-sizing: border-box;
    -moz-box-sizing: border-box;
    box-sizing: border-box;
}

.table-layout >>> .vgt-table tr.tablesorter-filter-row,
.table-layout >>> .vgt-table tr.tablesorter-filter-row td {
    text-align: center;
}

/* optional disabled input styling */
.table-layout >>> .vgt-table input.tablesorter-filter-row .disabled {
    display: none;
}

.tablesorter-header-inner {
    padding: 0 2px;
    text-align: center;
}

.table-layout >>> .vgt-table tfoot tr {
    text-align: center;
    border-collapse: collapse;
}

.table-layout >>> .vgt-table tfoot a {
    text-decoration: none;
}

.table-layout >>> .vgt-table th.vgt-row-header {
    text-align: left;
}

.table-layout >>> .vgt-table .season-header {
    display: inline;
    margin-left: 5px;
}

.table-layout >>> .vgt-table tr.spacer {
    height: 25px;
}

.table-layout >>> .vgt-dropdown {
    float: right;
}

.table-layout >>> .vgt-dropdown-menu {
    position: absolute;
    z-index: 1000;
    float: left;
    min-width: 160px;
    padding: 5px 0;
    margin: 2px 0 0;
    font-size: 14px;
    text-align: left;
    list-style: none;
    background-clip: padding-box;
    border-radius: 4px;
}

.table-layout >>> .vgt-dropdown-menu > li > span {
    display: block;
    padding: 3px 20px;
    clear: both;
    font-weight: 400;
    line-height: 1.42857143;
    white-space: nowrap;
}

.table-layout >>> .indexer-image :not(:last-child) {
    margin-right: 5px;
}

.table-layout >>> .vgt-input {
    width: 100%;
}

.table-layout >>> .vgt-select {
    margin-top: -1px;
}

</style>

<template>
    <div class="history-wrapper-compact vgt-table-styling">

        <vue-good-table
            ref="compact-history"
            mode="remote"
            @on-page-change="onPageChange"
            @on-per-page-change="onPerPageChange"
            @on-sort-change="onSortChange"
            @on-column-filter="onColumnFilter"

            :columns="columns"
            :rows="remoteHistory.rows"
            :totalRows="remoteHistory.totalRows"
            :search-options="{
                enabled: false
            }"
            :sort-options="{
                enabled: true,
                multipleColumns: false,
                initialSortBy: historyHeaderSort
            }"
            :pagination-options="{
                enabled: true,
                perPage: remoteHistory.perPage,
                perPageDropdown,
                dropdownAllowAll: false,
                setCurrentPage: remoteHistory.page,
                position: 'both'
            }"
            :column-filter-options="{
                enabled: true
            }"
            styleClass="vgt-table condensed"
        >
            <template slot="table-row" slot-scope="props">

                <span v-if="props.column.label === 'Date'" class="align-center">
                    {{props.row.actionDate ? fuzzyParseDateTime(props.formattedRow[props.column.field]) : ''}}
                </span>

                <span v-else-if="props.column.label === 'Episode'" class="episode-title">
                    <app-link :href="`home/displayShow?showslug=${props.row.showSlug}`">{{ props.row.episodeTitle }}</app-link>
                </span>

                <span v-else-if="props.column.label === 'Snatched'" class="align-center">
                    <div v-for="row in sortDate(props.row.rows)" :key="row.id">
                        <template v-if="row.statusName === 'Snatched'">
                            <img style="margin-right: 5px;"
                                 :src="`images/providers/${row.provider.imageName}`"
                                 :alt="row.provider.name" width="16" height="16"
                                 v-tooltip.right="`${row.provider.name}: ${row.resource} (${fuzzyParseDateTime(convertDateFormat(row.actionDate))})`"
                                 onError="this.onerror=null;this.src='images/providers/missing.png';"
                            >
                            <img v-if="row.manuallySearched" src="images/manualsearch.png" width="16" height="16" style="vertical-align:middle;" v-tooltip.right="`Manual searched episode: ${row.resource} (${fuzzyParseDateTime(convertDateFormat(row.actionDate))})`">
                            <img v-if="row.properTags" src="images/info32.png" width="16" height="16" style="vertical-align:middle;" v-tooltip.right="`${row.properTags.split(/[ |]+/).join(', ')}: ${row.resource} (${fuzzyParseDateTime(convertDateFormat(row.actionDate))})`">

                        </template>
                        <img v-else-if="row.statusName ==='Failed'" src="images/no16.png"
                             width="16" height="16" style="vertical-align:middle;"
                             v-tooltip.right="`${row.provider.name} download failed: ${row.resource} (${fuzzyParseDateTime(convertDateFormat(row.actionDate))})`"
                        >
                    </div>
                </span>

                <span v-else-if="props.column.label === 'Downloaded'" class="align-center">
                    <div v-for="row in sortDate(props.row.rows)" :key="row.id">
                        <template v-if="['Downloaded', 'Archived'].includes(row.statusName)">
                            <span v-if="row.releaseGroup && row.releaseGroup !== '-1'" class="release-group" v-tooltip.right="getFileBaseName(row.resource)"><i>{{row.releaseGroup}}</i></span>
                            <span v-else style="cursor: help;" v-tooltip.right="getFileBaseName(row.resource)"><i>Unknown</i></span>
                        </template>
                    </div>
                </span>

                <span v-else-if="props.column.label === 'Subtitled'" class="align-center">
                    <div v-for="row in sortDate(props.row.rows)" :key="row.id" style="margin-right: 5px;">
                        <template v-if="row.statusName === 'Subtitled'">
                            <img :src="`images/subtitles/${row.provider.name}.png`" width="16" height="16" style="vertical-align:middle;" :alt="row.provider.name" v-tooltip.right="`${row.provider.name}: ${getFileBaseName(row.resource)}`">
                            <span style="vertical-align:middle;"> / </span>
                            <img width="16" height="11" :src="`images/subtitles/flags/${row.resource}.png`" onError="this.onerror=null;this.src='images/flags/unknown.png';" style="vertical-align: middle !important;">
                        </template>
                    </div>
                </span>

                <span v-else-if="props.column.label === 'Quality'" class="align-center">
                    <quality-pill v-if="props.row.quality !== 0" :quality="props.row.quality" />
                </span>

                <span v-else>
                    {{props.formattedRow[props.column.field]}}
                </span>
            </template>

            <template #column-filter="{ column }">
                <span v-if="column.field === 'episodeTitle'">
                    <input :value="episodeFilter.inputValue" placeholder="Show title or release" class="'form-control input-sm vgt-input" @input="updateResource">
                </span>
            </template>
        </vue-good-table>
    </div>
</template>
<script>

import debounce from 'lodash/debounce';
import { mapActions, mapGetters, mapState } from 'vuex';
import { VueGoodTable } from 'vue-good-table';
import { humanFileSize } from '../utils/core';
import { normalizeHistoryTextFilter } from '../utils/history';
import { manageCookieMixin } from '../mixins/manage-cookie';
import QualityPill from './helpers/quality-pill.vue';
import AppLink from './helpers/app-link.vue';
import { VTooltip } from 'v-tooltip';
import parse from 'date-fns/parse';
import formatDate from 'date-fns/format';

export default {
    name: 'history-compact',
    components: {
        AppLink,
        QualityPill,
        VueGoodTable
    },
    directives: {
        tooltip: VTooltip
    },
    mixins: [
        manageCookieMixin('historyCompact')
    ],
    data() {
        const { getCookie } = this;
        const perPageDropdown = [25, 50, 100, 250, 500, 1000];
        const columns = [{
            label: 'Time',
            field: 'actionDate',
            dateInputFormat: 'yyyyMMddHHmmss', // E.g. 07-09-2017 19:16:25
            dateOutputFormat: 'yyyy-MM-dd HH:mm:ss',
            type: 'date',
            firstSortType: 'desc',
            hidden: getCookie('Time')
        }, {
            label: 'Episode',
            field: 'episodeTitle',
            sortable: false,
            filterOptions: {
                enabled: true,
                customFilter: true
            },
            hidden: getCookie('Episode')
        }, {
            label: 'Snatched',
            field: 'snatched',
            type: 'number',
            sortable: false,
            hidden: getCookie('Snatched')
        }, {
            label: 'Downloaded',
            field: 'downloaded',
            sortable: false,
            hidden: getCookie('Downloaded')
        }, {
            label: 'Subtitled',
            field: 'subtitled',
            hidden: getCookie('Subtitled')
        }, {
            label: 'Quality',
            field: 'quality',
            hidden: getCookie('Quality')
        }];

        return {
            columns,
            selectedClientStatusValue: [],
            perPageDropdown,
            historyTableMounted: false,
            historyHeaderSort: [],
            restoringSortHeader: false
        };
    },
    mounted() {
        this.historyTableMounted = true;
        this.loadItems();
    },
    created() {
        this.initializeEpisodeFilter({ layout: 'compact' });
        this.initializeHistorySort({
            layout: 'compact',
            sort: this.getSortFromCookie()
        });
        this.historyHeaderSort = this.remoteHistory.sort;
        this.initializeHistoryPagination({
            layout: 'compact',
            perPage: this.getCookie('pagination-perpage-history')
        });
        this.setCookie('sort', this.remoteHistory.sort);
        this.setCookie('pagination-perpage-history', this.remoteHistory.perPage);
        this.loadItemsDebounced = debounce(this.loadItems, 500);
    },
    beforeDestroy() {
        if (this.loadItemsDebounced && this.loadItemsDebounced.cancel) {
            this.loadItemsDebounced.cancel();
        }
    },
    computed: {
        ...mapState({
            layout: state => state.config.layout,
            remoteHistory: state => state.history.remoteCompact,
            episodeFilter: state => state.history.episodeFilter || {
                inputValue: '',
                filterValue: '',
                malformed: false,
                initialized: false
            },
            consts: state => state.config.consts
        }),
        ...mapGetters({
            fuzzyParseDateTime: 'fuzzyParseDateTime'
        }),
        serverParams() {
            return {
                page: this.remoteHistory.page, // What page I want to show
                perPage: this.remoteHistory.perPage, // How many items I'm showing per page
                sort: this.remoteHistory.sort,
                filter: this.remoteHistory.filter,
                compact: true
            };
        },
        qualityOptions() {
            const { consts } = this;
            return consts.qualities.values.map(quality => {
                return ({ value: quality.value, text: quality.name });
            });
        }
    },
    methods: {
        humanFileSize,
        ...mapActions({
            getHistory: 'getHistory',
            checkHistory: 'checkHistory',
            initializeEpisodeFilter: 'initializeEpisodeFilter',
            initializeHistorySort: 'initializeHistorySort',
            initializeHistoryPagination: 'initializeHistoryPagination',
            updateEpisodeFilter: 'updateEpisodeFilter',
            setStoreLayout: 'setStoreLayout'
        }),
        getSortFromCookie() {
            const { getCookie } = this;
            const sort = getCookie('sort'); // From manage-cookie.js mixin
            const supportedFields = ['date', 'actionDate', 'subtitled', 'quality'];
            const defaultSort = [{ field: 'date', type: 'desc' }];
            if (!Array.isArray(sort) || sort.length === 0) {
                return defaultSort;
            }
            const [firstSort] = sort;
            const firstSortPrototype = firstSort !== null && typeof firstSort === 'object' ? Object.getPrototypeOf(firstSort) : undefined;
            const isPlainObject = firstSortPrototype === Object.prototype || firstSortPrototype === null;
            if (!isPlainObject || typeof firstSort.field !== 'string' || typeof firstSort.type !== 'string' || !supportedFields.includes(firstSort.field) || !['asc', 'desc'].includes(firstSort.type)) {
                return defaultSort;
            }
            return [{ field: firstSort.field, type: firstSort.type }];
        },
        sortDate(rows) {
            const cloneRows = [...rows];
            const getNumericDate = value => {
                if (typeof value === 'number' && Number.isFinite(value)) {
                    return value;
                }
                if (typeof value === 'string' && value.trim() !== '') {
                    const numericValue = Number(value);
                    if (Number.isFinite(numericValue)) {
                        return numericValue;
                    }
                }
                return null;
            };
            const compareIds = (left, right) => {
                const leftId = Number(left.id);
                const rightId = Number(right.id);
                if (Number.isFinite(leftId) && Number.isFinite(rightId)) {
                    return leftId - rightId;
                }
                return String(left.id).localeCompare(String(right.id));
            };

            return cloneRows.sort((left, right) => {
                const leftDate = getNumericDate(left.actionDate);
                const rightDate = getNumericDate(right.actionDate);
                if (leftDate === null && rightDate !== null) {
                    return 1;
                }
                if (leftDate !== null && rightDate === null) {
                    return -1;
                }
                if (leftDate !== null && rightDate !== null && leftDate !== rightDate) {
                    return rightDate - leftDate;
                }
                return compareIds(left, right);
            });
        },
        getFileBaseName(path) {
            if (path) {
                return path.split(/[/\\]/).pop();
            }
            return path;
        },
        close() {
            this.$emit('close');
            // Destroy the vue listeners, etc
            this.$destroy();
            // Remove the element from the DOM
            this.$el.remove();
        },
        updatePaginationPerPage(pageLimit) {
            const { setStoreLayout } = this;
            setStoreLayout({ key: 'historyLimit', value: pageLimit });
        },
        onPageChange(params) {
            if (!this.historyTableMounted && params.currentPage === 1 && this.remoteHistory.page !== 1) {
                return;
            }
            this.remoteHistory.page = params.currentPage;
            this.loadItemsDebounced();
        },
        onPerPageChange(params) {
            this.setCookie('pagination-perpage-history', params.currentPerPage);
            this.remoteHistory.perPage = params.currentPerPage;
            this.loadItemsDebounced();
        },
        onSortChange(params) {
            if (this.restoringSortHeader) {
                return;
            }
            if (this.episodeFilter.malformed) {
                this.updateEpisodeFilter({
                    inputValue: this.episodeFilter.filterValue,
                    filterValue: this.episodeFilter.filterValue,
                    malformed: false,
                    resetPage: false
                });
            }
            const sort = Array.isArray(params) ? params.filter(item => item.type !== 'none') : [];
            const canonicalSort = sort.length > 0 ? sort : [{ field: 'actionDate', type: 'desc' }];
            this.setCookie('sort', canonicalSort);
            this.remoteHistory.sort = canonicalSort;
            if (sort.length === 0) {
                this.historyHeaderSort = canonicalSort;
                this.restoringSortHeader = true;
                this.$nextTick(() => {
                    try {
                        const table = this.$refs['compact-history'];
                        if (table && typeof table.initializeSort === 'function') {
                            table.initializeSort();
                        }
                    } finally {
                        this.restoringSortHeader = false;
                    }
                });
            }
            this.loadItemsDebounced();
        },
        onColumnFilter() {
            const currentFilters = this.remoteHistory.filter && this.remoteHistory.filter.columnFilters ? this.remoteHistory.filter.columnFilters : {};
            const resource = this.episodeFilter.initialized ? this.episodeFilter.filterValue : currentFilters.resource;
            this.applyFilter(resource ? { resource } : {});
        },
        applyFilter(columnFilters) {
            const nextFilter = Object.assign({}, this.remoteHistory.filter, {
                columnFilters
            });
            this.remoteHistory.filter = nextFilter;
            this.remoteHistory.page = 1;
            this.loadItemsDebounced();
        },
        updateFilterValue(field, value) {
            const currentFilters = this.remoteHistory.filter && this.remoteHistory.filter.columnFilters ? this.remoteHistory.filter.columnFilters : {};
            const columnFilters = Object.assign({}, currentFilters, {
                [field]: value
            });
            this.applyFilter(columnFilters);
        },
        updateClientStatusFilter(event) {
            const combinedStatus = event.reduce((result, item) => {
                return result | item.value;
            }, 0);
            this.selectedClientStatusValue = event;
            this.updateFilterValue('clientStatus', combinedStatus);
        },
        updateQualityFilter(quality) {
            this.updateFilterValue('quality', quality.currentTarget.value);
        },
        updateResource(resource) {
            const { value } = resource.currentTarget;
            const normalized = normalizeHistoryTextFilter(value);
            this.updateEpisodeFilter({
                inputValue: normalized.clearInput ? '' : value,
                filterValue: normalized.filterValue,
                malformed: normalized.malformed
            });
            this.loadItemsDebounced();
        },
        // Load items is what brings back the rows from server
        loadItems() {
            const { getHistory } = this;
            console.log(this.serverParams);
            getHistory(this.serverParams);
        },
        /**
         * Re-format date.
         * @param {number} date - Date formatted as a number.
         * @returns {string} - Formatted date as a string.
         */
        convertDateFormat(date) {
            const dateObj = parse(date, 'yyyyMMddHHmmss', new Date()); // Example: 20210813162256
            return formatDate(dateObj, 'yyyy-MM-dd HH:mm:ss');
        }
    }
};
</script>
<style scoped>
/* History compact */
span.release-group {
    cursor: help;
    margin-right: 5px;
}
</style>

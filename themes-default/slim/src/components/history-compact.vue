<template>
    <div class="history-wrapper-compact vgt-table-styling">

        <vue-good-table
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
                initialSortBy: getSortFromCookie()
            }"
            :pagination-options="{
                enabled: true,
                perPage: remoteHistory.perPage,
                perPageDropdown,
                dropdownAllowAll: false,
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
                    <input placeholder="Resource" class="'form-control input-sm vgt-input" @input="updateResource">
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
            hidden: getCookie('Date')
        }, {
            label: 'Episode',
            field: 'episodeTitle',
            sortable: false,
            filterOptions: {
                enabled: true,
                customFilter: true
            },
            hidden: getCookie('Status')
        }, {
            label: 'Snatched',
            field: 'snatched',
            type: 'number',
            sortable: false,
            hidden: getCookie('Quality')
        }, {
            label: 'Downloaded',
            field: 'downloaded',
            sortable: false,
            hidden: getCookie('Provider/Group')
        }, {
            label: 'Subtitled',
            field: 'subtitled',
            hidden: getCookie('Release')
        }, {
            label: 'Quality',
            field: 'quality',
            hidden: getCookie('Release')
        }];

        return {
            columns,
            selectedClientStatusValue: [],
            perPageDropdown
        };
    },
    mounted() {
        const { getCookie, getSortFromCookie } = this;

        // Get per-page pagination from cookie
        const perPage = getCookie('pagination-perpage-history');
        if (perPage) {
            this.remoteHistory.perPage = perPage;
        }
        this.remoteHistory.sort = getSortFromCookie();
    },
    created() {
        this.loadItemsDebounced = debounce(this.loadItems, 500);
    },
    computed: {
        ...mapState({
            layout: state => state.config.layout,
            remoteHistory: state => state.history.remoteCompact,
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
            setStoreLayout: 'setStoreLayout'
        }),
        getSortFromCookie() {
            const { getCookie } = this;
            const sort = getCookie('sort'); // From manage-cookie.js mixin
            if (sort) {
                if (sort[0].type === 'none') {
                    sort[0].type = 'desc';
                }
                return sort;
            }
            return [{ field: 'date', type: 'desc' }];
        },
        sortDate(rows) {
            const cloneRows = [...rows];
            return cloneRows.sort(x => x.actionDate).reverse();
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
            this.remoteHistory.page = params.currentPage;
            this.loadItemsDebounced();
        },
        onPerPageChange(params) {
            this.setCookie('pagination-perpage-history', params.currentPerPage);
            this.remoteHistory.perPage = params.currentPerPage;
            this.loadItemsDebounced();
        },
        onSortChange(params) {
            this.setCookie('sort', params);
            this.remoteHistory.sort = params.filter(item => item.type !== 'none');
            this.loadItemsDebounced();
        },
        onColumnFilter(params) {
            this.remoteHistory.filter = params;
            this.loadItemsDebounced();
        },
        updateClientStatusFilter(event) {
            const combinedStatus = event.reduce((result, item) => {
                return result | item.value;
            }, 0);
            if (!this.remoteHistory.filter) {
                this.remoteHistory.filter = { columnFilters: {} };
            }
            this.selectedClientStatusValue = event;
            this.remoteHistory.filter.columnFilters.clientStatus = combinedStatus;
            this.loadItemsDebounced();
        },
        updateQualityFilter(quality) {
            if (!this.remoteHistory.filter) {
                this.remoteHistory.filter = { columnFilters: {} };
            }
            this.remoteHistory.filter.columnFilters.quality = quality.currentTarget.value;
            this.loadItemsDebounced();
        },
        updateResource(resource) {
            resource = resource.currentTarget.value;
            if (!this.remoteHistory.filter) {
                this.remoteHistory.filter = { columnFilters: {} };
            }

            this.remoteHistory.filter.columnFilters.resource = resource;
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

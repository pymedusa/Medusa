<template>
    <div class="history-detailed-wrapper vgt-table-styling">

        <vue-good-table
            ref="detailed-history"
            mode="remote"
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
            :row-style-class="rowStyleClassFn"
            styleClass="vgt-table condensed"
            @on-page-change="onPageChange"
            @on-per-page-change="onPerPageChange"
            @on-sort-change="onSortChange"
            @on-column-filter="onColumnFilter"
        >
            <template #table-row="props">
                <span v-if="props.column.label === 'Date'" class="align-center">
                    {{props.row.actionDate ? fuzzyParseDateTime(props.formattedRow[props.column.field]) : ''}}
                </span>

                <span v-else-if="props.column.label === 'Episode'" class="episode-title">
                    <app-link :href="`home/displayShow?showslug=${props.row.showSlug}`">{{ props.row.episodeTitle }}</app-link>
                </span>

                <span v-else-if="props.column.label === 'Action'" class="align-center status-name">
                    <span v-tooltip.right="props.row.resource">{{props.row.statusName}}</span>
                    <font-awesome-icon v-if="props.row.partOfBatch" icon="images" v-tooltip.right="'This release is part of a batch of releases'" />
                </span>

                <span v-else-if="props.column.label === 'Provider'" class="align-center">
                    <!-- These should get a provider icon -->
                    <template v-if="['Snatched', 'Failed'].includes(props.row.statusName)">
                        <img  style="margin-right: 5px;"
                              :src="`images/providers/${props.row.provider.imageName}`"
                              :alt="props.row.provider.name" width="16" height="16"
                              :title="props.row.provider.name"
                              v-tooltip.right="props.row.provider.name"
                              onError="this.onerror=null;this.src='images/providers/missing.png';"
                        >
                    </template>

                    <!-- Downloaded history items do not get a provider stored -->
                    <span v-if="props.row.statusName === 'Downloaded'">
                        <span v-if="props.row.releaseGroup && props.row.releaseGroup !== '-1'" class="release-group"><i>{{props.row.releaseGroup}}</i></span>
                        <span v-else style="cursor: help;" v-tooltip.right="'Release group unknown'"><i>Unknown</i></span>
                    </span>

                    <!-- Different path for subtitle providers -->
                    <img v-else-if="props.row.statusName === 'Subtitled'" class="addQTip" style="margin-right: 5px;"
                         :src="`images/subtitles/${props.row.provider.name}.png`"
                         :alt="props.row.provider.name" width="16" height="16"
                         :title="props.row.provider.name"
                         v-tooltip.right="props.row.provider.name"
                    >
                    <span v-else>
                        {{props.row.provider.name}}
                    </span>
                </span>

                <span v-else-if="props.column.label === 'Client Status'" class="align-center">
                    <span v-if="props.row.clientStatus" v-tooltip.right="props.row.clientStatus.status.join(', ')">{{props.row.clientStatus.string.join(', ')}}</span>
                </span>

                <span v-else-if="props.column.label === 'Release' && props.row.statusName === 'Subtitled'" class="align-center">
                    <img v-if="props.row.resource !== 'und'" :src="`images/subtitles/flags/${props.row.resource}.png`" width="16" height="11" :alt="props.row.resource" onError="this.onerror=null;this.src='images/flags/unknown.png';">
                    <img v-else :src="`images/subtitles/flags/${props.row.resource}.png`" class="subtitle-flag" width="16" height="11" :alt="props.row.resource" onError="this.onerror=null;this.src='images/flags/unknown.png';">
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

                <span v-else-if="column.field === 'providerId'">
                    <input :value="providerFilterValue" placeholder="Provider | Group" class="'form-control input-sm vgt-input" @input="updateProvider">
                </span>

                <span v-else-if="column.field === 'quality'">
                    <select class="form-control form-control-inline input-sm vgt-select" @input="updateQualityFilter">
                        <option value="">Filter Quality</option>
                        <option v-for="option in consts.qualities.values" :value="option.value" :key="option.key">{{ option.name }}</option>
                    </select>
                </span>

                <span v-else-if="column.field === 'size'">
                    <input :value="sizeFilterInputValue" placeholder="e.g. <200 MB or >1.3 GB" class="'form-control input-sm vgt-input" @input="updateSizeFilter">
                </span>

                <span v-else-if="column.field === 'clientStatus'">
                    <multiselect
                        :value="selectedClientStatusValue"
                        :multiple="true"
                        :options="consts.clientStatuses"
                        track-by="value"
                        label="name"
                        @input="updateClientStatusFilter"
                        class="vgt-multiselect"
                    />
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
import { normalizeHistorySizeFilter, normalizeHistoryTextFilter } from '../utils/history';
import { manageCookieMixin } from '../mixins/manage-cookie';
import AppLink from './helpers/app-link.vue';
import QualityPill from './helpers/quality-pill.vue';
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome';
import { VTooltip } from 'v-tooltip';
import Multiselect from 'vue-multiselect';
import 'vue-multiselect/dist/vue-multiselect.min.css';

export default {
    name: 'history-detailed',
    components: {
        AppLink,
        FontAwesomeIcon,
        QualityPill,
        VueGoodTable,
        Multiselect
    },
    directives: {
        tooltip: VTooltip
    },
    mixins: [
        manageCookieMixin('history-detailed')
    ],
    data() {
        const { getCookie } = this;
        const perPageDropdown = [25, 50, 100, 250, 500, 1000];
        const statusNames = [
            { value: -1, text: 'Unset' },
            { value: 1, text: 'Unaired' },
            { value: 5, text: 'Skipped' },
            { value: 3, text: 'Wanted' },
            { value: 2, text: 'Snatched' },
            { value: 9, text: 'Snatched (Proper)' },
            { value: 12, text: 'Snatched (Best)' },
            { value: 4, text: 'Downloaded' },
            { value: 6, text: 'Archived' },
            { value: 7, text: 'Ignored' },
            { value: 10, text: 'Subtitled' },
            { value: 11, text: 'Failed' }
        ];
        const columns = [{
            label: 'Date',
            field: 'actionDate',
            dateInputFormat: 'yyyyMMddHHmmss', // E.g. 07-09-2017 19:16:25
            dateOutputFormat: 'yyyy-MM-dd HH:mm:ss',
            type: 'date',
            firstSortType: 'desc',
            hidden: getCookie('Date')
        }, {
            label: 'Episode',
            field: 'episodeTitle',
            sortable: false,
            filterOptions: {
                customFilter: true
            },
            hidden: getCookie('Episode')
        }, {
            label: 'Action',
            field: 'statusName',
            filterOptions: {
                enabled: true,
                filterDropdownItems: statusNames
            },
            hidden: getCookie('Action')
        }, {
            label: 'Quality',
            field: 'quality',
            type: 'number',
            filterOptions: {
                customFilter: true
            },
            hidden: getCookie('Quality')
        }, {
            label: 'Provider',
            field: 'providerId',
            filterOptions: {
                enabled: true
            },
            hidden: getCookie('Provider')
        }, {
            label: 'Size',
            field: 'size',
            tdClass: 'align-center-span',
            formatFn: humanFileSize,
            type: 'number',
            filterOptions: {
                customFilter: true
            },
            hidden: getCookie('Size')
        }, {
            label: 'Client Status',
            field: 'clientStatus',
            type: 'number',
            filterOptions: {
                customFilter: true
            },
            hidden: getCookie('Client Status')
        }];

        return {
            columns,
            selectedClientStatusValue: [],
            perPageDropdown,
            historyTableMounted: false,
            historyHeaderSort: [],
            restoringSortHeader: false,
            providerFilterValue: '',
            sizeFilterInputValue: '',
            sizeFilterPendingCleanup: false,
            malformedTextFilters: {
                providerId: false
            }
        };
    },
    mounted() {
        this.historyTableMounted = true;
        this.loadItems();
    },
    created() {
        this.initializeEpisodeFilter({ layout: 'detailed' });
        const currentFilters = this.remoteHistory.filter && this.remoteHistory.filter.columnFilters ? this.remoteHistory.filter.columnFilters : {};
        this.initializeClientStatusFilter(currentFilters.clientStatus);
        this.providerFilterValue = currentFilters.providerId || '';
        this.sizeFilterInputValue = currentFilters.size || '';
        this.initializeHistorySort({
            layout: 'detailed',
            sort: this.getSortFromCookie()
        });
        this.historyHeaderSort = this.remoteHistory.sort;
        this.initializeHistoryPagination({
            layout: 'detailed',
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
            remoteHistory: state => state.history.remote,
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
                filter: this.remoteHistory.filter
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
            initializeEpisodeFilter: 'initializeEpisodeFilter',
            initializeHistorySort: 'initializeHistorySort',
            initializeHistoryPagination: 'initializeHistoryPagination',
            updateEpisodeFilter: 'updateEpisodeFilter',
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
        rowStyleClassFn(row) {
            return `${row.statusName.toLowerCase()} status` || 'skipped status';
        },
        close() {
            this.$emit('close');
            // Destroy the vue listeners, etc
            this.$destroy();
            // Remove the element from the DOM
            this.$el.remove();
        },
        onPageChange(params) {
            if (!this.historyTableMounted && params.currentPage === 1 && this.remoteHistory.page !== 1) {
                return;
            }
            console.log('page change called');
            console.log(params);
            this.remoteHistory.page = params.currentPage;
            this.loadItemsDebounced();
        },
        onPerPageChange(params) {
            console.log('per page change called');
            this.setCookie('pagination-perpage-history', params.currentPerPage);
            this.remoteHistory.perPage = params.currentPerPage;
            this.loadItemsDebounced();
        },
        onSortChange(params) {
            if (this.restoringSortHeader) {
                return;
            }
            this.canonicalizeMalformedTextFilters(undefined, false);
            const sort = Array.isArray(params) ? params.filter(item => item.type !== 'none') : [];
            const canonicalSort = sort.length > 0 ? sort : [{ field: 'actionDate', type: 'desc' }];
            this.setCookie('sort', canonicalSort);
            this.remoteHistory.sort = canonicalSort;
            if (sort.length === 0) {
                this.historyHeaderSort = canonicalSort;
                this.restoringSortHeader = true;
                this.$nextTick(() => {
                    try {
                        const table = this.$refs['detailed-history'];
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
        canonicalizeMalformedTextFilters(exceptField, resetPage = true) {
            if (exceptField !== 'resource' && this.episodeFilter.malformed) {
                this.updateEpisodeFilter({
                    inputValue: this.episodeFilter.filterValue,
                    filterValue: this.episodeFilter.filterValue,
                    malformed: false,
                    resetPage
                });
            }
            if (exceptField !== 'providerId' && this.malformedTextFilters.providerId) {
                const currentFilters = this.remoteHistory.filter && this.remoteHistory.filter.columnFilters ? this.remoteHistory.filter.columnFilters : {};
                this.providerFilterValue = currentFilters.providerId || '';
                this.malformedTextFilters.providerId = false;
            }
            if (exceptField !== 'size' && this.sizeFilterPendingCleanup) {
                const currentFilters = this.remoteHistory.filter && this.remoteHistory.filter.columnFilters ? this.remoteHistory.filter.columnFilters : {};
                this.sizeFilterInputValue = currentFilters.size || '';
                this.sizeFilterPendingCleanup = false;
            }
        },
        onColumnFilter(params) {
            this.canonicalizeMalformedTextFilters();
            const nextFilter = params && Object.prototype.hasOwnProperty.call(params, 'columnFilters') ? params.columnFilters : params || {};
            const currentFilters = this.remoteHistory.filter && this.remoteHistory.filter.columnFilters ? this.remoteHistory.filter.columnFilters : {};
            const manualKeys = ['resource', 'providerId', 'quality', 'size', 'clientStatus'];
            const manualFilters = manualKeys.reduce((result, key) => {
                if (Object.prototype.hasOwnProperty.call(currentFilters, key)) {
                    result[key] = currentFilters[key];
                }
                return result;
            }, {});

            this.applyFilter(Object.assign({}, manualFilters, nextFilter));
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
            if (!['resource', 'providerId'].includes(field)) {
                this.canonicalizeMalformedTextFilters(field === 'size' ? 'size' : undefined);
            }
            const currentFilters = this.remoteHistory.filter && this.remoteHistory.filter.columnFilters ? this.remoteHistory.filter.columnFilters : {};
            const columnFilters = Object.assign({}, currentFilters, {
                [field]: value
            });
            this.applyFilter(columnFilters);
        },
        initializeClientStatusFilter(value) {
            const clientStatuses = Array.isArray(this.consts.clientStatuses) ? this.consts.clientStatuses : [];
            if (value === undefined || value === null || value === '') {
                this.selectedClientStatusValue = [];
                return;
            }

            if (value === 0) {
                this.selectedClientStatusValue = clientStatuses.filter(option => option.value === 0);
                return;
            }

            const supportedMask = clientStatuses.reduce((result, option) => result | option.value, 0);
            if (!Number.isInteger(value) || value < 0 || value > supportedMask) {
                this.selectedClientStatusValue = [];
                return;
            }

            if ((value & ~supportedMask) !== 0) {
                this.selectedClientStatusValue = [];
                return;
            }

            this.selectedClientStatusValue = clientStatuses.filter(option => {
                return option.value !== 0 && (value & option.value) === option.value;
            });
        },
        updateClientStatusFilter(event) {
            const nextSelection = Array.isArray(event) ? event : [];
            if (nextSelection.length === 0) {
                this.selectedClientStatusValue = [];
                this.updateFilterValue('clientStatus', '');
                return;
            }

            const previousSelection = Array.isArray(this.selectedClientStatusValue) ? this.selectedClientStatusValue : [];
            const previousValues = previousSelection.map(item => item.value);
            const hasSnatched = nextSelection.some(item => item.value === 0);
            const nonzeroSelection = nextSelection.filter(item => item.value !== 0);
            let normalizedSelection = nextSelection;

            if (hasSnatched && nonzeroSelection.length > 0) {
                const hadSnatched = previousValues.includes(0);
                const hadNonzero = previousValues.some(value => value !== 0);
                normalizedSelection = hadNonzero && !hadSnatched ? nextSelection.filter(item => item.value === 0) : nonzeroSelection;
            }

            const combinedStatus = normalizedSelection.reduce((result, item) => {
                return result | item.value;
            }, 0);
            this.selectedClientStatusValue = normalizedSelection;
            this.updateFilterValue('clientStatus', combinedStatus);
        },
        updateQualityFilter(quality) {
            this.updateFilterValue('quality', quality.currentTarget.value);
        },
        /**
         * Update the History Size filter.
         * @param {Event} event - Input event containing a comparison with optional MB or GB units.
         */
        updateSizeFilter(event) {
            const rawValue = event.currentTarget.value;
            const normalized = normalizeHistorySizeFilter(rawValue);
            this.sizeFilterInputValue = rawValue;

            if (!normalized.valid && !normalized.clearFilter) {
                this.sizeFilterPendingCleanup = true;
                return;
            }

            this.sizeFilterPendingCleanup = !normalized.valid;
            this.updateFilterValue('size', normalized.filterValue);
        },
        updateResource(resource) {
            const { value } = resource.currentTarget;
            const normalized = normalizeHistoryTextFilter(value);
            this.updateEpisodeFilter({
                inputValue: normalized.clearInput ? '' : value,
                filterValue: normalized.filterValue,
                malformed: normalized.malformed
            });
            this.canonicalizeMalformedTextFilters('resource');
            this.loadItemsDebounced();
        },
        updateProvider(provider) {
            const { value } = provider.currentTarget;
            const normalized = normalizeHistoryTextFilter(value);
            this.providerFilterValue = normalized.clearInput ? '' : value;
            this.malformedTextFilters.providerId = normalized.malformed;
            this.canonicalizeMalformedTextFilters('providerId');
            this.updateFilterValue('providerId', normalized.filterValue);
        },
        // Load items is what brings back the rows from server
        loadItems() {
            const { getHistory } = this;
            console.log(this.serverParams);
            getHistory(this.serverParams);
        }
    }
};
</script>
<style scoped>
/* History tables */
.status-name > svg {
    margin-left: 5px;
}

.vgt-multiselect {
    min-height: 30px;
}

.multiselect--active {
    min-width: 200px;
}

.vgt-multiselect >>> .multiselect__placeholder {
    margin-bottom: 0;
    padding-top: 0;
}

.vgt-multiselect >>> .multiselect__tags {
    padding-top: 0;
    min-height: 30px;
}

:not(tr.status) span.episode-title a,
:not(tr.status) span.show-title a {
    text-decoration: none;
    color: rgb(255, 255, 255);
}

tr.status span.episode-title a,
tr span.show-title a {
    text-decoration: none;
    color: rgb(0, 0, 0);
}
</style>

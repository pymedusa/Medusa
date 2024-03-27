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
                    <input placeholder="Resource" class="'form-control input-sm vgt-input" @input="updateResource">
                </span>

                <span v-else-if="column.field === 'providerId'">
                    <input placeholder="Provider | Group" class="'form-control input-sm vgt-input" @input="updateProvider">
                </span>

                <span v-else-if="column.field === 'quality'">
                    <select class="form-control form-control-inline input-sm vgt-select" @input="updateQualityFilter">
                        <option value="">Filter Quality</option>
                        <option v-for="option in consts.qualities.values" :value="option.value" :key="option.key">{{ option.name }}</option>
                    </select>
                </span>

                <span v-else-if="column.field === 'size'">
                    <input placeholder="ex. `< 1024` (MB)" class="'form-control input-sm vgt-input" @input="updateSizeFilter">
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
            perPageDropdown
        };
    },
    mounted() {
        const { getCookie, getSortFromCookie } = this;
        this.loadItems();

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
            remoteHistory: state => state.history.remote,
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
            this.setCookie('sort', params);
            this.remoteHistory.sort = params.filter(item => item.type !== 'none');
            this.loadItemsDebounced();
        },
        onColumnFilter(params) {
            this.setCookie('filter', params);
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
        /**
         * Update the size filter.
         * As a specific size filter is useless. I've choosen to use a > or < operator.
         * The backend will parse these into queries.
         * @param {string} size - Operator with size in MB.
         */
        updateSizeFilter(size) {
            // Check for valid syntax, and pass along.
            size = size.currentTarget.value;
            if (!size) {
                this.remoteHistory.filter.columnFilters.size = size;
                this.loadItemsDebounced();
                return;
            }

            const validSizeRegex = /[<>] \d{2,6}/;
            if (size.match(validSizeRegex)) {
                this.invalidSizeMessage = '';
                if (!this.remoteHistory.filter) {
                    this.remoteHistory.filter = { columnFilters: {} };
                }
                this.remoteHistory.filter.columnFilters.size = size;
                this.loadItemsDebounced();
            }
        },
        updateResource(resource) {
            resource = resource.currentTarget.value;
            if (!this.remoteHistory.filter) {
                this.remoteHistory.filter = { columnFilters: {} };
            }

            this.remoteHistory.filter.columnFilters.resource = resource;
            this.loadItemsDebounced();
        },
        updateProvider(provider) {
            provider = provider.currentTarget.value;
            if (!this.remoteHistory.filter) {
                this.remoteHistory.filter = { columnFilters: {} };
            }

            this.remoteHistory.filter.columnFilters.providerId = provider;
            this.loadItemsDebounced();
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

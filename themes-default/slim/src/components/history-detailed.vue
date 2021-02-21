<template>
    <div class="history-detailed-wrapper vgt-table-styling">

        <vue-good-table 
            ref="detailed-history"
            mode="remote"
            @on-page-change="onPageChange"
            @on-per-page-change="onPerPageChange"

            :columns="columns"
            :rows="remoteHistory.rows"
            :totalRows="remoteHistory.totalRows"
            :search-options="{
                enabled: false
            }"
            :pagination-options="{
                enabled: true,
                perPage: remoteHistory.perPage,
                perPageDropdown,
                dropdownAllowAll: false,
                position: 'both'
            }"
            styleClass="vgt-table condensed"
        >
            <template slot="table-row" slot-scope="props">

                <span v-if="props.column.label === 'Date'" class="align-center">
                    {{props.row.actionDate ? fuzzyParseDateTime(props.formattedRow[props.column.field]) : ''}}
                </span>

                <span v-else-if="props.column.label === 'Action'" class="align-center status-name">
                    <span v-tooltip.right="props.row.resource">{{props.row.statusName}}</span>
                    <font-awesome-icon v-if="props.row.partOfBatch" icon="images" v-tooltip.right="'This release is part of a batch or releases'" />
                </span>

                <span v-else-if="props.column.label === 'Provider'" class="align-center">
                    <!-- These should get a provider icon -->
                    <template v-if="['Snatched', 'Failed'].includes(props.row.statusName)">
                        <img  style="margin-right: 5px;"
                              :src="`images/providers/${props.row.provider.id}.png`"
                              :alt="props.row.provider.name" width="16" height="16"
                              :title="props.row.provider.name"
                              v-tooltip.right="props.row.provider.name"
                              onError="this.onerror=null;this.src='images/providers/missing.png';"
                        >
                    </template>

                    <!-- Downloaded history items do not get a provider stored -->
                    <span v-if="props.row.statusName === 'Downloaded'">
                        {{props.row.releaseGroup !== -1 ? props.row.releaseGroup : ''}}
                    </span>

                    <!-- Different path for subtitle providers -->
                    <img v-else-if="props.row.statusName === 'Subtitled'" class="addQTip" style="margin-right: 5px;"
                            :src="`images/subtitles/${props.row.provider.id}.png`"
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
        </vue-good-table>
    </div>
</template>
<script>

import { mapActions, mapGetters, mapState } from 'vuex';
import { VueGoodTable } from 'vue-good-table';
import { humanFileSize } from '../utils/core';
import { manageCookieMixin } from '../mixins/manage-cookie';
import QualityPill from './helpers/quality-pill.vue';
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome';
import { VTooltip } from 'v-tooltip';


export default {
    name: 'history-detailed',
    components: {
        FontAwesomeIcon,
        QualityPill,
        VueGoodTable
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
            hidden: getCookie('Episode')
        }, {
            label: 'Action',
            field: 'statusName',
            hidden: getCookie('Action')
        }, {
            label: 'Quality',
            field: 'quality',
            type: 'number',
            hidden: getCookie('Quality')
        }, {
            label: 'Provider',
            field: 'provider.id',
            hidden: getCookie('Provider')
        }, {
            label: 'Size',
            field: 'size',
            tdClass: 'align-center',
            formatFn: humanFileSize,
            type: 'number',
            hidden: getCookie('Size')
        }, {
            label: 'Client Status',
            field: 'clientStatus',
            type: 'number',
            hidden: getCookie('Client Status')
        }];

        return {
            columns,
            loading: false,
            loadingMessage: '',
            layoutOptions: [
                { value: 'compact', text: 'Compact' },
                { value: 'detailed', text: 'Detailed' }
            ],
            perPageDropdown,
            nextPage: null,
            columnFilters: {},
            sort: {
                field: '', // example: 'name'
                type: '', // 'asc' or 'desc'
            }
        };
    },
    mounted() {
        const { checkHistory } = this;
        // checkHistory({compact: false});
        this.loadItems();
    },
    computed: {
        ...mapState({
            history: state => state.history.history,
            layout: state => state.config.layout,
            historyLimit: state => state.config.layout.historyLimit,
            currentHistoryPage: state => state.history.historyPage,
            remoteHistory: state => state.history.remote
        }),
        ...mapGetters({
            fuzzyParseDateTime: 'fuzzyParseDateTime'
        }),
        serverParams() {
            return { 
                // a map of column filters example: {name: 'john', age: '20'}
                // columnFilters: this.columnFilters,
                // sort: {
                //     field: this.field, // example: 'name'
                //     type: this.type, // 'asc' or 'desc'
                // },
                page: this.remoteHistory.page, // what page I want to show
                perPage: this.remoteHistory.perPage, // how many items I'm showing per page
            }
        }
    },
    methods: {
        humanFileSize,
        ...mapActions({
            getHistory: 'getHistory',
            checkHistory: 'checkHistory',
            setStoreLayout: 'setStoreLayout'
        }),
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
            console.log('page change called');
            console.log(params);
            this.remoteHistory.page = params.currentPage;
            this.loadItems();
        },
        onPerPageChange(params) {
            console.log('per page change called');
            console.log(params);
            this.remoteHistory.perPage = params.currentPerPage;
            this.loadItems();
        },
        onSortChange(params) {
            console.log(params);
            this.updateParams({
                sort: params,
            });
            this.loadItems();
        },
        onColumnFilter(params) {
            console.log('on column filter change');
            console.log(params);
            this.updateParams(params);
            this.loadItems();
        },
        // load items is what brings back the rows from server
        loadItems() {
            const { getHistory, serverParams } = this;
            console.log(this.serverParams);
            getHistory(serverParams);
        },
        // onLastPage(params) {
        //     const { getHistory, currentHistoryPage, history, historyLimit } = this;
        //     // let args = {};
        //     // if (params.currentPage > params.prevPage
        //     //     && params.currentPage * historyLimit > history.length) {
        //     //     args.page = params.currentPage;
        //     //     getHistory(args);
        //     // }
        //     getHistory();
        //     this.nextPage = true;        
        // }
    },
    beforeCreate() {
        this.$store.dispatch('initHistoryStore');
	}
    // watch: {
    //     history(value) {
    //         const { currentHistoryPage, historyLimit } = this;
    //         const vgtCurrentPage = this.$refs["detailed-history"].$refs.paginationBottom.currentPage;
    //         if (value.length / historyLimit > vgtCurrentPage && this.nextPage) {
    //             this.$refs["detailed-history"].$refs.paginationBottom.currentPage += 1;
    //             this.$refs["detailed-history"].$refs.paginationBottom.pageChanged();
    //             this.nextPage = false;
    //         }
    //     }
    // }
};
</script>
<style scoped src='../style/vgt-table.css'>
</style>

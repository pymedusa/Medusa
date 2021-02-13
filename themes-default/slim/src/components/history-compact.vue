<template>
    <div class="history-wrapper-compact vgt-table-styling">

        <vue-good-table 
            :columns="columns"
            :rows="filteredHistory"
            :search-options="{
                enabled: false
            }"
            :sort-options="{
                enabled: true,
                initialSortBy: { field: 'actionDate', type: 'desc' }
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

                <span v-else-if="props.column.label === 'Snatched'" class="align-center">
                    <div v-for="row in sortDate(props.row.rows)" :key="row.id">
                        <template v-if="row.statusName === 'Snatched'">
                            <img style="margin-right: 5px;"
                                    :src="`images/providers/${row.provider.id}.png`"
                                    :alt="row.provider.name" width="16" height="16"
                                    v-tooltip.right="`${row.provider.name}: ${row.resource} (${row.actionDate})`"
                                    onError="this.onerror=null;this.src='images/providers/missing.png';"
                            >
                            <img v-if="row.manuallySearched" src="images/manualsearch.png" width="16" height="16" style="vertical-align:middle;" v-tooltip.right="`Manual searched episode: ${row.resource} (${row.actionDate})`">
                            <img v-if="row.properTags" src="images/info32.png" width="16" height="16" style="vertical-align:middle;" v-tooltip.right="`${row.properTags.split(/[ |]+/).join(', ')}: ${row.resource} (${row.actionDate})`">
                                            
                        </template>
                        <img v-else-if="row.statusName ==='Failed'" src="images/no16.png"
                             width="16" height="16" style="vertical-align:middle;"
                             v-tooltip.right="`${row.provider.name} download failed: ${row.resource} (${row.actionDate})`"
                        />
                    </div>
                </span>

                <span v-else-if="props.column.label === 'Downloaded'" class="align-center">
                    <div v-for="row in sortDate(props.row.rows)" :key="row.id">
                        <template v-if="['Downloaded', 'Archived'].includes(row.statusName)">
                        <span v-if="row.provider" style="cursor: help;" v-tooltip.right="getFileBaseName(row.resource)"><i>{{row.provider.name}}</i></span>
                        <span v-else style="cursor: help;" v-tooltip.right="getFileBaseName(row.resource)"><i>Unknown</i></span>
                        </template>
                    </div>
                </span>

                <span v-else-if="props.column.label === 'Subtitled'" class="align-center">
                    <div v-for="row in sortDate(props.row.rows)" :key="row.id">
                        <template v-if="row.statusName === 'Subtitled'">
                            <img :src="`images/subtitles/${row.provider.name}.png`" width="16" height="16" style="vertical-align:middle;" :alt="row.provider.name" v-tooltip.right="`${row.provider.name}: ${getFileBaseName(row.resource)}`"/>
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
    name: 'history-compact',
    components: {
        FontAwesomeIcon,
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
            hidden: getCookie('Status')
        }, {
            label: 'Snatched',
            field: 'snatched',
            type: 'number',
            hidden: getCookie('Quality')
        }, {
            label: 'Downloaded',
            field: 'downloaded',
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
            loading: false,
            loadingMessage: '',
            layoutOptions: [
                { value: 'compact', text: 'Compact' },
                { value: 'detailed', text: 'Detailed' }
            ]
        };
    },
    mounted() {
        const { getHistory, checkLastHistory } = this;
        // getHistory();
        checkLastHistory();
    },
    computed: {
        ...mapState({
            layout: state => state.config.layout,
            history: state => state.history.historyCompact
        }),
        ...mapGetters({
            fuzzyParseDateTime: 'fuzzyParseDateTime'
        }),
        filteredHistory() {
            const { history, layout } = this;
            if (layout.historyLimit) {
                return history.slice(0, layout.historyLimit);
            }
            return history;
        }
    },
    methods: {
        humanFileSize,
        ...mapActions({
            getHistory: 'getHistory',
            setLayout: 'setLayout'
        }),
        close() {
            this.$emit('close');
            // Destroy the vue listeners, etc
            this.$destroy();
            // Remove the element from the DOM
            this.$el.remove();
        },
        rowStyleClassFn(row) {
            return row.statusName.toLowerCase() || 'skipped';
        },
        checkLastHistory() {
        // retrieve the last history item. Compare the record with state.history.setHistoryLast
        // and get new history data.
        const { history, getHistory, layout } = this;
        const params = { last: true };
        const historyParams = {};
        
        if (layout.historyLimit) {
            historyParams.total = layout.historyLimit;
        }

        if (!history || history.length === 0) {
            return getHistory({compact: true});
        }

        api.get('/history', { params })
            .then(response => {
                if (response.data && response.data.date > history[0].actionDate) {
                    getHistory({compact: true});
                }
            })
            .catch(() => {
                console.info(`No history record found`);
            });
        },
        sortDate(rows) {
            const cloneRows = [...rows];
            return cloneRows.sort(x => x.actionDate).reverse();
        },
        getFileBaseName(path) {
            if (path) {
                return path.split(/[\\/]/).pop();
            }
            return path;
        }
    },
    beforeCreate() {
        this.$store.dispatch('initHistoryStore');
	}
};
</script>
<style scoped src='../style/vgt-table.css'>
</style>

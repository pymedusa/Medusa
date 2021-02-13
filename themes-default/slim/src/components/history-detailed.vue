<template>
    <div class="history-detailed-wrapper vgt-table-styling">

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
            ]
        };
    },
    mounted() {
        const { checkHistory } = this;
        checkHistory({compact: false});
    },
    computed: {
        ...mapState({
            history: state => state.history.history,
            layout: state => state.config.layout
        }),
        ...mapGetters({
            fuzzyParseDateTime: 'fuzzyParseDateTime'
        }),
        filteredHistory() {
            const { history, layout } = this;
            if (Number(layout.historyLimit)) {
                return history.slice(0, Number(layout.historyLimit));
            }
            return history;
        }
    },
    methods: {
        humanFileSize,
        ...mapActions({
            getHistory: 'getHistory',
            checkHistory: 'checkHistory'
        }),
        close() {
            this.$emit('close');
            // Destroy the vue listeners, etc
            this.$destroy();
            // Remove the element from the DOM
            this.$el.remove();
        }
    },
    beforeCreate() {
        this.$store.dispatch('initHistoryStore');
	}
};
</script>
<style scoped src='../style/vgt-table.css'>
</style>

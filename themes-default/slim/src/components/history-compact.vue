<template>
    <div class="history-wrapper-compact">

        <vue-good-table 
            :columns="columns"
            :rows="history"
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

                <span v-else-if="props.column.label === 'Quality'" class="align-center">
                    <quality-pill v-if="props.row.quality !== 0" :quality="props.row.quality" />
                </span>

                <span v-else-if="props.column.label === 'Provider/Group'" class="align-center">
                    <!-- These should get a provider icon -->
                    <template v-if="['Snatched', 'Failed'].includes(props.row.statusName)">
                        <img  class="addQTip" style="margin-right: 5px;"
                                :src="`images/providers/${props.row.provider.id}.png`"
                                :alt="props.row.provider.name" width="16" height="16"
                                :title="props.row.provider.name"
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
                    >

                    <span v-else>
                        {{props.row.provider.name}}
                    </span>
                </span>

                <span v-else-if="props.column.label === 'Release' && props.row.statusName === 'Subtitled'" class="align-center">
                    <img v-if="props.row.resource !== 'und'" :src="`images/subtitles/flags/${props.row.resource}.png`" width="16" height="11" :alt="props.row.resource" onError="this.onerror=null;this.src='images/flags/unknown.png';">
                    <img v-else :src="`images/subtitles/flags/${props.row.resource}.png`" class="subtitle-flag" width="16" height="11" :alt="props.row.resource" onError="this.onerror=null;this.src='images/flags/unknown.png';">
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
import { addQTip } from '../utils/jquery';

export default {
    name: 'history-compact',
    components: {
        VueGoodTable,
        QualityPill
    },
    mixins: [
        manageCookieMixin('downloadHistory')
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
            field: 'episode',
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
            config: state => state.config.general,
            stateLayout: state => state.config.layout,
            history: state => state.history.historyCompact
        }),
        ...mapGetters({
            fuzzyParseDateTime: 'fuzzyParseDateTime'
        }),
        layout: {
            get() {
                const { stateLayout } = this;
                return stateLayout.history;
            },
            set(layout) {
                const { setLayout } = this;
                const page = 'history';
                setLayout({ page, layout });
            }
        },
        selectHistory() {
            const { layout } = this;
            if (layout) {
                getHistory({compact: layout});
            }

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
        const { history, getHistory } = this;
        const params = { last: true };
        
        if (!history || history.length === 0) {
            return getHistory({compact: true});
        }

        api.get(`/history`, { params })
            .then(response => {
                if (response.data && response.data.date > history[0].actionDate) {
                    getHistory({compact: true});
                }
            })
            .catch(() => {
                console.info(`No history record found`);
            });
        }
    },
    beforeCreate() {
        this.$store.dispatch('initHistoryStore');
	}
};
</script>
<style scoped>
</style>

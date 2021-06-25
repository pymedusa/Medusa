<template>
    <div class="current-downloads-wrapper">
        <div class="row horizontal-scroll">
            <div class="vgt-table-styling col-md-12 top-15">
                <vue-good-table v-show="filterHistory"
                                :columns="columns"
                                :rows="filterHistory"
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

                        <span v-else-if="props.column.label === 'Provider'" class="align-center">
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

                        <span v-else-if="props.column.label === 'Release'">
                            <span>{{props.formattedRow[props.column.field]}}</span>
                            <font-awesome-icon v-if="props.row.partOfBatch" icon="images" v-tooltip.right="'This release is part of a batch of releases'" />
                        </span>

                        <span v-else-if="props.column.label === 'Client Status'">
                            <span v-tooltip.right="props.formattedRow[props.column.field].status.join(', ')">{{props.formattedRow[props.column.field].string.join(', ')}}</span>
                        </span>

                        <span v-else>
                            {{props.formattedRow[props.column.field]}}
                        </span>
                    </template>
                </vue-good-table>
            </div>
        </div>
    </div>
</template>
<script>

import { mapActions, mapGetters, mapState } from 'vuex';
import { VueGoodTable } from 'vue-good-table';
import { humanFileSize } from '../utils/core';
import { manageCookieMixin } from '../mixins/manage-cookie';
import QualityPill from './helpers/quality-pill.vue';
import { addQTip } from '../utils/jquery';
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome';
import { VTooltip } from 'v-tooltip';

export default {
    name: 'downloads',
    components: {
        FontAwesomeIcon,
        VueGoodTable,
        QualityPill
    },
    directives: {
        tooltip: VTooltip
    },
    mixins: [
        manageCookieMixin('downloadHistory')
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
            label: 'Status',
            field: 'statusName',
            hidden: getCookie('Status')
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
            label: 'Release',
            field: 'resource',
            hidden: getCookie('Release')
        }, {
            label: 'Season',
            field: 'season',
            type: 'number',
            hidden: getCookie('Season')
        }, {
            label: 'Episode',
            field: 'episode',
            type: 'number',
            hidden: getCookie('Episode')
        }, {
            label: 'Size',
            field: 'size',
            formatFn: humanFileSize,
            type: 'number',
            hidden: getCookie('Size')
        }, {
            label: 'Client Status',
            field: 'clientStatus',
            hidden: getCookie('Client Status')
        }];

        return {
            columns,
            loading: false,
            loadingMessage: ''
        };
    },
    mounted() {
        const { getHistory } = this;
        getHistory();
        addQTip();
    },
    computed: {
        ...mapState({
            config: state => state.config.general,
            layout: state => state.config.layout,
            history: state => state.history.remote
        }),
        ...mapGetters({
            fuzzyParseDateTime: 'fuzzyParseDateTime'
        }),
        filterHistory() {
            const { history } = this;
            if (!history.rows || !history.rows.length > 0) {
                return [];
            }
            // Const downloading = [2];
            return history.rows
                .filter(row => row.clientStatus && row.status === 2);
            // .filter(row => row.clientStatus.status.some(status => downloading.includes(status)))
        }
    },
    methods: {
        humanFileSize,
        ...mapActions({
            getHistory: 'getHistory'
        }),
        close() {
            this.$emit('close');
            // Destroy the vue listeners, etc
            this.$destroy();
            // Remove the element from the DOM
            this.$el.remove();
        }
    }
};
</script>
<style scoped>
</style>

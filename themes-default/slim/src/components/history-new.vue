<template>
    <div class="history-wrapper">
        <div class="row horizontal-scroll" :class="{ fanartBackground: layout.fanartBackground }">
            <div class="col-md-12 top-15">
                <vue-good-table v-show="history.length > 0"
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
                                :row-style-class="rowStyleClassFn"
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

export default {
    name: 'show-history',
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
            label: 'Provider/Group',
            field: 'provider.id',
            hidden: getCookie('Provider/Group')
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
            type: 'number',
            hidden: getCookie('Client Status')
        }, {
            label: 'Part of batch',
            field: 'partOfBatch',
            type: 'boolean',
            hidden: getCookie('Part of batch')
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
            history: state => state.history.history
        }),
        ...mapGetters({
            fuzzyParseDateTime: 'fuzzyParseDateTime'
        })
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
        },
        rowStyleClassFn(row) {
            return row.statusName.toLowerCase() || 'skipped';
        }
    }
};
</script>
<style scoped>
</style>

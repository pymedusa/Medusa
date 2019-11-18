<template>
    <div class="show-history-wrapper">
        <div class="row">
            <div class="col-md-12 top-15 displayShow horizontal-scroll" :class="{ fanartBackground: config.fanartBackground }">
                <vue-good-table v-if="showHistoryByEpisode.length > 0"
                                :columns="columns"
                                :rows="showHistoryByEpisode"
                                :search-options="{
                                    enabled: false
                                }"
                                :sort-options="{
                                    enabled: true,
                                    initialSortBy: { field: 'actionDate', type: 'desc' }
                                }"
                                styleClass="vgt-table condensed"
                />
            </div>
        </div>
    </div>
</template>
<script>

import { mapActions, mapGetters, mapState } from 'vuex';
import { VueGoodTable } from 'vue-good-table';
import { humanFileSize } from '../utils/core';

export default {
    name: 'show-history',
    components: {
        VueGoodTable
    },
    props: {
        show: {
            type: Object,
            required: true
        },
        season: {
            type: [String, Number],
            required: true
        },
        episode: {
            type: [String, Number],
            required: true
        }
    },
    data() {
        return {
            columns: [{
                label: 'Date',
                field: 'actionDate',
                /**
                 * Vue-good-table sort overwrite function.
                 * @param {Object} x - row1 value for column.
                 * @param {object} y - row2 value for column.
                 * @returns {Boolean} - if we want to display this row before the next
                 */
                dateInputFormat: 'yyyyMMddHHmmss', //e.g. 07-09-2017 19:16:25
                dateOutputFormat: 'yyyy/MM/dd HH:mm:ss',
                type: 'date'
            }, {
                label: 'Status',
                field: 'status',
                sortable: false
            }, {
                label: 'Provider',
                sortable: false,
                field: 'provider.name'
            }, {
                label: 'Release',
                field: 'resource',
                sortable: false
            }, {
                label: 'Size',
                field: 'size',
                formatFn: humanFileSize,
                sortable: false,
                type: 'number'
            }],
            loading: false,
            loadingMessage: ''
        };
    },
    computed: {
        ...mapState({
            config: state => state.config,
            showHistory: state => state.showHistory
        }),
        ...mapGetters([
            'getShowHistoryBySlug'
        ]),
        showHistoryByEpisode() {
            const { episode, season, show, getShowHistoryBySlug } = this;
            const historyBySlug = getShowHistoryBySlug(show.id.slug);
            if (!historyBySlug) {
                return [];
            }
            return historyBySlug.filter(history => history.season === season && history.episode === episode) || [];
        }
    },
    mounted() {
        const { getShowHistory, show } = this;
        // Get showHistory
        getShowHistory({ slug: show.id.slug });
    },
    methods: {
        humanFileSize,
        ...mapActions({
            getShowHistory: 'getShowHistory'
        }),
        close() {
            this.$emit('close');
            // Destroy the vue listeners, etc
            this.$destroy();
            // Remove the element from the DOM
            this.$el.parentNode.removeChild(this.$el);
        }
    }
};
</script>
<style scoped>
.show-history-wrapper {
    display: table-row;
    column-span: all;
}

.show-history-wrapper >>> table.subtitle-table tr {
    background-color: rgb(190, 222, 237);
}

.show-history-wrapper > td {
    padding: 0;
}

.search-question,
.loading-message {
    background-color: rgb(51, 51, 51);
    color: rgb(255, 255, 255);
    padding: 10px;
    line-height: 55px;
}

span.subtitle-name {
    color: rgb(0, 0, 0);
}
</style>

<template>
    <div class="show-history-wrapper">
        <div class="row">
            <div class="col-md-12 top-15 displayShow horizontal-scroll table-layout" :class="{ fanartBackground: config.fanartBackground }">
                <div class="button-row">
                    <button id="showhistory" type="button" class="btn-medusa top-5 bottom-5 pull-right" @click="hideHistory = !hideHistory">
                        {{hideHistory ? 'Show History' : 'Hide History'}}
                    </button>
                </div>
                <vue-good-table v-show="!hideHistory && show.id.slug && history.length > 0"
                                :columns="columns"
                                :rows="history"
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
            type: Number,
            required: true
        },
        episode: {
            type: Number,
            required: false
        },
        searchType: {
            type: String,
            default: 'episode'
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
            loadingMessage: '',
            history: [],
            hideHistory: true
        };
    },
    mounted() {
        const { getHistory } = this;
        getHistory();
    },
    computed: {
        ...mapState({
            config: state => state.config,
            showHistory: state => state.history.showHistory,
            episodeHistory: state => state.history.episodeHistory
        }),
        ...mapGetters({
            getEpisodeHistory: 'getEpisodeHistory',
            getSeasonHistory: 'getSeasonHistory'
        })
    },
    methods: {
        humanFileSize,
        ...mapActions({
            getShowEpisodeHistory: 'getShowEpisodeHistory'
        }),
        close() {
            this.$emit('close');
            // Destroy the vue listeners, etc
            this.$destroy();
            // Remove the element from the DOM
            this.$el.remove();
        },
        episodeSlug() {
            const { season, episode } = this;
            return `s${season.toString().padStart(2, '0')}e${episode.toString().padStart(2, '0')}`;
        },
        getHistory() {
            const { getShowEpisodeHistory, show, episodeSlug, updateHistory } = this;
            if (show.id.slug) {
                // Use apiv2 to get latest episode history
                getShowEpisodeHistory({ showSlug: show.id.slug, episodeSlug: episodeSlug() });
            }

            // Update the local history array with store data.
            updateHistory();
        },
        updateHistory() {
            const { getEpisodeHistory, getSeasonHistory, show, episodeSlug, searchType } = this;
            if (searchType === 'episode') {
                this.history = getEpisodeHistory({ showSlug: show.id.slug, episodeSlug: episodeSlug() });
            }

            this.history = getSeasonHistory({ showSlug: show.id.slug });
        }
    },
    watch: {
        episodeHistory: {
            handler() {
                const { show, updateHistory } = this;
                if (show.id.slug) {
                    updateHistory();
                }
            },
            deep: true,
            immediate: false
        }
    }
};
</script>
<style scoped>
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

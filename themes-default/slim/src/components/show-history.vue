<template>
    <div class="show-history-wrapper" :class="{'component-margin': !hideHistory}">
        <div class="row horizontal-scroll" :class="{ fanartBackground: layout.fanartBackground }">
            <div class="col-md-12 top-15">
                <div v-show="history.length > 0" class="button-row">
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
import { humanFileSize, episodeToSlug } from '../utils/core';
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
        manageCookieMixin('showHistory')
    ],
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
        }
    },
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
        }];

        if (this.episode) {
            columns.find(column => column.label === 'Season').hidden = true;
            columns.find(column => column.label === 'Episode').hidden = true;
        }

        return {
            columns,
            loading: false,
            loadingMessage: '',
            history: [],
            hideHistory: true
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
            showHistory: state => state.history.showHistory,
            episodeHistory: state => state.history.episodeHistory
        }),
        ...mapGetters({
            getEpisodeHistory: 'getEpisodeHistory',
            getSeasonHistory: 'getSeasonHistory',
            fuzzyParseDateTime: 'fuzzyParseDateTime'
        })
    },
    methods: {
        humanFileSize,
        ...mapActions({
            getShowEpisodeHistory: 'getShowEpisodeHistory',
            getShowHistory: 'getHistory'
        }),
        close() {
            this.$emit('close');
            // Destroy the vue listeners, etc
            this.$destroy();
            // Remove the element from the DOM
            this.$el.remove();
        },
        getHistory() {
            const { getShowHistory, getShowEpisodeHistory, show, episode, season, updateHistory } = this;
            if (show.id.slug) {
                if (episode) {
                    // Use apiv2 to get latest episode history
                    getShowEpisodeHistory({ showSlug: show.id.slug, episodeSlug: episodeToSlug(season, episode) });
                } else {
                    getShowHistory(show.id.slug);
                }
            }

            // Update the local history array with store data.
            updateHistory();
        },
        updateHistory() {
            const { getEpisodeHistory, getSeasonHistory, show, episode, season } = this;
            if (!show.id.slug) {
                return;
            }

            if (episode) {
                this.history = getEpisodeHistory({ showSlug: show.id.slug, episodeSlug: episodeToSlug(season, episode) });
            } else {
                // As this is not an episode search, we're returning all results for the specific season.
                this.history = getSeasonHistory({ showSlug: show.id.slug, season });
            }
        },
        rowStyleClassFn(row) {
            return row.statusName.toLowerCase() || 'skipped';
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
/* Make some room for the Select columns ul / dropdown. */
.component-margin {
    margin-bottom: 50px;
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

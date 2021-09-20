<template>
<div>
    <div class="row">
        <div class="col-md-12">
    <!-- <
        def titler(x):
            return (remove_article(x), x)[not x or app.SORT_ARTICLE]

        totalWanted = totalQual = 0
        backLogShows = sorted([x for x in app.showList if x.paused == 0 and
                            showCounts[(x.indexer, x.series_id)][Overview.QUAL] +
                            showCounts[(x.indexer, x.series_id)][Overview.WANTED]],
                            key=lambda x: titler(x.name).lower())
        for cur_show in backLogShows:
            totalWanted += showCounts[(cur_show.indexer, cur_show.series_id)][Overview.WANTED]
            totalQual += showCounts[(cur_show.indexer, cur_show.series_id)][Overview.QUAL]
    > -->
            <div class="show-option pull-left">Jump to Show:
                <select id="pickShow" class="form-control-inline input-sm-custom">
                 <!-- for cur_show in backLogShows:
                    <option value="${cur_show.indexer_name}${cur_show.series_id}">${cur_show.name}</option>
                 endfor -->
                </select>
            </div>
            <div class="show-option pull-left">Period:
                <select v-model="period" id="backlog_period" class="form-control-inline input-sm-custom">
                    <option value="all" :selected="period === 'all'">All</option>
                    <option value="one_day" :selected="period === 'one_day'">Last 24h</option>
                    <option value="three_days" :selected="period === 'three_days'">Last 3 days</option>
                    <option value="one_week" :selected="period === 'one_week'">Last 7 days</option>
                    <option value="one_month" :selected="period === 'one_month'">Last 30 days</option>
                </select>
            </div>
            <div class="show-option pull-left">Status:
                <select v-model="status" id="backlog_status" class="form-control-inline input-sm-custom">
                    <option value="all" :selected="status === 'all'">All</option>
                    <option value="quality" :selected="status === 'quality'">Quality</option>
                    <option value="wanted" :selected="status === 'wanted'">Wanted</option>
                </select>
            </div>

            <div id="status-summary" class="pull-right">
                <div class="h2footer pull-right">
                    <span v-if="totalWanted > 0" class="listing-key wanted">Wanted: <b>{{totalWanted}}</b></span>
                    <span v-if="totalQuality > 0" class="listing-key qual">Quality: <b>{{totalQuality}}</b></span>
                </div>
            </div> <!-- status-summary -->
        </div> <!-- end of col -->
    </div> <!-- end of row -->

    <div class="row">
        <div class="col-md-12 horizontal-scroll">
            <table class="defaultTable" v-for="show in backlog" :key="show.slug" cellspacing="0" border="0" cellpadding="0">
             <!-- for cur_show in backLogShows:
                 if not showCounts[(cur_show.indexer, cur_show.series_id)][Overview.WANTED] + showCounts[(cur_show.indexer, cur_show.series_id)][Overview.QUAL]:
                    < continue >
                 endif -->
                <tr class="seasonheader" :id="`show-${show.slug}`">
                    <td class="row-seasonheader" colspan="5" style="vertical-align: bottom; width: auto;">
                        <div class="col-md-12">
                            <div class="col-md-6 left-30">
                                <h3 style="display: inline;">
                                    <app-link :href="`home/displayShow?showslug=${show.slug}`">{{show.name}}</app-link>
                                </h3>
                                <template v-if="getQualityPreset({ value: show.quality }) !== undefined">
                                    <div>
                                        <i>Quality:</i>
                                        <quality-pill :quality="show.quality" />
                                    </div>
                                </template>    
                            </div>
                            <div class="col-md-6 pull-right right-30">
                                <div class="top-5 bottom-5 pull-right">
                                    <span v-if="show.episodeCount.wanted > 0" class="listing-key wanted">Wanted: <b>{{show.episodeCount.wanted}}</b></span>
                                    <span v-if="show.episodeCount.quality > 0" class="listing-key qual">Quality: <b>{{show.episodeCount.quality}}</b></span>
                                    <app-link class="btn-medusa btn-inline forceBacklog" :href="`manage/backlogShow?showslug=${show.slug}`"><i class="icon-play-circle icon-white"></i> Force Backlog</app-link>
                                    <app-link class="btn-medusa btn-inline editShow" :href="`home/editShow?showslug=${show.slug}`"><i class="icon-play-circle icon-white"></i> Edit Show</app-link>
                                </div>
                            </div>
                        </div>
                    </td>
                </tr>
                <tr v-if="getQualityPreset({ value: show.quality }) === undefined">
                    <td colspan="5" class="backlog-quality">
                        <div class="col-md-12 left-30">
                            <div v-if="splitQuality(show.quality).allowed.length > 0" class="col-md-12 align-left">
                                <i>Allowed:</i>
                                <template v-for="curQuality in splitQuality(show.quality).allowed">
                                    <quality-pill :quality="curQuality" :key="`${show.slug}-allowed-${curQuality}`"></quality-pill>
                                </template>
                            </div>

                            <div v-if="splitQuality(show.quality).preferred.length > 0" class="col-md-12 align-left">
                                <i>Preferred:</i>
                                <template v-for="curQuality in splitQuality(show.quality).preferred">
                                    <quality-pill :quality="curQuality" :key="`${show.slug}-preferred-${curQuality}`"></quality-pill>
                                </template>
                            </div>
                        </div>
                    </td>
                </tr>
                 <!-- endif -->
                <tr class="seasoncols">
                    <th>Episode</th>
                    <th>Status / Quality</th>
                    <th>Episode Title</th>
                    <th class="nowrap">Airdate</th>
                    <th>Actions</th>
                </tr>
                 <!-- for cur_result in showSQLResults[(cur_show.indexer, cur_show.series_id)]:
                    <
                        old_status = cur_result['status']
                        old_quality = cur_result['quality']
                    > -->
                    <tr v-for="episode in show.episodes" :key="episode.slug" :class="`seasonstyle ${show.category[episode.slug]}`">
                        <td class="tableleft" align="center">{{episode.slug}}</td>
                        <td class="col-status">
                            <span v-if="episode.quality !== 0">
                                {{episode.statusString}} <quality-pill :quality="episode.quality" />
                            </span>
                            <span>
                                {{episode.statusString}}
                            </span>
                        </td>
                        <td class="tableright nowrap" align="center">
                            {{episode.name}}
                        </td>
                        <td>
                            <span v-if="episode.airdate">
                                <time :datetime="episode.airdate" class="date">{{fuzzyParseDateTime(episode.airdate)}}</time>
                            </span>
                            <span>
                                Never
                            </span>
                        </td>
                        <td class="col-search">

                            <app-link class="epSearch" :id="`${show.slug}x${episode.slug}`" :name="`${show.slug}x${episode.slug}`" :href="`home/searchEpisode?showslug=${show.slug}&amp;season=${episode.season}&amp;episode=${episode.episode}`">
                                <img data-ep-search src="images/search16.png" width="16" height="16" alt="search" title="Forced Search" />
                            </app-link>

                            <app-link class="epManualSearch" :id="`${show.slug}x${episode.slug}`"
                                        :name="`${show.slug}x${episode.slug}`"
                                        :href="`home/snatchSelection?showslug=${show.slug}&season=${episode.season}&episode=${episode.episode}`"
                            >
                                <img data-ep-manual-search src="images/manualsearch.png" width="16" height="16" alt="search" title="Manual Search">
                            </app-link>

                            <template v-if="episode.statusString === 'Downloaded'">
                                <app-link class="epArchive" :id="`${show.slug}x${episode.slug}`" :name="`${show.slug}x${episode.slug}`"
                                          :href="`home/setStatus?showslug=${show.slug}&eps=s${episode.season}e${episode.episode}&status=6&direct=1`"><!-- Status 6 = ARCHIVED -->
                                <img data-ep-archive src="images/archive.png" width="16" height="16" alt="search" title="Archive episode" /></app-link>
                            </template>
                        </td>
                    </tr>
            </table>
        </div> <!-- end of col-12 -->
    </div> <!-- end of row -->
</div>
</template>

<script>
import { mapGetters, mapState } from 'vuex';
import { api } from '../api';

export default {
    name: 'manage-backlog',
    data() {
        return {
            backlog: []
        }
    },
    mounted() {
        this.unwatchProp = this.$watch('layout', layout => {
            if (layout) {
                this.unwatchProp();
                this.getBacklog();
            }
        }, {
            immediate: true,
            deep: true
        });
    },
    computed: {
        ...mapState({
            layout: state => state.config.layout
        }),
        ...mapGetters({
            getOverviewStatus: 'getOverviewStatus',
            getQualityPreset: 'getQualityPreset',
            splitQuality: 'splitQuality',
            fuzzyParseDateTime: 'fuzzyParseDateTime'
        }),
        period: {
            get() {
                return this.layout.backlogOverview.period;
            },
            set(value) {
                const { $store } = this;
                return $store.dispatch('setBacklogOverview', { key: 'period', value })
                       .then(setTimeout(() => location.reload(), 500));
            }
        },
        status: {
            get() {
                return this.layout.backlogOverview.status;
            },
            set(value) {
                const { $store } = this;
                return $store.dispatch('setBacklogOverview', { key: 'status', value })
                       .then(setTimeout(() => location.reload(), 500));
            }
        },
        totalWanted() {
            const { backlog } = this;
            return backlog.reduce((prev, log) => prev + log.episodeCount.wanted, 0);
        },
        totalQuality() {
            const { backlog } = this;
            return backlog.reduce((prev, log) => prev + log.episodeCount.quality, 0);
        }
    },
    methods: {
        async getBacklog() {
            const { period, status } = this;
            try {
                const { data } = await api.get('internal/getEpisodeBacklog', { params: { period, status }});
                this.backlog = data;
            } catch (error) {
                this.$snotify.warning('error', 'Error trying to get episode backlog');
            }
        }
    }
}
</script>

<style>

</style>
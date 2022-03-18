<template>
    <div id="manage-backlog">
        <div class="row">
            <div class="col-md-12">
                <div class="show-option pull-left">Jump to Show:
                    <select id="pickShow" v-model="selectedJumpShow" @change="jumpToShow" class="form-control-inline input-sm-custom">
                        <option disabled value="">--select show--</option>
                        <option v-for="show in backlog" :value="show.slug" :key="show.slug">{{show.name}}</option>
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
                                        <div class="preset-quality">
                                            <i>Quality:</i>
                                            <quality-pill :quality="show.quality" />
                                        </div>
                                    </template>
                                </div>
                                <div class="col-md-6 pull-right right-30">
                                    <div class="top-5 bottom-5 pull-right">
                                        <span v-if="show.episodeCount.wanted > 0" class="listing-key wanted">Wanted: <b>{{show.episodeCount.wanted}}</b></span>
                                        <span v-if="show.episodeCount.quality > 0" class="listing-key qual">Quality: <b>{{show.episodeCount.quality}}</b></span>
                                        <button class="btn-medusa btn-inline forceBacklog" @click.prevent="forceBacklog(show.slug)"><i class="icon-white-search icon-white" /> Force Backlog</button>
                                        <app-link class="btn-medusa btn-inline editShow" :href="`home/editShow?showslug=${show.slug}`"><i class="icon-play-configure icon-white" /> Edit Show</app-link>
                                    </div>
                                </div>
                            </div>
                        </td>
                    </tr>
                    <tr v-if="getQualityPreset({ value: show.quality }) === undefined">
                        <td colspan="5" class="backlog-quality">
                            <div class="col-md-12 left-30">
                                <div v-if="splitQuality(show.quality).allowed.length > 0" class="col-md-12 align-left quality-pills">
                                    <i>Allowed:</i>
                                    <div v-for="curQuality in splitQuality(show.quality).allowed" :key="curQuality">
                                        <quality-pill :quality="curQuality" :key="`${show.slug}-allowed-${curQuality}`" />
                                    </div>
                                </div>

                                <div v-if="splitQuality(show.quality).preferred.length > 0" class="col-md-12 align-left quality-pills">
                                    <i>Preferred:</i>
                                    <div v-for="curQuality in splitQuality(show.quality).preferred" :key="curQuality">
                                        <quality-pill :quality="curQuality" :key="`${show.slug}-preferred-${curQuality}`" />
                                    </div>
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
                    <tr v-for="episode in show.episodes" :key="episode.slug" :class="`seasonstyle ${show.category[episode.slug]}`">
                        <td class="tableleft" align="center">{{episode.slug}}</td>
                        <td class="col-status">
                            <span v-if="episode.quality !== 0">
                                {{episode.statusString}} <quality-pill :quality="episode.quality" />
                            </span>
                            <span v-else>
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
                            <span v-else>
                                Never
                            </span>
                        </td>
                        <td class="col-search">
                            <div class="align-center-evenly">
                                <search searchType="backlog" :showSlug="show.slug" :episode="{
                                    episode: episode.episode, season: episode.season, slug: episode.slug
                                }" />
                                <search searchType="manual" :showSlug="show.slug" :episode="{
                                    episode: episode.episode, season: episode.season, slug: episode.slug
                                }" />
                                <template v-if="episode.statusString === 'Downloaded'">
                                    <img src="images/archive.png" class="archive" width="16" height="16" alt="search" title="Archive episode" @click="setStatus(show, episode, $event)">
                                </template>
                            </div>
                        </td>
                    </tr>
                </table>
            </div> <!-- end of col-12 -->
        </div> <!-- end of row -->
    </div>
</template>

<script>
import { mapGetters, mapState } from 'vuex';
import { AppLink, QualityPill, Search } from './helpers';

export default {
    name: 'manage-backlog',
    components: {
        AppLink,
        QualityPill,
        Search
    },
    data() {
        return {
            backlog: [],
            selectedJumpShow: ''
        };
    },
    mounted() {
        if (this.period === null) {
            this.unwatchProp = this.$watch('layout', layout => {
                if (layout) {
                    this.unwatchProp();
                    this.getBacklog();
                }
            }, {
                deep: true
            });
        } else {
            this.getBacklog();
        }
    },
    computed: {
        ...mapState({
            layout: state => state.config.layout,
            client: state => state.auth.client
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
                return $store.dispatch('setBacklogOverview', {
                    key: 'period', value
                })
                    .then(this.$nextTick(() => this.getBacklog()));
            }
        },
        status: {
            get() {
                return this.layout.backlogOverview.status;
            },
            set(value) {
                const { $store } = this;
                return $store.dispatch('setBacklogOverview', { key: 'status', value })
                    .then(this.$nextTick(() => this.getBacklog()));
            }
        },
        totalWanted() {
            const { backlog } = this;
            return backlog.reduce((prev, log) => prev + log.episodeCount.wanted, 0);
        },
        totalQuality() {
            const { backlog } = this;
            return backlog.reduce((prev, log) => prev + log.episodeCount.quality, 0);
        },
        jumpShowOptions() {
            const { backlog } = this;
            return backlog.map(show => ({ text: show.name, value: show.slug }));
        }
    },
    methods: {
        async getBacklog() {
            const { client, period, status } = this;
            try {
                const { data } = await client.api.get('internal/getEpisodeBacklog', { params: { period, status } });
                this.backlog = data;
            } catch (error) {
                this.$snotify.warning('error', 'Error trying to get episode backlog');
            }
        },
        jumpToShow() {
            const { selectedJumpShow } = this;
            if (selectedJumpShow) {
                $('html,body').animate({ scrollTop: $(`#show-${selectedJumpShow}`).offset().top - 50 }, 'slow');
            }
        },
        async forceBacklog(showSlug) {
            try {
                const { data } = await this.client.api.put('search/backlog', { showSlug });
                this.$snotify.success('Searched', data);
            } catch (error) {
                this.$snotify.warning('error', `Error trying to start a backlog search for ${showSlug}`);
            }
        },
        async setStatus(show, episode) {
            try {
                await this.client.api.patch(`series/${show.slug}/episodes`, {
                    [episode.slug]: { status: 6 } // 6 = Archived
                });
                this.getBacklog();
                this.$snotify.success('Saved', `Changed status to Archived for episode ${episode.slug}`);
            } catch (error) {
                this.$snotify.warning('error', `Error trying to change status for episode ${episode.slug}`);
            }
        }
    }
};
</script>

<style>
.preset-quality {
    display: inline-block;
    margin-left: 0.8rem;
}

.preset-quality span {
    margin-left: 0.5rem;
}

.quality-pills > div {
    margin-left: 0.2rem;
    display: inline-block;
}

img.archive {
    cursor: pointer;
}
</style>

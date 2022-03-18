<template>
    <div id="episode-status">
        <div id="select-status">
            <span>Manage episodes with status</span>
            <select :disabled="manageStatus" v-model="selectedStatus" class="form-control form-control-inline input-sm">
                <option v-for="status in availableStatus" :value="status.value" :key="status.value">{{status.text}}</option>
            </select>

            <button :disabled="manageStatus" class="btn-medusa btn-inline" @click="getEpisodes">Manage</button>
        </div>
        <div v-if="manageStatus !== null">
            <form action="manage/changeEpisodeStatuses" method="post" @submit.prevent>
                <svg class="back-arrow" @click="clearPage"><use xlink:href="images/svg/go-back-arrow.svg#arrow" /></svg>
                <h2>Shows containing {{statuses.find(s => s.value === manageStatus).name}} episodes</h2>
                <span>Set checked shows/episodes to </span>
                <select name="newStatus" v-model="newStatus" class="form-control form-control-inline input-sm">
                    <option v-for="status in availableNewStatus" :value="status.value" :key="status.value">{{status.text}}</option>
                </select>
                <button class="btn-medusa btn-inline" @click="changeEpisodes">Go</button>
                <div>
                    <button type="button" class="btn-medusa btn-xs selectAllShows" @click="check(true)">Select all</button>
                    <button type="button" class="btn-medusa btn-xs unselectAllShows" @click="check(false)">Clear all</button>
                </div>
                <br>
                <table v-for="show in data" :id="show.slug" :key="show.slug" class="defaultTable manageTable" cellspacing="1" border="0" cellpadding="0">
                    <tr>
                        <th><input v-model="show.selected" type="checkbox" class="allCheck" @change="checkShow($event, show)"></th>
                        <th colspan="2" style="width: 100%; text-align: left;">
                            <app-link indexer-id="${cur_series[0]}" class="whitelink" :href="`home/displayShow?showslug=${show.slug}`">
                                {{show.name}}
                            </app-link> ({{show.episodes.length}})
                            <button class="pull-right get_more_eps btn-medusa" @click="show.showEpisodes = !show.showEpisodes">Expand</button>
                        </th>
                    </tr>
                    <tr v-for="episode in show.episodes" :key="episode.slug"
                        :style="show.showEpisodes ? 'display: table-row' : 'display: none'"
                        :class="statusIdToString(manageStatus)"
                    >
                        <td class="tableleft"><input v-model="episode.selected" type="checkbox"></td>
                        <td>{{episode.slug}}</td>
                        <td class="tableright" style="width: 100%">{{episode.name}}</td>
                    </tr>
                </table>
            </form>

        </div>
        <!-- </form> -->
    </div>
</template>

<script>
import { mapGetters, mapState } from 'vuex';
import { AppLink } from './helpers';

export default {
    name: 'manage-episode-status',
    components: {
        AppLink
    },
    data() {
        return {
            selectedStatus: 3,
            manageStatus: null,
            newStatus: 3,
            data: []
        };
    },
    computed: {
        ...mapState({
            statuses: state => state.config.consts.statuses,
            failedDownloads: state => state.config.search.general.failedDownloads,
            client: state => state.auth.client
        }),
        ...mapGetters(['getOverviewStatus']),
        availableStatus() {
            const { statuses } = this;
            if (!statuses) {
                return [];
            }
            return statuses.filter(s => s.value > 0 && s.name !== 'Unaired').map(s => ({
                text: s.name, value: s.value
            }));
        },
        availableNewStatus() {
            const { failedDownloads, manageStatus } = this;
            let statusList = [
                { text: 'Wanted', value: 3 },
                { text: 'Downloaded', value: 4 },
                { text: 'Skipped', value: 5 },
                { text: 'Ignored', value: 7 }
            ];
            if (manageStatus === 4) {
                statusList.push({ text: 'Archived', value: 6 });
            }
            if (failedDownloads.enabled && [2, 9, 12, 4, 6].includes(manageStatus)) {
                statusList.push({ text: 'Failed', value: 11 });
            }
            statusList = statusList.filter(list => list.value !== manageStatus);
            return statusList;
        }
    },
    methods: {
        async getEpisodes() {
            const { client } = this;
            this.manageStatus = this.selectedStatus;
            try {
                const { data } = await client.api.get('internal/getEpisodeStatus', { params: { status: this.manageStatus } });
                this.data = data.episodeStatus;
                this.newStatus = this.availableNewStatus[0].value;
            } catch (error) {
                this.$snotify.warning('error', `Could not get episode status for status ${this.manageStatus}`);
            }
        },
        /**
         * Change episode statusses.
         */
        async changeEpisodes() {
            const { client, data, newStatus } = this;
            // Create episode data structure.
            const shows = [];
            // eslint-disable-next-line guard-for-in
            for (const [showSlug, value] of Object.entries(data)) {
                if (value.selected) {
                    shows.push({
                        slug: showSlug,
                        episodes: value.episodes.filter(ep => ep.selected).map(ep => ep.slug)
                    });
                }
            }
            const postData = {
                status: newStatus,
                shows
            };
            try {
                const { data } = await client.api.post('internal/updateEpisodeStatus', postData);
                if (data.count > 0) {
                    this.$snotify.success(
                        `Changed status for ${data.count} episodes`,
                        'Saved',
                        { timeout: 5000 }
                    );
                }
                this.clearPage();
            } catch (error) {
                this.$snotify.warning('error', `Could not get episode status for status ${this.manageStatus}`);
            }
        },
        statusIdToString(status) {
            const { getOverviewStatus, statuses } = this;
            const statusName = statuses.find(s => s.value === status).name;
            if ([
                'Ignored',
                'Snatched',
                'Snatched (Proper)',
                'Snatched (Best)',
                'Downloaded',
                'Archived'
            ].includes(statusName)) {
                return 'good';
            }
            return getOverviewStatus(statusName).toLowerCase();
        },
        check(value) {
            const { data } = this;
            // eslint-disable-next-line guard-for-in
            for (const show of Object.values(data)) {
                show.selected = value;
                for (const episode of show.episodes) {
                    episode.selected = value;
                }
            }
        },
        checkShow(event, show) {
            for (const episode of show.episodes) {
                episode.selected = event.currentTarget.checked;
            }
        },
        clearPage() {
            this.manageStatus = null;
            this.data = [];
        }
    },
    mounted() {
        const { status } = this.$route.query;
        if (status) {
            this.selectedStatus = Number(status);
            this.getEpisodes();
        }
    }
};
</script>

<style scoped>
</style>

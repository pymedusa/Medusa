<template>
    <div id="test-rename" v-if="showConfigLoaded">
        <!-- if app.PROCESS_METHOD == 'symlink': -->
        <div v-if="postprocessing.processMethod == 'symlink'" class="text-center">
            <div class="alert alert-danger upgrade-notification hidden-print" role="alert">
                <span>WARNING: Your current process method is SYMLINK. Renaming these files will break all symlinks in your Post-Processor {{ seedLocation ? '/Seeding' : '' }} directory for this show</span>
            </div>
        </div>

        <backstretch :slug="showSlug" />

        <app-link :href="`home/displayShow?showslug=${showSlug}`">
            <svg class="back-arrow"><use xlink:href="images/svg/go-back-arrow.svg#arrow" /></svg>
        </app-link>
        <h3>Preview of the proposed name changes</h3>

        <blockquote>
            <template v-if="show.config.airByDate && postprocessing.naming.enableCustomNamingAirByDate">{{postprocessing.naming.patternAirByDate}}</template>
            <template v-else-if="show.config.sports && postprocessing.naming.enableCustomNamingSports">{{postprocessing.naming.patternSportse}}</template>
            <template v-else>{{postprocessing.naming.pattern}}</template>
        </blockquote>

        <div class="rename-cancel">
            <button class="btn-medusa btn-success" @click="renameSelected">Rename Selected</button>
            <app-link :href="`home/displayShow?showslug=${showSlug}`" class="btn-medusa btn-danger">Cancel Rename</app-link>
        </div>
        <div>
            <button type="button" class="btn-medusa btn-xs selectAllShows" @click="check(true)">Select all</button>
            <button type="button" class="btn-medusa btn-xs unselectAllShows" @click="check(false)">Clear all</button>
        </div>
        <state-switch v-if="loading" state="loading" class="loading" />
        <table v-for="season in seasonedList" :key="season.season" id="testRenameTable" :class="{ summaryFanArt: layout.fanartBackground }" class="defaultTable" cellspacing="1" border="0" cellpadding="0">
            <thead>
                <tr class="seasonheader" :id="`season-${season.season}`">
                    <td colspan="4">
                        <span class="season-header">{{season.season === 0 ? 'Specials' : `Season ${season.season}`}}</span>
                    </td>
                </tr>
                <tr class="seasoncols" :id="`season-${season.season}-cols`">
                    <th class="col-checkbox">
                        <input :disabled="season.episodes.filter(episode => namingChanged(episode).result).length === 0" type="checkbox" class="seasonCheck" @click="check($event.currentTarget.checked, season.season)" :id="`season-${season.season}-cols`">
                    </th>
                    <th class="nowrap">Episode</th>
                    <th class="col-name">Old Location</th>
                    <th class="col-name">New Location</th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="episode in season.episodes" :key="episode.slug" :class="[`season-${season.season}`, namingChanged(episode).result ? 'wanted' : 'good']" class="seasonstyle">
                    <td class="col-checkbox">
                        <input :disabled="!namingChanged(episode).result" v-model="episode.selected" type="checkbox" class="epCheck" :id="episode.slug" :name="episode.slug">
                    </td>
                    <td align="center" valign="top" class="nowrap">{{ formatRelated(episode)}}</td>
                    <td width="50%" class="col-name">{{namingChanged(episode).currentLocation}}</td>
                    <td width="50%" class="col-name">{{namingChanged(episode).newLocation}}</td>
                </tr>
            </tbody>
        </table>
        <div class="rename-cancel">
            <button class="btn-medusa btn-success" @click="renameSelected">Rename Selected</button>
            <app-link :href="`home/displayShow?showslug=${showSlug}`" class="btn-medusa btn-danger">Cancel Rename</app-link>
        </div>
    </div>
</template>

<script>
import { mapActions, mapGetters, mapState } from 'vuex';
import { AppLink } from './helpers';
import Backstretch from './backstretch.vue';
import StateSwitch from './helpers/state-switch.vue';

export default {
    name: 'test-rename',
    components: {
        AppLink,
        Backstretch,
        StateSwitch
    },
    props: {
        slug: String
    },
    data() {
        return {
            episodeRenameList: [],
            loading: false
        };
    },
    async mounted() {
        // We need detailed info for the xem / scene exceptions, so let's get it.
        const { showSlug } = this;
        await this.getShow({ showSlug, detailed: true });
        await this.setCurrentShow(showSlug);

        this.loadTestRename();
    },
    computed: {
        ...mapState({
            postprocessing: state => state.config.postprocessing,
            seedLocation: state => state.config.clients.torrents.seedLocation,
            layout: state => state.config.layout,
            client: state => state.auth.client
        }),
        showConfigLoaded() {
            return this.show.id.slug !== null;
        },
        ...mapGetters({
            show: 'getCurrentShow'
        }),
        showSlug() {
            const { slug } = this;
            return slug || this.$route.query.showslug;
        },
        /**
         * Create a structure with episodes grouped by season.
         * @returns {array} of season objects (with episodes).
         */
        seasonedList() {
            const { episodeRenameList } = this;
            const data = [];
            for (const episode of episodeRenameList) {
                const findSeason = data.find(season => season.season === episode.season);
                if (findSeason) {
                    findSeason.episodes.push(episode);
                } else {
                    // Create a season object
                    data.push({ season: episode.season, episodes: [episode] });
                }
            }
            return data;
        }
    },
    methods: {
        ...mapActions({
            getShow: 'getShow',
            setCurrentShow: 'setCurrentShow'
        }),
        async loadTestRename() {
            const { showSlug } = this;
            try {
                this.loading = true;
                const url = `series/${showSlug}/operation`;
                const data = [];
                const reversedSeasons = this.show.seasonCount.slice().sort((a, b) => b.season - a.season);
                for (const { season } of reversedSeasons) {
                    // eslint-disable-next-line no-await-in-loop
                    const result = await this.client.api.post(url, { type: 'TEST_RENAME', season }, { timeout: 120000 });
                    data.push(...result.data);
                }

                this.episodeRenameList = data;
            } catch (error) {
                this.$snotify.error(
                    `Error while trying to get the test rename list for ${showSlug}`,
                    'Error'
                );
            } finally {
                this.loading = false;
            }
        },
        /**
         * Check if according to the new naming rule, the naming has changed for this episode.
         * @param {object} episode object.
         * @returns {boolean} True if the expected naming has changed for the episode's location.
         */
        namingChanged(episode) {
            const { show } = this;

            const currentLocation = episode.file.location.slice(show.config.location.length + 1);
            const currentLocationExt = currentLocation.split('.')[currentLocation.split('.').length - 1];
            return {
                result: !currentLocation || currentLocation !== `${episode.file.properPath}.${currentLocationExt}`,
                currentLocation,
                newLocation: `${episode.file.properPath}.${currentLocationExt}`
            };
        },
        async renameSelected() {
            const { episodeRenameList, showSlug } = this;
            const episodes = episodeRenameList.filter(ep => ep.selected).map(ep => ep.slug);
            try {
                this.loading = true;
                const url = `series/${showSlug}/operation`;
                await this.client.api.post(url, { type: 'RENAME_EPISODES', episodes }, { timeout: 120000 });
                this.$router.push({ name: 'show', query: { showslug: showSlug } });
            } catch (error) {
                this.$snotify.error(
                    'Error while trying to perform the rename task',
                    'Error'
                );
            } finally {
                this.loading = false;
            }
        },
        formatRelated(episode) {
            const relatedEpisodes = [episode, ...episode.related];
            if (relatedEpisodes.length === 1) {
                return relatedEpisodes[0].episode;
            }
            const first = relatedEpisodes[0];
            const last = relatedEpisodes[relatedEpisodes.length - 1];
            return `${first.episode}-${last.episode}`;
        },
        check(value, season = null) {
            const { episodeRenameList, namingChanged } = this;
            for (const episode of episodeRenameList) {
                if (!namingChanged(episode).result) {
                    continue;
                }
                if (season === null) {
                    episode.selected = value;
                } else if (episode.season === season) {
                    episode.selected = value;
                }
            }
        }
    }
};
</script>

<style scoped>
.defaultTable {
    margin: 0.3em 0;
}

.defaultTable tr.seasonheader > td {
    padding: 0;
}

.season-header {
    color: white;
    font-family: inherit;
    font-weight: 700;
    line-height: 1.1;
    background-color: rgb(51, 51, 51);
    display: block;
    padding: 5px 5px;
    font-size: 1em;
}

.loading {
    display: block;
    margin: 10px 0;
}

.rename-cancel {
    margin: 5px 0;
}
</style>

<template>
    <div id="missing-subtitles">
        <span>Manage episodes missing subtitle language</span>
        <div id="select-missing-language">
            <select :disabled="manageLanguage" v-model="selectedLanguage" class="form-control form-control-inline input-sm">
                <option v-for="language in availableLanguages" :value="language.value" :key="language.value">{{language.text}} {{language.value === 'all' ? '' : `(${language.value})`}}</option>
            </select>

            <button :disabled="manageLanguage" class="btn-medusa btn-inline" @click="getSubtitleMissed">Manage</button>
        </div>
        <div v-if="manageLanguage !== null">
            <form action="manage/changeEpisodeStatuses" method="post" @submit.prevent>
                <svg class="back-arrow" @click="clearPage"><use xlink:href="images/svg/go-back-arrow.svg#arrow" /></svg>
                <h2>Episodes without {{availableLanguages.find(lang => lang.value === selectedLanguage).text}} wanted subtitles</h2>
                <span>Download missed subtitles for selected episodes</span>
                <button class="btn-medusa btn-inline" @click="searchSubtitles">Go</button>
                <div>
                    <button type="button" class="btn-medusa btn-xs selectAllShows" @click="check(true)">Select all</button>
                    <button type="button" class="btn-medusa btn-xs unselectAllShows" @click="check(false)">Clear all</button>
                </div>
                <br>
                <table v-for="show in data" :id="show.slug" :key="show.slug" class="defaultTable manageTable" cellspacing="1" border="0" cellpadding="0">
                    <tr>
                        <th><input v-model="show.selected" type="checkbox" class="allCheck" @change="checkShow($event, show)"></th>
                        <th colspan="3" style="width: 100%; text-align: left;">
                            <app-link indexer-id="${cur_series[0]}" class="whitelink" :href="`home/displayShow?showslug=${show.slug}`">
                                {{show.name}}
                            </app-link> ({{show.episodes.length}})
                            <button class="pull-right get_more_eps btn-medusa" @click="show.showEpisodes = !show.showEpisodes">Expand</button>
                        </th>
                    </tr>
                    <tr v-for="episode in show.episodes" :key="episode.slug"
                        :style="show.showEpisodes ? 'display: table-row' : 'display: none'"
                        class="good"
                    >
                        <td class="tableleft"><input v-model="episode.selected" type="checkbox"></td>
                        <td>{{episode.slug}}</td>
                        <td v-if="episode.subtitles.length > 0" class="flag">
                            <img v-for="subtitle in episode.subtitles" :key="subtitle" :src="`images/subtitles/flags/${subtitle}.png`" width="16" height="11" :alt="subtitle">
                        </td>
                        <td v-else>No subtitles</td>
                        <td class="tableright" style="width: 100%">{{episode.name}}</td>
                    </tr>
                </table>
            </form>

        </div>
        <!-- </form> -->
    </div>
</template>

<script>
import { mapState } from 'vuex';
import { AppLink } from './helpers';

export default {
    name: 'manage-missing-subtitle',
    components: {
        AppLink
    },
    data() {
        return {
            selectedLanguage: 'all',
            manageLanguage: null,
            data: []
        };
    },
    computed: {
        ...mapState({
            subtitleLanguages: state => state.config.subtitles.wantedLanguages,
            client: state => state.auth.client
        }),
        availableLanguages() {
            const { subtitleLanguages } = this;
            const languages = [
                { text: 'All', value: 'all' }
            ];
            return [...languages, ...subtitleLanguages.map(lang => ({ text: lang.name, value: lang.id }))];
        }
    },
    methods: {
        async getSubtitleMissed() {
            const { client } = this;
            this.manageLanguage = this.selectedLanguage;
            try {
                const { data } = await client.api.get('internal/getSubtitleMissed', { params: { language: this.manageLanguage } });
                this.data = data;
            } catch (error) {
                this.$snotify.warning('error', `Could not get missed subtitles for ${this.manageLanguage}`);
            }
        },
        /**
         * Search for subtitles.
         */
        async searchSubtitles() {
            const { client, data, manageLanguage } = this;
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
                language: manageLanguage,
                shows
            };
            try {
                const { data } = await client.api.post('internal/searchMissingSubtitles', postData, { timeout: 120000 });
                if (data.count > 0) {
                    this.$snotify.success(
                        `Searched for ${manageLanguage} missing subtitle languages`,
                        'Saved',
                        { timeout: 5000 }
                    );
                }
                this.clearPage();
            } catch (error) {
                this.$snotify.warning('error', 'Could not search for missing subtitles');
            }
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
            this.manageLanguage = null;
            this.data = [];
        }
    }
};
</script>

<style scoped>
svg.back-arrow {
    color: #337ab7;
    width: 20px;
    height: 20px;
    float: left;
    margin-right: 1em;
    cursor: pointer;
}

svg.back-arrow:hover,
svg.back-arrow:focus {
    color: #23527c;
    transform: translateX(-2px);
    transition: transform ease-in-out 0.2s;
}

.flag {
    width: 15%;
}

.flag > img {
    margin-right: 5px;
}

#select-missing-language {
    display: inline;
}
</style>

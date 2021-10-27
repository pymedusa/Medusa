<template>
    <div>
        <config-toggle-slider v-model="trakt.enabled" label="Enable" id="use_trakt" :explanations="['Send Trakt.tv notifications?']" @change="save()" />
        <div v-show="trakt.enabled" id="content-use-trakt-client"> <!-- show based on trakt.enabled -->

            <config-template label-for="trakt_request_auth" label="">
                <input type="button" class="btn-medusa" value="Connect to your trakt account" id="Trakt" @click="TraktRequestDeviceCode">
                <span style="display: inline" v-if="traktRequestSend && traktUserCode">Use this code in the popup: {{traktUserCode}}</span>
                <p v-if="traktRequestSend && traktUserCode && traktRequestMessage">Trakt request status: {{traktRequestMessage}}</p>
                <p v-if="traktRequestAuthenticated && traktRequestMessage">{{traktRequestMessage}}</p>
            </config-template>

            <template v-if="!authOnly">
                <config-textbox-number v-model="trakt.timeout" label="API Timeout" id="trakt_timeout" :explanations="['Seconds to wait for Trakt API to respond. (Use 0 to wait forever)']" />

                <config-template label-for="trakt_default_indexer" label="Default indexer">
                    <select id="trakt_default_indexer" name="trakt_default_indexer" v-model="trakt.defaultIndexer" class="form-control">
                        <option v-for="option in traktIndexersOptions" :value="option.value" :key="option.key">
                            {{ option.text }}
                        </option>
                    </select>
                </config-template>

                <config-toggle-slider v-model="trakt.sync" label="Sync libraries" id="trakt_sync" @change="save()">
                    <p>Sync your Medusa show library with your Trakt collection.</p>
                    <p>Note: Don't enable this setting if you use the Trakt addon for Kodi or any other script that syncs your library.</p>
                    <p>Kodi detects that the episode was deleted and removes from collection which causes Medusa to re-add it. This causes a loop between Medusa and Kodi adding and deleting the episode.</p>
                </config-toggle-slider>

                <div v-show="trakt.sync" id="content-use-trakt-client">
                    <config-toggle-slider v-model="trakt.removeWatchlist" label="Remove Episodes From Collection" id="trakt_remove_watchlist" :explanations="['Remove an Episode from your Trakt Collection if it is not in your Medusa Library.',                                                                                                                                                                                                    'Note:Don\'t enable this setting if you use the Trakt addon for Kodi or any other script that syncs your library.']" @change="save()" />
                </div>

                <config-toggle-slider v-model="trakt.syncWatchlist" label="Sync watchlist" id="trakt_sync_watchlist" @change="save()">
                    <p>Sync your Medusa library with your Trakt Watchlist (either Show and Episode).</p>
                    <p>Episode will be added on watch list when wanted or snatched and will be removed when downloaded</p>
                    <p>Note: By design, Trakt automatically removes episodes and/or shows from watchlist as soon you have watched them.</p>
                </config-toggle-slider>

                <div v-show="trakt.syncWatchlist" id="content-use-trakt-client">
                    <config-template label-for="trakt_default_indexer" label="Watchlist add method">
                        <select id="trakt_method_add" name="trakt_method_add" v-model="trakt.methodAdd" class="form-control">
                            <option v-for="option in traktMethodOptions" :value="option.value" :key="option.key">
                                {{ option.text }}
                            </option>
                        </select>
                        <p>method in which to download episodes for new shows.</p>
                    </config-template>

                    <config-toggle-slider v-model="trakt.removeWatchlist" label="Remove episode" id="trakt_remove_watchlist" @change="save()">
                        <p>remove an episode from your watchlist after it's downloaded.</p>
                    </config-toggle-slider>

                    <config-toggle-slider v-model="trakt.removeSerieslist" label="Remove series" id="trakt_remove_serieslist" @change="save()">
                        <p>remove the whole series from your watchlist after any download.</p>
                    </config-toggle-slider>

                    <config-toggle-slider v-model="trakt.removeShowFromApplication" label="Remove watched show" id="trakt_remove_show_from_application" @change="save()">
                        <p>remove the show from Medusa if it\'s ended and completely watched</p>
                    </config-toggle-slider>

                    <config-toggle-slider v-model="trakt.startPaused" label="Start paused" id="trakt_start_paused" @change="save()">
                        <p>shows grabbed from your trakt watchlist start paused.</p>
                    </config-toggle-slider>
                </div>

                <config-textbox v-model="trakt.blacklistName" :class="traktBlacklistClass" label="Trakt blackList name" id="trakt_blacklist_name" @change="save()">
                    <p>Name(slug) of List on Trakt for blacklisting show on 'Add Trending Show' & 'Add Recommended Shows' pages</p>
                </config-textbox>

            </template>

            <div class="testNotification" id="testTrakt-result">{{testTraktResult}}</div>
            <input type="hidden" id="trakt_pin_url" :value="trakt.pinUrl">

            <button class="btn-medusa" id="testTrakt" @click="testTrakt">Test Trakt</button>
            <button v-if="!authOnly" class="btn-medusa" id="forceSync" @click="traktForceSync">Force Sync</button>
            <button class="btn-medusa config_submitter" @click="save" :disabled="saving">Save Changes</button>
        </div>
    </div>
</template>
<script>
import { mapActions, mapState } from 'vuex';
import {
    ConfigToggleSlider,
    ConfigTemplate,
    ConfigTextboxNumber,
    ConfigTextbox
} from '.';

export default {
    components: {
        ConfigToggleSlider,
        ConfigTemplate,
        ConfigTextboxNumber,
        ConfigTextbox
    },
    props: {
        authOnly: Boolean
    },
    data() {
        return {
            traktRequestSend: false,
            traktRequestAuthenticated: false,
            traktUserCode: '',
            traktRequestMessage: '',
            traktMethodOptions: [
                { text: 'Skip all', value: 0 },
                { text: 'Download pilot only', value: 1 },
                { text: 'Get whole show', value: 2 }
            ],
            saving: false,
            testTraktResult: 'Click below to test.',
            traktBlacklistClass: ''
        };
    },
    computed: {
        ...mapState({
            indexers: state => state.config.indexers,
            trakt: state => state.config.notifiers.trakt
        }),
        traktIndexersOptions() {
            const { indexers } = this;
            const { traktIndexers } = indexers.main;

            const validTraktIndexer = Object.keys(indexers.indexers).filter(k => traktIndexers[k]);
            return validTraktIndexer.map(indexer => {
                return { text: indexer, value: indexers.indexers[indexer].id };
            });
        }
    },
    methods: {
        ...mapActions(['setConfig']),
        async TraktRequestDeviceCode() {
            this.traktUserCode = '';
            this.traktRequestAuthenticated = false;
            const response = await this.client.apiRoute('home/requestTraktDeviceCodeOauth');
            if (response.data) {
                this.traktVerificationUrl = response.data.verification_url;
                window.open(response.data.verification_url, 'popUp', 'toolbar=no, scrollbars=no, resizable=no, top=200, left=200, width=650, height=550');
                this.traktRequestSend = true;
                this.traktUserCode = response.data.user_code;
                this.checkTraktAuthenticated();
            }
        },
        checkTraktAuthenticated() {
            let counter = 0;
            const i = setInterval(() => {
                this.client.apiRoute('home/checkTrakTokenOauth')
                    .then(response => {
                        if (response.data) {
                            this.traktRequestMessage = response.data.result;
                            if (!response.data.error) {
                                clearInterval(i);
                                this.traktRequestAuthenticated = true;
                                this.traktUserCode = '';
                            }
                        }
                    });

                counter++;
                if (counter === 12) {
                    clearInterval(i);
                    this.traktRequestAuthenticated = false;
                    this.traktUserCode = '';
                }
            }, 5000);
        },
        testTrakt() {
            const { trakt } = this;
            const { blacklistName } = trakt;

            if (/\s/g.test(blacklistName)) {
                this.testTraktResult = 'Check blacklist name; the value needs to be a trakt slug';
                this.traktBlacklistClass = 'warning';
                return;
            }
            this.traktBlacklistClass = '';

            // $('#testTrakt-result').html(MEDUSA.config.layout.loading);
            this.client.apiRoute(`home/testTrakt?blacklist_name=${blacklistName}`)
                .then(result => {
                    this.testTraktResult = result.data;
                    // $('#testTrakt').prop('disabled', false);
                });
        },
        traktForceSync() {
            // $('#testTrakt-result').html(MEDUSA.config.layout.loading);
            $.getJSON('home/forceTraktSync', data => {
                this.testTraktResult = data.result;
            });
        },
        async save() {
            const { trakt, setConfig } = this;

            // Disable the save button until we're done.
            this.saving = true;
            const section = 'main';
            const config = {
                notifiers: {
                    trakt
                }
            };

            try {
                await setConfig({ section, config });
                this.$snotify.success(
                    'Saved Trakt config',
                    'Saved',
                    { timeout: 5000 }
                );
            } catch (error) {
                this.$snotify.error(
                    'Error while trying to save Trakt config',
                    'Error'
                );
            } finally {
                this.saving = false;
            }
        }
    }
};
</script>
<style scoped>
</style>

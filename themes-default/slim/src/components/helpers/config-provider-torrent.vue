<template>
    <div id="provider-options-torrent">
        <!-- Newznab section -->
        <div v-if="Object.keys(editProvider).length > 0" class="providerDiv" :id="`${editProvider.id}Div`">
            <config-textbox v-if="'customUrl' in editProvider.config" v-model="editProvider.config.customUrl" label="Custom Url" :id="`${editProvider.id}_custom_url`">
                <p>The URL should include the protocol (and port if applicable).  Examples:  http://192.168.1.4/ or http://localhost:3000/</p>
            </config-textbox>

            <config-textbox v-if="'apikey' in editProvider.config && editProvider.config.subType !== 'torznab'" v-model="editProvider.config.apikey" type="password" label="API key" :id="`${editProvider.id}_api_key`" />

            <config-textbox v-if="'digest' in editProvider.config" v-model="editProvider.config.digest" type="password" label="Digest" :id="`${editProvider.id}_digest`" />

            <config-textbox v-if="'hash' in editProvider.config" v-model="editProvider.config.hash" label="Hash" :id="`${editProvider.id}_hash`" />

            <config-textbox v-if="'username' in editProvider.config" v-model="editProvider.config.username" label="Username" :id="`${editProvider.id}_username`" />

            <config-textbox v-if="'password' in editProvider.config" v-model="editProvider.config.password" autocomplete="no" type="password" label="Password" :id="`${editProvider.id}_password`" />

            <config-textbox v-if="editProvider.config.cookies.enabled || editProvider.subType === 'torrentrss'"
                            v-model="editProvider.config.cookies.values" label="Cookies" :id="`${editProvider.id}_cookies`">
                <template v-if="editProvider.config.cookies.required">
                    <p>eg. {{editProvider.config.cookies.required.map(cookie => cookie + '=xx;').join('').slice(0, -1)}}</p>
                    <p>This provider requires the following cookies: {{editProvider.config.cookies.required.join(', ')}}.
                        <br>For a step by step guide please follow the link to our <app-link href="https://github.com/pymedusa/Medusa/wiki/Configure-Providers-with-captcha-protection">WIKI</app-link>
                    </p>
                </template>
            </config-textbox>

            <config-textbox v-if="'passkey' in editProvider.config" v-model="editProvider.config.passkey" label="Passkey" :id="`${editProvider.id}_passkey`" />

            <config-textbox v-if="'pin' in editProvider.config" v-model="editProvider.config.pin" type="password" label="Pin" :id="`${editProvider.id}_pin`" />

            <config-textbox v-if="'pid' in editProvider.config" v-model="editProvider.config.pid" type="password" label="Pid" :id="`${editProvider.id}_pid`" />

            <config-textbox-number v-if="'ratio' in editProvider.config" v-model="editProvider.config.ratio" :min="-1" :step="0.1" label="Seed ratio" :id="`${editProvider.id}_seed_ratio`">
                <p>Configure a desired seeding ratio. Used by the (automated download handler in config - postprocessing)
                    <br>-1 for provider specific option is disabled.
                    <br>0 for not using a seed ratio. Actions configured in the download handler, will not wait for finished seeding.
                    <br>If disabled the global option is used in config - postprocessing (automated download handling))
                </p>
            </config-textbox-number>

            <config-textbox-number
                v-if="'minseed' in editProvider.config"
                v-model="editProvider.config.minseed" label="Minimum seeders" :min="0" :step="1"
                :id="`${editProvider.id}_min_seed`"
            />

            <config-textbox-number
                v-if="'minleech' in editProvider.config"
                v-model="editProvider.config.minleech" label="Minimum leechers" :min="0" :step="1"
                :id="`${editProvider.id}_min_leech`"
            />

            <config-toggle-slider v-if="'confirmed' in editProvider.config" v-model="editProvider.config.confirmed" label="Confirmed downloads" :name="`${editProvider.id}_confirmed`" :id="`${editProvider.id}_confirmed`">
                <p>only download torrents from trusted or verified uploaders ?</p>
            </config-toggle-slider>

            <config-toggle-slider v-if="'ranked' in editProvider.config" v-model="editProvider.config.ranked" label="Ranked torrents" :name="`${editProvider.id}_ranked`" :id="`${editProvider.id}_ranked`">
                <p>only download ranked torrents (trusted releases)</p>
            </config-toggle-slider>

            <config-template v-if="'sorting' in editProvider.config" label-for="sorting" label="Sorting results by">
                <select id="sorting" class="form-control input-sm max-input350" v-model="editProvider.config.sorting">
                    <option value="last">last</option>
                    <option value="seeders">seeders</option>
                    <option value="leechers">leechers</option>
                </select>
            </config-template>

            <config-toggle-slider v-if="'freeleech' in editProvider.config" v-model="editProvider.config.freeleech" label="Freeleech" :name="`${editProvider.id}_freeleech`" :id="`${editProvider.id}_freeleech`">
                <p>only download <b>"FreeLeech"</b> torrents.</p>
            </config-toggle-slider>

            <config-toggle-slider v-model="editProvider.config.search.daily.enabled" label="Enable daily searches" :name="`${editProvider.id}_enable_daily`" :id="`${editProvider.id}_enable_daily`">
                <p>enable provider to perform daily searches.</p>
            </config-toggle-slider>

            <config-toggle-slider v-model="editProvider.config.search.manual.enabled" label="Enable manual searches" :name="`${editProvider.id}_enable_manual`" :id="`${editProvider.id}_enable_manual`">
                <p>enable provider to be used in 'Manual Search' feature.</p>
            </config-toggle-slider>

            <config-toggle-slider v-model="editProvider.config.search.backlog.enabled" label="Enable backlog searches" :name="`${editProvider.id}_enable_backlog`" :id="`${editProvider.id}_enable_backlog`">
                <p>enable provider to perform backlog searches.</p>
            </config-toggle-slider>

            <config-template label-for="backlog_search_mode" label="Backlog search mode">
                <div class="radio-item">
                    <input type="radio" :name="`${editProvider.id}_search_mode_sponly`" :id="`${editProvider.id}_search_mode_sponly`" value="sponly" v-model="editProvider.config.search.mode">
                    <label for="one">Season packs only</label>
                </div>
                <div class="radio-item">
                    <input type="radio" :name="`${editProvider.id}_search_mode_eponly`" :id="`${editProvider.id}_search_mode_eponly`" value="eponly" v-model="editProvider.config.search.mode">
                    <label for="one">Episodes only</label>
                </div>
                <p>when searching with backlog you can choose to have it look for season packs only, or choose to have it build a complete season from just single episodes.</p>
            </config-template>

            <config-toggle-slider v-model="editProvider.config.search.fallback" label="Enable fallback" :name="`${editProvider.id}_enable_fallback`" :id="`${editProvider.id}_enable_fallback`">
                <p>when searching for a complete season depending on search mode you may return no results, this helps by restarting the search using the opposite search mode.</p>
            </config-toggle-slider>

            <config-toggle-slider v-model="editProvider.config.search.delay.enabled" label="Enable search delay" :name="`${editProvider.id}_enable_search_delay`" :id="`${editProvider.id}_enable_search_delay`">
                <p>Enable to delay downloads for this provider for an x amount of hours. The provider will start snatching results for a specific episode after a delay has expired, compared to when it first got a result for the specific episode.</p>
                <p>A negative value will have the daily search accepts results before the episode scheduled air date/time.</p>
                <p>Proper and Backlog searches are exempted from the delay.</p>
            </config-toggle-slider>

            <config-textbox-number
                v-if="editProvider.config.search.delay.enabled" :value="editProvider.config.search.delay.duration / 60.0"
                label="Search delay (hours)" :id="`${editProvider.id}_search_delay_duration`" :step="0.5"
                @input="editProvider.config.search.delay.duration = $event * 60"
            >
                <p>Amount of hours to wait for downloading a result compared to the first result for a specific episode.</p>
            </config-textbox-number>
        </div>
        <button class="btn-medusa config_submitter" :disabled="saving" @click="save" style="float: left">Save Changes</button>
        <test-provider :provider-id="editProvider.id" :provider-name="editProvider.name" />
    </div>
</template>

<script>
import { mapState } from 'vuex';
import {
    AppLink,
    ConfigTextbox,
    ConfigTextboxNumber,
    ConfigTemplate,
    ConfigToggleSlider
} from '.';
import TestProvider from './test-provider.vue';

export default {
    name: 'config-provider-torrent',
    components: {
        AppLink,
        ConfigTextbox,
        ConfigTextboxNumber,
        ConfigTemplate,
        ConfigToggleSlider,
        TestProvider
    },
    props: {
        provider: {
            type: Object,
            required: true
        }
    },
    data() {
        return {
            saving: false,
            editProvider: {}
        };
    },
    computed: {
        ...mapState({
            client: state => state.auth.client
        })
    },
    mounted() {
        const { provider } = this;
        this.editProvider = { ...provider };
    },
    methods: {
        async save() {
            const { editProvider } = this;
            // Disable the save button until we're done.
            this.saving = true;

            try {
                await this.client.api.patch(`providers/${editProvider.id}`, editProvider.config);
                this.$snotify.success(
                    `Saved provider ${editProvider.name}`,
                    'Saved',
                    { timeout: 5000 }
                );
            } catch (error) {
                this.$snotify.error(
                    `Error while trying to save provider ${editProvider.name}`,
                    'Error'
                );
            } finally {
                this.saving = false;
            }
        }
    }
};
</script>

<style>
</style>

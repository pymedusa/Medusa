<template>
    <div id="provider-options-torrent">
        <!-- Newznab section -->
        <div class="providerDiv" :id="`${provider.id}Div`">
            <config-textbox v-if="'customUrl' in provider.config" v-model="provider.config.customUrl" label="Custom Url" :id="`${provider.id}_custom_url`">
                <p>The URL should include the protocol (and port if applicable).  Examples:  http://192.168.1.4/ or http://localhost:3000/</p>
            </config-textbox>

            <config-textbox v-if="'apikey' in provider.config && provider.config.subType !== 'torznab'" v-model="provider.config.apikey" type="password" label="API key" :id="`${provider.id}_api_key`"/>

            <config-textbox v-if="'digest' in provider.config" v-model="provider.config.digest" type="password" label="Digest" :id="`${provider.id}_digest`"/>

            <config-textbox v-if="'hash' in provider.config" v-model="provider.config.hash" label="Hash" :id="`${provider.id}_hash`"/>

            <config-textbox v-if="'username' in provider.config" v-model="provider.config.username" label="Username" :id="`${provider.id}_username`"/>

            <config-textbox v-if="'password' in provider.config" v-model="provider.config.password" autocomplete="no" type="password" label="Password" :id="`${provider.id}_password`"/>

            <config-textbox v-if="provider.config.cookies.enabled || provider.subType === 'torrentrss'" label="Cookies" :id="`${provider.id}_cookies`">
                <template v-if="provider.config.cookies.required">
                    <p>eg. {{provider.config.cookies.required.map(cookie => cookie + '=xx;').join('').slice(0, -1)}}</p>
                    <p>This provider requires the following cookies: {{provider.config.cookies.required.join(', ')}}.
                        <br/>For a step by step guide please follow the link to our <app-link href="https://github.com/pymedusa/Medusa/wiki/Configure-Providers-with-captcha-protection">WIKI</app-link>
                    </p>
                </template>
            </config-textbox>

            <config-textbox v-if="'passkey' in provider.config" v-model="provider.config.passkey" label="Passkey" :id="`${provider.id}_passkey`" />

            <config-textbox v-if="'pin' in provider.config" v-model="provider.config.pin" type="password" label="Pin" :id="`${provider.id}_pin`" />

            <config-textbox-number v-if="'ratio' in provider.config" v-model="provider.config.ratio" :min="-1" :step="0.1" label="Seed ratio" :id="`${provider.id}_seed_ratio`">
                <p>Configure a desired seeding ratio. Used by the (automated download handler in config - postprocessing)
                <br />-1 for provider specific option is disabled.
                <br />0 for not using a seed ratio. Actions configured in the download handler, will not wait for finished seeding.
                <br />If disabled the global option is used in config - postprocessing (automated download handling))</p>
            </config-textbox-number>

            <config-textbox-number v-if="'minseed' in provider.config"
                v-model="provider.config.minseed" label="Minimum seeders" :min="0" :step="1"
                :id="`${provider.id}_min_seed`"
            />

            <config-textbox-number v-if="'minleech' in provider.config"
                v-model="provider.config.minleech" label="Minimum leechers" :min="0" :step="1"
                :id="`${provider.id}_min_leech`"
            />

            <config-toggle-slider v-if="'confirmed' in provider.config" v-model="provider.config.confirmed" label="Confirmed downloads" :name="`${provider.id}_confirmed`" :id="`${provider.id}_confirmed`">
                <p>only download torrents from trusted or verified uploaders ?</p>
            </config-toggle-slider>

            <config-toggle-slider v-if="'ranked' in provider.config" v-model="provider.config.ranked" label="Ranked torrents" :name="`${provider.id}_ranked`" :id="`${provider.id}_ranked`">
                <p>only download ranked torrents (trusted releases)</p>
            </config-toggle-slider>

            <config-template v-if="'sorting' in provider.config" label-for="sorting" label="Sorting results by">
                <select id="sorting" class="form-control input-sm" v-model="provider.config.sorting">
                    <option value="last">last</option>
                    <option value="seeders">seeders</option>
                    <option value="leechers">leechers</option>
                </select>
            </config-template>

            <config-toggle-slider v-if="'freeleech' in provider.config" v-model="provider.config.freeleech" label="Freeleech" :name="`${provider.id}_freeleech`" :id="`${provider.id}_freeleech`">
                <p>only download <b>"FreeLeech"</b> torrents.</p>
            </config-toggle-slider>

            <config-toggle-slider v-model="provider.config.search.daily.enabled" label="Enable daily searches" :name="`${provider.id}_enable_daily`" :id="`${provider.id}_enable_daily`">
                <p>enable provider to perform daily searches.</p>
            </config-toggle-slider>

            <config-toggle-slider v-model="provider.config.search.manual.enabled" label="Enable manual searches" :name="`${provider.id}_enable_manual`" :id="`${provider.id}_enable_manual`">
                <p>enable provider to be used in 'Manual Search' feature.</p>
            </config-toggle-slider>

            <config-toggle-slider v-model="provider.config.search.backlog.enabled" label="Enable backlog searches" :name="`${provider.id}_enable_backlog`" :id="`${provider.id}_enable_backlog`">
                <p>enable provider to perform backlog searches.</p>
            </config-toggle-slider>

            <config-template label-for="backlog_search_mode" label="Backlog search mode">
                <div class="radio-item">
                    <input type="radio" :name="`${provider.id}_search_mode_sponly`" :id="`${provider.id}_search_mode_sponly`" value="sponly" v-model="provider.config.search.mode">
                    <label for="one">Season packs only</label>
                </div>
                <div class="radio-item">
                    <input type="radio" :name="`${provider.id}_search_mode_eponly`" :id="`${provider.id}_search_mode_eponly`" value="eponly" v-model="provider.config.search.mode">
                    <label for="one">Episodes only</label>
                </div>
                <p>when searching with backlog you can choose to have it look for season packs only, or choose to have it build a complete season from just single episodes.</p>
            </config-template>

            <config-toggle-slider v-model="provider.config.search.fallback" label="Enable fallback" :name="`${provider.id}_enable_fallback`" :id="`${provider.id}_enable_fallback`">
                <p>when searching for a complete season depending on search mode you may return no results, this helps by restarting the search using the opposite search mode.</p>
            </config-toggle-slider>

            <config-toggle-slider v-model="provider.config.search.delay.enabled" label="Enable search delay" :name="`${provider.id}_enable_search_delay`" :id="`${provider.id}_enable_search_delay`">
                <p>Enable to delay downloads for this provider for an x amount of hours. The provider will start snatching results for a specific episode after a delay has expired, compared to when it first got a result for the specific episode.</p>
                <p>Searches for PROPER releases are exempted from the delay.</p>
            </config-toggle-slider>

            <config-textbox-number
                v-if="provider.config.search.delay.enabled" :value="provider.config.search.delay.duration / 60.0"
                label="Search delay (hours)" :id="`${provider.id}_search_delay_duration`" :min="0.5" :step="0.5"
                @input="provider.config.search.delay.duration = $event * 60"
            >
                <p>Amount of hours to wait for downloading a result compared to the first result for a specific episode.</p>
            </config-textbox-number>        
        </div>
        <input type="submit"
            class="btn-medusa config_submitter"
            value="Save Changes"
            :disabled="saving"
            @click="save"
        >
    </div>
</template>

<script>
import { api } from '../../api';
import { 
    ConfigTextbox,
    ConfigTextboxNumber,
    ConfigTemplate,
    ConfigToggleSlider
} from ".";

export default {
    name: 'config-provider-torrent',
    components: {
        ConfigTextbox,
        ConfigTextboxNumber,
        ConfigTemplate,
        ConfigToggleSlider
    },
    props: {
        provider: {
            type: Object,
            required: true
        }
    },
    data() {
        return {
            saving: false
        }
    },
    methods: {
        async save() {
            const { provider } = this;
            // Disable the save button until we're done.
            this.saving = true;

            try {
                await api.patch(`providers/${provider.id}`, provider.config);
                this.$snotify.success(
                    `Saved provider ${provider.name}`,
                    'Saved',
                    { timeout: 5000 }
                );
            } catch (error) {
                this.$snotify.error(
                    `Error while trying to save provider ${provider.name}`,
                    'Error'
                );
            } finally {
                this.saving = false;
            }
        }
    }
}
</script>

<style>

</style>
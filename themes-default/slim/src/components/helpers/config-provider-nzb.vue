<template>
    <div id="provider-options-nzb">
        <!-- Newznab section -->
        <div class="providerDiv" :id="`${provider.id}Div`">
            <config-textbox v-if="'username' in provider.config && provider.subType !== 'newznab'" v-model="provider.config.username" label="Username" :id="`${provider.id}_username`" />

            <!-- if cur_newznab_provider.default and cur_newznab_provider.needs_auth: -->
            <template v-if="provider.default && provider.needsAuth">
                <config-template :label-for="`${provider.id}_url`" label="URL">
                    <input type="text" :id="`${provider.id}_url`" :value="`${provider.url}`" class="form-control input-sm input350" disabled />
                </config-template>
                <config-textbox v-if="'apikey' in provider.config" v-model="provider.config.apikey" type="password" label="API key" :id="`${provider.id}_url`" input-class="newznab_api_key"/>
            </template>
            <template v-else-if="provider.subType !== 'newznab'">
                <config-textbox v-if="'apikey' in provider.config" v-model="provider.config.apikey" type="password" label="API key" :id="`${provider.id}_url`" input-class="newznab_api_key"/>
            </template>

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
    name: 'config-provider-nzb',
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
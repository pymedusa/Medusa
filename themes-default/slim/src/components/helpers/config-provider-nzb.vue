<template>
    <div id="provider-options-nzb">
        <!-- Newznab section -->
        <div v-if="Object.keys(editProvider).length > 0" class="providerDiv" :id="`${editProvider.id}Div`">
            <config-textbox v-if="'username' in editProvider.config && editProvider.subType !== 'newznab'" v-model="editProvider.config.username" label="Username" :id="`${editProvider.id}_username`" />

            <template v-if="editProvider.default && editProvider.needsAuth">
                <config-template :label-for="`${editProvider.id}_url`" label="URL">
                    <input type="text" :id="`${editProvider.id}_url`" v-model="editProvider.config.url" class="form-control input-sm max-input350">
                </config-template>
                <config-textbox v-if="'apikey' in editProvider.config" v-model="editProvider.config.apikey" type="password" label="API key" :id="`${editProvider.id}_url`" input-class="newznab_api_key" />
            </template>
            <template v-else-if="editProvider.subType !== 'newznab'">
                <config-textbox v-if="'apikey' in editProvider.config" v-model="editProvider.config.apikey" type="password" label="API key" :id="`${editProvider.id}_url`" input-class="newznab_api_key" />
            </template>

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
                label="Search delay (hours)" :id="`${editProvider.id}_search_delay_duration`" :min="0.5" :step="0.5"
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
    ConfigTextbox,
    ConfigTextboxNumber,
    ConfigTemplate,
    ConfigToggleSlider
} from '.';
// Putting this import with the rest from index.js, results in an error. Don't know why.
import TestProvider from './test-provider.vue';

export default {
    name: 'config-provider-nzb',
    components: {
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

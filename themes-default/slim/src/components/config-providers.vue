<template>
    <div id="config-providers">
        <vue-snotify />

        <vue-tabs>
            <v-tab key="provider_priorities" title="Provider Priorities">
                <div class="row component-group">
                    <div class="component-group-desc col-xs-12 col-md-2">
                        <h3>Provider Priorities</h3>
                        <p>Check off and drag the providers into the order you want them to be used.</p>
                        <p>At least one provider is required but two are recommended.</p>

                        <blockquote v-if="!clients.nzb.enabled || !clients.torrents.enabled" style="margin: 20px 0;">NZB/Torrent providers can be toggled in <b>
                            <app-link href="config/search">Search Settings</app-link></b>
                        </blockquote>
                        <br v-else>
                        <div>
                            <p class="note"><span class="red-text">*</span> Provider does not support backlog searches at this time.</p>
                            <p class="note"><span class="red-text">!</span> Provider is <b>NOT WORKING</b>.</p>
                        </div>
                    </div>
                    <div class="col-xs-12 col-md-10">
                        <!-- List with draggable providers -->
                        <draggable id="provider_order_list" tag="ul" v-model="providerPriorities" class="list-group" handle=".ui-state-default">
                            <li v-for="currentProvider in providerPriorities" :key="currentProvider.id" class="ui-state-default" :class="[currentProvider.type === 'torrent' ? 'torrent-provider' : 'nzb-provider']" :id="currentProvider.id">
                                <input type="checkbox" :id="`enable_${currentProvider.name}`" class="provider_enabler" v-model="currentProvider.config.enabled" :disabled="general.brokenProviders.includes(currentProvider.id)">
                                <app-link :href="currentProvider.url" class="imgLink" rel="noreferrer" onclick="window.open(this.href, '_blank'); return false;"><img :src="`images/providers/${currentProvider.imageName}`" :alt="currentProvider.name" :title="currentProvider.name" width="16" height="16" style="vertical-align:middle;"></app-link>
                                <span style="vertical-align:middle;">{{currentProvider.name}}</span> <!-- // eslint-disable-line vue/html-self-closing -->
                                <span v-if="!currentProvider.config.search.backlog.enabled" class="red-text">*</span>
                                <span v-if="general.brokenProviders.includes(currentProvider.id)" class="red-text">!</span>
                                <span class="ui-icon ui-icon-arrowthick-2-n-s pull-right" style="vertical-align:middle;" title="Re-order provider" />
                                <span class="ui-icon pull-right" :class="[currentProvider.public ? 'ui-icon-unlocked' : 'ui-icon-locked']" style="vertical-align:middle;" title="Public or Private" />
                                <span :class="[currentProvider.config.search.manual.enabled ? 'ui-icon enable-manual-search-icon pull-right' : '']" style="vertical-align:middle;" title="Enabled for 'Manual Search' feature" />
                                <span :class="[currentProvider.config.search.backlog.enabled ? 'ui-icon enable-backlog-search-icon pull-right' : '']" style="vertical-align:middle;" title="Enabled for Backlog Searches" />
                                <span :class="[currentProvider.config.search.backlog.enabled ? 'ui-icon enable-daily-search-icon pull-right' : '']" style="vertical-align:middle;" title="Enabled for Daily Searches" />
                            </li>
                        </draggable>
                    </div>
                </div>

                <button class="btn-medusa config_submitter" :disabled="saving" @click="save()">Save Changes</button>
            </v-tab>

            <v-tab key="provider_options" title="Provider Options &amp; Feel">
                <div class="row component-group">
                    <div class="component-group-desc col-xs-12 col-md-2">
                        <h3>Provider Options</h3>
                        <p>Configure individual provider settings here.</p>
                        <p>Check with provider's website on how to obtain an API key if needed.</p>
                    </div>
                    <div class="col-xs-12 col-md-10">
                        <!-- list with provider options -->
                        <config-template label-for="edit_a_provider" label="Select Provider">
                            <select id="edit_a_provider" class="form-control input-sm max-input350" v-model="selectedProvider">
                                <option disabled value="">Select Provider</option>
                                <option :value="option.value" v-for="option in enabledProviders" :key="option.value">
                                    {{ option.text }}
                                </option>
                            </select>
                        </config-template>

                        <template v-if="currentProvider">
                            <config-provider-nzb v-if="currentProvider.type === 'nzb'"
                                                 :provider="currentProvider"
                                                 :key="currentProvider.id"
                            />
                            <config-provider-torrent v-if="currentProvider.type === 'torrent'"
                                                     :provider="currentProvider"
                                                     :key="currentProvider.id"
                            />
                        </template>

                    </div>
                </div><!-- row component-group //-->
                <button class="btn-medusa config_submitter" :disabled="saving" @click="save()">Save Changes</button>
            </v-tab>

            <v-tab key="custom_newznab_providers" title="Configure Custom Newznab Providers">
                <div class="row component-group">
                    <div class="component-group-desc col-xs-12 col-md-2">
                        <h3>Configure Custom Newznab Providers</h3>
                        <p>Add and setup or remove custom Newznab providers.</p>
                    </div>
                    <div class="col-xs-12 col-md-10">
                        <config-custom-newznab @save="save()" />
                    </div>
                </div><!-- row component-group //-->

                <button class="btn-medusa config_submitter" :disabled="saving" @click="save()">Save Changes</button>
            </v-tab>

            <v-tab key="custom_torrent_providers" title="Configure Custom Torrent Providers">
                <div class="row component-group">
                    <div class="component-group-desc col-xs-12 col-md-2">
                        <h3>Configure Custom Torrent Providers</h3>
                        <p>Add and setup or remove custom RSS providers.</p>
                    </div>
                    <div class="col-xs-12 col-md-10">
                        <config-custom-torrentrss @save="save()" />
                    </div>
                </div><!-- row component-group //-->

                <button class="btn-medusa config_submitter" :disabled="saving" @click="save()">Save Changes</button>
            </v-tab>

            <v-tab key="custom_torznab_providers" title="Configure Custom Torznab Providers">
                <div class="row component-group">
                    <div class="component-group-desc col-xs-12 col-md-2">
                        <h3>Configure Torznab Providers</h3>
                        <p>Add and setup or remove Torznab providers.</p>

                        <p>
                            <img src="images/providers/jackett.png">
                            When using Jackett. You can add it's jackett url's here. Jackett makes use of the Torznab protocol.
                        </p>
                    </div>
                    <div class="col-xs-12 col-md-10">
                        <config-custom-torznab @save="save()" />
                    </div>
                </div><!-- row component-group //-->

                <button class="btn-medusa config_submitter" :disabled="saving" @click="save()">Save Changes</button>
            </v-tab>

            <v-tab key="custom_prowlarr_providers" title="Configure Custom Prowlarr Providers">
                <div class="row component-group">
                    <div class="component-group-desc col-xs-12 col-md-2">
                        <img src="images/providers/prowlarr.png">
                        <h3>Configure Prowlarr</h3>
                        <p>Add or Remove Prowlarr providers</p>
                    </div>
                    <div class="col-xs-12 col-md-10">
                        <config-custom-prowlarr @save="save()" />
                    </div>
                </div><!-- row component-group //-->

                <button class="btn-medusa config_submitter" :disabled="saving" @click="save()">Save Changes</button>
            </v-tab>
        </vue-tabs>
    </div>
</template>

<script>
import { mapActions, mapState } from 'vuex';
import { VueTabs, VTab } from 'vue-nav-tabs/dist/vue-tabs.js';
import Draggable from 'vuedraggable';
import {
    AppLink,
    ConfigCustomNewznab,
    ConfigCustomProwlarr,
    ConfigCustomTorrentrss,
    ConfigCustomTorznab,
    ConfigTemplate,
    ConfigProviderNzb,
    ConfigProviderTorrent
} from './helpers';

export default {
    name: 'config-providers',
    components: {
        AppLink,
        Draggable,
        ConfigCustomNewznab,
        ConfigCustomProwlarr,
        ConfigCustomTorrentrss,
        ConfigCustomTorznab,
        ConfigProviderNzb,
        ConfigProviderTorrent,
        ConfigTemplate,
        VueTabs,
        VTab
    },
    data() {
        return {
            saving: false,
            selectedProvider: ''
        };
    },
    mounted() {
        const { getProviders } = this;
        getProviders();
    },
    computed: {
        ...mapState({
            provider: state => state.provider,
            providers: state => state.provider.providers,
            clients: state => state.config.clients,
            general: state => state.config.general,
            client: state => state.auth.client
        }),
        providerPriorities: {
            get() {
                const { clients, provider } = this;
                return provider.providers.filter(provider => (
                    provider.type === 'torrent' && clients.torrents.enabled
                ) || (
                    provider.type === 'nzb' && clients.nzb.enabled
                ));
            },
            set(providers) {
                this.provider.providers = providers;
            }
        },
        enabledProviders() {
            const { clients, providers } = this;
            const data = [];
            for (const provider of providers) {
                if (!provider.config.enabled) {
                    continue;
                }

                if (provider.type === 'torrent' && clients.torrents.enabled) {
                    data.push({ value: provider.id, text: provider.name });
                }

                if (provider.type === 'nzb' && clients.nzb.enabled) {
                    data.push({ value: provider.id, text: provider.name });
                }
            }
            return data;
        },
        currentProvider() {
            const { providers, selectedProvider } = this;
            return providers.find(prov => prov.id === selectedProvider);
        }
    },
    methods: {
        ...mapActions([
            'getProviders'
        ]),
        async save() {
            const { client, provider } = this;
            const { providers } = provider;

            // Disable the save button until we're done.
            this.saving = true;

            try {
                await client.api.post('providers', { providers });
                this.$snotify.success(
                    'Saved providers',
                    'Saved',
                    { timeout: 5000 }
                );
            } catch (error) {
                this.$snotify.error(
                    'Error while trying to save providers',
                    'Error'
                );
            } finally {
                this.saving = false;
                this.reOrderProviders();
            }
        },
        /**
         * Re-order providers. Make sure enabled providers are on top.
         */
        reOrderProviders() {
            this.providerPriorities = [
                ...this.providerPriorities.filter(provider => provider.config.enabled),
                ...this.providerPriorities.filter(provider => !provider.config.enabled)
            ];
        }
    }
};
</script>
<style>
</style>

<template>
    <div id="custom-prowlarr">
        <div class="row">
            <div class="col-lg-12">
                <config-textbox v-model="prowlarr.url" label="Prowler Url" id="prowler_url" />
                <config-textbox v-model="prowlarr.apikey" label="Api Key" id="prowler_apikey" />

                <button class="btn-medusa config_submitter" @click="saveConfig">Save</button>
                <button class="btn-medusa config_submitter" @click="testConnectivity">Test</button>
                <span v-show="testResult" class="testresult">{{testResult}}</span>
            </div>
        </div>
        <div class="row">
            <div class="col-lg-12">
                <h3>Available prowlarr providers</h3>
                <vue-good-table
                    :columns="columns"
                    :rows="providersAvailable"
                    :search-options="{
                        enabled: false
                    }"
                    :sort-options="{
                        enabled: true,
                        initialSortBy: { field: 'name', type: 'asc' }
                    }"
                    styleClass="vgt-table condensed"
                />
            </div>
        </div>
    </div>
</template>

<script>
import { api } from '../../api';
import { mapActions, mapState } from 'vuex';
import { ADD_PROVIDER, REMOVE_PROVIDER } from '../../store/mutation-types';
import { 
    ConfigTextbox,
    ConfigTextboxNumber,
    ConfigTemplate,
    ConfigToggleSlider
} from ".";
import Multiselect from 'vue-multiselect';
import { VueGoodTable } from 'vue-good-table';

export default {
    name: 'config-custom-prowlarr',
    components: {
        ConfigTextbox,
        ConfigTextboxNumber,
        ConfigTemplate,
        ConfigToggleSlider,
        Multiselect,
        VueGoodTable
    },
    data() {
        return {
            saving: false,
            name: '',
            url: '',
            apikey: '',
            testResult: null,
            providersAdded: [],
            providersAvailable: [],
            columns: [{
                label: 'added',
                field: 'addedToMedusa'
            }, {
                label: 'name',
                field: 'name'
            }, {
                label: 'protocol',
                field: 'protocol'
            }]
        }
    },
    mounted() {
        const { getAvailableProviders } = this;
        // If we already have an url and apikey, try to get the list with prowlarr (available) providers.
        
        this.unwatchProp = this.$watch('prowlarr', prowlarr => {
            if (prowlarr.url && prowlarr.apikey) {
                this.unwatchProp();
                getAvailableProviders();
            }
        }, {
            immediate: true, // run immediately
            deep: true // detects changes inside objects. not needed here, but maybe in other cases
        });
    },
    methods: {        
        ...mapActions({
            setConfig: 'setConfig'
        }),
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
        },
        async getCategories() {
            const { currentProvider } = this;
            if (!currentProvider.name || !currentProvider.url || !currentProvider.config.apikey ) {
                return;
            }

            try {
                const response = await api.post(`providers/torznab/operation`, {
                    type: 'GETCATEGORIES',
                    apikey: currentProvider.config.apikey,
                    name: currentProvider.name,
                    url: currentProvider.url
                });
                if (response.data.result.success) {
                    this.availableCategories = response.data.result.categories;
                }
            } catch (error) {
                this.$snotify.error(
                    `Error while trying to get cats for provider ${currentProvider.name}`,
                    'Error'
                );
            }
        },
        async addProvider() {
            const { name, apikey, url } = this;
            try {
                const response = await api.post(`providers/torznab`, { apikey, name, url });
                this.$store.commit(ADD_PROVIDER, response.data.result);
                this.$snotify.success(
                    `Saved provider ${name}`,
                    'Saved',
                    { timeout: 5000 }
                );
                this.apikey = '';
                this.name = '';
                this.url = '';
            } catch (error) {
                this.$snotify.error(
                    `Error while trying to get cats for provider ${name}`,
                    'Error'
                );
            }
        },
        async removeProvider() {
            const { currentProvider } = this;
            try {
                const response = await api.delete(`providers/torznab/${currentProvider.id}`);
                this.$store.commit(REMOVE_PROVIDER, currentProvider);
                this.$snotify.success(
                    `Removed provider ${currentProvider.name}`,
                    'Removed',
                    { timeout: 5000 }
                );
                this.selectedProvider = '#add'
            } catch (error) {
                this.$snotify.error(
                    `Error while trying to remove provider ${currentProvider.name}`,
                    'Error'
                );
            }
        },
        createId(providerName) {
            return providerName.replace(/[^\d\w_]/gi, '_').toLowerCase().trim();
        },
        async testConnectivity() {
            const { prowlarr } = this;
            try {
                const response = await api.post('providers/prowlarr/operation', {
                    type: 'TEST', url: prowlarr.url, apikey: prowlarr.apikey
                });
                this.testResult = 'connected';
            } catch (error) {
                this.testResult = 'could not connect'
                this.$snotify.error(
                    'Error while trying to connect to prowlarr',
                    'Error'
                );
            }
        },
        async saveConfig() {
            const { prowlarr, setConfig } = this;
            const config = {
                providers: {
                    prowlarr
                }
            }

            try {
                await setConfig({section: 'main', config});
                this.$snotify.success(
                    'Saved general config',
                    'Saved',
                    { timeout: 5000 }
                );
            } catch (error) {
                this.$snotify.error(
                    'Error while trying to save general config',
                    `Error: ${error}`
                );
            }
        },
        async getAvailableProviders() {
            const { prowlarr } = this; 
            if (prowlarr.url && prowlarr.apikey) {
                try {
                    const response = await api.post('providers/prowlarr/operation', {
                        type: 'GETINDEXERS', url: prowlarr.url, apikey: prowlarr.apikey
                    });
                    this.providersAvailable = response.data;
                } catch (error) {
                    this.$snotify.warning(
                        'Could not retrieve available providers',
                        'Warning'
                    );
                }
            }
        }
    },
    computed: {
        ...mapState({
            prowlarr: state => state.config.general.providers.prowlarr,
            providers: state => state.provider.providers
        }),
        torznabProviderOptions() {
            const { providers } = this;
            return providers.filter(prov => prov.subType === 'torznab').map(prov => {
                return ({value: prov.id, text: prov.name});
            })
        },
        currentProvider() {
            const { providers, selectedProvider } = this;
            if (!selectedProvider) return null;
            return providers.find(prov => prov.id === selectedProvider);
        },
        providerCatIds() {
            const { currentProvider } = this;
            if (!currentProvider || currentProvider.config.catIds.length === 0) {
                return []
            }

            // Check if we have a list of objects.
            if (currentProvider.config.catIds.every(x => typeof(x) === 'string' )) {
                return currentProvider.config.catIds.map(cat => ({ id: cat, name: null }))
            }

            return currentProvider.config.catIds;
        },
        providerIdAvailable() {
            const { providers, name } = this;
            const compareId = provider => {
                const providerId = name.replace(/[^\d\w_]/gi, '_').toLowerCase().trim();
                return providerId === provider.id;
            }
            return providers.filter(compareId).length === 0;
        }
    },
    watch: {
        currentProvider(newProvider, oldProvider) {
            if (newProvider && newProvider != oldProvider) {
                this.getCategories();
            }
        }
    }
}
</script>

<style scoped>

.warning-enter-active,
.warning-leave-active {
    -moz-transition-duration: 0.3s;
    -webkit-transition-duration: 0.3s;
    -o-transition-duration: 0.3s;
    transition-duration: 0.3s;
    -moz-transition-timing-function: ease-in;
    -webkit-transition-timing-function: ease-in;
    -o-transition-timing-function: ease-in;
    transition-timing-function: ease-in;
}

.warning-enter-to,
.warning-leave {
    max-height: 100%;
}

.warning-enter,
.warning-leave-to {
    max-height: 0;
}

.warning {
    display: block;
    overflow: hidden;
    width: 100%;
    position: absolute;
    left: 0;
    background-color: #e23636;
    padding: 0 2px 0 2px;
}

.testresult {
    display: inline-block;
    border-style: solid;
    border-width: 1px;
    padding: 1px 4px 4px 4px;
    border-color: #ccc;
}
</style>
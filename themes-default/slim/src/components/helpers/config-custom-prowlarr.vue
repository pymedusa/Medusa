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
            <div class="col-lg-12 vgt-table-styling">
                <h3>Available prowlarr providers</h3>
                <vue-good-table
                    :columns="columns"
                    :rows="prowlarrProviders"
                    :search-options="{
                        enabled: false
                    }"
                    :sort-options="{
                        enabled: true,
                        initialSortBy: { field: 'name', type: 'asc' }
                    }"
                    styleClass="vgt-table condensed"
                >
                <template #table-row="props">
                    <span v-if="props.column.label === 'Added'" class="align-center">
                        <img v-if="props.row.localProvider" src="/images/yes16.png">
                    </span>

                    <span v-else-if="props.column.label === 'Action'" class="align-center">
                        <button v-if="!props.row.localProvider" class="btn-medusa config_submitter" @click="addProvider(props.row)">Add Provider</button>
                        <button v-else class="btn-medusa btn-danger" @click="removeProvider(props.row)">Remove Provider</button>
                    </span>
                </template>
                </vue-good-table>
            </div>
        </div>
    </div>
</template>

<script>
import { api } from '../../api';
import { mapActions, mapState } from 'vuex';
import { ADD_PROVIDER, REMOVE_PROVIDER } from '../../store/mutation-types';
import { ConfigTextbox } from ".";
import { VueGoodTable } from 'vue-good-table';

export default {
    name: 'config-custom-prowlarr',
    components: {
        ConfigTextbox,
        VueGoodTable
    },
    data() {
        return {
            saving: false,
            url: '',
            apikey: '',
            testResult: null,
            providersAvailable: [],
            columns: [{
                label: 'Added',
                field: 'addedProvider',
                sortable: false
            }, {
                label: 'name',
                field: 'name'
            }, {
                label: 'protocol',
                field: 'protocol'
            }, {
                label: 'Action',
                field: 'action',
                sortable: false
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
        async addProvider(provider) {
            const subType = provider.protocol === 'torrent' ? 'torznab' : 'newznab';
            try {
                const response = await api.post(`providers/prowlarr`, { subType, id: provider.id, name: provider.name });
                this.$store.commit(ADD_PROVIDER, response.data.result);
                this.$snotify.success(
                    `Saved provider ${provider.name}`,
                    'Saved',
                    { timeout: 5000 }
                );
            } catch (error) {
                this.$snotify.error(
                    `Error while trying to get cats for provider ${provider.name}`,
                    'Error'
                );
            }
        },
        async removeProvider(provider) {
            const subType = provider.protocol === 'torrent' ? 'torznab' : 'newznab';
            try {
                const response = await api.delete(`providers/${subType}/${provider.localId}`);
                this.$store.commit(REMOVE_PROVIDER, provider.localId);
                this.$snotify.success(
                    `Removed provider ${provider.name}`,
                    'Removed',
                    { timeout: 5000 }
                );
            } catch (error) {
                this.$snotify.error(
                    `Error while trying to remove provider ${provider.name}`,
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
        prowlarrProviders() {
            const { createId, providers, providersAvailable } = this;
            const managedProviders = providers.filter(prov => prov.manager === 'prowlarr');
            return providersAvailable.map(prov => {
                prov.localProvider = Boolean(managedProviders.find(internalProvider => internalProvider.id === createId(prov.name)));
                prov.localId = createId(prov.name);
                return prov;
            })

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
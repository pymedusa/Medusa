<template>
    <div id="custom-prowlarr">
        <div class="row">
            <div class="col-lg-12">
                <config-textbox v-model="prowlarr.url" label="Prowlarr Url" id="prowlarr_url" />
                <config-textbox v-model="prowlarr.apikey" label="Api Key" id="prowlarr_apikey" />

                <button class="btn-medusa config_submitter" @click="saveConfig">Save</button>
                <button class="btn-medusa config_submitter" @click="testConnectivity">Test</button>
                <button class="btn-medusa config_submitter" @click="getAvailableProviders">Get Providers</button>

                <span v-show="testResult" class="testresult">{{testResult}}</span>
            </div>
        </div>
        <div class="row">
            <div class="col-lg-12 vgt-table-styling">
                <h3>Available providers</h3>
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
import { mapActions, mapGetters, mapState } from 'vuex';
import { ADD_PROVIDER, REMOVE_PROVIDER } from '../../store/mutation-types';
import { ConfigTextbox } from '.';
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
            availableProviders: [],
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
        };
    },
    mounted() {
        const { getAvailableProviders } = this;
        // If we already have an url and apikey, try to get the list with prowlarr (available) providers.

        this.unwatchProp = this.$watch('prowlarr', prowlarr => {
            if (prowlarr.url && prowlarr.apikey) {
                this.unwatchProp();
                getAvailableProviders();
            }
        });
    },
    methods: {
        ...mapActions({
            setConfig: 'setConfig'
        }),
        async addProvider(provider) {
            const subType = provider.protocol === 'torrent' ? 'torznab' : 'newznab';
            try {
                const response = await this.client.api.post('providers/prowlarr', { subType, id: provider.id, name: provider.name });
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
            const useProviderId = provider.localProvider ? provider.localProvider.id : provider.localId;

            try {
                await this.client.api.delete(`providers/${subType}/${useProviderId}`);
                this.$store.commit(REMOVE_PROVIDER, useProviderId);
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
        async testConnectivity() {
            const { prowlarr } = this;
            try {
                await this.client.api.post('providers/prowlarr/operation', {
                    type: 'TEST', url: prowlarr.url, apikey: prowlarr.apikey
                });
                this.testResult = 'connected';
            } catch (error) {
                this.testResult = 'could not connect';
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
            };

            try {
                await setConfig({ section: 'main', config });
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
                    const response = await this.client.api.post('providers/prowlarr/operation', {
                        type: 'GETINDEXERS', url: prowlarr.url, apikey: prowlarr.apikey
                    });
                    this.availableProviders = response.data;
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
            providers: state => state.provider.providers,
            client: state => state.auth.client
        }),
        ...mapGetters(['providerNameToId']),
        prowlarrProviders() {
            const { providerNameToId, providers, availableProviders } = this;
            const managedProviders = providers.filter(prov => prov.manager === 'prowlarr');
            return availableProviders.map(prov => {
                prov.localProvider = managedProviders.find(internalProvider => internalProvider.idManager === prov.name);
                prov.localId = providerNameToId(prov.name);
                return prov;
            });
        }
    }
};
</script>

<style scoped>
.testresult {
    display: inline-block;
    border-style: solid;
    border-width: 1px;
    padding: 1px 4px 4px 4px;
    border-color: #ccc;
}
</style>

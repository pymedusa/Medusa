<template>
    <div id="custom-newznab">
        <config-template label-for="select_newznab_provider" label="Select Provider">
            <select id="select-provider" class="form-control input-sm" v-model="selectedProvider">
                <option value="#add">--- add new provider ---</option>
                <option :value="option.value" v-for="option in newznabProviderOptions" :key="option.value">
                    {{ option.text }}
                </option>
            </select>
        </config-template>

        <div v-if="currentProvider && selectedProvider !== '#add'" class="edit-provider">
            <config-textbox disabled v-model="currentProvider.name" label="Provider name" id="edit_provider_name" />
            <config-textbox disabled v-model="currentProvider.url" label="Site Url" id="edit_provider_url" />
            <config-textbox type="password" v-model="currentProvider.config.apikey" label="Api key" id="edit_provider_api" />
        
            <config-template label="Categories" label-for="catids">
                <multiselect
                    :value="providerCatIds"
                    :multiple="true"
                    :options="availableCategories"
                    label="id"
                    track-by="id"
                    @input="currentProvider.config.catIds = $event.map(cat => cat.id)"
                >
                    <template slot="option" slot-scope="props">
                        <span><strong>{{props.option.id}}</strong> ({{props.option.name}})</span>
                    </template>

                </multiselect>
            </config-template>

        </div>

        <div v-if="selectedProvider === '#add'" class="add-provider">
            <config-textbox v-model="name" label="Provider name" id="add_provider_name">
                <template v-slot:warning>
                    <transition name="warning">
                        <div v-if="!providerIdAvailable" class="warning">This provider id is already used.</div>
                    </transition>
                </template>
            </config-textbox>
            <config-textbox v-model="url" label="Site Url" id="add_provider_url" />
            <config-textbox type="password" v-model="apikey" label="Api key" id="add_provider_api" />
        
            <button :disabled="!providerIdAvailable" class="btn-medusa config_submitter" @click="addProvider">Add Provider</button>
        </div>
    </div>
</template>

<script>
import { api } from '../../api';
import { mapState } from 'vuex';
import { ADD_PROVIDER } from '../../store/mutation-types';
import { 
    ConfigTextbox,
    ConfigTextboxNumber,
    ConfigTemplate,
    ConfigToggleSlider
} from ".";
import Multiselect from 'vue-multiselect';

export default {
    name: 'config-custom-newznab',
    components: {
        ConfigTextbox,
        ConfigTextboxNumber,
        ConfigTemplate,
        ConfigToggleSlider,
        Multiselect
    },
    data() {
        return {
            saving: false,
            selectedProvider: '#add',
            name: '',
            url: '',
            apikey: '',
            availableCategories: []
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
        },
        async getCategories() {
            const { currentProvider } = this;
            if (!currentProvider.name || !currentProvider.url || !currentProvider.config.apikey ) {
                return;
            }

            try {
                const response = await api.post(`providers/newznab/operation`, {
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
                const response = await api.post(`providers/newznab`, { apikey, name, url });
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
                    `Error while trying to get cats for provider ${currentProvider.name}`,
                    'Error'
                );
            }
        },
        createId(value) {
            return value.replace(/[^\d\w_]/gi, '_').toLowerCase().trim();
        }
    },
    computed: {
        ...mapState({
            providers: state => state.provider.providers
        }),
        newznabProviderOptions() {
            const { providers } = this;
            return providers.filter(prov => prov.subType === 'newznab').map(prov => {
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
</style>
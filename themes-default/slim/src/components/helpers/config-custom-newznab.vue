<template>
    <div id="custom-newznab">
        <config-template label-for="select_newznab_provider" label="Select Provider">
            <select id="select-provider" class="form-control input-sm max-input350" v-model="selectedProvider">
                <option value="#add">--- add new provider ---</option>
                <option :value="option.value" v-for="option in newznabProviderOptions" :key="option.value">
                    {{ option.text }}
                </option>
            </select>
        </config-template>

        <!-- Edit Provider -->
        <div v-if="currentProvider && selectedProvider !== '#add'" class="edit-provider">
            <config-textbox disabled v-model="currentProvider.name" label="Provider name" id="edit_provider_name" />
            <config-textbox v-model="currentProvider.config.url" label="Site Url" id="edit_provider_url" />
            <config-textbox type="password" v-model="currentProvider.config.apikey" label="Api key" id="edit_provider_api" />

            <config-template label="Categories" label-for="catids">
                <multiselect
                    :value="providerCatIds"
                    :multiple="true"
                    :options="availableCategories"
                    label="id"
                    track-by="id"
                    :taggable="true"
                    tag-placeholder="Add this as new cat id" placeholder="Search or add a cat id"
                    @tag="addTag"
                    @input="currentProvider.config.catIds = $event.map(cat => cat.id)"
                >
                    <template slot="option" slot-scope="props">
                        <span v-if="props.option.isTag"><strong>{{props.option.label}}</strong></span>
                        <span v-else><strong>{{props.option.id}}</strong> ({{props.option.name}})</span>
                    </template>

                </multiselect>
            </config-template>

            <button :disabled="currentProvider.default" class="btn-medusa btn-danger newznab_delete" id="newznab_delete" @click="removeProvider">Delete</button>
            <button class="btn-medusa config_submitter_refresh" @click="$emit('save')">Save Changes</button>

            <p class="manager-note" v-if="currentProvider.manager === 'prowlarr'">
                <img src="images/providers/prowlarr.png" style="width: 16px">
                Note! This is a provider configured through the 'Configure Custom Prowlarr Providers' tab.
            </p>
        </div>

        <!-- Add Provider -->
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
import { mapGetters, mapState } from 'vuex';
import { ADD_PROVIDER, REMOVE_PROVIDER } from '../../store/mutation-types';
import {
    ConfigTextbox,
    ConfigTemplate
} from '.';
import Multiselect from 'vue-multiselect';

export default {
    name: 'config-custom-newznab',
    components: {
        ConfigTextbox,
        ConfigTemplate,
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
        };
    },
    methods: {
        async save() {
            const { provider } = this;
            // Disable the save button until we're done.
            this.saving = true;

            try {
                await this.client.api.patch(`providers/${provider.id}`, provider.config);
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
            if (!currentProvider.name || !currentProvider.url || !currentProvider.config.apikey) {
                return;
            }

            try {
                const response = await this.client.api.post('providers/newznab/operation', {
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
                const response = await this.client.api.post('providers/newznab', { apikey, name, url });
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
                await this.client.api.delete(`providers/newznab/${currentProvider.id}`);
                this.$store.commit(REMOVE_PROVIDER, currentProvider.id);
                this.$snotify.success(
                    `Removed provider ${currentProvider.name}`,
                    'Removed',
                    { timeout: 5000 }
                );
                this.selectedProvider = '#add';
            } catch (error) {
                this.$snotify.error(
                    `Error while trying to remove provider ${currentProvider.name}`,
                    'Error'
                );
            }
        },
        /**
         * Add custom cat id's.
         * @param {string} newTag category id.
         */
        addTag(newTag) {
            if (!Number(newTag) || Number(newTag) < 1) {
                return;
            }
            const tag = { id: newTag, name: newTag };
            this.availableCategories.push(tag);
        }
    },
    computed: {
        ...mapState({
            providers: state => state.provider.providers,
            client: state => state.auth.client
        }),
        ...mapGetters(['providerNameToId']),
        newznabProviderOptions() {
            const { providers } = this;
            return providers.filter(prov => prov.subType === 'newznab').map(prov => {
                return ({ value: prov.id, text: prov.name });
            });
        },
        currentProvider() {
            const { providers, selectedProvider } = this;
            if (!selectedProvider) {
                return null;
            }
            return providers.find(prov => prov.id === selectedProvider);
        },
        providerCatIds() {
            const { currentProvider } = this;
            if (!currentProvider || currentProvider.config.catIds.length === 0) {
                return [];
            }

            // Check if we have a list of objects.
            if (currentProvider.config.catIds.every(x => typeof x === 'string')) {
                return currentProvider.config.catIds.map(cat => ({ id: cat, name: null }));
            }

            return currentProvider.config.catIds;
        },
        providerIdAvailable() {
            const { providerNameToId, providers, name } = this;
            return providers.filter(provider => providerNameToId(name) === provider.id).length === 0;
        }
    },
    watch: {
        currentProvider(newProvider, oldProvider) {
            if (newProvider && newProvider !== oldProvider) {
                this.getCategories();
            }
        }
    }
};
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

.manager-note {
    margin: 5px 0;
    padding: 10px;
    border: 1px solid #ccc;
}

.manager-note > img {
    width: 16px;
    padding-bottom: 4px;
}
</style>

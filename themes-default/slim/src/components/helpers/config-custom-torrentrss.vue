<template>
    <div id="custom-torrentrss">
        <config-template label-for="select_torrentrss_provider" label="Select Provider">
            <select id="select-provider" class="form-control input-sm max-input350" v-model="selectedProvider">
                <option value="#add">--- add new provider ---</option>
                <option :value="option.value" v-for="option in torrentrssProviderOptions" :key="option.value">
                    {{ option.text }}
                </option>
            </select>
        </config-template>

        <!-- Edit Provider -->
        <div v-if="currentProvider && selectedProvider !== '#add'" class="edit-provider">
            <config-textbox disabled v-model="currentProvider.name" label="Provider name" id="edit_provider_name" />
            <config-textbox v-model="currentProvider.config.url" label="Rss Url" id="edit_provider_url" />
            <config-textbox v-model="currentProvider.config.cookies.values" label="Cookies (optional)" id="edit_provider_cookies" />
            <config-textbox v-model="currentProvider.config.titleTag" label="Search element" id="edit_provider_search_element" />

            <button class="btn-medusa btn-danger torrentrss_delete" id="torrentrss_delete" @click="removeProvider">Delete</button>
            <button class="btn-medusa config_submitter_refresh" @click="$emit('save')">Save Changes</button>
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
            <config-textbox v-model="cookies" label="Cookies" id="add_provider_cookies" />
            <config-textbox v-model="searchElement" label="Search element" id="add_provider_search_element" />

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

export default {
    name: 'config-custom-torrentrss',
    components: {
        ConfigTextbox,
        ConfigTemplate
    },
    data() {
        return {
            saving: false,
            selectedProvider: '#add',
            name: '',
            url: '',
            cookies: '',
            searchElement: ''
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
        async addProvider() {
            const { name, url, cookies, searchElement } = this;
            try {
                const cookieValues = {
                    values: cookies
                };

                const response = await this.client.api.post('providers/torrentrss', {
                    name, url, cookies: cookieValues, titleTag: searchElement
                });
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
                    `Error while trying to add provider ${name}`,
                    'Error'
                );
            }
        },
        async removeProvider() {
            const { currentProvider } = this;
            try {
                await this.client.api.delete(`providers/torrentrss/${currentProvider.id}`);
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
        }
    },
    computed: {
        ...mapState({
            providers: state => state.provider.providers,
            client: state => state.auth.client
        }),
        ...mapGetters(['providerNameToId']),
        torrentrssProviderOptions() {
            const { providers } = this;
            return providers.filter(prov => prov.subType === 'torrentrss').map(prov => {
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
        providerIdAvailable() {
            const { providerNameToId, providers, name } = this;
            return providers.filter(provider => providerNameToId(name) === provider.id).length === 0;
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
</style>

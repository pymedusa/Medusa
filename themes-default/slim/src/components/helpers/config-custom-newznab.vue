<template>
    <div id="custom-newznab">
        <config-template label-for="select_newznab_provider" label="Select Provider">
            <select id="edit_a_provider" class="form-control input-sm" v-model="selectedProvider">
                <option value="#add">--- add new provider ---</option>
                <option :value="option.value" v-for="option in newznabProviderOptions" :key="option.value">
                    {{ option.text }}
                </option>
            </select>
        </config-template>

        <div v-if="currentProvider && selectedProvider !== '#add'" class="edit-provider">
            <config-textbox disabled v-model="currentProvider.name" label="Provider name" id="edit_provider_name" />
            <config-textbox disabled v-model="currentProvider.url" label="Site Url" id="edit_provider_url" />
            <config-textbox v-model="currentProvider.config.apikey" label="Api key" id="edit_provider_api" />
        
            <multiselect
                :value="providerCatIds"
                :multiple="true"
                :options="availableCategories"
                label="id"
                track-by="id"
                @input="currentProvider.config.catIds = $event"
            >
                <template slot="singleLabel" slot-scope="{ option }"><strong>{{ option.id }}</strong> ({{ option.name }})</template>
                <template slot="option" slot-scope="props">
                    <span><strong>{{props.option.id}}</strong> ({{props.option.name}})</span>
                </template>

            </multiselect>

        </div>

        <div v-if="selectedProvider === '#add'" class="add-provider">
            <config-textbox v-model="name" label="Provider name" id="add_provider_name" />
            <config-textbox v-model="url" label="Site Url" id="add_provider_url" />
            <config-textbox v-model="apikey" label="Api key" id="add_provider_api" />
        </div>

        
    </div>
</template>

<script>
import { api } from '../../api';
import { mapGetters, mapState } from 'vuex';
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
                const response = await api.post(`providers/newznab`, {
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

<style>

</style>
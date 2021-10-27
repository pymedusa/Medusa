<template>
    <div class="test-provider">
        <button class="btn-medusa config_submitter" @click="test">Test for results</button>
        <state-switch v-if="loading" state="loading" :theme="layout.themeName" />
        <span v-else v-show="testResult" class="testresult">{{testResult}}</span>
    </div>
</template>
<script>
import { mapState } from 'vuex';
import StateSwitch from './state-switch.vue';

export default {
    name: 'test-provider',
    components: {
        StateSwitch
    },
    props: {
        providerId: String,
        providerName: String
    },
    data() {
        return {
            testResult: '',
            loading: false
        };
    },
    computed: {
        ...mapState({
            layout: state => state.config.layout,
            client: state => state.auth.client
        })
    },
    methods: {
        async test() {
            const { providerId, providerName } = this;
            this.testResult = '';
            this.loading = true;
            try {
                const response = await this.client.api.post('providers/internal/operation', {
                    type: 'TESTPROVIDER', providerId
                })
                    .catch(error => {
                        if ([404, 401].includes(error.response.status)) {
                            throw new Error(error.response.data.error);
                        }
                        throw error;
                    });
                this.testResult = response.data;
            } catch (error) {
                this.testResult = error;
                this.$snotify.error(
                    `Error while trying to test provider ${providerName} for results`,
                    'Error'
                );
            } finally {
                this.loading = false;
            }
        }
    }
};
</script>
<style scoped>
.test-provider {
    float: left;
}

.test-provider > button {
    margin: 0 5px;
}

.testresult {
    border-style: solid;
    border-width: 1px;
    padding: 1px 4px 4px 4px;
    border-color: #ccc;
}
</style>

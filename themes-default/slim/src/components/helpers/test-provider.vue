<template>
    <div>
        <button class="btn-medusa config_submitter" @click="test">Test</button>
        <span v-show="testResult" class="testresult">{{testResult}}</span>
    </div>
</template>
<script>
import { api } from '../../api';

export default {
    name: 'test-provider',
    props: {
        providerId: {
            type: String,
            required: true
        }
    },
    data() {
        return {
            testResult: ''
        }
    },
    methods: {
        async test() {
            const { providerId } = this;
            this.testResult = '';
            try {
                const response = await api.post('providers/internal/operation', {
                    type: 'TESTPROVIDER', providerid: providerId
                });
                this.testResult = response.data;
            } catch (error) {
                this.testResult = 'could not connect';
                this.$snotify.error(
                    `Error while trying to test provider ${providerId} for results`,
                    'Error'
                );
            }
 
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

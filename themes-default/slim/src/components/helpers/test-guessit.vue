<template>
    <div>
        <div class="row">
            <div class="col-lg-12">
                <p>Guessit is a library used for parsing release names. As a minimum Medusa requires a show title, season and episode (if not parsed as a season pack).</p>
                <p>You can fill in your release name and click the `Test Release Name` button, to get the guessit response.</p>
            </div>
        </div>
        <div class="row">
            <div class="col-lg-2">
                <span>Release name:</span>
            </div>
            <div class="col-lg-10">
                <input type="text" class="form-control input-sm" v-model="releaseName">
            </div>
        </div>
        <div class="row">
            <div class="col-lg-12">
                <pre>{{JSON.stringify(guessitResult, undefined, 4)}}</pre>
            </div>
        </div>
        <button class="btn-medusa config_submitter" @click.prevent="testReleaseName">Test Release Name</button>
    </div>
</template>
<script>
import { api } from '../../api';

export default {
    name: 'test-guessit',
    data() {
        return {
            releaseName: '',
            guessitResult: {}
        };
    },
    methods: {
        /**
         * Send the release name to the /api/v2/guessit endpoint.
         */
        async testReleaseName() {
            const { releaseName } = this;
            try {
                const { data } = await api.get('guessit', { params: { release: releaseName } });
                this.guessitResult = data;
            } catch (error) {
                console.log('Woops');
            }
        }
    }
};
</script>
<style scoped>
pre {
    word-wrap: break-word;
}
</style>

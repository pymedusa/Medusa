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
        <div v-if="error" class="row">
            <div class="col-lg-12">
                <div class="error">{{error}}</div>
            </div>
        </div>

        <div v-if="show" class="row">
            <div class="col-lg-12 matched-show">
                <div>Matched to show:</div>
                <div><app-link :href="`home/displayShow?showslug=${show.id.slug}`">{{show.title}}</app-link></div>
            </div>
        </div>
        <button class="btn-medusa config_submitter" @click.prevent="testReleaseName">Test Release Name</button>
    </div>
</template>
<script>
import { mapState } from 'vuex';
import AppLink from './app-link.vue';

export default {
    name: 'test-guessit',
    components: {
        AppLink
    },
    data() {
        return {
            releaseName: '',
            guessitResult: {},
            show: null,
            error: null
        };
    },
    computed: {
        ...mapState({
            client: state => state.auth.client
        })
    },
    methods: {
        /**
         * Send the release name to the /api/v2/guessit endpoint.
         */
        async testReleaseName() {
            const { releaseName } = this;
            try {
                const { data } = await this.client.api.get('guessit', { params: { release: releaseName } });
                this.guessitResult = data.guess;
                this.show = data.show;
                this.error = data.error;
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

.error {
    width: 100%;
    padding: 0.5rem;
    background-color: red;
    font-weight: 700;
    border-radius: 2px;
    margin-bottom: 2rem;
}

.matched-show {
    display: flex;
    margin-bottom: 2rem;
}

.matched-show > div {
    margin-right: 2rem;
}
</style>

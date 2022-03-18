<template>
    <div id="changelog" v-html="changelog" />
</template>
<script>
import { mapState } from 'vuex';
/**
 * An object representing a restart component.
 * @typedef {Object} restart
 */
export default {
    name: 'changelog',
    data() {
        return {
            changelog: ''
        };
    },
    computed: {
        ...mapState({
            client: state => state.auth.client
        })
    },
    mounted() {
        this.getChangelog();
    },
    methods: {
        async getChangelog() {
            try {
                const { data } = await this.client.api.get('internal/getChangelog');
                this.changelog = data;
            } catch (error) {
                this.$snotify.warning('error', 'Error trying to get changelog');
            }
        }
    }
};
</script>
<style>
</style>

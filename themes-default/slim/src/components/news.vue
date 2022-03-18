<template>
    <div id="news" v-html="news" />
</template>
<script>
import { mapState } from 'vuex';
/**
 * An object representing a restart component.
 * @typedef {Object} restart
 */
export default {
    name: 'news',
    data() {
        return {
            news: ''
        };
    },
    computed: {
        ...mapState({
            client: state => state.auth.client
        })
    },
    mounted() {
        this.getNews();
    },
    methods: {
        async getNews() {
            try {
                const { data } = await this.client.api.get('internal/getNews');
                this.news = data;
            } catch (error) {
                this.$snotify.warning('error', 'Error trying to get news');
            }
        }
    }
};
</script>
<style>
</style>

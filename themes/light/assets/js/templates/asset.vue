<template>
    <img v-if="!link" :src="src" :class="cls" @error="error = true">
    <app-link v-else :href="href">
        <img :src="src" :class="cls" @error="error = true">
    </app-link>
</template>
<script>
import { webRoot, apiKey } from '../api';
import AppLink from './app-link.vue';

module.exports = {
    name: 'asset',
    components: {
        AppLink
    },
    props: {
        seriesSlug: String,
        type: {
            type: String,
            required: true
        },
        default: String,
        link: {
            type: Boolean,
            default: false
        },
        cls: String
    },
    data() {
        return {
            error: false
        };
    },
    computed: {
        src() {
            const { error, seriesSlug, type } = this;

            if (error || !seriesSlug || !type) {
                return this.default;
            }

            return webRoot + '/api/v2/series/' + seriesSlug + '/asset/' + type + '?api_key=' + apiKey;
        },
        href() {
            // Compute a link to the full asset, if applicable
            if (this.link) {
                return this.src.replace('Thumb', '');
            }
        }
    }
};
</script>
<style>
/* placeholder */
</style>

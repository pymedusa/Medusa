<template>
    <img v-if="!link" :src="src" :class="cls" @error="error = true">
    <app-link v-else :href="href">
        <img :src="src" :class="cls" @error="error = true">
    </app-link>
</template>
<script>
import { webRoot, apiKey } from '../../api';
import AppLink from './app-link.vue';

export default {
    name: 'asset',
    components: {
        AppLink
    },
    props: {
        showSlug: {
            type: String
        },
        type: {
            type: String,
            required: true
        },
        default: {
            type: String,
            required: true
        },
        link: {
            type: Boolean,
            default: false
        },
        cls: {
            type: String
        }
    },
    data() {
        return {
            error: false
        };
    },
    computed: {
        src() {
            const { error, showSlug, type } = this;

            if (error || !showSlug || !type) {
                return this.default;
            }

            return webRoot + '/api/v2/series/' + showSlug + '/asset/' + type + '?api_key=' + apiKey;
        },
        href() {
            // Compute a link to the full asset, if applicable
            if (this.link) {
                return this.src.replace('Thumb', '');
            }
            return undefined;
        }
    }
};
</script>
<style>

</style>

<template>
    <img v-if="!link" v-bind="{ src, class: cls, 'data-src': dataSrc, class: newCls }" @error="error = true">
    <app-link v-else :href="href">
        <img v-bind="{ src, class: cls, 'data-src': dataSrc, class: newCls }" @error="error = true">
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
        },
        imgWidth: {
            type: Number
        },
        lazy: {
            type: Boolean
        }
    },
    data() {
        return {
            error: false
        };
    },
    computed: {
        src() {
            const { lazy, error, showSlug, type } = this;

            if (error || !showSlug || !type) {
                return this.default;
            }

            if (!lazy) {
                return webRoot + '/api/v2/series/' + showSlug + '/asset/' + type + '?api_key=' + apiKey;
            }

            return this.default;
        },
        href() {
            // Compute a link to the full asset, if applicable
            if (this.link) {
                return this.src.replace('Thumb', '');
            }
            return undefined;
        },
        newCls() {
            const { cls, imgWidth } = this;
            let newClass = cls;

            if (imgWidth) {
                newClass += ` width-${imgWidth}`;
            }

            return newClass;
        },
        dataSrc() {
            const { lazy, error, showSlug, type } = this;

            if (error || !showSlug || !type) {
                return this.default;
            }

            if (lazy) {
                return webRoot + '/api/v2/series/' + showSlug + '/asset/' + type + '?api_key=' + apiKey;
            }

            return '';
        }
    }
};
</script>
<style scoped>
.width-40 {
    width: 40px;
}

.width-50 {
    width: 50px;
}
</style>

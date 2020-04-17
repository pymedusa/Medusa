<template>
    <div>
        <h1 v-if="header" class="header">{{ listTitle }}</h1>
        <component v-if="shows.length >= 1" :is="mappedLayout" v-bind="$props" />

        <span v-else>No shows were found for this list type.</span>
    </div>
</template>
<script>

import Banner from './banner.vue';
import Simple from './simple.vue';
import Poster from './poster.vue';
import Smallposter from './smallposter.vue';


export default {
    name: 'show-list',
    components: {
        Banner,
        Simple,
        Poster,
        Smallposter
    },
    props: {
        layout: {
            validator: layout => [
                null,
                '',
                'poster',
                'banner',
                'simple',
                'small'
            ].includes(layout),
            required: true
        },
        shows: {
            type: Array,
            required: true
        },
        listTitle: {
            type: String
        },
        header: {
            type: Boolean
        },
        sortArticle: {
            type: Boolean
        }
    },
    computed: {
        mappedLayout() {
            const { layout } = this;
            if (layout === 'small') {
                return 'smallposter';
            }
            return layout;
        }
    }
};
</script>
<style>
</style>

<template>
    <div>
        <h1 v-if="header" class="header">{{ listTitle }}</h1>
        <component v-if="shows.length >= 1" :is="layout" v-bind="$props" />
        <span v-else>No shows were found for this list type.</span>
    </div>
</template>
<script>

import Banner from './banner.vue';
import Simple from './simple.vue';
import Small from './small.vue';

export default {
    name: 'show-list',
    components: {
        Small,
        Banner,
        Simple
    },
    props: {
        layout: {
            validator: layout => [
                null,
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
    }
};
</script>
<style>
</style>

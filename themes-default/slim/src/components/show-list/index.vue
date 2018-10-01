<template>
    <div>
        <h1 v-if="header" class="header">{{ listTitle }}</h1>
        <component :is="layout" v-bind="$props" />
    </div>
</template>
<script>
import Banner from './banner.vue';
import Simple from './simple.vue';

export default {
    name: 'show-list',
    components: {
        Banner,
        Simple
    },
    props: {
        layout: {
            validator: layout => [
                null,
                '',
                'banner',
                'simple'
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
}
</script>

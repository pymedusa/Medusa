<template>
    <loader v-if="loading" type="square"></loader>
    <router-view v-else></router-view>
</template>

<script>
import {mapGetters} from 'vuex';

import navbar from './navbar.vue';
import loader from './loader.vue';

export default {
    name: 'App',
    head: {
        meta: [{
            name: 'theme-color',
            content: '#333333'
        }]
    },
    data() {
        return {
            loading: false
        };
    },
    mounted() {

    },
    computed: {
        ...mapGetters([
            'blogs'
        ])
    },
    components: {
        navbar,
        loader
    }
};
</script>

<style>
#app {
    font-family: 'Avenir', Helvetica, Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    text-align: center;
    color: #2c3e50;
    margin-top: 60px;
}
</style>

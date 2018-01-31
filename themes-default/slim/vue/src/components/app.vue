<template>
    <div id="app">
        <loader v-if="loading" type="square"></loader>
        <router-view v-else></router-view>
    </div>
</template>

<script>
import loader from './loader.vue';

export default {
    name: 'App',
    data() {
        return {
            loading: false
        };
    },
    methods: {
        stopLoading() {
            this.loading = !this.loading;
        }
    },
    components: {
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

<template>
    <div id="app">
        <loader type="square"></loader>
        <router-view></router-view>
    </div>
</template>

<script>
import loader from './components/loader.vue';

export default {
    name: 'App',
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

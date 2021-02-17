<template>
    <div id="app">
        <vue-snotify />
        <h1 v-if="$route.meta.header" class="header">{{ $route.meta.header }}</h1>
        <router-view :key="$route.meta.nocache ? $route.fullPath : $route.name" />
    </div>
</template>

<script>
export default {
    name: 'app'
};
</script>

<style>
/* Global style definitions should go here. */
</style>

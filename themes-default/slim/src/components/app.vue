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

<style lang="scss">
/* Global style definitions should go here. */
@use '../style/vgt-table.scss';
@use '../style/v-tooltip.scss';
@use '../style/modal.scss';
@use '../style/vue-tags.scss';
@use '../style/back-arrow.scss';
</style>

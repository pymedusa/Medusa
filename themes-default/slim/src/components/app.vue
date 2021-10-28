<template>
    <div v-if="isAuthenticated" id="app">
        <div id="content-row" class="row">
            <div id="content-col" :class="layout.wide ? 'col-lg-12 col-md-12' : 'col-lg-10 col-lg-offset-1 col-md-10 col-md-offset-1'">
                <vue-snotify />
                <app-header />
                <sub-menu />
                <alerts />
                <h1 v-if="$route.meta.header" class="header">{{ $route.meta.header }}</h1>
                <router-view :key="$route.meta.nocache ? $route.fullPath : $route.name" />
                <app-footer />
                <scroll-buttons />
            </div>
        </div><!-- /content -->
    </div>
</template>

<script>
import Alerts from './alerts.vue';
import AppHeader from './app-header.vue';
import SubMenu from './sub-menu.vue';
import AppFooter from './app-footer.vue';
import { ScrollButtons } from './helpers';

import { mapState } from 'vuex';

export default {
    name: 'app',
    components: {
        Alerts,
        AppFooter,
        AppHeader,
        ScrollButtons,
        SubMenu
    },
    computed: {
        ...mapState({
            isAuthenticated: state => state.auth.isAuthenticated,
            layout: state => state.config.layout
        })
    }
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

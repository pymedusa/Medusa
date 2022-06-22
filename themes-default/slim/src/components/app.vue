<template>
    <div id="app">
        <div v-if="isAuthenticated">
            <load-progress-bar v-if="showsLoading" v-bind="{display: showsLoading.display, current: showsLoading.current, total: showsLoading.total}" />
            <app-header />
            <sub-menu />
            <div id="content-row">
                <!-- <submenu-offset /> -->
                <div id="content-col" :class="layout.wide ? 'col-lg-12 col-md-12' : 'col-lg-10 col-lg-offset-1 col-md-10 col-md-offset-1'">
                    <vue-snotify />
                    <alerts />
                    <h1 v-if="$route.meta.header" class="header">{{ $route.meta.header }}</h1>
                    <keep-alive :exclude="excludeFromCaching">
                        <router-view :key="$route.meta.nocache ? `${$route.fullPath}` : $route.name" />
                    </keep-alive>
                    <app-footer />
                    <scroll-buttons />
                </div>
            </div><!-- /content -->
        </div>
        <div v-else>
            <!-- Only render for /login -->
            <router-view />
        </div>
    </div>
</template>

<script>
import Alerts from './alerts.vue';
import AppHeader from './app-header.vue';
import SubMenu from './sub-menu.vue';
import AppFooter from './app-footer.vue';
import { LoadProgressBar, ScrollButtons } from './helpers';

import { mapState } from 'vuex';

export default {
    name: 'app',
    components: {
        Alerts,
        AppFooter,
        AppHeader,
        LoadProgressBar,
        ScrollButtons,
        SubMenu
    },
    computed: {
        ...mapState({
            isAuthenticated: state => state.auth.isAuthenticated,
            layout: state => state.config.layout,
            showsLoading: state => state.shows.loading
        }),
        excludeFromCaching() {
            // Exclude components from caching, using their `name` option.
            return [
                'new-show',
                'new-show-existing',
                'news',
                'changelog',
                'status'
            ];
        }
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
@use '../style/spin.scss';

#app {
    padding-top: 4rem;
}

@media (max-width: 768px) {
    #app {
        padding-top: 3.8rem;
    }
}
</style>

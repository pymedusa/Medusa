<template>
    <div class="container-fluid">
        <loader v-if="loading" type="square"></loader>
        <template v-else>
            <navbar v-if="isAuthenticated"></navbar>
            <!-- % if submenu:
                /partials/submenu.mako
            % endif -->
            <!-- /partials/alerts.mako -->
           <div id="content-row" class="row">
                <div id="content-col" class="col-lg-10 col-lg-offset-1 col-md-10 col-md-offset-1 col-sm-12 col-xs-12">
                    <router-view></router-view>
                </div>
           </div>
           <stats-bar v-if="isAuthenticated"></stats-bar>
           <scroll-to v-if="isAuthenticated" :showIcon="true"></scroll-to>
        </template>
    </div>
</template>

<script>
import {mapGetters, mapActions} from 'vuex';

import navbar from './navbar.vue';
import statsBar from './stats-bar.vue';
import scrollTo from './scroll-to.vue';
import loader from './loader.vue';

export default {
    name: 'app',
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
        const vm = this;
        vm.loading = true;
        vm.checkAuth().then(() => {
            vm.getRecentShows().then(() => {
                vm.loading = false;
            }).catch(console.error);
        }).catch(console.error);
    },
    computed: {
        ...mapGetters([
            'allSeries',
            'config',
            'user',
            'userError',
            'isAuthenticated'
        ])
    },
    methods: {
        ...mapActions([
            'getRecentShows',
            'checkAuth'
        ])
    },
    components: {
        navbar,
        statsBar,
        scrollTo,
        loader
    }
};
</script>

<style>
@import "/css/vender.min.css";
@import "/css/bootstrap-formhelpers.min.css";
@import "/css/browser.css";
@import "/css/lib/jquery-ui-1.10.4.custom.min.css";
@import "/css/lib/jquery.qtip-2.2.1.min.css";
@import "/css/style.css";
/* The CSS below should be dependant on the theme */
@import "/css/dark.css";
@import "/css/print.css";
@import "/css/country-flags.css";

#content-row {
    margin-top: 51px;
}
</style>

<template>
    <loader v-if="loading" type="square"></loader>
    <router-view v-else></router-view>
</template>

<script>
import {mapGetters} from 'vuex';

import navbar from './navbar.vue';
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

    },
    computed: {
        ...mapGetters({
            series: 'allSeries'
        })
    },
    components: {
        navbar,
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
</style>

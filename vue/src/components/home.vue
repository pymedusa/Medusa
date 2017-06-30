<template>
    <div>
        <loader v-if="loading" type="square"></loader>
        <template v-else></template>
    </div>
</template>

<script>
import {mapActions, mapGetters} from 'vuex';

import loader from './loader.vue';

export default {
    name: 'home',
    data() {
        return {
            loading: true
        };
    },
    mounted() {
        const vm = this;
        vm.loading = true;
        vm.getAllSeries().then(() => {
            vm.loading = false;
        }).catch(console.error);
    },
    methods: {
        ...mapActions([
            'addSeries',
            'getAllSeries'
        ])
    },
    computed: {
        ...mapGetters([
            'allSeries'
        ])
    },
    components: {
        loader
    }
};
</script>

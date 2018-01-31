<template>
    <div>
        <loader v-if="loading" type="square"></loader>
        <template v-else>
            This is the homepage.<br>
            <form v-on:submit.prevent="submitSeries">
                <input v-model="series.id" type="text"></input>
                <input v-model="series.name" type="text"></input>
                <button>{{$t('series.add.new')}}</button>
            </form>
            <div v-for="series in allSeries">{{series}}</div>
        </template>
    </div>
</template>

<script>
import {mapActions, mapGetters} from 'vuex';

import loader from './loader.vue';

export default {
    name: 'Home',
    data() {
        return {
            series: {
                id: '',
                name: ''
            },
            loading: true
        };
    },
    mounted() {
        const vm = this;
        vm.getAllSeries().then(() => {
            vm.loading = false;
        });
    },
    methods: {
        ...mapActions([
            'addSeries',
            'getAllSeries'
        ]),
        submitSeries() {
            const vm = this;
            vm.addSeries({
                ...vm.series
            });
            vm.series = {};
        }
    },
    computed: {
        ...mapGetters([
            'allSeries',
            'seriesByName',
            'seriesById'
        ])
    },
    components: {
        loader
    }
};
</script>

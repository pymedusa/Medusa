<template>
    <div>
        This is the homepage.<br>
        <form v-on:submit.prevent="submitShow">
            <input v-model="show.id" type="text"></input>
            <input v-model="show.name" type="text"></input>
            <button>Add a show?</button>
        </form>
        <div v-for="show in shows">{{show}}</div>
    </div>
</template>

<script>
import { mapActions, mapGetters } from 'vuex'

export default {
    name: 'Home',
    data() {
        return {
            show: {
                id: '',
                name: ''
            }
        }
    },
    methods: {
        ...mapActions([
            'addShow'
        ]),
        submitShow() {
            const vm = this;
            vm.addShow({
                ...vm.show
            });
            vm.show = {};
        }
    },
    computed: {
        ...mapGetters({
            shows: 'allShows'
        }),
        ...mapGetters[
            'showByName',
            'showById'
        ]
    }
};
</script>

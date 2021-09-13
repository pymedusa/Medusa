<template>
    <div>
        <div class="row">
            <div class="col-lg-12">
                <span>{{checkedShows.length}} Shows selected</span>
                <div id="filter-indexers">
                    <label for="tvdb">tvdb<input type="checkbox" v-model="filter.tvdb" name="tvdb" id="tvdb"></label>
                    <label for="tvmaze">tvmaze<input type="checkbox" v-model="filter.tvmaze" name="tvmaze" id="tvmaze"></label>
                    <label for="tmdb">tmdb<input type="checkbox" v-model="filter.tmdb" name="tmdb" id="tmdb"></label>
                </div>
            </div>
        </div>
        <table class="defaultTable tablesorter">
            <thead>
                <th><input type="checkbox" id="select-all"></th>
                <th>Show</th>
                <th>current indexer</th>
                <th>new indexer</th>
            </thead>
            <tbody>
                <change-indexer-row
                    v-for="show in filteredShows"
                    :show="show" :key="show.id.slug"
                    @selected="showSelected"
                />
            </tbody>
        </table>
    </div>
</template>
<script>
import Vue from 'vue';
import { mapState } from 'vuex';
import { ChangeIndexerRow }  from './manage';

export default {
    name: 'change-indexer',
    components: {
        ChangeIndexerRow
    },
    data() {
        return {
            allShows: [],
            filter: {
                tvdb: true,
                tvmaze: true,
                tmdb: true
            }
        }
    },
    mounted() {
        const unwatchProp = this.$watch('shows', shows => {
            unwatchProp();
            this.allShows = shows;
        }, {
            immediate: true,
            deep: true
        });
    },
    computed: {
        ...mapState({
            shows: state => state.shows.shows
        }),
        checkedShows() {
            const { filteredShows } = this;
            return filteredShows.filter(show => show.checked);
        },
        filteredShows() {
            const { allShows, filter } = this;
            return allShows.filter(
                show =>
                show.indexer === 'tvdb' && filter.tvdb
                || show.indexer === 'tvmaze' && filter.tvmaze
                || show.indexer === 'tmdb' && filter.tmdb
            );
        }
    },
    methods: {
        selectAll(value) {
            const { filteredShows } = this;
            filteredShows.forEach(show => Vue.set(show, 'checked', value));
        },
        // An indexer/showId has been choosen.
        // Update 
        showSelected({show, indexer, showId}) {
            const { filteredShows } = this;
            Vue.set(filteredShows.find(s => s === show), 'selected', { indexer, showId });
        }
    },
}
</script>
<style scoped>
#filter-indexers {
    float: right;
}
</style>
<template>
    <div>
        <div class="row">
            <div class="col-lg-12">
                <span>{{checkedShows.length}} Shows selected</span>
                <button class="btn-medusa" :disabled="started" @click="start">Start</button>
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
                <th>status</th>
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
import { api } from '../api';
import Vue from 'vue';
import { mapState } from 'vuex';
import { ChangeIndexerRow } from './manage';

export default {
    name: 'manage-change-indexer',
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
            },
            started: false
        };
    },
    mounted() {
        if (this.shows.length > 0) {
            this.allShows = this.shows;
        } else {
            const unwatchProp = this.$watch('shows', shows => {
                unwatchProp();
                this.allShows = shows;
            });
        }
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
                    (show.indexer === 'tvdb' && filter.tvdb) ||
                    (show.indexer === 'tvmaze' && filter.tvmaze) ||
                    (show.indexer === 'tmdb' && filter.tmdb)
            );
        }
    },
    methods: {
        selectAll(value) {
            const { filteredShows } = this;
            filteredShows.forEach(show => Vue.set(show, 'checked', value));
        },
        // An indexer/showId has been choosen.
        showSelected({ show, indexer, showId }) {
            const { filteredShows } = this;
            Vue.set(filteredShows.find(s => s === show), 'selected', { indexer, showId });
        },
        /**
         * Start changing the shows indexer.
         */
        async start() {
            const { allShows } = this;
            for (const show of allShows.filter(show => show.checked && show.selected)) {
                // Loop through the shows and start a ChangeIndexerQueueItem for each.
                // Store the queueItem identifier, to keep track.
                const oldSlug = show.id.slug;
                const newSlug = `${show.selected.indexer}${show.selected.showId}`;
                if (oldSlug === newSlug) {
                    this.$snotify.warning(
                        'Old shows indexer and new shows indexer are the same, skipping',
                        'Error'
                    );
                    continue;
                }

                try {
                    this.started = true;
                    // eslint-disable-next-line no-await-in-loop
                    const { data } = await api.post('changeindexer', {
                        oldSlug, newSlug
                    });
                    Vue.set(allShows.find(s => s === show), 'changeStatus', {
                        identifier: data.identifier,
                        steps: []
                    });
                } catch (error) {
                    this.$snotify.warning(
                        'Error while trying to change shows indexer',
                        `Error: ${error}`
                    );
                }
            }
        }
    }
};
</script>
<style scoped>
#filter-indexers {
    float: right;
}
</style>

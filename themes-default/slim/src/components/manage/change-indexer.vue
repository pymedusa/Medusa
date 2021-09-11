<template>
    <div>
        <table class="defaultTable tablesorter">
            <thead>
                <th><input type="checkbox" id="select-all"></th>
                <th>Show</th>
                <th>current indexer</th>
                <th>new indexer</th>
            </thead>
            <tbody>
                <tr v-for="show in shows" :key="show.id.slug">
                    <td><input type="checkbox" :data-slug="show.id.slug"></td>
                    <td>{{show.name}}</td>
                    <td>{{show.indexer}}</td>
                    <td>
                        <select name="indexer">
                            <option v-if="show.indexer !== 'tvdb' && show.externals.tvdb" :value="show.externals.tvdb">tvdb</option>
                            <option v-if="show.indexer !== 'tmdb' && show.externals.tmdb" :value="show.externals.tmdb">tmdb</option>
                            <option v-if="show.indexer !== 'tvmaze' && show.externals.tvmaze" :value="show.externals.tvmaze">tvmaze</option>
                        </select>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
</template>
<script>
import { mapState } from 'vuex';

export default {
    name: 'change-indexer',
    computed: {
        ...mapState({
            shows: state => state.shows.shows
        })
    }
}
</script>
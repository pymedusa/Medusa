<template>
    <div>
        <app-link :href="`https://www.imdb.com/title/${show.imdbInfo.imdbId}`" :title="`https://www.imdb.com/title/${show.imdbInfo.imdbId}`">
            <img alt="[imdb]" height="16" width="16" src="images/imdb16.png" style="margin-top: -1px; vertical-align:middle;">
        </app-link>

        <app-link v-if="show.id.trakt" :href="`https://trakt.tv/shows/${show.id.trakt}`" :title="`https://trakt.tv/shows/${show.id.trakt}`">
            <img alt="[trakt]" height="16" width="16" src="images/trakt.png">
        </app-link>

        <app-link v-if="show.xemNumbering && show.xemNumbering.length > 0" :href="`http://thexem.de/search?q=${show.title}`" :title="`http://thexem.de/search?q=${show.title}`">
            <img alt="[xem]" height="16" width="16" src="images/xem.png" style="margin-top: -1px; vertical-align:middle;">
        </app-link>

        <app-link v-if="show.id.tvdb" :href="`https://fanart.tv/series/${show.id.tvdb}`" :title="`https://fanart.tv/series/${show.id.tvdb}`">
            <img alt="[fanart.tv]" height="16" width="16" src="images/fanart.tv.png" class="fanart">
        </app-link>

    </div>

</template>

<script>
import { AppLink } from '.';

export default {
    name: 'externals',
    components: {
        AppLink
    },
    props: {
        show: Object
    },
    computed: {
        externals() {
            const { show } = this;
            debugger;
            
            return show.externals;
        }
    }
};
</script>

<style>
</style>

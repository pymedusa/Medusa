<template>
    <div class="external-ids">
        <span> - </span>
        <app-link v-if="externals.imdb && show.imdbInfo" :href="`https://www.imdb.com/title/${show.imdbInfo.imdbId}`" :title="`https://www.imdb.com/title/${show.imdbInfo.imdbId}`">
            <img alt="[imdb]" height="16" width="16" src="images/imdb16.png" style="margin-top: -1px; vertical-align:middle;">
        </app-link>

        <app-link v-if="externals.trakt" :href="`https://trakt.tv/shows/${externals.trakt}`" :title="`https://trakt.tv/shows/${externals.trakt}`">
            <img alt="[trakt]" height="16" width="16" src="images/trakt.png">
        </app-link>

        <app-link v-if="externals.tvdb" :href="`https://www.thetvdb.com/dereferrer/series/${externals.tvdb}`" :title="`https://www.thetvdb.com/dereferrer/series/${externals.tvdb}`">
            <img alt="[tvdb]" height="16" width="16" src="images/thetvdb16.png">
        </app-link>

        <app-link v-if="externals.tvmaze" :href="`https://www.tvmaze.com/shows/${externals.tvmaze}`" :title="`https://www.tvmaze.com/shows/${externals.tvmaze}`">
            <img alt="[tvmaze]" height="16" width="16" src="images/tvmaze16.png">
        </app-link>

        <app-link v-if="externals.tmdb" :href="`https://www.themoviedb.org/tv/${externals.tmdb}`" :title="`https://www.themoviedb.org/tv/${externals.tmdb}`">
            <img alt="[tmdb]" height="16" width="16" src="images/tmdb16.png">
        </app-link>

        <app-link v-if="show.xemNumbering && show.xemNumbering.length > 0" :href="`http://thexem.de/search?q=${show.title}`" :title="`http://thexem.de/search?q=${show.title}`">
            <img alt="[xem]" height="16" width="16" src="images/xem.png" style="margin-top: -1px; vertical-align:middle;">
        </app-link>

        <app-link v-if="externals.tvdb" :href="`https://fanart.tv/series/${externals.tvdb}`" :title="`https://fanart.tv/series/${externals.tvdb}`">
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
            if (!show || !show.externals || !Object.keys(show.externals).length === 0) {
                return {};
            }

            delete show.externals[show.indexer];
            return show.externals;
        }
    }
};
</script>

<style>
.external-ids {
    display: inline-block;
}

.external-ids > * {
    margin-left: 2px;
}
</style>

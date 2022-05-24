<template>
    <div class="calendar-wrapper" :class="{fanartOpacity: layout.fanartBackgroundOpacity}">
        <div class="wrap-center">
            <div class="day-column" v-for="day in groupedSchedule" :key="day.airdate">
                <span class="day-header" :title="day.airdate ? `airs ${day.airdate}` : 'No shows for this day'">{{day.header}}</span>
                <ul v-if="day.episodes.length > 0">
                    <li v-for="episode in day.episodes" :key="`${episode.showSlug}${episode.episodeSlug}`" class="calendar-show">
                        <div class="poster">
                            <app-link :title="episode.showName" :href="`home/displayShow?showslug=${episode.showSlug}`">
                                <asset default-src="images/poster.png" :show-slug="episode.showSlug" type="posterThumb" :link="false" />
                            </app-link>
                        </div>
                        <div class="text">
                            <span class="airtime">
                                {{fuzzyParseTime(episode.localAirTime, false)}} on {{episode.network}}
                            </span>
                            <span class="episode-title" :title="episode.epName">
                                {{episode.episodeSlug}} - {{episode.epName}}
                            </span>
                        </div>
                    </li>
                </ul>
                <ul v-else>
                    <li class="calendar-show">
                        <div class="text">
                            <span class="airtime">No shows for this day</span>
                        </div>
                    </li>
                </ul>
            </div>
        </div>
    </div>
</template>
<script>
import { mapGetters, mapState } from 'vuex';
import { AppLink, Asset } from '../helpers';

export default {
    name: 'calendar',
    components: {
        AppLink,
        Asset
    },
    computed: {
        ...mapState({
            layout: state => state.config.layout,
            general: state => state.config.general
        }),
        ...mapGetters([
            'groupedSchedule',
            'fuzzyParseTime'
        ])
    }
};
</script>

<style scoped>
.shows-today {
    background-color: rgb(245, 241, 228);
}

.shows-soon {
    background-color: rgb(221, 255, 221);
}

.shows-missed {
    background-color: rgb(255, 221, 221);
}

.shows-later {
    background-color: rgb(190, 222, 237);
}

ul {
    margin: 0;
    padding: 0;
}

ul > li {
    list-style: none;
}

.calendar-wrapper {
    display: flex;
    justify-content: center;
}

.wrap-center {
    display: flex;
    flex-direction: row;
    flex-wrap: wrap;

    --column-width: 15rem;
    --poster-height: 22rem;
}

.day-column {
    display: block;
    width: var(--column-width);
    color: rgb(0, 0, 0);
    margin-bottom: 2rem;
}

.calendar-show .text {
    padding: 3px 5px 10px;
    width: var(--column-width);
}

.day-header {
    display: block;
    text-align: center;
    border-collapse: collapse;
    font-weight: normal;
    padding: 4px;
    height: 3rem;
}

.calendar-show .poster >>> img {
    width: var(--column-width);
    height: var(--poster-height);
}

.calendar-show .text .airtime,
.calendar-show .text .episode-title {
    overflow: hidden;
    text-overflow: ellipsis;
    display: block;
    font-size: 11px;
    white-space: nowrap;
}
</style>

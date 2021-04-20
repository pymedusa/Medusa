<template>
    <div class="calendar-wrapper" :class="{fanartOpacity: layout.fanartBackgroundOpacity}">
        <div class="wrap-center">
            <div class="day-column" v-for="day in sortedEpisodes" :key="day.header">
                <span class="day-header">{{day.header}}</span>
                <ul v-if="day.episodes.length > 0">
                    <li v-for="episode in day.episodes" :key="episode.episodeSlug" class="calendar-show">
                        <div class="poster">
                            <app-link :title="episode.showName" :href="`home/displayShow?showslug=${episode.showSlug}`">
                                <asset default-src="images/poster.png" :show-slug="episode.showSlug" type="posterThumb" :link="false" />
                            </app-link>
                        </div>
                        <div class="text">
                            <span class="airtime">
                                {{episode.airsTime}} on {{episode.network}}
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
        <backstretch :slug="general.randomShowSlug" />
    </div>
</template>
<script>
import { mapGetters, mapState } from 'vuex';
import { AppLink, Asset, ProgressBar, QualityPill } from '../helpers';
import BannerCard from './banner-card.vue';
import Backstretch from '../backstretch.vue';

export default {
    name: 'calendar',
    components: {
        AppLink,
        Asset,
        Backstretch,
        BannerCard,
        ProgressBar,
        QualityPill
    },
    computed: {
        ...mapState({
            layout: state => state.config.layout,
            general: state => state.config.general,
            later: state => state.schedule.later,
            missed: state => state.schedule.missed,
            soon: state => state.schedule.soon,
            today: state => state.schedule.today,
            consts: state => state.config.consts,
            displayPaused: state => state.config.layout.comingEps.displayPaused,
            sort: state => state.config.layout.comingEps.sort
        }),
        ...mapGetters([
            'getScheduleFlattened',
            'fuzzyParseDateTime'
        ]),
        filteredSchedule() {
            const { displayPaused, getScheduleFlattened } = this;
            return getScheduleFlattened.filter(item => !Boolean(item.paused) || displayPaused);
        },
        /**
         * Group the coming episodes into an array of objects with an attibute header (the week day) 
         * and an attribute episodes with an array of coming episodes.
         */
        sortedEpisodes() {
            const { displayPaused, soon, today } = this;
            const days = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
            
            /* Return an array of the days to come */
            const comingDays = (currentDay, nrComingDays) => {
                let returnDays = [];
                for (let i=0; i < nrComingDays; i++) {
                    returnDays.push(currentDay)
                    if (currentDay > 5) {
                        currentDay = 0;
                    } else {
                        currentDay += 1;
                    }
                }
                return returnDays;
            }
            const newArray = [];

            const filteredSoon = soon.filter(item => !Boolean(item.paused) || displayPaused);
            if (filteredSoon.length === 0) {
                 return [];
            }
            
            let currentDay = filteredSoon[0].weekday;

            // Group the coming episodes by day.
            for (const episode of filteredSoon) {
                
                // Calculate the gaps in the week, for which we don't have any scheduled shows.
                if (currentDay !== episode.weekday) {
                    const diffDays = episode.weekday - currentDay;
                    if (diffDays > 1) {
                        for (const emptyDay of comingDays(currentDay, diffDays).slice(-1)) {
                            newArray.push({
                                header: days[emptyDay],
                                class: 'shows-soon',
                                episodes: []
                            });
                        }
                        currentDay = episode.weekday + 1;
                        continue;
                    }
                }
                
                currentDay = episode.weekday

                let weekDay = newArray.find(item => item.header === days[episode.weekday]);
                if (!weekDay) {
                    weekDay = {
                        header: days[episode.weekday],
                        class: 'shows-soon',
                        episodes: []
                    }
                    newArray.push(weekDay);
                }

                episode.airsTime = episode.airs.split(' ').slice(-2).join(' ');
                weekDay.episodes.push(episode);
            }
            return newArray;
        }
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
    flex-direction: column;
    --column-width: 15rem;
    --poster-max-height: 22rem;
    --background-text-grey: rgb(210, 210, 210);
}

.wrap-center {
    display:flex;
}

.day-column {
    display: block;
    color: rgb(0, 0, 0);
}

.calendar-show .text {
    padding: 3px 5px 10px;
    color: rgb(136, 136, 136);
    background-color: var(--background-text-grey);
}

.day-header {
    display: block;
    color: rgb(255, 255, 255);
    text-align: center;
    text-shadow: -1px -1px 0 rgb(0 0 0 / 30%);
    background-color: rgb(51, 51, 51);
    border-collapse: collapse;
    font-weight: normal;
    padding: 4px;
    border-top: rgb(255, 255, 255) 1px solid;
    border-bottom: rgb(255, 255, 255) 1px solid;
    height: 3rem;
} 

.calendar-show .poster >>> img {
    width: 100%;
    height: auto;
}

.calendar-show .text .airtime {
    color: rgb(0, 0, 0);
}

.calendar-show .text .episode-title {
    color: rgb(136, 136, 136);
}

.calendar-show .text .airtime,
.calendar-show .text .episode-title {
    overflow: hidden;
    text-overflow: ellipsis;
    display: block;
    font-size: 11px;
    white-space: nowrap;
}

@media (min-width: 767px) {
    .wrap-center {
        flex-direction: row;
    }

    .day-column {
        width: var(--column-width);
    }

    .calendar-show .poster >>> img {
        width: var(--column-width);
        max-height: var(--poster-max-height);
    }

    .calendar-show .text {
        width: var(--column-width);
    }
}
</style>

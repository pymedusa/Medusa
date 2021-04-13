<template>
<div class="banner-wrapper">
    <template v-if="sort === 'show'">
        <banner-card v-for="episode in filteredSchedule.sort((a, b) => a.showName.localeCompare(b.showName))"
                     :key="`${episode.showSlug}${episode.episodeSlug}`" :episode="episode"
                     :class="`shows-${episode.category}`"
        />
    </template>
    <!-- For the sort by date and network options -->
    <template v-else>
        <div  v-for="group in sortedEpisodes" :key="group.header">
            <!-- Coming shows are grouped per week day -->
            <h2 class="day">{{group.header}}</h2>
            <banner-card v-for="episode in group.episodes"
                         :key="`${episode.showSlug}${episode.episodeSlug}`" :episode="episode"
                         :class="`shows-${episode.category}`"
            />
        </div>
    </template>
    </div>
</div>

</template>
<script>
import { mapGetters, mapState } from 'vuex';
import { AppLink, ProgressBar, QualityPill, Search } from '../helpers';
import BannerCard from './banner-card.vue';

export default {
    name: 'banner',
    components: {
        AppLink,
        BannerCard,
        ProgressBar,
        QualityPill
    },
    computed: {
        ...mapState({
            layout: state => state.config.layout,
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
            const { displayPaused, filteredSchedule, missed, soon, today, sort} = this;
            const days = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
            const newArray = [];

            if (sort === 'date') {
                // Group missed episodes (one group)
                newArray.push({
                    header: 'missed',
                    class: 'shows-missed',
                    episodes: missed.filter(item => !Boolean(item.paused) || displayPaused)
                });
                
                // Group missed episodes (one group)
                newArray.push({
                    header: 'today',
                    class: 'shows-today',
                    episodes: today.filter(item => !Boolean(item.paused) || displayPaused)
                });

                // Group the coming episodes by day.
                for (const episode of soon.filter(item => !Boolean(item.paused) || displayPaused)) {
                    let weekDay = newArray.find(item => item.header === days[episode.weekday]);
                    if (!weekDay) {
                        weekDay = {
                            header: days[episode.weekday],
                            class: 'shows-soon',
                            episodes: []
                        }
                        newArray.push(weekDay);
                    }
                    weekDay.episodes.push(episode);
                }

                // Group missed episodes (one group)
                newArray.push({
                    header: 'later',
                    class: 'shows-later',
                    episodes: today.filter(item => !Boolean(item.paused) || displayPaused)
                });
                return newArray;
            }

            if (sort === 'network') {
                for (const episode of filteredSchedule.sort((a, b) => a.network.localeCompare(b.network))) {
                    let network = newArray.find(item => item.header === episode.network);
                    if (!network) {
                        network = {
                            header: episode.network,
                            class: `shows-${episode.category}`,
                            episodes: []
                        }
                        newArray.push(network);
                    }
                    network.episodes.push(episode);
                }
                return newArray;
            }
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
</style>

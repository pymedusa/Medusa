<template>
    <div class="banner-wrapper">
        <template v-if="sort === 'show'">
            <banner-card v-for="episode in filteredSchedule.slice().sort((a, b) => a.showName.localeCompare(b.showName))"
                         :key="`${episode.showSlug}${episode.episodeSlug}`" :episode="episode"
                         :class="`shows-${episode.class}`" layout="poster"
            />
        </template>
        <!-- For the sort by date and network options -->
        <template v-else>
            <div  v-for="group in sortedSchedule(sort)" :key="group.header">
                <!-- Coming shows are grouped per week day -->
                <h2 class="day">{{group.header}}</h2>
                <banner-card v-for="episode in group.episodes"
                             :key="`${episode.showSlug}${episode.episodeSlug}`" :episode="episode"
                             :class="`shows-${group.class}`" layout="poster"
                />
            </div>
        </template>
    </div>
</template>
<script>
import { mapGetters, mapState } from 'vuex';
import BannerCard from './banner-card.vue';

export default {
    name: 'poster',
    components: {
        BannerCard
    },
    computed: {
        ...mapState({
            layout: state => state.config.layout,
            displayPaused: state => state.config.layout.comingEps.displayPaused,
            sort: state => state.config.layout.comingEps.sort
        }),
        ...mapGetters([
            'getScheduleFlattened',
            'sortedSchedule'
        ]),
        filteredSchedule() {
            const { displayPaused, getScheduleFlattened } = this;
            return getScheduleFlattened.filter(item => !item.paused || displayPaused);
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

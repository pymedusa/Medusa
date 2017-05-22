<template>
    <footer>
        <div class="footer clearfix">
            <span class="highlight">{{allSeries.length}}</span> Series (<span class="highlight">{{seriesActive.length}}</span> Active) | <span class="highlight">${ep_downloaded}</span>
            <template v-if="stats.episodes.snatched">
                <a class="highlight" href="manage/episodeStatuses?whichStatus=2" title="View overview of snatched episodes">+${ep_snatched}</a> Snatched /
                <span class="highlight">${ep_total}</span> Episodes Downloaded ${ep_percentage}
            </template>
            Daily Search: <span class="highlight">${str(daily_search_scheduler.timeLeft()).split('.')[0]}</span> |
            Backlog Search: <span class="highlight">${str(backlog_search_scheduler.timeLeft()).split('.')[0]}</span> |
            <div>
            <template v-if="stats.memoryUsage">
                Memory used: <span class="highlight">{{stats.memoryUsage}}</span> |
            </template>
                Load time: <span class="highlight">${"%.4f" % (time() - sbStartTime)}s</span> |
                Branch: <span class="highlight">{{config.branch}}</span> |
                Now: <span class="highlight">${datetime.now().strftime(DATE_PRESET+" "+TIME_PRESET)}</span>
            </div>
        </div>
    </footer>
</template>

<script>
import {mapGetters} from 'vuex';

export default {
    name: 'stats-bar',
    data() {
        return {
            stats: {
                memoryUsage: null,
                episodes: {
                    snatched: null
                }
            }
        };
    },
    computed: {
        ...mapGetters([
            'config',
            'allSeries',
            'seriesEnded',
            'seriesActive'
        ])
    }
};
</script>

<style scoped>
.highlight {
    color: rgb(9, 162, 255);
    display: inline;
}
</style>

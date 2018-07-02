<template>
    <footer>
        <div class="footer clearfix">
            <span class="footerhighlight">{{ stats.overall.shows.total }}</span> Shows (<span class="footerhighlight">{{ stats.overall.shows.active }}</span> Active)
            | <span class="footerhighlight">{{ stats.overall.episodes.downloaded }}</span>
            <template v-if="stats.overall.episodes.snatched">
                <span class="footerhighlight"><app-link :href="`manage/episodeStatuses?whichStatus=${snatchedStatus}`" title="View overview of snatched episodes">+{{ stats.overall.episodes.snatched }}</app-link></span>
                Snatched
            </template>
            / <span class="footerhighlight">{{ stats.overall.episodes.total }}</span> Episodes Downloaded <span v-if="episodePercentage" class="footerhighlight">({{ episodePercentage }})</span>
            | Daily Search: <span class="footerhighlight">{{ nextDailySearch }}</span>
            | Backlog Search: <span class="footerhighlight">{{ nextBacklogSearch }}</span>
            <div>
                <template v-if="system.memoryUsage">
                Memory used: <span class="footerhighlight">{{ system.memoryUsage }}</span> |
                </template>
                <!-- Load time: <span class="footerhighlight">{{ loadTime }}s</span> / Mako: <span class="footerhighlight">{{ makoTime }}s</span> | -->
                Branch: <span class="footerhighlight">{{ config.branch || 'Unknown' }}</span> |
                Now: <span class="footerhighlight">{{ nowInUserPreset }}</span>
            </div>
        </div>
    </footer>
</template>

<script>
import { mapGetters, mapState } from 'vuex';
import formatDate from 'date-fns/format';

import { convertDateFormat } from '../utils/core';
import { AppLink } from './helpers';

export default {
    name: 'app-footer',
    components: {
        AppLink
    },
    computed: {
        ...mapState([
            'config',
            'stats',
            'system'
        ]),
        ...mapGetters([
            'getStatus',
            'getScheduler'
        ]),
        snatchedStatus() {
            const status = this.getStatus({ key: 'snatched' });
            return status ? status.value : '';
        },
        episodePercentage() {
            const { downloaded, total } = this.stats.overall.episodes;
            if (!total) {
                return '';
            }
            const raw = (downloaded / total) * 100;
            return raw.toFixed(1) + '%';
        },
        nowInUserPreset() {
            const { datePreset, timePreset } = this.config;
            const preset = convertDateFormat(`${datePreset} ${timePreset}`);
            return formatDate(new Date(), preset);
        },
        nextDailySearch() {
            const dailySearchScheduler = this.getScheduler('dailySearch');
            const { nextRun } = dailySearchScheduler || {};
            if (nextRun === undefined) {
                return '??:??:??';
            }
            return this.formatTimeDuration(nextRun);
        },
        nextBacklogSearch() {
            const backlogScheduler = this.getScheduler('backlog');
            const { nextRun } = backlogScheduler || {};
            if (nextRun === undefined) {
                return '??:??:??';
            }
            return this.formatTimeDuration(nextRun);
        }
    },
    methods: {
        formatTimeDuration(durationInMs) {
            const days = parseInt(durationInMs / 86400000, 10);
            let daysText = '';
            if (days > 0) {
                daysText = String(days) + (days > 1 ? ' days, ' : ' day, ');
            }

            const date = new Date(durationInMs % 86400000);
            const zeroPad = (num, len = 2) => String(num).padStart(len, '0');
            const hours = String(date.getUTCHours());
            const minutes = zeroPad(date.getUTCMinutes());
            const seconds = zeroPad(date.getUTCSeconds() + Math.round(date.getUTCMilliseconds() / 1000));
            return daysText + [hours, minutes, seconds].join(':');
        }
    }
};
</script>

<style scoped>
</style>

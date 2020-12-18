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
            | Daily Search: <span class="footerhighlight">{{ schedulerNextRun('dailySearch') }}</span>
            | Backlog Search: <span class="footerhighlight">{{ schedulerNextRun('backlog') }}</span>
            <div>
                <template v-if="system.memoryUsage">
                    Memory used: <span class="footerhighlight">{{ system.memoryUsage }}</span> |
                </template>
                <!-- Load time: <span class="footerhighlight">{{ loadTime }}s</span> / Mako: <span class="footerhighlight">{{ makoTime }}s</span> | -->
                Branch: <span class="footerhighlight">{{ system.branch || 'Unknown' }}</span> |
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
        ...mapState({
            layout: state => state.config.layout,
            system: state => state.config.system,
            stats: state => state.stats
        }),
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
            const { dateStyle, timeStyle } = this.layout;
            const preset = convertDateFormat(`${dateStyle} ${timeStyle}`);
            return formatDate(new Date(), preset);
        }
    },
    methods: {
        /**
         * Return a formatted next run time of the scheduler matching the provided key.
         *
         * @param {string} scheduler A scheduler key.
         * @returns {string} The formatted next run time.
         */
        schedulerNextRun(scheduler) {
            /** @type {import('../store/modules/system').Scheduler} */
            const { nextRun } = this.getScheduler(scheduler);
            // The next run can be `undefined` when the scheduler was not initialized
            // on the backend, and `null` when the scheduler is not enabled.
            if (nextRun === undefined) {
                return '??:??:??';
            }
            if (nextRun === null) {
                return 'Disabled';
            }
            return this.formatTimeDuration(nextRun);
        },
        /**
         * Return a formatted string representing the provided duration.
         *
         * This function will not use any units greater than a day.
         * @param {number} durationInMs Duration of time in milliseconds.
         * @returns {string} The formatted duration.
         *
         * @example
         */
        formatTimeDuration(durationInMs) {
            const days = Number.parseInt(durationInMs / 86400000, 10);
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

<template>
    <div id="schedule-template">
        <div class="row">
            <div class="col-md-12">
                <div class="key pull-left">
                    <template v-if="scheduleLayout !== 'calendar'">
                        <b>Key:</b>
                        <span class="listing-key listing-overdue">Missed</span>
                        <span class="listing-key listing-current">Today</span>
                        <span class="listing-key listing-default">Soon</span>
                        <span class="listing-key listing-toofar">Later</span>
                    </template>
                    <app-link class="btn-medusa btn-inline forceBacklog" :href="`webcal://${location.hostname}:${location.port}/calendar`">
                    <i class="icon-calendar icon-white"></i>Subscribe</app-link>
                </div>

                <div class="pull-right">
                    <div class="show-option">
                        <span>Show Paused:
                            <toggle-button :width="45" :height="22" v-model="layout.comingEps.displayPaused" sync />
                        </span>
                    </div>
                    <div class="show-option">
                        <span>Layout:
                            <select v-model="scheduleLayout" name="layout" class="form-control form-control-inline input-sm show-layout">
                                <option :value="option.value" v-for="option in layoutOptions" :key="option.value">{{ option.text }}</option>
                            </select>
                        </span>
                    </div>
                    <!-- Calendar sorting is always by date -->
                    <div v-if="!['calendar', 'list'].includes(scheduleLayout)" class="show-option">
                        <span>Sort By:
                            <select v-model="layout.comingEps.sort" name="sort" class="form-control form-control-inline input-sm">
                                <option value="date">Date</option>
                                <option value="network">Network</option>
                                <option value="show">Show</option>
                            </select>
                        </span>
                    </div>
                </div>
            </div>
        </div>

        <component :is="scheduleLayout" v-bind="$props" />

    </div>
</template>

<script>
import { mapActions, mapState } from 'vuex';
import { AppLink } from './helpers';
import { ToggleButton } from 'vue-js-toggle-button';
import List from './schedule/list.vue';
import Banner from './schedule/banner.vue';
import Poster from './schedule/poster.vue';

export default {
    name: 'schedule',
    components: {
        AppLink,
        Banner,
        Poster,
        List,
        ToggleButton
    },
    data() {
        return {
            layoutOptions: [
                { value: 'poster', text: 'Poster' },
                { value: 'calendar', text: 'Calendar' },
                { value: 'banner', text: 'Banner' },
                { value: 'list', text: 'List' }
            ]
        };
    },
    computed: {
        ...mapState({
            general: state => state.config.general,
            // Renamed because of the computed property 'layout'.
            layout: state => state.config.layout
        }),
        scheduleLayout: {
            get() {
                const { layout } = this;
                return layout.schedule;
            },
            set(layout) {
                const { setLayout } = this;
                const page = 'schedule';
                setLayout({ page, layout });
            }
        },
        themeSpinner() {
            const { layout } = this;
            return layout.themeName === 'dark' ? '-dark' : '';
        },
        /**
         * Wrapper to get access to window.location in template.
         */
        location() {
            return location;
        }
    },
    mounted() {
        // $store.dispatch('getShows');

        this.$root.$once('loaded', () => {
            const { scheduleLayout, layout, themeSpinner } = this;
            const { comingEps } = layout;
            if (scheduleLayout === 'list') {
                const sortCodes = {
                    date: 0,
                    show: 2,
                    network: 5
                };
                const { sort } = comingEps;
                const sortList = (sort in sortCodes) ? [[sortCodes[sort], 0]] : [[0, 0]];

                $('#showListTable:has(tbody tr)').tablesorter({
                    widgets: ['stickyHeaders', 'filter', 'columnSelector', 'saveSort'],
                    sortList,
                    textExtraction: {
                        0: node => $(node).find('time').attr('datetime'),
                        1: node => $(node).find('time').attr('datetime'),
                        7: node => $(node).find('span').text().toLowerCase(),
                        8: node => $(node).find('a[data-indexer-name]').attr('data-indexer-name')
                    },
                    headers: {
                        0: { sorter: 'realISODate' },
                        1: { sorter: 'realISODate' },
                        2: { sorter: 'loadingNames' },
                        4: { sorter: 'loadingNames' },
                        7: { sorter: 'quality' },
                        8: { sorter: 'text' },
                        9: { sorter: false, filter: false }
                    },
                    widgetOptions: {
                        filter_columnFilters: true, // eslint-disable-line camelcase
                        filter_hideFilters: true, // eslint-disable-line camelcase
                        filter_saveFilters: true, // eslint-disable-line camelcase
                        columnSelector_mediaquery: false // eslint-disable-line camelcase
                    }
                });

                $.ajaxEpSearch();
            }

            if (['banner', 'poster'].includes(scheduleLayout)) {
                $.ajaxEpSearch({
                    size: 16,
                    loadingImage: `loading16${themeSpinner}.gif`
                });
                $('.ep_summary').hide();
                $('.ep_summaryTrigger').on('click', function() {
                    $(this).next('.ep_summary').slideToggle('normal', function() {
                        $(this).prev('.ep_summaryTrigger').prop('src', function(i, src) {
                            return $(this).next('.ep_summary').is(':visible') ? src.replace('plus', 'minus') : src.replace('minus', 'plus');
                        });
                    });
                });
            }

            $('#popover').popover({
                placement: 'bottom',
                html: true, // Required if content has HTML
                content: '<div id="popover-target"></div>'
            }).on('shown.bs.popover', () => { // Bootstrap popover event triggered when the popover opens
                // call this function to copy the column selection code into the popover
                $.tablesorter.columnSelector.attachTo($('#showListTable'), '#popover-target');
            });
        });

        // Vue stuff
        const { getSchedule } = this;
        getSchedule();
    },
    methods: {
        ...mapActions({
            setLayout: 'setLayout',
            getSchedule: 'getSchedule'
        })
    }
};
</script>

<style scoped>
/* Also defined in style.css and dark.css, but i'm overwriting for light and dark, because the schedule table has coloring. */
td.tvShow a {
    color: rgb(0, 0, 0);
    text-decoration: none;
}

td.tvShow a:hover {
    cursor: pointer;
    color: rgb(66, 139, 202);
}
</style>

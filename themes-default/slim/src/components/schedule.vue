<template>
    <div id="schedule-template">
        <div class="row">
            <div class="col-md-12">
                <div class="filters pull-left">
                    <label for="checkbox-missed">
                        <div class="missed">
                            <input id="checkbox-missed" type="checkbox" v-model="displayCategory.missed">
                            missed
                        </div>
                    </label>
                    <label for="checkbox-today">
                        <div class="today">
                            <input id="checkbox-today" type="checkbox" v-model="displayCategory.today">
                            today
                        </div>
                    </label>
                    <label for="checkbox-soon">
                        <div class="soon">
                            <input id="checkbox-soon" type="checkbox" v-model="displayCategory.soon">
                            soon
                        </div>
                    </label>
                    <label for="checkbox-later">
                        <div class="later">
                            <input id="checkbox-later" type="checkbox" v-model="displayCategory.later">
                            later
                        </div>
                    </label>
                </div>

                <div class="pull-left">
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
import Calendar from './schedule/calendar.vue';

export default {
    name: 'schedule',
    components: {
        AppLink,
        Banner,
        Calendar,
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
            ],
            displayMissed: false,
            displayToday: true,
            displaySoon: true,
            displayLater: false
        };
    },
    computed: {
        ...mapState({
            general: state => state.config.general,
            // Renamed because of the computed property 'layout'.
            layout: state => state.config.layout,
            displayCategory: state => state.schedule.displayCategory
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

.filters {
    color: rgb(0, 0, 0);
    margin: -2px 5px;
}

.filters > label {
    display: block;
    float: left;

}

.filters div {
    padding: 5px 5px 2px 3px;
}

.filters div:active {
    transform: translateY(2px);
}

.filters .today {
    background-color: rgb(245, 241, 228);
}

.filters .soon {
    background-color: rgb(221, 255, 221);
}

.filters .missed {
    background-color: rgb(255, 221, 221);
}

.filters .later {
    background-color: rgb(190, 222, 237);
}
</style>

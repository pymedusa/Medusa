<template>
    <div id="schedule-template">
        <div class="row">
            <div class="col-md-12">
                <div class="filters pull-left">
                    <label for="checkbox-missed">
                        <div class="missed">
                            <input id="checkbox-missed" type="checkbox" :checked="displayCategory.missed" @change="storeDisplayCategory('missed', $event.currentTarget.checked)">
                            missed
                        </div>
                    </label>
                    <label for="checkbox-today">
                        <div class="today">
                            <input id="checkbox-today" type="checkbox" :checked="displayCategory.today" @change="storeDisplayCategory('today', $event.currentTarget.checked)">
                            today
                        </div>
                    </label>
                    <label for="checkbox-soon">
                        <div class="soon">
                            <input id="checkbox-soon" type="checkbox" :checked="displayCategory.soon" @change="storeDisplayCategory('soon', $event.currentTarget.checked)">
                            soon
                        </div>
                    </label>
                    <label for="checkbox-later">
                        <div class="later">
                            <input id="checkbox-later" type="checkbox" :checked="displayCategory.later" @change="storeDisplayCategory('later', $event.currentTarget.checked)">
                            later
                        </div>
                    </label>
                </div>

                <div class="pull-left subscribe">
                    <app-link class="btn-medusa btn-inline forceBacklog" :href="`webcal://${location.hostname}:${location.port}/calendar`">
                        <i class="icon-calendar icon-white" />
                        Subscribe
                    </app-link>
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
        <backstretch :slug="general.randomShowSlug" />
    </div>
</template>

<script>
import { mapActions, mapMutations, mapState } from 'vuex';
import { AppLink } from './helpers';
import { ToggleButton } from 'vue-js-toggle-button';
import List from './schedule/list.vue';
import Banner from './schedule/banner.vue';
import Poster from './schedule/poster.vue';
import Calendar from './schedule/calendar.vue';
import { manageCookieMixin } from '../mixins/manage-cookie';
import Backstretch from './backstretch.vue';

export default {
    name: 'schedule',
    components: {
        AppLink,
        Backstretch,
        Banner,
        Calendar,
        Poster,
        List,
        ToggleButton
    },
    mixins: [
        manageCookieMixin('schedule')
    ],
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
            displayCategory: state => state.schedule.displayCategory,
            categories: state => state.schedule.categories
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
         * @returns {object} - returns window.location object.
         */
        location() {
            return location;
        }
    },
    mounted() {
        const { getSchedule } = this;
        getSchedule();

        // Get the enabled/disabled categories from cookies.
        const { categories, getCookie, setDisplayCategory } = this;
        for (const category of categories) {
            const storedCat = getCookie(category);
            if (storedCat !== null) {
                setDisplayCategory({ category, value: storedCat });
            }
        }
    },
    methods: {
        ...mapActions({
            setLayout: 'setLayout',
            getSchedule: 'getSchedule'
        }),
        ...mapMutations({
            setDisplayCategory: 'setDisplayCategory'
        }),
        storeDisplayCategory(category, value) {
            const { setDisplayCategory, setCookie } = this;
            // Store value in cookie, and then call the action.
            setCookie(category, value);
            setDisplayCategory({ category, value });
        }
    }
};
</script>

<style scoped>
.subscribe {
    margin: 9px 5px 0 5px;
}

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
    margin-top: 5px;
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
    color: rgb(130, 111, 48);
}

.filters .soon {
    background-color: rgb(221, 255, 221);
    color: rgb(41, 87, 48);
}

.filters .missed {
    background-color: rgb(255, 221, 221);
    color: rgb(137, 0, 0);
}

.filters .later {
    background-color: rgb(190, 222, 237);
    color: rgb(29, 80, 104);
}
</style>

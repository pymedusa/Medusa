import { ADD_SCHEDULE } from '../mutation-types';

const state = {
    categories: ['later', 'missed', 'soon', 'today'],
    later: [],
    missed: [],
    soon: [],
    today: [],
    displayCategory: {
        later: false,
        missed: false,
        soon: true,
        today: true
    }
};

const mutations = {
    [ADD_SCHEDULE](state, schedule) {
        for (const category in schedule) { // eslint-disable-line guard-for-in
            state[category] = schedule[category];
        }
    },
    setDisplayCategory(state, { category, value }) {
        state.displayCategory[category] = value;
    }
};

const getters = {
    getScheduleFlattened: state => {
        const flattendedSchedule = [];
        const { categories, displayCategory } = state;
        for (const category of categories) {
            if (!displayCategory[category]) {
                continue;
            }

            const episodes = state[category];
            for (const episode of episodes) {
                episode.class = category;
            }
            flattendedSchedule.push(...episodes);
        }
        return flattendedSchedule;
    },
    /**
     * Group the coming episodes into an array of objects with an attibute header (the week day)
     * and an attribute episodes with an array of coming episodes.
     * @param {object} state - local state object.
     * @param {object} getters - local getters object.
     * @param {object} rootState - root state object.
     * @returns {array} - Array of grouped episodes by header.
     */
    groupedSchedule: (state, getters, rootState) => {
        const { missed, soon, today, later, displayCategory } = state;
        const { displayPaused } = rootState.config.layout.comingEps;

        const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

        /* Return an array of the days to come */
        const comingDays = (currentDay, nrComingDays) => {
            let currentDayOfTheWeek = currentDay.getDay();
            const returnDays = [];
            for (let i = 0; i < nrComingDays; i++) {
                if (currentDayOfTheWeek > 7) {
                    currentDayOfTheWeek = 1;
                }
                returnDays.push(currentDayOfTheWeek);
                currentDayOfTheWeek += 1;
            }
            return returnDays;
        };

        const _MS_PER_DAY = 1000 * 60 * 60 * 24;

        // A and b are javascript Date objects
        function dateDiffInDays(a, b) {
            // Discard the time and time-zone information.
            const utc1 = Date.UTC(a.getFullYear(), a.getMonth(), a.getDate());
            const utc2 = Date.UTC(b.getFullYear(), b.getMonth(), b.getDate());

            return Math.floor((utc2 - utc1) / _MS_PER_DAY);
        }

        const newArray = [];
        const combinedEpisodes = [];

        if (displayCategory.missed) {
            combinedEpisodes.push(...missed);
        }

        if (displayCategory.today) {
            combinedEpisodes.push(...today);
        }

        if (displayCategory.soon) {
            combinedEpisodes.push(...soon);
        }

        if (displayCategory.later) {
            combinedEpisodes.push(...later);
        }

        const filteredEpisodes = combinedEpisodes.filter(item => !item.paused || displayPaused);
        if (filteredEpisodes.length === 0) {
            return [];
        }

        let currentDay = new Date(filteredEpisodes[0].airdate);

        // Group the coming episodes by day.
        for (const episode of filteredEpisodes) {
            // Calculate the gaps in the week, for which we don't have any scheduled shows.
            if (currentDay !== new Date(episode.airdate)) {
                const diffDays = dateDiffInDays(currentDay, new Date(episode.airdate));
                if (diffDays > 1) {
                    let dayHeader = days[comingDays(currentDay, diffDays)[1] - 1];

                    // Add the elipses if there is a wider gap then 1 day.
                    if (diffDays > 2) {
                        dayHeader = `${dayHeader} ...`;
                    }

                    newArray.push({
                        header: dayHeader,
                        class: 'soon',
                        episodes: []
                    });
                }
            }

            currentDay = new Date(episode.airdate);

            let weekDay = newArray.find(item => item.airdate === episode.airdate);
            if (!weekDay) {
                weekDay = {
                    airdate: episode.airdate,
                    header: days[episode.weekday],
                    class: 'soon',
                    episodes: []
                };
                newArray.push(weekDay);
            }

            episode.airsTime = episode.airs.split(' ').slice(-2).join(' ');
            weekDay.episodes.push(episode);
        }
        return newArray;
    },
    /**
     * Group and sort the coming episodes into an array of objects with an attibute header (the week day).
     * Group the coming episodes into groups of missed, today, soon (subgrouped per day) and later.
     * @param {object} state - local state object.
     * @param {object} getters - local getters object.
     * @param {object} rootState - root state object.
     * @returns {array} - Array of grouped episodes by header.
     */
    sortedSchedule: (state, getters, rootState) => sort => {
        const {
            displayCategory,
            missed, today, soon, later
        } = state;
        const { displayPaused } = rootState.config.layout.comingEps;
        const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
        const newArray = [];

        if (sort === 'date') {
            if (displayCategory.missed) {
                // Group missed episodes (one group)
                newArray.push({
                    header: 'missed',
                    class: 'missed',
                    episodes: missed.filter(item => !item.paused || displayPaused)
                });
            }

            if (displayCategory.today) {
                // Group missed episodes (one group)
                newArray.push({
                    header: 'today',
                    class: 'today',
                    episodes: today.filter(item => !item.paused || displayPaused)
                });
            }

            if (displayCategory.soon) {
                // Group the coming episodes by day.
                for (const episode of soon.filter(item => !item.paused || displayPaused)) {
                    let weekDay = newArray.find(item => item.header === days[episode.weekday]);
                    if (!weekDay) {
                        weekDay = {
                            header: days[episode.weekday],
                            class: 'soon',
                            episodes: []
                        };
                        newArray.push(weekDay);
                    }
                    weekDay.episodes.push(episode);
                }
            }

            if (displayCategory.later) {
                // Group later episodes (one group)
                newArray.push({
                    header: 'later',
                    class: 'later',
                    episodes: later.filter(item => !item.paused || displayPaused)
                });
            }
            return newArray;
        }

        if (sort === 'network') {
            const { getScheduleFlattened } = getters;
            const filteredSchedule = getScheduleFlattened.filter(item => !item.paused || displayPaused);

            for (const episode of filteredSchedule.sort((a, b) => a.network.localeCompare(b.network))) {
                let network = newArray.find(item => item.header === episode.network);
                if (!network) {
                    network = {
                        header: episode.network,
                        class: episode.class,
                        episodes: []
                    };
                    newArray.push(network);
                }
                network.episodes.push(episode);
            }
            return newArray;
        }
    }
};

/**
 * An object representing request parameters for getting a show from the API.
 *
 * @typedef {object} ShowGetParameters
 * @property {boolean} detailed Fetch detailed information? (e.g. scene/xem numbering)
 * @property {boolean} episodes Fetch seasons & episodes?
 */

const actions = {
    /**
     * Get show schedule from API and commit it to the store.
     *
     * @param {*} context The store context.
     * @param {ShowIdentifier&ShowGetParameters} parameters Request parameters.
     * @returns {Promise} The API response.
     */
    async getSchedule({ rootState, commit, state }) {
        const params = {
            category: state.categories,
            paused: true
        };
        const response = await rootState.auth.client.api.get('/schedule', { params });
        if (response.data) {
            commit(ADD_SCHEDULE, response.data);
        }
    }
};

export default {
    state,
    mutations,
    getters,
    actions
};

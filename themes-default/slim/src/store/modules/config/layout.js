import { ADD_CONFIG, UPDATE_LAYOUT_LOCAL } from '../../mutation-types';
import formatDate from 'date-fns/format';
import parseISO from 'date-fns/parseISO';
import TimeAgo from 'javascript-time-ago';
import en from 'javascript-time-ago/locale/en';

import { convertDateFormat, divmod } from '../../../utils/core';

// Add locale-specific relative date/time formatting rules.
TimeAgo.addDefaultLocale(en);

const state = {
    show: {
        specials: null,
        showListOrder: [],
        pagination: {
            enable: null
        }
    },
    home: null,
    selectedRootIndex: null,
    history: null,
    historyLimit: null,
    schedule: null,
    wide: null,
    timezoneDisplay: null,
    timeStyle: null,
    dateStyle: null,
    themeName: null,
    splitHomeInTabs: null,
    animeSplitHome: null,
    fanartBackground: null,
    fanartBackgroundOpacity: null,
    trimZero: null,
    sortArticle: null,
    fuzzyDating: null,
    comingEps: {
        missedRange: null,
        sort: null,
        displayPaused: null,
        layout: null
    },
    backlogOverview: {
        status: null,
        period: null
    },
    posterSortdir: null,
    posterSortby: null,
    // Local config store properties, are saved to.
    local: {
        showFilterByName: '',
        posterSize: 188,
        currentShowTab: null
    }
};

const mutations = {
    [ADD_CONFIG](state, { section, config }) {
        if (section === 'layout') {
            state = Object.assign(state, config);
        }
    },
    [UPDATE_LAYOUT_LOCAL](state, local) {
        state.local = { ...state.local, ...local };
    }
};

const getters = {
    fuzzyParseDateTime: state => (airDate, showSeconds = false) => {
        const timeAgo = new TimeAgo('en-US');
        const { dateStyle, fuzzyDating, timeStyle } = state;

        if (!airDate || !dateStyle) {
            return '';
        }

        if (fuzzyDating) {
            return timeAgo.format(new Date(airDate));
        }

        if (dateStyle === '%x') {
            return new Date(airDate).toLocaleString();
        }

        // Only the history page should show seconds.
        const formatTimeStyle = showSeconds ? timeStyle : timeStyle.replace(':%S', '');
        const fdate = parseISO(airDate);
        return formatDate(fdate, convertDateFormat(`${dateStyle} ${formatTimeStyle}`));
    },
    fuzzyParseTime: state => (airDate, showSeconds = false) => {
        const timeAgo = new TimeAgo('en-US');
        const { dateStyle, fuzzyDating, timeStyle } = state;

        if (!airDate || !dateStyle) {
            return '';
        }

        if (timeStyle === '%x') {
            return new Date(airDate).toLocaleTimeString();
        }

        if (fuzzyDating) {
            return timeAgo.format(new Date(airDate));
        }

        // Only the history page should show seconds.
        const formatTimeStyle = showSeconds ? timeStyle : timeStyle.replace(':%S', '');
        const fdate = parseISO(airDate);
        return formatDate(fdate, convertDateFormat(formatTimeStyle));
    },
    getShowFilterByName: state => {
        return state.local.showFilterByName;
    },
    /**
     * PrettyTimeDelta
     *
     * Translate seconds into a pretty hours, minutes, seconds representation.
     * @param {object} state - State object.
     * @returns {number} seconds - Number of seconds to translate.
     */
    prettyTimeDelta: state => seconds => { // eslint-disable-line no-unused-vars
        let signStr = '';
        if (seconds < 0) {
            signStr = '-';
        }

        let days = 0;
        let hours = 0;
        let minutes = 0;

        const daysSeconds = divmod(seconds, 86400);
        days = daysSeconds.quotient;
        seconds = daysSeconds.remainder;

        const hoursSeconds = divmod(seconds, 3600);
        hours = hoursSeconds.quotient;
        seconds = hoursSeconds.remainder;

        const minuteSeconds = divmod(seconds, 60);
        minutes = minuteSeconds.quotient;
        seconds = minuteSeconds.remainder;

        if (days > 0) {
            signStr += ` ${days}d`;
        }

        if (hours > 0) {
            signStr += ` ${hours}h`;
        }

        if (minutes > 0) {
            signStr += ` ${minutes}m`;
        }

        if (seconds > 0) {
            signStr += ` ${seconds}s`;
        }

        return signStr;
    }
};

const actions = {
    setLayout({ rootState, commit }, { page, layout }) {
        // Don't wait for the api, just commit to store.
        commit(ADD_CONFIG, {
            section: 'layout', config: { [page]: layout }
        });

        return rootState.auth.client.api.patch('config/main', { layout: { [page]: layout } });
    },
    setTheme({ rootState, commit }, { themeName }) {
        return rootState.auth.client.api.patch('config/main', { layout: { themeName } })
            .then(() => {
                return commit(ADD_CONFIG, {
                    section: 'layout', config: { themeName }
                });
            });
    },
    setSpecials({ rootState, commit, state }, specials) {
        const show = Object.assign({}, state.show);
        show.specials = specials;

        return rootState.auth.client.api.patch('config/main', { layout: { show } })
            .then(() => {
                return commit(ADD_CONFIG, {
                    section: 'layout', config: { show }
                });
            });
    },
    setPosterSortBy({ rootState, commit }, { value }) {
        return rootState.auth.client.api.patch('config/main', { layout: { posterSortby: value } })
            .then(() => {
                return commit(ADD_CONFIG, {
                    section: 'layout', config: { posterSortby: value }
                });
            });
    },
    setPosterSortDir({ rootState, commit }, { value }) {
        return rootState.auth.client.api.patch('config/main', { layout: { posterSortdir: value } })
            .then(() => {
                return commit(ADD_CONFIG, {
                    section: 'layout', config: { posterSortdir: value }
                });
            });
    },
    setLayoutShow({ rootState, commit }, value) {
        return rootState.auth.client.api.patch('config/main', { layout: { show: value } })
            .then(() => {
                return commit(ADD_CONFIG, {
                    section: 'layout', config: { show: value }
                });
            });
    },
    setStoreLayout({ rootState, commit }, { key, value }) {
        return rootState.auth.client.api.patch('config/main', { layout: { [key]: value } })
            .then(() => {
                return commit(ADD_CONFIG, {
                    section: 'layout', config: { [key]: value }
                });
            });
    },
    setLayoutLocal(context, { key, value }) {
        const { commit } = context;
        return commit(UPDATE_LAYOUT_LOCAL, { [key]: value });
    },
    setBacklogOverview({ rootState, commit, state }, { key, value }) {
        const backlogOverview = { ...state.backlogOverview };
        backlogOverview[key] = value;
        commit(ADD_CONFIG, {
            section: 'layout', config: { backlogOverview }
        });
        return rootState.auth.client.api.patch('config/main', { layout: { backlogOverview } });
    }
};

export default {
    state,
    mutations,
    getters,
    actions
};

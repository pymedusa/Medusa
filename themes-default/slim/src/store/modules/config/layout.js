import { ADD_CONFIG, UPDATE_LAYOUT_LOCAL } from '../../mutation-types';
import { api } from '../../../api';
import formatDate from 'date-fns/format';
import parseISO from 'date-fns/parseISO';
import TimeAgo from 'javascript-time-ago';
import en from 'javascript-time-ago/locale/en';

import { convertDateFormat } from '../../../utils/core';

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

        if (!airDate) {
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
    getShowFilterByName: state => {
        return state.local.showFilterByName;
    }

};

const actions = {
    setLayout(context, { page, layout }) {
        const { commit } = context;
        // Don't wait for the api, just commit to store.
        commit(ADD_CONFIG, {
            section: 'layout', config: { [page]: layout }
        });

        return api.patch('config/main', { layout: { [page]: layout } });
    },
    setTheme(context, { themeName }) {
        const { commit } = context;
        return api.patch('config/main', { layout: { themeName } })
            .then(() => {
                return commit(ADD_CONFIG, {
                    section: 'layout', config: { themeName }
                });
            });
    },
    setSpecials(context, specials) {
        const { commit, state } = context;
        const show = Object.assign({}, state.show);
        show.specials = specials;

        return api.patch('config/main', { layout: { show } })
            .then(() => {
                return commit(ADD_CONFIG, {
                    section: 'layout', config: { show }
                });
            });
    },
    setPosterSortBy(context, { value }) {
        const { commit } = context;
        return api.patch('config/main', { layout: { posterSortby: value } })
            .then(() => {
                return commit(ADD_CONFIG, {
                    section: 'layout', config: { posterSortby: value }
                });
            });
    },
    setPosterSortDir(context, { value }) {
        const { commit } = context;
        return api.patch('config/main', { layout: { posterSortdir: value } })
            .then(() => {
                return commit(ADD_CONFIG, {
                    section: 'layout', config: { posterSortdir: value }
                });
            });
    },
    setLayoutShow(context, value) {
        const { commit } = context;
        return api.patch('config/main', { layout: { show: value } })
            .then(() => {
                return commit(ADD_CONFIG, {
                    section: 'layout', config: { show: value }
                });
            });
    },
    setStoreLayout(context, { key, value }) {
        const { commit } = context;
        return api.patch('config/main', { layout: { [key]: value } })
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
    setBacklogOverview(context, { key, value }) {
        const { commit } = context;
        return api.patch('config/main', { layout: { backlogOverview: { [key]: value } } })
            .then(() => {
                return commit(ADD_CONFIG, {
                    section: 'layout', config: { backlogOverview: { [key]: value } }
                });
            });
    }
};

export default {
    state,
    mutations,
    getters,
    actions
};

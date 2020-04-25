import { ADD_CONFIG } from '../mutation-types';
import { api } from '../../api';
import formatDate from 'date-fns/format';
import parseISO from 'date-fns/parseISO';
import TimeAgo from 'javascript-time-ago';
import timeAgoLocalEN from 'javascript-time-ago/locale/en';

import { convertDateFormat } from '../../utils/core';

// Add locale-specific relative date/time formatting rules.
TimeAgo.addLocale(timeAgoLocalEN);

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
    animeSplitHomeInTabs: null,
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
    posterFilterByName: '',
    posterSortdir: null,
    posterSortby: null,
    posterSize: 188
};

const mutations = {
    [ADD_CONFIG](state, { section, config }) {
        if (section === 'layout') {
            state = Object.assign(state, config);
        }
    }
};

const getters = {
    fuzzyParseDateTime: state => airDate => {
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

        const fdate = parseISO(airDate);
        return formatDate(fdate, convertDateFormat(`${dateStyle} ${timeStyle}`));
    },
    posterFilterByName: (state) => {
        return state.posterFilterByName;
    }

};

const actions = {
    setLayout(context, { page, layout }) {
        const { commit } = context;
        return api.patch('config/main', { layout: { [page]: layout } })
            .then(() => {
                return commit(ADD_CONFIG, {
                    section: 'layout', config: { [page]: layout }
                });
            });
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
    setPosterFilterByName(context, { filter }) {
        const { commit } = context;
        return commit(ADD_CONFIG, {
            section: 'layout', config: { posterFilterByName: filter } 
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
    setPosterSize(context, { posterSize }) {
        const { commit } = context;
        return commit(ADD_CONFIG, {
            section: 'layout', config: { posterSize }
        });
    },
    setShowListOrder(context, { value }) {
        const { commit } = context;
        return api.patch('config/main', { layout: { show: { showListOrder: value } } })
            .then(() => {
                return commit(ADD_CONFIG, {
                    section: 'layout', config: { show: { showListOrder: value } }
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
    }
};

export default {
    state,
    mutations,
    getters,
    actions
};

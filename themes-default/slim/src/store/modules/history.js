import Vue from 'vue';
import { ADD_HISTORY, ADD_HISTORY_ROW, ADD_SHOW_HISTORY, ADD_SHOW_EPISODE_HISTORY } from '../mutation-types';
import { episodeToSlug } from '../../utils/core';

const DEFAULT_HISTORY_PER_PAGE = 25;

const state = {
    remote: {
        rows: [],
        totalRows: 0,
        page: 1,
        perPage: DEFAULT_HISTORY_PER_PAGE,
        sort: [{
            field: 'date',
            type: 'desc'
        }],
        filter: null
    },
    remoteCompact: {
        rows: [],
        totalRows: 0,
        page: 1,
        perPage: DEFAULT_HISTORY_PER_PAGE,
        sort: [{
            field: 'date',
            type: 'desc'
        }],
        filter: null
    },
    episodeHistory: {},
    historyLast: null,
    historyLastCompact: null,
    loading: false,
    historyActive: false,
    historySortInitialized: false,
    historyPaginationInitialized: false,
    historyRequestIds: {
        detailed: 0,
        compact: 0
    },
    episodeFilter: {
        inputValue: '',
        filterValue: '',
        malformed: false,
        initialized: false
    }
};

const historyFilter = remote => remote.filter && remote.filter.columnFilters ? remote.filter.columnFilters : {};

const setResourceFilter = (remote, value, resetPage = true) => {
    const nextFilter = Object.assign({}, remote.filter || {}, {
        columnFilters: Object.assign({}, historyFilter(remote), {
            resource: value
        })
    });
    Vue.set(remote, 'filter', nextFilter);
    if (resetPage) {
        Vue.set(remote, 'page', 1);
    }
};

const compactHistoryFilters = resource => resource ? { resource } : {};

const positiveHistoryPerPage = value => {
    const canConvert = typeof value === 'number' || (typeof value === 'string' && value.trim() !== '');
    if (!canConvert) {
        return null;
    }
    const numericValue = Number(value);
    return Number.isFinite(numericValue) && numericValue > 0 ? numericValue : null;
};

const initialHistoryPerPage = (remote, value) => positiveHistoryPerPage(value) || positiveHistoryPerPage(remote.perPage) || DEFAULT_HISTORY_PER_PAGE;

const defaultHistorySort = () => [{ field: 'actionDate', type: 'desc' }];

const normalizeInitialHistorySort = sort => {
    let sortEntries = defaultHistorySort();
    if (Array.isArray(sort)) {
        sortEntries = sort;
    } else if (sort) {
        sortEntries = [sort];
    }
    return sortEntries.map(entry => {
        if (!entry || typeof entry !== 'object' || entry.field !== 'date') {
            return entry;
        }
        return Object.assign({}, entry, { field: 'actionDate' });
    });
};

const mapHistorySort = sort => {
    const sortEntry = Array.isArray(sort) ? sort[0] : sort;
    if (!sortEntry || !['asc', 'desc'].includes(sortEntry.type)) {
        return defaultHistorySort();
    }
    let field = null;
    if (['date', 'actionDate'].includes(sortEntry.field)) {
        field = 'actionDate';
    } else if (sortEntry.field === 'quality') {
        field = 'quality';
    }
    return field ? [{ field, type: sortEntry.type }] : defaultHistorySort();
};

const hasTrackedHistoryQuery = args => args && !args.showSlug && ['page', 'perPage', 'sort', 'filter'].every(key => {
    return Object.prototype.hasOwnProperty.call(args, key);
});

const historyLayoutKey = compact => compact ? 'compact' : 'detailed';

const serializeHistoryQuery = ({ page, perPage, sort, filter, compact }) => JSON.stringify({
    page,
    perPage,
    sort,
    filter,
    compact: Boolean(compact)
});

const currentHistoryQuery = (state, compact) => {
    const remote = compact ? state.remoteCompact : state.remote;
    return serializeHistoryQuery({
        page: remote.page,
        perPage: remote.perPage,
        sort: remote.sort,
        filter: remote.filter,
        compact
    });
};

const isCurrentHistoryRequest = (state, { compact, tracked, requestId, querySnapshot }) => {
    return !tracked || (
        state.historyRequestIds[historyLayoutKey(compact)] === requestId &&
        currentHistoryQuery(state, compact) === querySnapshot
    );
};

const lastHistoryPage = (total, perPage) => {
    if (!Number.isFinite(total) || !Number.isFinite(perPage) || perPage <= 0) {
        return null;
    }
    return Math.max(1, Math.ceil(total / perPage));
};

const applyHistoryResponse = async ({ response, args, page, compact, showSlug, tracked, state, commit, dispatch, requestId, querySnapshot }) => {
    if (!isCurrentHistoryRequest(state, { compact, tracked, requestId, querySnapshot })) {
        return;
    }
    const total = Number(response.headers['x-pagination-count']);
    commit('setRemoteTotal', { total, compact });
    const lastPage = tracked ? lastHistoryPage(total, Number(args.perPage)) : null;
    if (tracked && lastPage !== null && Number(page) > lastPage) {
        commit('setRemotePage', { page: lastPage, compact });
        await dispatch('getHistory', Object.assign({}, args, { page: lastPage })); // eslint-disable-line no-await-in-loop
    } else if (showSlug) {
        commit(ADD_SHOW_HISTORY, { showSlug, history: response.data, compact });
    } else {
        commit(ADD_HISTORY, { history: response.data, compact });
    }
};

const mutations = {
    [ADD_HISTORY_ROW](state, { history, compact }) {
        // Only evaluate compact once.
        const historyKey = compact ? 'remoteCompact' : 'remote';

        // Update state, add one item at the top.
        state[historyKey].rows.unshift(history);
    },
    [ADD_HISTORY](state, { history, compact }) {
        // Only evaluate compact once.
        const historyKey = compact ? 'remoteCompact' : 'remote';

        // Update state
        Vue.set(state[historyKey], 'rows', history);
    },
    [ADD_SHOW_HISTORY](state, { showSlug, history }) {
        // Add history data to episodeHistory, but without passing the show slug.
        for (const row of history) {
            if (!Object.keys(state.episodeHistory).includes(showSlug)) {
                Vue.set(state.episodeHistory, showSlug, {});
            }

            const episodeSlug = episodeToSlug(row.season, row.episode);
            if (!state.episodeHistory[showSlug][episodeSlug]) {
                state.episodeHistory[showSlug][episodeSlug] = [];
            }

            state.episodeHistory[showSlug][episodeSlug].push(row);
        }
    },
    [ADD_SHOW_EPISODE_HISTORY](state, { showSlug, episodeSlug, history }) {
        // Keep an object of shows, with their history per episode
        // Example: {tvdb1234: {s01e01: [history]}}

        if (!Object.keys(state.episodeHistory).includes(showSlug)) {
            Vue.set(state.episodeHistory, showSlug, {});
        }

        Vue.set(state.episodeHistory[showSlug], episodeSlug, history);
    },
    setLoading(state, value) {
        state.loading = value;
    },
    setHistoryActive(state, value) {
        state.historyActive = Boolean(value);
    },
    incrementHistoryRequest(state, { compact = false }) {
        const layout = historyLayoutKey(compact);
        Vue.set(state.historyRequestIds, layout, state.historyRequestIds[layout] + 1);
    },
    initializeHistorySort(state, { layout = 'detailed', sort }) {
        if (state.historySortInitialized) {
            return;
        }
        const remote = layout === 'compact' ? state.remoteCompact : state.remote;
        Vue.set(remote, 'sort', normalizeInitialHistorySort(sort));
        Vue.set(state, 'historySortInitialized', true);
    },
    initializeHistoryPagination(state, { layout = 'detailed', perPage }) {
        if (state.historyPaginationInitialized) {
            return;
        }
        const remote = layout === 'compact' ? state.remoteCompact : state.remote;
        const initialPerPage = initialHistoryPerPage(remote, perPage);
        Vue.set(state.remote, 'perPage', initialPerPage);
        Vue.set(state.remoteCompact, 'perPage', initialPerPage);
        Vue.set(state, 'historyPaginationInitialized', true);
    },
    initializeEpisodeFilter(state, { inputValue, filterValue, malformed }) {
        if (state.episodeFilter.initialized) {
            return;
        }
        state.episodeFilter = {
            inputValue,
            filterValue,
            malformed: Boolean(malformed),
            initialized: true
        };
        setResourceFilter(state.remote, filterValue, false);
        setResourceFilter(state.remoteCompact, filterValue, false);
    },
    updateEpisodeFilter(state, { inputValue, filterValue, malformed, resetPage = true }) {
        state.episodeFilter = {
            inputValue,
            filterValue,
            malformed: Boolean(malformed),
            initialized: true
        };
        setResourceFilter(state.remote, filterValue, resetPage);
        setResourceFilter(state.remoteCompact, filterValue, resetPage);
    },
    prepareHistoryLayoutTransition(state, { layout, fromLayout = 'detailed' }) {
        if (!['compact', 'detailed'].includes(layout) || layout === fromLayout) {
            return;
        }
        if (state.episodeFilter.initialized && state.episodeFilter.malformed) {
            Vue.set(state.episodeFilter, 'inputValue', state.episodeFilter.filterValue);
            Vue.set(state.episodeFilter, 'malformed', false);
        }
        Object.keys(state.historyRequestIds).forEach(requestLayout => {
            Vue.set(state.historyRequestIds, requestLayout, state.historyRequestIds[requestLayout] + 1);
        });
        const source = fromLayout === 'compact' ? state.remoteCompact : state.remote;
        const target = layout === 'compact' ? state.remoteCompact : state.remote;
        [state.remote, state.remoteCompact].forEach(remote => {
            Vue.set(remote, 'page', source.page);
            Vue.set(remote, 'perPage', source.perPage);
        });
        Vue.set(target, 'sort', mapHistorySort(source.sort));

        if (layout !== 'compact') {
            return;
        }
        let resource = historyFilter(state.remote).resource || historyFilter(state.remoteCompact).resource;
        if (state.episodeFilter.initialized) {
            resource = state.episodeFilter.filterValue;
        }
        [state.remote, state.remoteCompact].forEach(remote => {
            const filter = Object.assign({}, remote.filter || {}, {
                columnFilters: compactHistoryFilters(resource)
            });
            Vue.set(remote, 'filter', filter);
        });
    },
    setRemoteTotal(state, { total, compact = false }) {
        state[compact ? 'remoteCompact' : 'remote'].totalRows = total;
    },
    setRemotePage(state, { page, compact = false }) {
        Vue.set(state[compact ? 'remoteCompact' : 'remote'], 'page', page);
    }
};

const getters = {
    getShowHistoryBySlug: state => showSlug => state.showHistory[showSlug],
    getLastReleaseName: state => ({ showSlug, episodeSlug }) => {
        if (state.episodeHistory[showSlug] !== undefined) {
            if (state.episodeHistory[showSlug][episodeSlug] !== undefined) {
                if (state.episodeHistory[showSlug][episodeSlug].length === 1) {
                    return state.episodeHistory[showSlug][episodeSlug][0].resource;
                }
                const filteredHistory = state.episodeHistory[showSlug][episodeSlug]
                    .slice()
                    .sort((a, b) => (a.actionDate - b.actionDate) * -1)
                    .filter(ep => ['Snatched', 'Downloaded'].includes(ep.statusName) && ep.resource !== '');
                if (filteredHistory.length > 0) {
                    return filteredHistory[0].resource;
                }
            }
        }
    },
    getEpisodeHistory: state => ({ showSlug, episodeSlug }) => {
        if (state.episodeHistory[showSlug] === undefined) {
            return [];
        }

        return state.episodeHistory[showSlug][episodeSlug] || [];
    },
    getSeasonHistory: state => ({ showSlug, season }) => {
        if (state.episodeHistory[showSlug] === undefined) {
            return [];
        }

        return Object.values(state.episodeHistory[showSlug]).flat().filter(row => row.season === season) || [];
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
    setHistoryActive({ commit }, value) {
        commit('setHistoryActive', value);
    },
    initializeEpisodeFilter({ state, rootState, commit }, payload = {}) {
        if (state.episodeFilter.initialized) {
            return;
        }
        const layout = payload.layout || (rootState.config.layout && rootState.config.layout.history) || 'detailed';
        const remote = layout === 'compact' ? state.remoteCompact : state.remote;
        const resource = historyFilter(remote).resource || '';
        commit('initializeEpisodeFilter', {
            inputValue: resource,
            filterValue: resource,
            malformed: false
        });
    },
    updateEpisodeFilter({ commit }, value) {
        commit('updateEpisodeFilter', value);
    },
    initializeHistorySort({ commit, state }, payload = {}) {
        if (state.historySortInitialized) {
            return;
        }
        commit('initializeHistorySort', payload);
    },
    initializeHistoryPagination({ commit, state }, payload = {}) {
        if (state.historyPaginationInitialized) {
            return;
        }
        commit('initializeHistoryPagination', payload);
    },
    prepareHistoryLayoutTransition({ rootState, commit }, payload = {}) {
        const currentLayout = (rootState.config.layout && rootState.config.layout.history) || 'detailed';
        commit('prepareHistoryLayoutTransition', Object.assign({}, payload, {
            fromLayout: currentLayout
        }));
    },
    /**
     * Get show history from API and commit it to the store.
     *
     * @param {*} context The store context.
     * @param {ShowIdentifier&ShowGetParameters} parameters Request parameters.
     * @returns {Promise} The API response.
     */
    async getShowHistory({ rootState, commit }, { slug }) {
        const response = await rootState.auth.client.api.get(`/history/${slug}`);
        if (response.data.length > 0) {
            commit(ADD_SHOW_HISTORY, { showSlug: slug, history: response.data });
        }
    },
    /**
     * Get detailed history from API and commit them to the store.
     *
     * @param {*} context - The store context.
     * @param {object} args - arguments.
     */
    async getHistory({ rootState, commit, dispatch, state }, args) {
        const tracked = hasTrackedHistoryQuery(args);
        const requestCompact = args && args.compact;
        const layout = historyLayoutKey(requestCompact);
        const querySnapshot = tracked ? serializeHistoryQuery(args) : null;
        let requestId = null;
        if (tracked) {
            commit('incrementHistoryRequest', { compact: requestCompact });
            requestId = state.historyRequestIds[layout];
        }
        let url = '/history';
        const page = args?.page || 1;
        const limit = args?.perPage || 1000;
        let sort = args?.sort || [{ field: 'date', type: 'desc' }];
        const filter = args?.filter || {};
        const showSlug = args?.showSlug;
        const compact = args?.compact;

        const params = {
            page,
            limit
        };

        if (sort) {
            if (!Array.isArray(sort)) {
                sort = [sort];
            }
            params.sort = JSON.stringify(sort);
        }

        if (filter) {
            params.filter = JSON.stringify(filter);
        }

        if (showSlug) {
            url = `${url}/${showSlug}`;
        }

        if (compact) {
            params.compact = true;
        }

        commit('setLoading', true);
        let response = null;
        try {
            response = await rootState.auth.client.api.get(url, { params }); // eslint-disable-line no-await-in-loop
            if (response) {
                await applyHistoryResponse({
                    response,
                    args,
                    page,
                    compact,
                    showSlug,
                    tracked,
                    state,
                    commit,
                    dispatch,
                    requestId,
                    querySnapshot
                }); // eslint-disable-line no-await-in-loop
            }
        } catch (error) {
            if (error.response && error.response.status === 404) {
                console.debug(`No history available${showSlug ? ' for show ' + showSlug : ''}`);
            }
        }

        commit('setLoading', false);
    },
    /**
     * Get episode history from API and commit it to the store.
     *
     * @param {*} context The store context.
     * @param {ShowIdentifier&ShowGetParameters} parameters Request parameters.
     * @returns {Promise} The API response.
     */
    getShowEpisodeHistory({ rootState, commit }, { showSlug, episodeSlug }) {
        return new Promise(resolve => {
            rootState.auth.client.api.get(`/history/${showSlug}/episode/${episodeSlug}`)
                .then(response => {
                    if (response.data.length > 0) {
                        commit(ADD_SHOW_EPISODE_HISTORY, { showSlug, episodeSlug, history: response.data });
                    }
                    resolve();
                })
                .catch(() => {
                    console.warn(`No episode history found for show ${showSlug} and episode ${episodeSlug}`);
                });
        });
    },
    updateHistory({ rootState, commit, dispatch, state }, data) {
        // Update store's search queue item. (provided through websocket)
        const layout = rootState.config.layout && rootState.config.layout.history;
        const compact = layout === 'compact';
        // We can't live update the compact layout, as it requires to aggregate the data.
        if (compact) {
            return;
        }
        if (layout === 'detailed' && state.historyActive) {
            return dispatch('getHistory', {
                page: state.remote.page,
                perPage: state.remote.perPage,
                sort: state.remote.sort,
                filter: state.remote.filter
            });
        }
        commit(ADD_HISTORY_ROW, { history: data });
    }
};

export default {
    state,
    mutations,
    getters,
    actions
};

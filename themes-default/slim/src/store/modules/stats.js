import { ADD_STATS, SET_STATS, SET_MAX_DOWNLOAD_COUNT } from '../mutation-types';

const state = {
    overall: {
        episodes: {
            downloaded: null,
            snatched: null,
            total: null
        },
        shows: {
            active: null,
            total: null
        }
    },
    show: {
        maxDownloadCount: 0,
        stats: []
    }
};

const statsRequests = new WeakMap();

const fetchShowStats = async ({ rootState, rootGetters, commit }, showSlug) => {
    const show = rootState.shows.shows.find(show => show.id.slug === showSlug);
    if (!show) {
        return;
    }
    const response = await rootState.auth.client.api.get('/stats/show', { params: { showslug: showSlug } });
    if (rootState.shows.shows.some(show => show.id.slug === showSlug)) {
        commit('updateShowStats', {
            indexerId: rootGetters.indexerNameToId(show.indexer),
            seriesId: show.id[show.indexer],
            stats: response.data.stats
        });
    }
};

const queueStats = (context, { showSlug, overall = false } = {}) => {
    const { state, rootState, commit } = context;
    let refresh = statsRequests.get(state);
    if (!refresh) {
        refresh = { pending: new Set(), full: false, overall: false };
        statsRequests.set(state, refresh);
        // One drain batches bursts and prevents a full response overwriting a newer single-show response.
        refresh.promise = Promise.resolve().then(async () => {
            try {
                while (refresh.full || refresh.pending.size > 0 || refresh.overall) {
                    // Refresh the footer once the pending show updates have settled.
                    // Clear before awaiting so a new event can request fresh totals again.
                    if (!refresh.full && refresh.pending.size === 0) {
                        refresh.overall = false;
                        try {
                            const response = await rootState.auth.client.api.get('/stats/'); // eslint-disable-line no-await-in-loop
                            commit(ADD_STATS, { type: 'overall', stats: response.data });
                        } catch (error) {
                            console.warn('Unable to refresh overall statistics', error);
                        }
                        continue;
                    }
                    const { full } = refresh;
                    const covered = full ? [...refresh.pending] : [];
                    const nextSlug = refresh.pending.values().next().value;
                    refresh.full = false;
                    if (full) {
                        refresh.pending.clear();
                    } else {
                        refresh.pending.delete(nextSlug);
                    }
                    try {
                        if (full) {
                            const response = await rootState.auth.client.api.get('/stats/show'); // eslint-disable-line no-await-in-loop
                            commit(ADD_STATS, { type: 'show', stats: response.data });
                        } else {
                            await fetchShowStats(context, nextSlug); // eslint-disable-line no-await-in-loop
                        }
                    } catch (error) {
                        covered.forEach(slug => refresh.pending.add(slug));
                        console.warn('Unable to refresh show statistics', error);
                    }
                }
            } finally {
                statsRequests.delete(state);
            }
        });
    }
    if (showSlug) {
        refresh.pending.add(showSlug);
        refresh.overall = true;
    } else if (overall) {
        refresh.overall = true;
    } else {
        refresh.full = true;
    }
    return refresh.promise;
};

const mutations = {
    [ADD_STATS](state, payload) {
        const { type, stats } = payload;
        state[type] = Object.assign(state[type], stats);
    },
    [SET_STATS](state, stats) {
        state.stats = stats;
    },
    [SET_MAX_DOWNLOAD_COUNT](state, downloadCount) {
        state.maxDownloadCount = downloadCount;
    },
    updateShowStats(state, { indexerId, seriesId, stats }) {
        const matchesShow = row => row.indexerId === indexerId && row.seriesId === seriesId;
        const index = state.show.stats.findIndex(matchesShow);
        const updated = stats.find(matchesShow);
        if (index === -1) {
            if (updated) {
                state.show.stats.push(updated);
            }
        } else {
            state.show.stats.splice(index, 1, ...(updated ? [updated] : []));
        }
    }
};

const getters = {};

const actions = {
    getStats(context, type) {
        if (type === 'show') {
            return queueStats(context);
        }
        if (!type || type === 'overall') {
            return queueStats(context, { overall: true });
        }
        const { rootState, commit } = context;
        return rootState.auth.client.api.get(`/stats/${(type || '')}`).then(res => {
            commit(ADD_STATS, {
                type: (type || 'overall'),
                stats: res.data
            });
        });
    },
    refreshShowStats(context, showSlug) {
        if (showSlug && context.rootState.shows.shows.some(show => show.id.slug === showSlug)) {
            return queueStats(context, { showSlug });
        }
    }
};

export default {
    state,
    mutations,
    getters,
    actions
};

import Vue from 'vue';
import {
    ADD_PROVIDER,
    ADD_PROVIDERS,
    ADD_PROVIDER_CACHE,
    ADD_SEARCH_RESULTS,
    REMOVE_PROVIDER
} from '../mutation-types';

const state = {
    providers: []
};

const cacheRequests = new WeakMap();

// Match the backend query so a refresh replaces only the cached rows it can return.
const matchesScope = (result, { showSlug, season, episode }) => {
    if (result.showSlug !== showSlug) {
        return false;
    }

    // A null season means any season. Season 0 is specials and must still match.
    if (season !== null && result.season !== season) {
        return false;
    }

    // Without an episode filter, every release type in the selected show/season matches,
    // including individual episodes, multi-episode releases and season packs.
    if (episode === null) {
        return true;
    }

    // An episode query matches exactly '|N|' in the backend, not a list containing N.
    // For example, refreshing episode 3 must retain a cached [3, 4] release because
    // that request cannot return its replacement.
    if (result.episodes.length !== 1) {
        return false;
    }

    return result.episodes[0] === episode;
};

const mutations = {
    [ADD_PROVIDER](state, provider) {
        if (!state.providers.find(p => p.id === provider.id)) {
            state.providers.push(provider);
        }
    },
    [ADD_PROVIDERS](state, providers) {
        providers.forEach(provider => {
            const existingProvider = state.providers.find(p => p.id === provider.id);
            if (existingProvider) {
                Vue.set(state.providers, state.providers.indexOf(existingProvider), {
                    ...provider, cache: existingProvider.cache || []
                });
            } else {
                state.providers.push(provider);
            }
        });
    },
    [REMOVE_PROVIDER](state, providerId) {
        state.providers = state.providers.filter(prov => prov.id !== providerId);
    },
    [ADD_PROVIDER_CACHE](state, { providerId, cache, scope, previousCache }) {
        // Check if this provider has already been added.
        let currentProvider = state.providers.find(prov => prov.id === providerId);
        if (!currentProvider) {
            currentProvider = {
                id: providerId,
                name: '',
                config: {}
            };
            state.providers.push(currentProvider);
        }

        if (currentProvider.cache === undefined) {
            Vue.set(currentProvider, 'cache', []);
        }

        const previousRows = new Set(previousCache || currentProvider.cache);
        const incoming = new Map();
        for (const result of cache) {
            incoming.set(result.identifier, result);
        }

        const merged = [];
        for (const current of currentProvider.cache) {
            // Consume unchanged snapshot rows; replaced rows must keep their newer values.
            const unchanged = previousRows.delete(current);
            const fetched = incoming.get(current.identifier);
            if (!unchanged || (scope && !matchesScope(current, scope))) {
                merged.push(unchanged && fetched ? { ...current, ...fetched } : current);
                incoming.delete(current.identifier);
            } else if (fetched) {
                incoming.set(current.identifier, { ...current, ...fetched });
            }
        }

        // Remaining snapshot rows were removed or replaced by a newer update.
        for (const previous of previousRows) {
            incoming.delete(previous.identifier);
        }
        for (const result of incoming.values()) {
            merged.push(result);
        }
        Vue.set(currentProvider, 'cache', merged);
    },
    /**
     * Add search results which have been retreived through the webSocket.
     * @param {*} state - Vue state
     * @param {Array} searchResults - One or more search results.
     */
    [ADD_SEARCH_RESULTS](state, searchResults) {
        for (const searchResult of searchResults) {
            let currentProvider = state.providers.find(prov => prov.id === searchResult.provider.id);

            if (!currentProvider) {
                currentProvider = {
                    id: searchResult.provider.id,
                    name: searchResult.provider.name,
                    config: {},
                    cache: []
                };
                state.providers.push(currentProvider);
            }

            const { cache } = currentProvider;

            // Check if we don't allready have this result in our store.
            // In that case, we update the existing object.
            const existingSearchResult = (cache || []).find(result => result.identifier === searchResult.identifier);
            if (existingSearchResult) {
                // Because this is an existing result, whe're not overwriting dateAdded field.
                const { dateAdded, ...rest } = searchResult;
                Vue.set(currentProvider.cache, cache.indexOf(existingSearchResult), { ...existingSearchResult, ...rest });
            } else {
                Vue.set(currentProvider, 'cache', [...cache || [], ...[searchResult]]);
            }
        }
    }
};

const getters = {
    providerNameToId: _ => providerName => providerName.replace(/[^\d\w_]/gi, '_').toLowerCase().trim() // eslint-disable-line unicorn/better-regex
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
     * Get providers.
     *
     * @param {*} context The store context.
     * @returns {Promise} The API response.
     */
    getProviders({ rootState, commit }) {
        return new Promise((resolve, reject) => {
            rootState.auth.client.api.get('/providers')
                .then(response => {
                    commit(ADD_PROVIDERS, response.data);
                    resolve();
                })
                .catch(error => {
                    console.error(`Could not get providers with error: ${error}`);
                    reject();
                });
        });
    },
    /**
     * Get provider cache results for enabled providers.
     *
     * @param {*} context The store context.
     * @param {String} The provider id.
     * @returns {void}.
     */
    async getProviderCacheResults({ rootState, commit, state }, { showSlug, season, episode, isCurrent = () => true }) {
        const result = { providersSearched: 0, totalSearchResults: [] };
        if (!showSlug) {
            return result;
        }
        if (!isCurrent()) {
            return { ...result, cancelled: true };
        }

        const scope = {
            showSlug,
            season: season === undefined || season === null ? null : Number(season),
            episode: episode ? Number(episode) : null
        };
        const key = JSON.stringify(scope);
        const requests = cacheRequests.get(state) || new Map();
        cacheRequests.set(state, requests);
        const request = {};
        requests.set(key, request);
        const current = () => isCurrent() && requests.get(key) === request;
        const limit = 1000;
        const params = { limit, showslug: showSlug, season };
        if (episode) {
            params.episode = episode;
        }

        const getProviderResults = async provider => {
            let page = 0;
            const results = [];
            const previousCache = (provider.cache || []).slice();
            while (current()) {
                let response;
                page += 1;
                try {
                    response = await rootState.auth.client.api.get(`/providers/${provider.id}/results`, { params: { ...params, page } }); // eslint-disable-line no-await-in-loop
                } catch (error) {
                    if (error.response && error.response.status === 404) {
                        response = { data: [] };
                    } else {
                        return results;
                    }
                }
                if (!current()) {
                    return results;
                }
                results.push(...response.data);
                if (response.data.length < limit) {
                    commit(ADD_PROVIDER_CACHE, { providerId: provider.id, cache: results, scope, previousCache });
                    return results;
                }
            }
            return results;
        };

        try {
            for (const provider of state.providers) {
                if (!current()) {
                    break;
                }
                if (!provider.config.enabled) {
                    continue;
                }
                result.providersSearched += 1;
                const providerResults = await getProviderResults(provider); // eslint-disable-line no-await-in-loop
                result.totalSearchResults.push(...providerResults);
            }
            return current() ? result : { ...result, cancelled: true };
        } finally {
            if (requests.get(key) === request) {
                requests.delete(key);
            }
        }
    },
    /**
     * Get provider cache results for enabled providers.
     *
     * @param {*} {commit} Destructured commit object.
     * @param {Object} searchResult - Search result.
     * @returns {void}.
     */
    addManualSearchResult({ commit }, searchResult) {
        commit(ADD_SEARCH_RESULTS, [searchResult]);
    }

};

export default {
    state,
    mutations,
    getters,
    actions
};

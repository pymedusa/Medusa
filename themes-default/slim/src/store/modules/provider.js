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
                Vue.set(state.providers, state.providers.indexOf(existingProvider), provider);
            } else {
                state.providers.push(provider);
            }
        });
    },
    [REMOVE_PROVIDER](state, providerId) {
        state.providers = state.providers.filter(prov => prov.id !== providerId);
    },
    [ADD_PROVIDER_CACHE](state, { providerId, cache }) {
        // Check if this provider has already been added.
        let currentProvider = state.providers.find(prov => prov.id === providerId);
        if (!currentProvider) {
            currentProvider = {
                name: '',
                config: {}
            };
            state.providers.push(currentProvider);
        }

        if (currentProvider.cache === undefined) {
            Vue.set(currentProvider, 'cache', []);
        }

        const newCache = [];

        for (const result of cache) {
            const existingIdentifier = currentProvider.cache.find(item => item.identifier === result.identifier);
            if (existingIdentifier) {
                newCache.push({ ...existingIdentifier, ...result });
            } else {
                newCache.push(result);
            }
        }

        Vue.set(currentProvider, 'cache', newCache);
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
                    name: '',
                    config: {},
                    cache: []
                };
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
    async getProviderCacheResults({ rootState, commit, state }, { showSlug, season, episode }) {
        const limit = 1000;
        const params = { limit, showslug: showSlug, season };
        if (episode) {
            params.episode = episode;
        }

        const getProviderResults = async provider => {
            let page = 0;
            let lastPage = false;
            const results = [];

            const currentProvider = state.providers.find(prov => prov.id === provider.id);
            if (!currentProvider) {
                return results;
            }

            const { id: providerId } = currentProvider;

            page = 0;
            lastPage = false;

            while (!lastPage) {
                let response = null;
                page += 1;

                params.page = page;

                try {
                    response = await rootState.auth.client.api.get(`/providers/${providerId}/results`, { params }); // eslint-disable-line no-await-in-loop
                } catch (error) {
                    if (error.response && error.response.status === 404) {
                        console.debug(`No results available for provider ${provider.name}`);
                    }

                    lastPage = true;
                }

                if (response) {
                    commit(ADD_PROVIDER_CACHE, { providerId, cache: response.data });
                    results.push(...response.data);

                    if (response.data.length < limit) {
                        lastPage = true;
                    }
                } else {
                    lastPage = true;
                }
            }
            return results;
        };

        const result = {
            providersSearched: 0,
            totalSearchResults: []
        };

        for (const provider of state.providers) {
            if (!provider.config.enabled) {
                continue;
            }

            result.providersSearched += 1;
            const providerResults = await getProviderResults(provider); // eslint-disable-line no-await-in-loop
            result.totalSearchResults.push(...providerResults);
        }

        return result;
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

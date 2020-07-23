import Vue from 'vue';

import { api } from '../../api';
import { ADD_PROVIDERS, ADD_PROVIDER_CACHE, ADD_SEARCH_RESULTS } from '../mutation-types';

const state = {
    providers: {}
};

const mutations = {
    [ADD_PROVIDERS](state, providers) {
        for (const provider of providers) {
            Vue.set(state.providers, provider.id, { ...state.providers[provider.id], ...provider });
        }
    },
    [ADD_PROVIDER_CACHE](state, { providerId, cache }) {
        // Check if this provider has already been added.
        if (!state.providers[providerId]) {
            state.providers[providerId] = {
                name: '',
                config: {}
            };
        }

        if (state.providers[providerId].cache === undefined) {
            Vue.set(state.providers[providerId], 'cache', []);
        }

        const newCache = [];

        for (const result of cache) {
            const existingIdentifier = state.providers[providerId].cache.find(item => item.identifier === result.identifier);
            if (existingIdentifier) {
                newCache.push({ ...existingIdentifier, ...result });
            } else {
                newCache.push(result);
            }
        }

        Vue.set(state.providers[providerId], 'cache', newCache);
    },
    /**
     * Add search results which have been retreived through the webSocket.
     * @param {*} state - Vue state
     * @param {Array} searchResults - One or more search results.
     */
    [ADD_SEARCH_RESULTS](state, searchResults) {
        for (const searchResult of searchResults) {
            if (!state.providers[searchResult.provider.id]) {
                state.providers[searchResult.provider.id] = {
                    name: '',
                    config: {},
                    cache: []
                };
            }

            const { cache } = state.providers[searchResult.provider.id];

            // Check if we don't allready have this result in our store.
            // In that case, we update the existing object.
            const existingSearchResult = (cache || []).find(result => result.identifier === searchResult.identifier);
            if (existingSearchResult) {
                // Because this is an existing result, whe're not overwriting dateAdded field.
                const { dateAdded, ...rest } = searchResult;
                Vue.set(state.providers[searchResult.provider.id].cache, cache.indexOf(existingSearchResult), { ...existingSearchResult, ...rest });
            } else {
                Vue.set(state.providers[searchResult.provider.id], 'cache', [...cache || [], ...[searchResult]]);
            }
        }
    }
};

const getters = {};

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
    getProviders(context) {
        return new Promise((resolve, reject) => {
            const { commit } = context;
            api.get('/providers')
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
    async getProviderCacheResults(context, { showSlug, season, episode }) {
        const { commit, state } = context;
        const limit = 1000;
        const params = { limit, showslug: showSlug, season };
        if (episode) {
            params.episode = episode;
        }

        const getProviderResults = async provider => {
            let page = 0;
            let lastPage = false;
            const results = [];

            const { id: providerId } = state.providers[provider];

            page = 0;
            lastPage = false;

            while (!lastPage) {
                let response = null;
                page += 1;

                params.page = page;

                try {
                    response = await api.get(`/providers/${providerId}/results`, { params }); // eslint-disable-line no-await-in-loop
                } catch (error) {
                    if (error.response && error.response.status === 404) {
                        console.debug(`No results available for provider ${provider}`);
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

        for (const provider in state.providers) {
            if (!state.providers[provider].config.enabled) {
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

import { ADD_CONFIG } from '../../mutation-types';

const state = {
    main: {
        externalMappings: {},
        statusMap: {},
        traktIndexers: {},
        validLanguages: [],
        langabbvToId: {},
        recommendedLists: {}
    },
    indexers: {
        tvdb: {
            apiParams: {
                useZip: null,
                language: null
            },
            baseUrl: null,
            enabled: null,
            icon: null,
            id: null,
            identifier: null,
            mappedTo: null,
            name: null,
            scene_loc: null, // eslint-disable-line camelcase
            showUrl: null,
            xemOrigin: null
        },
        tmdb: {
            apiParams: {
                useZip: null,
                language: null
            },
            baseUrl: null,
            enabled: null,
            icon: null,
            id: null,
            identifier: null,
            mappedTo: null,
            name: null,
            scene_loc: null, // eslint-disable-line camelcase
            showUrl: null,
            xemOrigin: null
        },
        tvmaze: {
            apiParams: {
                useZip: null,
                language: null
            },
            baseUrl: null,
            enabled: null,
            icon: null,
            id: null,
            identifier: null,
            mappedTo: null,
            name: null,
            scene_loc: null, // eslint-disable-line camelcase
            showUrl: null,
            xemOrigin: null
        },
        imdb: {
            apiParams: {
                useZip: null,
                language: null
            },
            baseUrl: null,
            enabled: null,
            icon: null,
            id: null,
            identifier: null,
            mappedTo: null,
            name: null,
            scene_loc: null, // eslint-disable-line camelcase
            showUrl: null,
            xemOrigin: null
        }
    }
};

const mutations = {
    [ADD_CONFIG](state, { section, config }) {
        if (section === 'indexers') {
            state = Object.assign(state, config);
        }
    }
};

const getters = {
    // Get an indexer's name using its ID.
    indexerIdToName: state => indexerId => {
        if (!indexerId) {
            return undefined;
        }
        const { indexers } = state;
        return Object.keys(indexers).find(name => indexers[name].id === Number.parseInt(indexerId, 10));
    },
    // Get an indexer's ID using its name.
    indexerNameToId: state => indexerName => {
        const { indexers } = state;
        if (!indexerName || !indexers) {
            return undefined;
        }
        return indexers[indexerName].id;
    },
    /**
     * Return the indexers showUrl.
     * @param {object} state - State object.
     * @returns {string|undefined} Indexers show url or undefined if not found.
     */
    getIndexer: state => indexerId => {
        return Object.values(state.indexers).find(indexer => indexer.id === indexerId);
    }
};

const actions = {};

export default {
    state,
    mutations,
    getters,
    actions
};

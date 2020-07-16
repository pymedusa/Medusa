import { ADD_CONFIG } from '../../mutation-types';

const state = {
    main: {
        externalMappings: {},
        statusMap: {},
        traktIndexers: {},
        validLanguages: [],
        langabbvToId: {}
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
    }
};

const actions = {};

export default {
    state,
    mutations,
    getters,
    actions
};

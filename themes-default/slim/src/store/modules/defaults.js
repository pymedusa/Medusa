const state = {
    show: {
        airs: null,
        akas: null,
        cache: null,
        classification: null,
        config: {
            airByDate: null,
            aliases: null,
            anime: null,
            defaultEpisodeStatus: null,
            dvdOrder: null,
            location: null,
            paused: null,
            qualities: null,
            release: null,
            scene: null,
            seasonFolders: null,
            sports: null,
            subtitlesEnabled: null
        },
        countries: null,
        country_codes: null, // eslint-disable-line camelcase
        genres: null,
        id: {
            tvdb: null,
            slug: null
        },
        indexer: null,
        language: null,
        network: null,
        nextAirDate: null,
        plot: null,
        rating: {
            imdb: {
                rating: null,
                votes: null
            }
        },
        runtime: null,
        showType: null,
        status: null,
        title: null,
        type: null,
        year: {}
    }
};

const mutations = {};

const getters = {};

const actions = {};

export default {
    state,
    mutations,
    getters,
    actions
};

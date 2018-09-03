const state = {
    show: {
        airs: null,
        akas: {},
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
        countries: [],
        countryCodes: [],
        genres: [],
        id: {
            tvdb: null,
            tmdb: null,
            tvmaze: null,
            imdb: null,
            slug: null
        },
        indexer: null,
        language: null,
        network: null,
        nextAirDate: null,
        plot: null,
        imdbInfo: {
            year: {
                start: null
            },
            runtime: null,
            plot: null,
            rating: null,
            votes: null
        },
        runtime: null,
        showType: null,
        status: null,
        title: null,
        type: null,
        year: {
            start: null,
            end: null
        }
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

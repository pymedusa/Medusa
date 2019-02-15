const state = {
    show: {
        airs: null,
        airsFormatValid: null,
        akas: null,
        cache: null,
        classification: null,
        config: {
            airByDate: null,
            aliases: [],
            anime: null,
            defaultEpisodeStatus: null,
            dvdOrder: null,
            location: null,
            locationValid: null,
            paused: null,
            qualities: {
                allowed: [],
                preferred: []
            },
            release: {
                requiredWords: [],
                ignoredWords: [],
                blacklist: [],
                whitelist: [],
                allgroups: [],
                requiredWordsExclude: null,
                ignoredWordsExclude: null
            },
            scene: null,
            seasonFolders: null,
            sports: null,
            subtitlesEnabled: null,
            airdateOffset: null
        },
        countries: null,
        genres: [],
        id: {
            tvdb: null,
            slug: null
        },
        indexer: null,
        imdbInfo: {
            akas: null,
            certificates: null,
            countries: null,
            countryCodes: null,
            genres: null,
            imdbId: null,
            imdbInfoId: null,
            indexer: null,
            indexerId: null,
            lastUpdate: null,
            plot: null,
            rating: null,
            runtimes: null,
            title: null,
            votes: null
        },
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
        year: {},
        size: null,
        showQueueStatus: [],
        xemNumbering: []
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

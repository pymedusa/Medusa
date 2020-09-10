const state = {
    show: {
        airs: null,
        airsFormatValid: null,
        akas: null,
        cache: null,
        classification: null,
        seasonCount: [],
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
            trakt: null,
            imdb: null,
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

        // ===========================
        // Detailed (`?detailed=true`)
        // ===========================

        showQueueStatus: [],
        xemNumbering: [],
        sceneAbsoluteNumbering: [],
        xemAbsoluteNumbering: [],
        sceneNumbering: [],

        // ===========================
        // Episodes (`?episodes=true`)
        // ===========================

        // Seasons array is added to the show object under this query,
        // but we currently check to see if this property is defined before fetching the show with `?episodes=true`.
        // seasons: [],
        episodeCount: null
    },
    provider: {
        id: null,
        name: null,
        config: {},
        cache: []
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

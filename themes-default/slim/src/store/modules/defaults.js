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
        country_codes: null, // eslint-disable-line camelcase
        genres: [],
        id: {
            tvdb: null,
            slug: null
        },
        indexer: null,
        imdbInfo: {},
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
        showQueueStatus: []
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

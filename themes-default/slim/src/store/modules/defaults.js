const state = {
    show: {
        id: {
            tvdb: null,
            slug: null
        },
        rating: {
            imdb: {
                rating: null,
                votes: null
            }
        },
        country_codes: [], // eslint-disable-line camelcase
        network: null,
        airs: null,
        config: {
            qualities: null,
            defaultEpisodeStatus: null,
            dvdOrder: null,
            seasonFolders: null,
            scene: null,
            sports: null,
            paused: null,
            location: null,
            airByDate: null,
            release: null,
            aliases: null,
            subtitlesEnabled: null,
            anime: null
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

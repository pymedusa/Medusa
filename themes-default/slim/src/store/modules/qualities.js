import { ADD_CONFIG } from '../mutation-types';

const state = {
    values: {},
    anySets: {},
    presets: {},
    strings: {
        values: {},
        anySets: {},
        presets: {},
        cssClass: {}
    }
};

const mutations = {
    [ADD_CONFIG](state, { section, config }) {
        if (section === 'qualities') {
            state = Object.assign(state, config);
        }
    }
};

const getters = {
    getPreset: state => value => {
        return Object.keys(state.presets)
            .filter(key => {
                return state.presets[key] === value;
            })
            .map(key => {
                return {
                    [key]: state.presets[key]
                };
            });
    },
    combineQualities: () => qualities => {
        const reducer = (accumulator, currentValue) => accumulator | currentValue;
        return qualities.reduce(reducer, 0);
    }
};

const actions = {};

export default {
    state,
    mutations,
    getters,
    actions
};

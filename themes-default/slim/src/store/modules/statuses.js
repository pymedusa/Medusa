import { ADD_CONFIG } from '../mutation-types';

const state = {
    values: {},
    strings: {}
};

const mutations = {
    [ADD_CONFIG](state, { section, config }) {
        if (section === 'statuses') {
            state = Object.assign(state, config);
        }
    }
};

const getters = {
    getOverviewStatus: state => (status, quality, showQualities) => {
        if (['Unset', 'Unaired'].includes(status)) {
            return 'Unaired';
        }
        if (['Skipped', 'Ignored'].includes(status)) {
            return 'Skipped';
        }
        if (['Wanted', 'Failed'].includes(status)) {
            return 'Wanted';
        }
        if (['Snatched', 'Snatched (Proper)', 'Snatched (Best)'].includes(status)) {
            return 'Snatched';
        }
        if (['Downloaded', 'Archived'].includes(status)) {
            if (showQualities.preferred.includes(quality)) {
                return 'Preferred';
            }
            if (showQualities.allowed.includes(quality)) {
                return 'Allowed';
            }
        }

    }
};

const actions = {};

export default {
    state,
    mutations,
    getters,
    actions
};

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
    /**
     * Get an overview status for an episodes status, quality and show config's quality configuration.
     * @param {String} status - current episode status
     * @param {Number} quality - current episode quality
     * @param {Object} showQualities - show config's quality configuration. Including the arrays, 'preferred' and 'allowed'.
     * @return {String} the overview status.
     */
    // eslint-disable-next-line no-unused-vars
    getOverviewStatus: _state => (status, quality, showQualities) => {
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

        if (['Downloaded'].includes(status)) {
            if (showQualities.preferred.includes(quality)) {
                return 'Preferred';
            }

            if (showQualities.allowed.includes(quality)) {
                return 'Allowed';
            }
        }

        return status;
    }
};

const actions = {};

export default {
    state,
    mutations,
    getters,
    actions
};

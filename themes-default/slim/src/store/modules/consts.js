import { ADD_CONFIG } from '../mutation-types';

/**
 * An object representing a split quality.
 *
 * @typedef {Object} Quality
 * @property {number[]} allowed - Allowed qualities
 * @property {number[]} preferred - Preferred qualities
 */

const state = {
    qualities: {
        values: [],
        anySets: [],
        presets: []
    },
    statuses: []
};

const mutations = {
    [ADD_CONFIG](state, { section, config }) {
        if (section === 'consts') {
            state = Object.assign(state, config);
        }
    }
};

const getters = {
    // Get a quality object using a key or a value
    getQuality: state => ({ key, value }) => {
        if ([key, value].every(x => x === undefined) || [key, value].every(x => x !== undefined)) {
            throw new Error('Conflict in `getQuality`: Please provide either `key` or `value`.');
        }
        return state.qualities.values.find(quality => key === quality.key || value === quality.value);
    },
    // Get a quality any-set object using a key or a value
    getQualityAnySet: state => ({ key, value }) => {
        if ([key, value].every(x => x === undefined) || [key, value].every(x => x !== undefined)) {
            throw new Error('Conflict in `getQualityAnySet`: Please provide either `key` or `value`.');
        }
        return state.qualities.anySets.find(preset => key === preset.key || value === preset.value);
    },
    // Get a quality preset object using a key or a value
    getQualityPreset: state => ({ key, value }) => {
        if ([key, value].every(x => x === undefined) || [key, value].every(x => x !== undefined)) {
            throw new Error('Conflict in `getQualityPreset`: Please provide either `key` or `value`.');
        }
        return state.qualities.presets.find(preset => key === preset.key || value === preset.value);
    },
    // Get a status object using a key or a value
    getStatus: state => ({ key, value }) => {
        if ([key, value].every(x => x === undefined) || [key, value].every(x => x !== undefined)) {
            throw new Error('Conflict in `getStatus`: Please provide either `key` or `value`.');
        }
        return state.statuses.find(status => key === status.key || value === status.value);
    },
    // Get an episode overview status using the episode status and quality
    // eslint-disable-next-line no-unused-vars
    getOverviewStatus: (_state, getters) => (status, quality, showConfig) => {
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
            // Check if the show has been configured with a default quality preset.
            if (showConfig.qualities.allowed.length > 0 && showConfig.qualities.preferred.length === 0) {
                const reducedAllowed = showConfig.qualities.allowed.reduce((result, value) => {
                    return result + value;
                }, 0);

                if (getters.getQualityPreset({ value: reducedAllowed })) {
                    if (showConfig.qualities.allowed.includes(quality)) {
                        // This is a hack, because technically the quality does not fit in the Preferred quality.
                        // But because 'preferred' translates to the css color "green", we use it.
                        return 'Preferred';
                    }
                }
            }

            if (showConfig.qualities.preferred.includes(quality)) {
                return 'Preferred';
            }

            if (showConfig.qualities.allowed.includes(quality)) {
                return 'Allowed';
            }
        }

        return status;
    },
    splitQuality: state => {
        /**
         * Split a combined quality to allowed and preferred qualities.
         * Converted Python method from `medusa.common.Quality.split_quality`.
         *
         * @param {number} quality - The combined quality to split
         * @returns {Quality} The split quality
         */
        const _splitQuality = quality => {
            return state.qualities.values.reduce((result, { value }) => {
                quality >>>= 0; // Unsigned int
                if (value & quality) {
                    result.allowed.push(value);
                }
                if ((value << 16) & quality) {
                    result.preferred.push(value);
                }
                return result;
            }, { allowed: [], preferred: [] });
        };
        return _splitQuality;
    }
};

const actions = {};

export default {
    state,
    mutations,
    getters,
    actions
};

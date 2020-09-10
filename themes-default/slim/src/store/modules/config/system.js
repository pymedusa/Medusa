import { ADD_CONFIG } from '../../mutation-types';

/**
 * An object representing a scheduler.
 *
 * If a scheduler isn't initialized on the backend,
 * this object will only have the `key` and `name` properties.
 * @typedef {object} Scheduler
 * @property {string} key
 *      A camelCase key representing this scheduler.
 * @property {string} name
 *      The scheduler's name.
 * @property {boolean} [isAlive]
 *      Is the scheduler alive?
 * @property {boolean|string} [isEnabled]
 *      Is the scheduler enabled? For the `backlog` scheduler, the value might be `Paused`.
 * @property {boolean} [isActive]
 *      Is the scheduler's action currently running?
 * @property {string|null} [startTime]
 *      The time of day in which this scheduler runs (format: ISO-8601 time), or `null` if not applicable.
 * @property {number} [cycleTime]
 *      The duration in milliseconds between each run, or `null` if not applicable.
 * @property {number} [nextRun]
 *      The duration in milliseconds until the next run.
 * @property {string} [lastRun]
 *      The date and time of the previous run (format: ISO-8601 date-time).
 * @property {boolean} [isSilent]
 *      Is the scheduler silent?
 */

const state = {
    branch: null,
    memoryUsage: null,
    schedulers: [],
    showQueue: [],
    sslVersion: null,
    pythonVersion: null,
    pid: null,
    os: null,
    logDir: null,
    dbPath: null,
    configFile: null,
    databaseVersion: {
        major: null,
        minor: null
    },
    locale: null,
    localUser: null,
    programDir: null,
    dataDir: null,
    cacheDir: null,
    appArgs: [],
    webRoot: null,
    runsInDocker: null,
    gitRemoteBranches: [],
    cpuPresets: null,
    news: {
        lastRead: null,
        latest: null,
        unread: null
    }
};

const mutations = {
    [ADD_CONFIG](state, { section, config }) {
        if (section === 'system') {
            state = Object.assign(state, config);
        }
    }
};

const getters = {
    getScheduler: state => {
        /**
         * Get a scheduler object using a key.
         *
         * @param {string} key The combined quality to split.
         * @returns {Scheduler|object} The scheduler object or an empty object if not found.
         */
        const _getScheduler = key => state.schedulers.find(scheduler => key === scheduler.key) || {};
        return _getScheduler;
    }
};

const actions = {};

export default {
    state,
    mutations,
    getters,
    actions
};

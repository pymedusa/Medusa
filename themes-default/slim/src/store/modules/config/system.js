import { ADD_CONFIG, ADD_REMOTE_BRANCHES, ADD_SHOW_QUEUE_ITEM } from '../../mutation-types';
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
    configLoaded: false,
    branch: null,
    memoryUsage: null,
    schedulers: [],
    showQueue: [],
    diskSpace: [],
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
    timezone: null,
    localUser: null,
    programDir: null,
    dataDir: null,
    cacheDir: null,
    appArgs: [],
    webRoot: null,
    runsInDocker: null,
    newestVersionMessage: null,
    gitRemoteBranches: [],
    cpuPresets: null,
    news: {
        lastRead: null,
        latest: null,
        unread: null
    },
    ffprobeVersion: null
};

const mutations = {
    [ADD_CONFIG](state, { section, config }) {
        if (section === 'system') {
            state = Object.assign(state, config);
        }
    },
    [ADD_REMOTE_BRANCHES](state, branches) {
        state.gitRemoteBranches = branches;
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

const actions = {
    getGitRemoteBranches({ rootState, commit }) {
        return rootState.auth.client.apiRoute('home/branchForceUpdate')
            .then(response => {
                if (response.data && response.data.branches.length > 0) {
                    commit(ADD_REMOTE_BRANCHES, response.data.branches);
                    return response.data.branches;
                }
            });
    },
    getShowQueue({ rootState, commit }) {
        return rootState.auth.client.api.get('/config/system/showQueue').then(res => {
            const showQueue = res.data;
            const config = { showQueue };
            commit(ADD_CONFIG, { section: 'system', config });
            return showQueue;
        });
    },
    updateQueueItemShow({ commit }, queueItem) {
        // Update store's show queue item. (provided through websocket)
        return commit(ADD_SHOW_QUEUE_ITEM, queueItem);
    }

};

export default {
    state,
    mutations,
    getters,
    actions
};

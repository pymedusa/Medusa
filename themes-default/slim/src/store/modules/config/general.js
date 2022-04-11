import { ADD_CONFIG } from '../../mutation-types';
import { arrayUnique, arrayExclude } from '../../../utils/core';

const state = {
    addTitleWithYear: null,
    wikiUrl: null,
    donationsUrl: null,
    namingForceFolders: null,
    sourceUrl: null,
    rootDirs: [],
    brokenProviders: [],
    logs: {
        debug: null,
        dbDebug: null,
        loggingLevels: {},
        numErrors: null,
        numWarnings: null,
        actualLogDir: null,
        nr: null,
        size: null,
        subliminalLog: null,
        privacyLevel: null,
        custom: {}
    },
    cpuPreset: null,
    anonRedirect: null,
    recentShows: [],
    randomShowSlug: null, // @TODO: Recreate this in Vue when the webapp has a reliable list of shows to choose from.
    showDefaults: {
        status: null,
        statusAfter: null,
        quality: null,
        subtitles: null,
        seasonFolders: null,
        anime: null,
        scene: null,
        showLists: null
    },
    launchBrowser: null,
    defaultPage: null,
    trashRemoveShow: null,
    indexerDefaultLanguage: null,
    showUpdateHour: null,
    indexerTimeout: null,
    indexerDefault: null,
    plexFallBack: {
        enable: null,
        notifications: null,
        timeout: null
    },
    recommended: {
        cache: {
            shows: null,
            trakt: null,
            imdb: null,
            anidb: null,
            anilist: null,
            purgeAfterDays: null
        },
        trakt: {
            selectedLists: [],
            availableLists: []
        }
    },
    versionNotify: null,
    autoUpdate: null,
    updateFrequency: null,
    notifyOnUpdate: null,
    availableThemes: null,
    timePresets: [],
    datePresets: [],
    webInterface: {
        apiKey: null,
        log: null,
        username: null,
        password: null,
        port: null,
        host: null,
        notifyOnLogin: null,
        ipv6: null,
        httpsEnable: null,
        httpsCert: null,
        httpsKey: null,
        handleReverseProxy: null
    },
    sslVerify: null,
    sslCaBundle: null,
    noRestart: null,
    encryptionVersion: null,
    calendarUnprotected: null,
    calendarIcons: null,
    proxySetting: null,
    proxyProviders: null,
    proxyClients: null,
    proxyIndexers: null,
    proxyOthers: null,
    skipRemovedFiles: null,
    epDefaultDeletedStatus: null,
    developer: null,
    experimental: null,
    git: {
        username: null,
        password: null,
        token: null,
        authType: null,
        remote: null,
        path: null,
        org: null,
        reset: null,
        resetBranches: null,
        url: null
    },
    // Remove backlogOverview after manage_backlogOverview.mako is gone.
    backlogOverview: {
        status: null,
        period: null
    },
    // Remove themeName when we get fully rid of MEDUSA.config.
    themeName: null,
    providers: {
        prowlarr: {
            url: null,
            apikey: null
        }
    },
    backup: {
        cacheDb: null,
        cacheFiles: null
    }
};

const mutations = {
    [ADD_CONFIG](state, { section, config }) {
        if (section === 'main') {
            state = Object.assign(state, config);
        }
    },
    addRecentShow(state, { show }) {
        state.recentShows = state.recentShows.filter(
            filterShow =>
                !(filterShow.showSlug === show.showSlug && filterShow.name === show.name)
        );

        state.recentShows.unshift(show); // Add the new show object to the start of the array.
        state.recentShows = state.recentShows.slice(0, 5); // Cut the array of at 5 items.
    },
    updateTraktSelectedLists(state, selectedLists) {
        state.recommended.trakt.selectedLists = selectedLists;
    }
};

const getters = {
    effectiveIgnored: (state, _, rootState) => series => {
        const seriesIgnored = series.config.release.ignoredWords.map(x => x.toLowerCase());
        const globalIgnored = rootState.config.search.filters.ignored.map(x => x.toLowerCase());
        if (!series.config.release.ignoredWordsExclude) {
            return arrayUnique(globalIgnored.concat(seriesIgnored));
        }
        return arrayExclude(globalIgnored, seriesIgnored);
    },
    effectiveRequired: (state, _, rootState) => series => {
        const seriesRequired = series.config.release.requiredWords.map(x => x.toLowerCase());
        const globalRequired = rootState.config.search.filters.required.map(x => x.toLowerCase());
        if (!series.config.release.requiredWordsExclude) {
            return arrayUnique(globalRequired.concat(seriesRequired));
        }
        return arrayExclude(globalRequired, seriesRequired);
    }
};

const actions = {
    getConfig({ rootState, commit }, section) {
        return rootState.auth.client.api.get('/config/' + (section || '')).then(res => {
            if (section) {
                const config = res.data;
                commit(ADD_CONFIG, { section, config });
                return config;
            }

            const sections = res.data;
            Object.keys(sections).forEach(section => {
                const config = sections[section];
                commit(ADD_CONFIG, { section, config });
            });
            return sections;
        });
    },
    setConfig({ rootState }, { section, config }) {
        return rootState.auth.client.api.patch(`config/${section}`, config);
    },
    updateConfig({ commit }, { section, config }) {
        return commit(ADD_CONFIG, { section, config });
    },
    getApiKey({ rootState, commit }) {
        const section = 'main';
        const config = { webInterface: { apiKey: '' } };
        return rootState.auth.client.apiRoute.get('config/general/generate_api_key')
            .then(response => {
                config.webInterface.apiKey = response.data;
                return commit(ADD_CONFIG, { section, config });
            });
    },
    setRecentShow({ rootState, commit, state }, show) {
        commit('addRecentShow', { show });
        const config = {
            recentShows: state.recentShows
        };
        return rootState.auth.client.api.patch('config/main', config);
    },
    setCustomLogs({ rootState, commit }, logs) {
        // Convert back to object.
        const reducedLogs = logs.reduce((obj, item) => ({ ...obj, [item.identifier]: item.level }), {});

        return rootState.auth.client.api.patch('config/main', { logs: { custom: logs } })
            .then(() => {
                return commit(ADD_CONFIG, {
                    section: 'main', config: { logs: { custom: reducedLogs } }
                });
            });
    },
    setTraktSelectedLists({ rootState, commit }, selectedLists) {
        return rootState.auth.client.api.patch('config/main', { recommended: { trakt: { selectedLists } } })
            .then(() => {
                return commit('updateTraktSelectedLists', selectedLists);
            });
    }
};

export default {
    state,
    mutations,
    getters,
    actions
};

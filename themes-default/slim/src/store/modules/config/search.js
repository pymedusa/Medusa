import { ADD_CONFIG } from '../../mutation-types';

const state = {
    filters: {
        ignoreUnknownSubs: false,
        ignored: [
            'german',
            'french',
            'core2hd',
            'dutch',
            'swedish',
            'reenc',
            'MrLss',
            'dubbed'
        ],
        undesired: [
            'internal',
            'xvid'
        ],
        ignoredSubsList: [
            'dk',
            'fin',
            'heb',
            'kor',
            'nor',
            'nordic',
            'pl',
            'swe'
        ],
        required: [],
        preferred: []
    },
    general: {
        minDailySearchFrequency: 10,
        minBacklogFrequency: 720,
        dailySearchFrequency: 40,
        checkPropersInterval: '4h',
        usenetRetention: 500,
        maxCacheAge: 30,
        backlogDays: 7,
        torrentCheckerFrequency: 60,
        backlogFrequency: 720,
        cacheTrimming: false,
        downloadPropers: true,
        failedDownloads: {
            enabled: null,
            deleteFailed: null
        },
        minTorrentCheckerFrequency: 30,
        removeFromClient: false,
        randomizeProviders: false,
        propersSearchDays: 2,
        allowHighPriority: true,
        trackersList: [
            'udp://tracker.coppersurfer.tk:6969/announce',
            'udp://tracker.leechers-paradise.org:6969/announce',
            'udp://tracker.zer0day.to:1337/announce',
            'udp://tracker.opentrackr.org:1337/announce',
            'http://tracker.opentrackr.org:1337/announce',
            'udp://p4p.arenabg.com:1337/announce',
            'http://p4p.arenabg.com:1337/announce',
            'udp://explodie.org:6969/announce',
            'udp://9.rarbg.com:2710/announce',
            'http://explodie.org:6969/announce',
            'http://tracker.dler.org:6969/announce',
            'udp://public.popcorn-tracker.org:6969/announce',
            'udp://tracker.internetwarriors.net:1337/announce',
            'udp://ipv4.tracker.harry.lu:80/announce',
            'http://ipv4.tracker.harry.lu:80/announce',
            'udp://mgtracker.org:2710/announce',
            'http://mgtracker.org:6969/announce',
            'udp://tracker.mg64.net:6969/announce',
            'http://tracker.mg64.net:6881/announce',
            'http://torrentsmd.com:8080/announce'
        ]
    }
};

const mutations = {
    [ADD_CONFIG](state, { section, config }) {
        if (section === 'search') {
            state = Object.assign(state, config);
        }
    }
};

const getters = {};

const actions = {};

export default {
    state,
    mutations,
    getters,
    actions
};

<%inherit file="/layouts/main.mako"/>
<%!
    import json
    from medusa import app
%>
<%block name="scripts">
<%
## Convert boolean values
def js_bool(value):
    return 'true' if value else 'false'
%>
<script>
window.app = {};
window.app = new Vue({
    store,
    router,
    el: '#vue-wrap',
    data() {
        return {
            configLoaded: false,
            checkPropersIntervalLabels: [
                { text: '24 hours', value: 'daily' },
                { text: '4 hours', value: '4h' },
                { text: '90 mins', value: '90m' },
                { text: '45 mins', value: '45m' },
                { text: '30 mins', value: '30m' },
                { text: '15 mins', value: '15m' }
            ],
            nzbGetPriorityOptions: [
                { text: 'Very low', value: -100 },
                { text: 'Low', value: -50 },
                { text: 'Normal', value: 0 },
                { text: 'High', value: 50 },
                { text: 'Very high', value: 100 },
                { text: 'Force', value: 900 },

            ],

            // Static clients config
            clientsConfig: {
                torrent: {
                    blackhole: {
                        title: 'Black hole'
                    },
                    utorrent: {
                        title: 'uTorrent',
                        description: 'URL to your uTorrent client (e.g. http://localhost:8000)',
                        labelOption: true,
                        labelAnimeOption: true,
                        seedTimeOption: true,
                        pausedOption: true,
                        testStatus: 'Click below to test'
                    },
                    transmission: {
                        title: 'Transmission',
                        description: 'URL to your Transmission client (e.g. http://localhost:9091)',
                        pathOption: true,
                        removeFromClientOption: true,
                        seedLocationOption: true,
                        seedTimeOption: true,
                        pausedOption: true,
                        testStatus: 'Click below to test'
                    },
                    deluge: {
                        title: 'Deluge (via WebUI)',
                        shortTitle: 'Deluge',
                        description: 'URL to your Deluge client (e.g. http://localhost:8112)',
                        pathOption: true,
                        removeFromClientOption: true,
                        labelOption: true,
                        labelAnimeOption: true,
                        seedLocationOption: true,
                        pausedOption: true,
                        verifyCertOption: true,
                        testStatus: 'Click below to test'
                    },
                    deluged: {
                        title: 'Deluge (via Daemon)',
                        shortTitle: 'Deluge',
                        description: 'IP or Hostname of your Deluge Daemon (e.g. scgi://localhost:58846)',
                        pathOption: true,
                        removeFromClientOption: true,
                        labelOption: true,
                        labelAnimeOption: true,
                        seedLocationOption: true,
                        pausedOption: true,
                        verifyCertOption: true,
                        testStatus: 'Click below to test'
                    },
                    downloadstation: {
                        title: 'Synology DS',
                        description: 'URL to your Synology DS client (e.g. http://localhost:5000)',
                        pathOption: true,
                        testStatus: 'Click below to test'
                    },
                    rtorrent: {
                        title: 'rTorrent',
                        description: 'URL to your rTorrent client (e.g. scgi://localhost:5000 <br> or https://localhost/rutorrent/plugins/httprpc/action.php)',
                        pathOption: true,
                        labelOption: true,
                        labelAnimeOption: true,
                        verifyCertOption: true,
                        testStatus: 'Click below to test'
                    },
                    qbittorrent: {
                        title: 'qBittorrent',
                        description: 'URL to your qBittorrent client (e.g. http://localhost:8080)',
                        labelOption: true,
                        labelAnimeOption: true,
                        pausedOption: true,
                        testStatus: 'Click below to test'
                    },
                    mlnet: {
                        title: 'MLDonkey',
                        description: 'URL to your MLDonkey (e.g. http://localhost:4080)',
                        verifyCertOption: true,
                        testStatus: 'Click below to test'
                    }
                },
                nzb: {
                    blackhole: {
                        title: 'Black hole'
                    },
                    nzbget: {
                        title: 'NZBget',
                        description: 'NZBget RPC host name and port number (not NZBgetweb!) (e.g. localhost:6789)',
                        testStatus: 'Click below to test'
                    },
                    sabnzbd: {
                        title: 'SABnzbd',
                        description: 'URL to your SABnzbd server (e.g. http://localhost:8080/)',
                        testStatus: 'Click below to test'
                    }
                },
            },
            // Mapped from state module: clients.js
            clients: {
                torrents: {
                    authType: null,
                    dir: null,
                    enabled: null,
                    highBandwidth: null,
                    host: null,
                    label: null,
                    labelAnime: null,
                    method: null,
                    path: null,
                    paused: null,
                    rpcUrl: null,
                    seedLocation: null,
                    seedTime: null,
                    username: null,
                    password: null,
                    verifySSL: null
                },
                nzb: {
                    enabled: null,
                    method: null,
                    nzbget: {
                        category: null,
                        categoryAnime: null,
                        categoryAnimeBacklog: null,
                        categoryBacklog: null,
                        host: null,
                        priority: null,
                        useHttps: null,
                        username: null,
                        password: null
                    },
                    sabnzbd: {
                        category: null,
                        forced: null,
                        categoryAnime: null,
                        categoryBacklog: null,
                        categoryAnimeBacklog: null,
                        host: null,
                        username: null,
                        password: null,
                        apiKey: null
                    }
                }
            },
            // Mapped from state module: search.js
            search: {
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
                    deleteFailed: false,
                    downloadPropers: true,
                    useFailedDownloads: false,
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
            },
            httpAuthTypes: {
                none: 'None',
                basic: 'Basic',
                digest: 'Digest'
            },
        };
    },
    computed: {
        stateSearch() {
            return this.$store.state.search;
        },
        stateClients() {
            return this.$store.state.clients;
        },
        torrentUsernameIsDisabled() {
            const { clients } = this;
            const { torrents } = clients;
            const { host, method } = torrents;
            let torrentHost = host || '';
            if (!['rtorrent', 'deluge'].includes(method) || method === 'rtorrent' && !torrentHost.startsWith('scgi://')) {
                return false;
            }
            return true;
        },
        torrentPasswordIsDisabled() {
            const { clients } = this;
            const { torrents } = clients;
            const { host, method } = torrents;
            let torrentHost = host || '';
            if (method !== 'rtorrent' || method === 'rtorrent' && !torrentHost.startsWith('scgi://')) {
                return false;
            }
            return true;
        },
        authTypeIsDisabled() {
            const { clients } = this;
            const { torrents } = clients;
            const { host, method } = torrents;
            let torrentHost = host || '';
            if (method === 'rtorrent' && !torrentHost.startsWith('scgi://')) {
                return false;
            }
            return true;
        }
    },
    beforeMount() {
        $('#config-components').tabs();
    },
    methods: {
        async testTorrentClient() {
            const { clients } = this;
            const { torrents } = clients;
            const { method, host, username, password } = torrents;

            this.clientsConfig.torrent[method].testStatus = MEDUSA.config.loading;

            const params = {
                torrent_method: method,
                host,
                username,
                password
            };
            const resp = await apiRoute.get('home/testTorrent', { params });

            this.clientsConfig.torrent[method].testStatus = resp.data;
        },
        async testNzbget() {
            const { clients } = this;
            const { nzb } = clients;
            const { nzbget, method } = nzb;
            const { host, username, password, useHttps } = nzbget;

            this.clientsConfig.nzb.nzbget.testStatus = MEDUSA.config.loading;

            const params = {
                host,
                username,
                password,
                use_https: useHttps
            };
            const resp = await apiRoute.get('home/testNZBget', { params });

            this.clientsConfig.nzb.nzbget.testStatus = resp.data;
        },
        async testSabnzbd() {
            const { clients } = this;
            const { nzb } = clients;
            const { sabnzbd } = nzb;
            const { host, username, password, apiKey } = sabnzbd;

            this.clientsConfig.nzb.sabnzbd.testStatus = MEDUSA.config.loading;

            const params = {
                host,
                username,
                password,
                apikey: apiKey
            };
            const resp = await apiRoute.get('home/testSABnzbd', { params });

            this.clientsConfig.nzb.sabnzbd.testStatus = resp.data;
        },
        save() {
            const { $store, clients, configLoaded, search } = this;
            // We want to wait until the page has been fully loaded, before starting to save stuff.
            if (!configLoaded) {
                return;
            }
            // Disable the save button until we're done.
            this.saving = true;

            // Clone the config into a new object
            const config = Object.assign({}, {search}, {clients});

            const section = 'main';
            $store.dispatch('setConfig', { section, config }).then(() => {
                this.$snotify.success(
                    'Saved Search config',
                    'Saved',
                    { timeout: 5000 }
                );
            }).catch(() => {
                this.$snotify.error(
                    'Error while trying to save search config',
                    'Error'
                );
            });
        }
    },
    watch: {
        'clients.torrents.host'(host) {
            const { clients } = this;
            const { torrents } = clients;
            const { method } = torrents;

            if (method === 'rtorrent') {
                if (!host) {
                    return;
                }
                const isMatch = host.startsWith('scgi://');

                if (isMatch) {
                    this.clients.torrents.username = '';
                    this.clients.torrents.password = '';
                    this.clients.torrents.authType = 'none';
                }
            }

            if (method === 'deluge') {
                this.clients.torrents.username = '';
            }
        },
        'clients.torrents.method'(method) {
            if (!this.clientsConfig.torrent[method].removeFromClientOption) {
                this.search.general.removeFromClient = false;
            }
        }
    },
    mounted() {
        // The real vue stuff
        // This is used to wait for the config to be loaded by the store.
        this.$once('loaded', () => {
            const { clients, search, stateClients, stateSearch } = this;

            // Map the state values to local data.
            this.search = Object.assign({}, search, stateSearch);
            this.clients = Object.assign({}, clients, stateClients);
            this.configLoaded = true;
        });
    }
});
</script>
</%block>
<%block name="content">
<vue-snotify></vue-snotify>
<h1 class="header">{{ $route.meta.header }}</h1>
<div id="config">
    <div id="config-content">
        <form id="configForm" method="post" @submit.prevent="save()">
            <div id="config-components">
                <ul>
                    <li><app-link href="#episode-search">Episode Search</app-link></li>
                    <li><app-link href="#nzb-search">NZB Search</app-link></li>
                    <li><app-link href="#torrent-search">Torrent Search</app-link></li>
                </ul>
                <div id="episode-search">
                    <!-- general settings //-->
                    <div class="row component-group">
                        <div class="component-group-desc col-xs-12 col-md-2">
                            <h3>General Search Settings</h3>
                            <p>How to manage searching with <app-link href="config/providers">providers</app-link>.</p>
                        </div>

                        <div class="col-xs-12 col-md-10">
                            <fieldset class="component-group-list">
                                <config-toggle-slider v-model="search.general.randomizeProviders" label="Randomize Providers" id="randomize_providers" :explanations="['randomize the provider search order instead of going in order of placement']" ></config-toggle-slider>
                                <config-toggle-slider v-model="search.general.downloadPropers" label="Download propers" id="download_propers" :explanations="['replace original download with \'Proper\' or \'Repack\' if nuked']" ></config-toggle-slider>

                                <div v-show="search.general.downloadPropers">
                                    <config-template label="Check propers every" label-for="check_propers_interval">
                                        <select id="check_propers_interval" name="check_propers_interval" v-model="search.general.checkPropersInterval" class="form-control input-sm">
                                            <option v-for="option in checkPropersIntervalLabels" :value="option.value">
                                                {{option.text}}
                                            </option>
                                        </select>
                                    </config-template>

                                    <config-textbox-number :min="2" :max="7" :step="1" v-model.number="search.general.propersSearchDays" label="Proper search days" id="propers_search_days" :explanations="['how many days to keep searching for propers since episode airdate (default: 2 days)']"></config-textbox-number>

                                </div><!-- check propers -->

                                <config-textbox-number :min="1" :step="1" v-model.number="search.general.backlogDays" label="Forced backlog search day(s)" id="backlog_days" :explanations="['how many days to search in the past for a forced backlog search (default: 7 days)']"></config-textbox-number>

                                <config-textbox-number :min="search.general.minBacklogFrequency" :step="1" v-model.number="search.general.backlogFrequency" label="Backlog search interval" id="backlog_frequency">
                                    <p>time in minutes between searches (min. {{search.general.minBacklogFrequency}})</p>
                                </config-textbox-number>

                                <config-textbox-number :min="search.general.minDailySearchFrequency" :step="1" v-model.number="search.general.dailySearchFrequency" label="Daily search interval" id="daily_frequency">
                                    <p>time in minutes between searches (min. {{search.general.minDailySearchFrequency}})</p>
                                </config-textbox-number>

                                <config-toggle-slider v-if="clientsConfig.torrent[clients.torrents.method]" v-show="clientsConfig.torrent[clients.torrents.method].removeFromClientOption" v-model="search.general.removeFromClient" label="Remove torrents from client" id="remove_from_client">
                                    <p>Remove torrent from client (also torrent data) when provider ratio is reached</p>
                                    <p><b>Note:</b> For now only Transmission and Deluge are supported</p>
                                </config-toggle-slider>

                                <config-textbox-number v-show="search.general.removeFromClient" :min="search.general.minTorrentCheckerFrequency" :step="1" v-model.number="search.general.torrentCheckerFrequency" label="Frequency to check torrents ratio" id="torrent_checker_frequency" :explanations="['Frequency in minutes to check torrent\'s ratio (default: 60)']"></config-textbox-number>


                                <config-textbox-number :min="1" :step="1" v-model.number="search.general.usenetRetention" label="Usenet retention" id="usenet_retention" :explanations="['age limit in days for usenet articles to be used (e.g. 500)']"></config-textbox-number>

                                <config-template label-for="trackers_list" label="Trackers list">
                                    <select-list name="trackers_list" id="trackers_list" :list-items="search.general.trackersList" @change="search.general.trackersList = $event.map(x => x.value)"></select-list>
                                    Trackers that will be added to magnets without trackers<br>
                                    separate trackers with a comma, e.g. "tracker1, tracker2, tracker3"
                                </config-template>

                                <config-toggle-slider v-model="search.general.allowHighPriority" label="Allow high priority" id="allow_high_priority" :explanations="['set downloads of recently aired episodes to high priority']" ></config-toggle-slider>


                                <config-toggle-slider v-model="search.general.useFailedDownloads" label="Use Failed Downloads" id="use_failed_downloads" :explanations="['Use Failed Download Handling?',
                                    'Will only work with snatched/downloaded episodes after enabling this']" >
                                </config-toggle-slider>


                                <config-toggle-slider v-show="search.general.useFailedDownloads" v-model="search.general.deleteFailed" label="Delete Failed" id="delete_failed">
                                    Delete files left over from a failed download?<br>
                                    <b>NOTE:</b> This only works if Use Failed Downloads is enabled.
                                </config-toggle-slider>


                                <config-toggle-slider v-model="search.general.cacheTrimming" label="Cache Trimming" id="cache_trimming" :explanations="['Enable trimming of provider cache']" ></config-toggle-slider>

                                <config-textbox-number v-show="search.general.cacheTrimming" :min="1" :step="1" v-model.number="search.general.maxCacheAge" label="Cache Retention" id="max_cache_age" :explanations="['Number of days to retain results in cache.  Results older than this will be removed if cache trimming is enabled.']"></config-textbox-number>

                                <input type="submit" class="btn-medusa config_submitter" value="Save Changes" />
                            </fieldset>
                        </div><!-- /general settings //-->
                    </div><!-- /row -->

                    <!-- search filters //-->
                    <div class="row component-group">
                        <div class="component-group-desc col-xs-12 col-md-2">
                            <h3>Search Filters</h3>
                            <p>Options to filter search results</p>
                        </div>
                        <div class="col-xs-12 col-md-10">
                            <fieldset class="component-group-list">
                                <config-template label-for="ignore_words" label="Ignore words">
                                    <select-list name="ignore_words" id="ignore_words" :list-items="search.filters.ignored" @change="search.filters.ignored = $event.map(x => x.value)"></select-list>
                                    results with any words from this list will be ignored
                                </config-template>

                                <config-template label-for="undesired_words" label="Undesired words">
                                    <select-list name="undesired_words" id="undesired_words" :list-items="search.filters.undesired" @change="search.filters.undesired = $event.map(x => x.value)"></select-list>
                                    results with words from this list will only be selected as a last resort
                                </config-template>

                                <config-template label-for="preferred_words" label="Preferred words">
                                    <select-list name="preferred_words" id="preferred_words" :list-items="search.filters.preferred" @change="search.filters.preferred = $event.map(x => x.value)"></select-list>
                                    results with one or more word from this list will be chosen over others
                                </config-template>

                                <config-template label-for="require_words" label="Require words">
                                    <select-list name="require_words" id="require_words" :list-items="search.filters.required" @change="search.filters.required = $event.map(x => x.value)"></select-list>
                                    results must include at least one word from this list
                                </config-template>

                                <config-template label-for="ignored_subs_list" label="Ignore language names in subbed results">
                                    <select-list name="ignored_subs_list" id="ignored_subs_list" :list-items="search.filters.ignoredSubsList" @change="search.filters.ignoredSubsList = $event.map(x => x.value)"></select-list>
                                    Ignore subbed releases based on language names <br>
                                    Example: "dk" will ignore words: dksub, dksubs, dksubbed, dksubed <br>
                                </config-template>

                                <config-toggle-slider v-model="search.filters.ignoreUnknownSubs" label="Ignore unknown subbed releases" id="ignore_und_subs" :explanations="['Ignore subbed releases without language names', 'Filter words: subbed, subpack, subbed, subs, etc.)']"></config-toggle-slider>

                                <input type="submit" class="btn-medusa config_submitter" value="Save Changes" />
                            </fieldset>
                        </div><!-- /col //-->
                    </div><!-- /row //-->
                </div><!-- /#episode-search //-->


                <div id="nzb-search">
                    <div class="row component-group">
                        <div class="component-group-desc col-xs-12 col-md-2">
                            <h3>NZB Search</h3>
                            <p>How to handle NZB search results.</p>
                            <div id="nzb_method_icon" :class="'add-client-icon-' + clients.nzb.method"></div>
                        </div>
                        <div class="col-xs-12 col-md-10">
                            <fieldset class="component-group-list">
                                <config-toggle-slider v-model="clients.nzb.enabled" label="Search NZBs" id="use_nzbs" :explanations="['enable NZB search providers']"></config-toggle-slider>

                                <div v-show="clients.nzb.enabled">
                                    <config-template label-for="nzb_method" label="Send .nzb files to">
                                        <select v-model="clients.nzb.method" name="nzb_method" id="nzb_method" class="form-control input-sm">
                                            <option v-for="(client, name) in clientsConfig.nzb" :value="name">{{client.title}}</option>
                                        </select>
                                    </config-template>

                                    <config-template v-show="clients.nzb.method === 'blackhole'" id="blackhole_settings" label-for="nzb_dir" label="Black hole folder location">
                                        <file-browser name="nzb_dir" title="Select .nzb black hole location" :initial-dir="clients.nzb.dir" @update="clients.nzb.dir = $event"></file-browser>
                                        <div class="clear-left">
                                            <p><b>.nzb</b> files are stored at this location for external software to find and use</p>
                                        </div>
                                    </config-template>


                                    <div v-if="clients.nzb.method" v-show="clients.nzb.method === 'sabnzbd'" id="sabnzbd_settings">

                                        <config-textbox v-model="clients.nzb.sabnzbd.host" label="SABnzbd server URL" id="sab_host" :explanations="['username for your KODI server (blank for none)']" @change="save()">
                                            <div class="clear-left">
                                                <p v-html="clientsConfig.nzb[clients.nzb.method].description"></p>
                                            </div>
                                        </config-textbox>

                                        <config-textbox v-model="clients.nzb.sabnzbd.username" label="SABnzbd username" id="sab_username" :explanations="['(blank for none)']"></config-textbox>
                                        <config-textbox v-model="clients.nzb.sabnzbd.password" type="password" label="SABnzbd password" id="sab_password" :explanations="['(blank for none)']"></config-textbox>
                                        <config-textbox v-model="clients.nzb.sabnzbd.apiKey" label="SABnzbd API key" id="sab_apikey" :explanations="['locate at... SABnzbd Config -> General -> API Key']"></config-textbox>
                                        <config-textbox v-model="clients.nzb.sabnzbd.category" label="Use SABnzbd category" id="sab_category" :explanations="['add downloads to this category (e.g. TV)']"></config-textbox>
                                        <config-textbox v-model="clients.nzb.sabnzbd.categoryBacklog" label="Use SABnzbd category (backlog episodes)" id="sab_category_backlog" :explanations="['add downloads of old episodes to this category (e.g. TV)']"></config-textbox>
                                        <config-textbox v-model="clients.nzb.sabnzbd.categoryAnime" label="Use SABnzbd category for anime" id="sab_category_anime" :explanations="['add anime downloads to this category (e.g. anime)']"></config-textbox>
                                        <config-textbox v-model="clients.nzb.sabnzbd.categoryAnimeBacklog" label="Use SABnzbd category for anime (backlog episodes)" id="sab_category_anime_backlog" :explanations="['add anime downloads of old episodes to this category (e.g. anime)']"></config-textbox>
                                        <config-toggle-slider v-model="clients.nzb.sabnzbd.forced" label="Use forced priority" id="sab_forced" :explanations="['enable to change priority from HIGH to FORCED']" ></config-toggle-slider>

                                        <div class="testNotification" v-show="clientsConfig.nzb.sabnzbd.testStatus" v-html="clientsConfig.nzb.sabnzbd.testStatus"></div>
                                        <input @click="testSabnzbd" type="button" value="Test SABnzbd" class="btn-medusa test-button"/>
                                        <input type="submit" class="btn-medusa config_submitter" value="Save Changes" /><br>
                                    </div>

                                    <div v-if="clients.nzb.method" v-show="clients.nzb.method === 'nzbget'" id="nzbget_settings">

                                        <config-toggle-slider v-model="clients.nzb.nzbget.useHttps" label="Connect using HTTP" id="nzbget_use_https">
                                            <p><b>note:</b> enable Secure control in NZBGet and set the correct Secure Port here</p>
                                        </config-toggle-slider>

                                        <config-textbox v-model="clients.nzb.nzbget.host" label="NZBget host:port" id="nzbget_host">
                                            <p v-if="clientsConfig.nzb[clients.nzb.method]" v-html="clientsConfig.nzb[clients.nzb.method].description"></p>
                                        </config-textbox>

                                        <config-textbox v-model="clients.nzb.nzbget.username" label="NZBget username" id="nzbget_username" :explanations="['locate in nzbget.conf (default:nzbget)']"></config-textbox>
                                        <config-textbox v-model="clients.nzb.nzbget.password" type="password" label="NZBget password" id="nzbget_password" :explanations="['locate in nzbget.conf (default:tegbzn6789)']"></config-textbox>
                                        <config-textbox v-model="clients.nzb.nzbget.category" label="Use NZBget category" id="nzbget_category" :explanations="['send downloads marked this category (e.g. TV)']"></config-textbox>
                                        <config-textbox v-model="clients.nzb.nzbget.categoryBacklog" label="Use NZBget category (backlog episodes)" id="nzbget_category_backlog" :explanations="['send downloads of old episodes marked this category (e.g. TV)']"></config-textbox>
                                        <config-textbox v-model="clients.nzb.nzbget.categoryAnime" label="Use NZBget category for anime" id="nzbget_category_anime" :explanations="['send anime downloads marked this category (e.g. anime)']"></config-textbox>
                                        <config-textbox v-model="clients.nzb.nzbget.categoryAnimeBacklog" label="Use NZBget category for anime (backlog episodes)" id="nzbget_category_anime_backlog" :explanations="['send anime downloads of old episodes marked this category (e.g. anime)']"></config-textbox>

                                        <config-template label-for="nzbget_priority" label="NZBget priority">
                                            <select name="nzbget_priority" id="nzbget_priority" v-model="clients.nzb.nzbget.priority" class="form-control input-sm">
                                                <option v-for="option in nzbGetPriorityOptions" :value="option.value">{{option.text}}</option>
                                            </select>
                                            <span>priority for daily snatches (no backlog)</span>
                                        </config-template>

                                        <div class="testNotification" v-show="clientsConfig.nzb.nzbget.testStatus" v-html="clientsConfig.nzb.nzbget.testStatus"></div>
                                        <input @click="testNzbget" type="button" value="Test NZBget" class="btn-medusa test-button"/>
                                        <input type="submit" class="btn-medusa config_submitter" value="Save Changes" /><br>
                                    </div><!-- /nzb.enabled //-->
                                </div>
                            </fieldset>
                        </div>
                    </div> <!-- /row -->
                </div><!-- /#nzb-search //-->

                <div id="torrent-search">
                    <div class="row component-group">
                        <div class="component-group-desc col-xs-12 col-md-2">
                            <h3>Torrent Search</h3>
                            <p>How to handle Torrent search results.</p>
                            <div id="torrent_method_icon" :class="'add-client-icon-' + clients.torrents.method"></div>
                        </div>
                        <div class="col-xs-12 col-md-10">
                            <fieldset class="component-group-list">

                                <config-toggle-slider v-model="clients.torrents.enabled" label="Search torrents" id="use_torrents" :explanations="['enable torrent search providers']"></config-toggle-slider>
                                <div v-show="clients.torrents.enabled">

                                    <config-template label-for="torrent_method" label="Send .torrent files to">
                                        <select v-model="clients.torrents.method" name="torrent_method" id="torrent_method" class="form-control input-sm">
                                            <option v-for="(client, name) in clientsConfig.torrent" :value="name">{{client.title}}</option>
                                        </select>
                                    </config-template>

                                    <div v-if="clients.torrents.method" v-show="clients.torrents.method === 'blackhole'">
                                        <config-template label-for="torrent_dir" label="Black hole folder location">
                                            <file-browser name="torrent_dir" title="Select .torrent black hole location" :initial-dir="clients.torrents.dir" @update="clients.torrents.dir = $event"></file-browser>
                                            <p><b>.torrent</b> files are stored at this location for external software to find and use</p>
                                        </config-template>
                                        <input type="submit" class="btn-medusa config_submitter" value="Save Changes" /><br>
                                    </div>

                                    <div v-if="clients.torrents.method" v-show="clients.torrents.method !== 'blackhole'">

                                        <config-textbox v-model="clients.torrents.host" :label="clientsConfig.torrent[clients.torrents.method].shortTitle || clientsConfig.torrent[clients.torrents.method].title + ' host:port'" id="torrent_host">
                                            <p v-html="clientsConfig.torrent[clients.torrents.method].description"></p>
                                        </config-textbox>

                                        <config-textbox v-show="clients.torrents.method === 'transmission'" v-model="clients.torrents.rpcUrl" :label="clientsConfig.torrent[clients.torrents.method].shortTitle || clientsConfig.torrent[clients.torrents.method].title + ' RPC URL'" id="rpcurl_title">
                                            <p id="rpcurl_desc_">The path without leading and trailing slashes (e.g. transmission)</p>
                                        </config-textbox>

                                        <config-template v-show="!authTypeIsDisabled" label-for="torrent_auth_type" label="Http Authentication">
                                            <select v-model="clients.torrents.authType" name="torrent_auth_type" id="torrent_auth_type" class="form-control input-sm">
                                                <option v-for="(title, name) in httpAuthTypes" :value="name">{{title}}</option>
                                            </select>
                                        </config-template>

                                        <config-toggle-slider v-show="clientsConfig.torrent[clients.torrents.method].verifyCertOption" v-model="clients.torrents.verifyCert" label="Verify certificate" id="torrent_verify_cert">
                                            <p>Verify SSL certificates for HTTPS requests</p>
                                            <p v-show="clients.torrents.method === 'deluge'">disable if you get "Deluge: Authentication Error" in your log</p>
                                        </config-toggle-slider>

                                        <config-textbox v-show="!torrentUsernameIsDisabled"
                                            v-model="clients.torrents.username" :label="(clientsConfig.torrent[clients.torrents.method].shortTitle || clientsConfig.torrent[clients.torrents.method].title) + ' username'" id="torrent_username" :explanations="['(blank for none)']">
                                        </config-textbox>

                                        <config-textbox type="password" v-show="!torrentPasswordIsDisabled"
                                            v-model="clients.torrents.password" :label="(clientsConfig.torrent[clients.torrents.method].shortTitle || clientsConfig.torrent[clients.torrents.method].title) + ' password'" id="torrent_password" :explanations="['(blank for none)']">
                                        </config-textbox>

                                        <div v-show="clientsConfig.torrent[clients.torrents.method].labelOption" id="torrent_label_option">
                                            <config-textbox v-model="clients.torrents.label" label="Add label to torrent" id="torrent_label">
                                                <span v-show="['deluge', 'deluged'].includes(clients.torrents.method)">
                                                    <p>(blank spaces are not allowed)</p>
                                                    <p>note: label plugin must be enabled in Deluge clients</p>
                                                </span>
                                                <span v-show="clients.torrents.method === 'qbittorrent'"><p>(blank spaces are not allowed)</p>
                                                    <p>note: for qBitTorrent 3.3.1 and up</p>
                                                </span>
                                                <span v-show="clients.torrents.method === 'utorrent'">
                                                    <p>Global label for torrents.<br>
                                                    <b>%N:</b> use Series-Name as label (can be used with other text)</p>
                                                </span>
                                            </config-textbox>
                                        </div>

                                        <div v-show="clientsConfig.torrent[clients.torrents.method].labelAnimeOption">
                                            <config-textbox v-model="clients.torrents.labelAnime" label="Add label to torrent for anime" id="torrent_label_anime">
                                                <span v-show="['deluge', 'deluged'].includes(clients.torrents.method)">
                                                    <p>(blank spaces are not allowed)</p>
                                                    <p>note: label plugin must be enabled in Deluge clients</p>
                                                </span>
                                                <span v-show="clients.torrents.method === 'qbittorrent'"><p>(blank spaces are not allowed)</p>
                                                    <p>note: for qBitTorrent 3.3.1 and up</p>
                                                <span v-show="clients.torrents.method === 'utorrent'">
                                                    <p>Global label for torrents.<br>
                                                    <b>%N:</b> use Series-Name as label (can be used with other text)</p>
                                                </span>
                                            </config-textbox>
                                        </div>

                                        <config-template v-show="clientsConfig.torrent[clients.torrents.method].pathOption" label-for="torrent_client" label="Downloaded files location">
                                                <file-browser name="torrent_path" title="Select downloaded files location" :initial-dir="clients.torrents.path" @update="clients.torrents.path = $event"></file-browser>
                                                <p>where <span id="torrent_client" v-if="clientsConfig.torrent[clients.torrents.method]">{{clientsConfig.torrent[clients.torrents.method].shortTitle || clientsConfig.torrent[clients.torrents.method].title}}</span> will save downloaded files (blank for client default)
                                                    <span v-show="clients.torrents.method === 'downloadstation'"> <b>note:</b> the destination has to be a shared folder for Synology DS</span>
                                                </p>
                                        </config-template>

                                        <config-template v-show="clientsConfig.torrent[clients.torrents.method].seedLocationOption" label-for="torrent_seed_location" label="Post-Processed seeding torrents location">
                                                <file-browser name="torrent_seed_location" title="Select torrent seed location" :initial-dir="clients.torrents.seedLocation" @update="clients.torrents.seedLocation = $event"></file-browser>
                                                <p>
                                                    where <span id="torrent_client_seed_path">{{clientsConfig.torrent[clients.torrents.method].shortTitle || clientsConfig.torrent[clients.torrents.method].title}}</span> will move Torrents after Post-Processing<br/>
                                                    <b>Note:</b> If your Post-Processor method is set to hard/soft link this will move your torrent
                                                    to another location after Post-Processor to prevent reprocessing the same file over and over.
                                                    This feature does a "Set Torrent location" or "Move Torrent" like in client
                                                </p>
                                        </config-template>

                                        <config-textbox-number v-show="clientsConfig.torrent[clients.torrents.method].seedTimeOption" :min="-1" :step="1" v-model.number="clients.torrents.seedTime" :label="clients.torrents.method === 'transmission' ? 'Stop seeding when inactive for' : 'Minimum seeding time is'" id="torrent_seed_time" :explanations="['hours. (default: \'0\' passes blank to client and \'-1\' passes nothing)']"></config-textbox-number>

                                        <config-toggle-slider v-show="clientsConfig.torrent[clients.torrents.method].pausedOption" v-model="clients.torrents.paused" label="Start torrent paused" id="torrent_paused">
                                            <p>add .torrent to client but do <b style="font-weight:900;">not</b> start downloading</p>
                                        </config-toggle-slider>

                                        <config-toggle-slider v-show="clients.torrents.method === 'transmission'" v-model="clients.torrents.highBandwidth" label="Allow high bandwidth" id="torrent_high_bandwidth" :explanations="['use high bandwidth allocation if priority is high']"></config-toggle-slider>

                                        <div class="testNotification" v-show="clientsConfig.torrent[clients.torrents.method].testStatus" v-html="clientsConfig.torrent[clients.torrents.method].testStatus"></div>
                                        <input @click="testTorrentClient" type="button" value="Test Connection" class="btn-medusa test-button"/>
                                        <input type="submit" class="btn-medusa config_submitter" value="Save Changes" /><br>
                                    </div>
                                </div><!-- /torrent.enabled //-->
                            </fieldset>
                        </div>
                    </div>
                </div><!-- /#torrent-search //-->
                <br>
                <h6 class="pull-right"><b>All non-absolute folder locations are relative to <span class="path">{{config.dataDir}}</span></b> </h6>
                <input type="submit" class="btn-medusa pull-left config_submitter button" value="Save Changes" />
            </div><!-- /config-components //-->
        </form>
    </div>
</div>
</%block>

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
            clients: {
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
                        pausedOption: true
                    },
                    transmission: {
                        title: 'Transmission',
                        description: 'URL to your Transmission client (e.g. http://localhost:9091)',
                        pathOption: true,
                        removeFromClientOption: true,
                        seedLocationOption: true,
                        seedTimeOption: true,
                        pausedOption: true,
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
                        verifyCertOption: true
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
                        verifyCertOption: true
                    },
                    download_station: {
                        title: 'Synology DS',
                        description: 'URL to your Synology DS client (e.g. http://localhost:5000)'
                    },
                    rtorrent: {
                        title: 'rTorrent',
                        description: 'URL to your rTorrent client (e.g. scgi://localhost:5000 <br> or https://localhost/rutorrent/plugins/httprpc/action.php)',
                        pathOption: true,
                        labelOption: true,
                        labelAnimeOption: true,
                        verifyCertOption: true
                    },
                    qbittorrent: {
                        title: 'qBittorrent',
                        description: 'URL to your qBittorrent client (e.g. http://localhost:8080)',
                        labelOption: true,
                        labelAnimeOption: true,
                        pausedOption: true
                    },
                    mlnet: {
                        title: 'MLDonkey',
                        description: 'URL to your MLDonkey (e.g. http://localhost:4080)',
                        verifyCertOption: true
                    }
                },
                nzb: {
                    blackhole: {
                        title: 'Black hole'
                    },
                    nzbget: {
                        title: 'NZBget',
                        description: 'NZBget RPC host name and port number (not NZBgetweb!) (e.g. localhost:6789)'
                    },
                    sabnzbd: {
                        title: 'SABnzbd',
                        description: 'URL to your SABnzbd server (e.g. http://localhost:8080/)'
                    }
                },
            },
            torrent: {
                enabled: ${js_bool(app.USE_TORRENTS)},
                dir: ${json.dumps(app.TORRENT_DIR)},
                method: ${json.dumps(app.TORRENT_METHOD)},
                host: ${json.dumps(app.TORRENT_HOST)},
                rpcUrl: ${json.dumps(app.TORRENT_RPCURL)},
                username: ${json.dumps(app.TORRENT_USERNAME)},
                password: ${json.dumps(app.TORRENT_PASSWORD)},
                label: ${json.dumps(app.TORRENT_LABEL)},
                labelAnime: ${json.dumps(app.TORRENT_LABEL_ANIME)},
                path: ${json.dumps(app.TORRENT_PATH)},
                seedLocation: ${json.dumps(app.TORRENT_SEED_LOCATION)},
                seedTime: ${json.dumps(app.TORRENT_SEED_TIME)},
                testStatus: 'Click below to test',
                authType: ${json.dumps(app.TORRENT_AUTH_TYPE)},
                verifyCert: ${js_bool(app.TORRENT_VERIFY_CERT)},
                paused: ${js_bool(app.TORRENT_PAUSED)},
                highBandwidth: ${js_bool(app.TORRENT_HIGH_BANDWIDTH)},
            },
            nzb: {
                enabled: ${js_bool(app.USE_NZBS)},
                dir: ${json.dumps(app.NZB_DIR)},
                method: ${json.dumps(app.NZB_METHOD)},
                nzbget: {
                    useHttps: ${js_bool(app.NZBGET_USE_HTTPS)},
                    host: ${json.dumps(app.NZBGET_HOST)},
                    username: ${json.dumps(app.NZBGET_USERNAME)},
                    password: ${json.dumps(app.NZBGET_PASSWORD)},
                    testStatus: 'Click below to test',
                    category: ${json.dumps(app.NZBGET_CATEGORY)},
                    categoryBacklog: ${json.dumps(app.NZBGET_CATEGORY_BACKLOG)},
                    categoryAnime: ${json.dumps(app.NZBGET_CATEGORY_ANIME)},
                    categoryAnimeBacklog: ${json.dumps(app.NZBGET_CATEGORY_ANIME_BACKLOG)},
                    priority: ${app.NZBGET_PRIORITY},
                    priorityOptions: {
                        'Very low': -100,
                        'Low': -50,
                        'Normal': 0,
                        'High': 50,
                        'Very high': 100,
                        'Force': 900
                    }
                },
                sabnzbd: {
                    host: ${json.dumps(app.SAB_HOST)},
                    username: ${json.dumps(app.SAB_USERNAME)},
                    password: ${json.dumps(app.SAB_PASSWORD)},
                    apiKey: ${json.dumps(app.SAB_APIKEY)},
                    testStatus: 'Click below to test',
                    category: ${json.dumps(app.SAB_CATEGORY)},
                    categoryBacklog: ${json.dumps(app.SAB_CATEGORY_BACKLOG)},
                    categoryAnime: ${json.dumps(app.SAB_CATEGORY_ANIME)},
                    categoryAnimeBacklog: ${json.dumps(app.SAB_CATEGORY_ANIME_BACKLOG)},
                    forced: ${js_bool(app.SAB_FORCED)}
                }
            },
            httpAuthTypes: {
                none: 'None',
                basic: 'Basic',
                digest: 'Digest'
            },

            // Episode Search: General Config
            randomizeProviders: ${js_bool(app.RANDOMIZE_PROVIDERS)},
            downloadPropers: ${js_bool(app.DOWNLOAD_PROPERS)},
            checkPropersInterval: ${json.dumps(app.CHECK_PROPERS_INTERVAL)},
            propersIntervalLabels: ${json.dumps(app.PROPERS_INTERVAL_LABELS)},
            propersSearchDays: ${app.PROPERS_SEARCH_DAYS},
            backlogDays: ${app.BACKLOG_DAYS},
            backlogFrequency: ${app.BACKLOG_FREQUENCY},
            minBacklogFrequency: ${app.MIN_BACKLOG_FREQUENCY},
            dailySearchFrequency: ${app.DAILYSEARCH_FREQUENCY},
            minDailySearchFrequency: ${app.MIN_DAILYSEARCH_FREQUENCY},
            removeFromClient: ${js_bool(app.REMOVE_FROM_CLIENT and app.TORRENT_METHOD in ('transmission', 'deluge', 'deluged'))},
            torrentCheckerFrequency: ${app.TORRENT_CHECKER_FREQUENCY},
            minTorrentCheckerFrequency: ${app.MIN_TORRENT_CHECKER_FREQUENCY},
            usenetRetention: ${app.USENET_RETENTION},
            trackersList: ${json.dumps(app.TRACKERS_LIST)}.join(', '),
            allowHighPriority: ${js_bool(app.ALLOW_HIGH_PRIORITY)},
            useFailedDownloads: ${js_bool(app.USE_FAILED_DOWNLOADS)},
            deleteFailed: ${js_bool(app.DELETE_FAILED)},
            cacheTrimming: ${js_bool(app.CACHE_TRIMMING)},
            maxCacheAge: ${app.MAX_CACHE_AGE},

            // Episode Search: Search Filters
            ignoreWords: ${json.dumps(app.IGNORE_WORDS)}.join(', '),
            undesiredWords: ${json.dumps(app.UNDESIRED_WORDS)}.join(', '),
            preferredWords: ${json.dumps(app.PREFERRED_WORDS)}.join(', '),
            requireWords: ${json.dumps(app.REQUIRE_WORDS)}.join(', '),
            ignoredSubsList: ${json.dumps(app.IGNORED_SUBS_LIST)}.join(', '),
            ignoreUndSubs: ${js_bool(app.IGNORE_UND_SUBS)},

            // Global
            dataDir: ${json.dumps(app.DATA_DIR)},
        };
    },
    beforeMount() {
        $('#config-components').tabs();
    },
    methods: {
        async testTorrentClient() {
            const { torrent } = this;
            const { method, host, username, password } = torrent;

            this.torrent.testStatus = MEDUSA.config.loading;

            const params = {
                torrent_method: method,
                host,
                username,
                password
            };
            const resp = await apiRoute.get('home/testTorrent', { params });

            this.torrent.testStatus = resp.data;
        },
        async testNzbget() {
            const { nzb } = this;
            const { nzbget } = nzb;
            const { host, username, password, useHttps } = nzbget;

            this.nzb.nzbget.testStatus = MEDUSA.config.loading;

            const params = {
                host,
                username,
                password,
                use_https: useHttps
            };
            const resp = await apiRoute.get('home/testNZBget', { params });

            this.nzb.nzbget.testStatus = resp.data;
        },
        async testSabnzbd() {
            const { nzb } = this;
            const { sabnzbd } = nzb;
            const { host, username, password, apiKey } = sabnzbd;

            this.nzb.sabnzbd.testStatus = MEDUSA.config.loading;

            const params = {
                host,
                username,
                password,
                apikey: apiKey
            };
            const resp = await apiRoute.get('home/testSABnzbd', { params });

            this.nzb.sabnzbd.testStatus = resp.data;
        }
    },
    watch: {
        'torrent.host'(host) {
            const { torrent } = this;
            const { method } = torrent;

            if (method === 'rtorrent') {
                const isMatch = host.startsWith('scgi://');

                if (isMatch) {
                    this.torrent.username = '';
                    this.torrent.password = '';
                    this.torrent.authType = 'none';
                }
            }

            if (method === 'deluge') {
                this.torrent.username = '';
            }
        },
        'torrent.method'(method) {
            if (!this.clients.torrent[method].removeFromClientOption) {
                this.removeFromClient = false;
            }
        }
    }
});
</script>
</%block>
<%block name="content">
<h1 class="header">{{ $route.meta.header }}</h1>
<div id="config">
    <div id="config-content">
        <form id="configForm" action="config/search/saveSearch" method="post">
            <div id="config-components">
                <ul>
                    <li><app-link href="#episode-search">Episode Search</app-link></li>
                    <li><app-link href="#nzb-search">NZB Search</app-link></li>
                    <li><app-link href="#torrent-search">Torrent Search</app-link></li>
                </ul>
                <div id="episode-search">
                    <!-- general settings //-->
                    <div class="component-group-desc-legacy">
                        <h3>General Search Settings</h3>
                        <p>How to manage searching with <app-link href="config/providers">providers</app-link>.</p>
                    </div>
                    <div class="component-group">
                        <fieldset class="component-group-list">
                            <div class="field-pair">
                                <label for="randomize_providers">
                                    <span class="component-title">Randomize Providers</span>
                                    <span class="component-desc">
                                        <input type="checkbox" name="randomize_providers" id="randomize_providers" v-model="randomizeProviders"/>
                                        <p>randomize the provider search order instead of going in order of placement</p>
                                    </span>
                                </label>
                            </div><!-- randomize providers -->
                            <div class="field-pair">
                                <label for="download_propers">
                                    <span class="component-title">Download propers</span>
                                    <span class="component-desc">
                                        <input type="checkbox" name="download_propers" id="download_propers" v-model="downloadPropers"/>
                                        <p>replace original download with "Proper" or "Repack" if nuked</p>
                                    </span>
                                </label>
                            </div><!-- download propers -->
                            <div v-show="downloadPropers">
                                <div class="field-pair">
                                    <label for="check_propers_interval">
                                        <span class="component-title">Check propers every:</span>
                                        <span class="component-desc">
                                            <select id="check_propers_interval" name="check_propers_interval" v-model="checkPropersInterval" class="form-control input-sm">
                                                <option v-for="(label, interval) in propersIntervalLabels" :value="interval">{{label}}</option>
                                            </select>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label>
                                        <span class="component-title">Proper search days</span>
                                        <span class="component-desc">
                                            <input type="number" min="2" max="7" step="1" name="propers_search_days" v-model.number="propersSearchDays" class="form-control input-sm input75"/>
                                            <p>how many days to keep searching for propers since episode airdate (default: 2 days)</p>
                                        </span>
                                    </label>
                                </div><!-- check propers -->
                            </div>
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">Forced backlog search day(s)</span>
                                    <span class="component-desc">
                                        <input type="number" min="1" step="1" name="backlog_days" v-model.number="backlogDays" class="form-control input-sm input75"/>
                                        <p>number of day(s) that the "Forced Backlog Search" will cover (e.g. 7 Days)</p>
                                    </span>
                                </label>
                            </div><!-- backlog days -->
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">Backlog search frequency</span>
                                    <span class="component-desc">
                                        <input type="number" :min="minBacklogFrequency" step="1" name="backlog_frequency" v-model.number="backlogFrequency" class="form-control input-sm input75"/>
                                        <p>time in minutes between searches (min. {{minBacklogFrequency}})</p>
                                    </span>
                                </label>
                            </div><!-- backlog frequency -->
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">Daily search frequency</span>
                                    <span class="component-desc">
                                        <input type="number" :min="minDailySearchFrequency" step="1" name="dailysearch_frequency" v-model.number="dailySearchFrequency" class="form-control input-sm input75"/>
                                        <p>time in minutes between searches (min. {{minDailySearchFrequency}})</p>
                                    </span>
                                </label>
                            </div><!-- daily search frequency -->
                            <div class="field-pair" v-show="clients.torrent[torrent.method].removeFromClientOption">
                                <label for="remove_from_client">
                                    <span class="component-title">Remove torrents from client</span>
                                    <span class="component-desc">
                                        <input type="checkbox" name="remove_from_client" id="remove_from_client" v-model="removeFromClient"/>
                                        <p>Remove torrent from client (also torrent data) when provider ratio is reached</p>
                                        <p><b>Note:</b> For now only Transmission and Deluge are supported</p>
                                    </span>
                                </label>
                            </div>
                            <div v-show="removeFromClient">
                                <div class="field-pair">
                                    <label>
                                        <span class="component-title">Frequency to check torrents ratio</span>
                                        <span class="component-desc">
                                            <input type="number" :min="minTorrentCheckerFrequency" step="1" name="torrent_checker_frequency" v-model.number="torrentCheckerFrequency" class="form-control input-sm input75"/>
                                            <p>Frequency in minutes to check torrent's ratio (default: 60)</p>
                                        </span>
                                    </label>
                                </div>
                            </div>
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">Usenet retention</span>
                                    <span class="component-desc">
                                        <input type="number" min="1" step="1" name="usenet_retention" v-model.number="usenetRetention" class="form-control input-sm input75"/>
                                        <p>age limit in days for usenet articles to be used (e.g. 500)</p>
                                    </span>
                                </label>
                            </div><!-- usenet retention -->
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">Trackers list</span>
                                    <span class="component-desc">
                                        <input type="text" name="trackers_list" v-model="trackersList" class="form-control input-sm input350"/>
                                        <div class="clear-left">
                                            Trackers that will be added to magnets without trackers<br>
                                            separate trackers with a comma, e.g. "tracker1, tracker2, tracker3"
                                        </div>
                                    </span>
                                </label>
                            </div><!-- trackers -->
                            <div class="field-pair">
                                <label for="allow_high_priority">
                                    <span class="component-title">Allow high priority</span>
                                    <span class="component-desc">
                                        <input type="checkbox" name="allow_high_priority" id="allow_high_priority" v-model="allowHighPriority"/>
                                        <p>set downloads of recently aired episodes to high priority</p>
                                    </span>
                                </label>
                            </div><!-- high priority -->
                            <div class="field-pair">
                                <label for="use_failed_downloads">
                                    <span class="component-title">Use Failed Downloads</span>
                                    <span class="component-desc">
                                        <input id="use_failed_downloads" type="checkbox" name="use_failed_downloads" v-model="useFailedDownloads"/>
                                        Use Failed Download Handling?<br>
                                        Will only work with snatched/downloaded episodes after enabling this
                                    </span>
                                </label>
                            </div><!-- use failed -->
                            <div class="field-pair" v-show="useFailedDownloads">
                                <label for="delete_failed">
                                    <span class="component-title">Delete Failed</span>
                                    <span class="component-desc">
                                        <input id="delete_failed" type="checkbox" name="delete_failed" v-model="deleteFailed"/>
                                        Delete files left over from a failed download?<br>
                                        <b>NOTE:</b> This only works if Use Failed Downloads is enabled.
                                    </span>
                                </label>
                            </div><!-- delete failed -->
                            <div class="field-pair">
                                <label for="cache_trimming">
                                    <span class="component-title">Cache Trimming</span>
                                    <span class="component-desc">
                                        <input id="cache_trimming" type="checkbox" name="cache_trimming" v-model="cacheTrimming"/>
                                        Enable trimming of provider cache<br>
                                    </span>
                                </label>
                            </div><!-- cache trimming -->
                            <div class="field-pair" v-show="cacheTrimming">
                                <label for="max_cache_age">
                                    <span class="component-title">Cache Retention</span>
                                    <span class="component-desc">
                                        <input type="number" min="1" step="1" name="max_cache_age" id="max_cache_age" v-model.number="maxCacheAge" class="form-control input-sm input75"/>
                                        days<br>
                                        <br>
                                        Number of days to retain results in cache.  Results older than this will be removed if cache trimming is enabled.
                                    </span>
                                </label>
                            </div><!-- max cache age -->
                            <input type="submit" class="btn-medusa config_submitter" value="Save Changes" />
                        </fieldset>
                    </div><!-- /general settings //-->
                    <!-- search filters //-->
                    <div class="component-group-desc-legacy">
                        <h3>Search Filters</h3>
                        <p>Options to filter search results</p>
                    </div>
                    <div class="component-group">
                        <fieldset class="component-group-list">
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">Ignore words</span>
                                    <span class="component-desc">
                                        <input type="text" name="ignore_words" v-model="ignoreWords" class="form-control input-sm input350"/>
                                        <div class="clear-left">
                                            results with any words from this list will be ignored<br>
                                            separate words with a comma, e.g. "word1,word2,word3"
                                        </div>
                                    </span>
                                </label>
                            </div><!-- ignored words -->
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">Undesired words</span>
                                    <span class="component-desc">
                                        <input type="text" name="undesired_words" v-model="undesiredWords" class="form-control input-sm input350"/>
                                        <div class="clear-left">
                                            results with words from this list will only be selected as a last resort<br>
                                            separate words with a comma, e.g. "word1, word2, word3"
                                        </div>
                                    </span>
                                </label>
                            </div><!-- undesired words -->
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">Preferred words</span>
                                    <span class="component-desc">
                                        <input type="text" name="preferred_words" v-model="preferredWords" class="form-control input-sm input350"/>
                                        <div class="clear-left">
                                            results with one or more word from this list will be chosen over others<br>
                                            separate words with a comma, e.g. "word1, word2, word3"
                                        </div>
                                    </span>
                                </label>
                            </div><!-- preferred words -->
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">Require words</span>
                                    <span class="component-desc">
                                        <input type="text" name="require_words" v-model="requireWords" class="form-control input-sm input350"/>
                                        <div class="clear-left">
                                            results must include at least one word from this list<br>
                                            separate words with a comma, e.g. "word1,word2,word3"
                                        </div>
                                    </span>
                                </label>
                            </div><!-- required words -->
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">Ignore language names in subbed results</span>
                                    <span class="component-desc">
                                        <input type="text" name="ignored_subs_list" v-model="ignoredSubsList" class="form-control input-sm input350"/>
                                        <div class="clear-left">
                                            Ignore subbed releases based on language names <br>
                                            Example: "dk" will ignore words: dksub, dksubs, dksubbed, dksubed <br>
                                            separate languages with a comma, e.g. "lang1, lang2, lang3"
                                        </div>
                                    </span>
                                </label>
                            </div><!-- subbed results -->
                            <div class="field-pair">
                                <label for="ignore_und_subs">
                                    <span class="component-title">Ignore unknown subbed releases</span>
                                    <span class="component-desc">
                                        <input type="checkbox" name="ignore_und_subs" id="ignore_und_subs" v-model="ignoreUndSubs"/>
                                        Ignore subbed releases without language names <br>
                                        Filter words: subbed, subpack, subbed, subs, etc.)
                                    </span>
                                </label>
                            </div><!-- ignore unknown subs -->
                            <input type="submit" class="btn-medusa config_submitter" value="Save Changes" />
                        </fieldset>
                    </div><!-- /search filters //-->
                </div><!-- /#episode-search //-->
                <div id="nzb-search" class="component-group">
                    <div class="component-group-desc-legacy">
                        <h3>NZB Search</h3>
                        <p>How to handle NZB search results.</p>
                        <div id="nzb_method_icon" :class="'add-client-icon-' + nzb.method"></div>
                    </div>
                    <fieldset class="component-group-list">
                        <div class="field-pair">
                            <label for="use_nzbs">
                                <span class="component-title">Search NZBs</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="use_nzbs" id="use_nzbs" v-model="nzb.enabled"/>
                                    <p>enable NZB search providers</p>
                                </span>
                            </label>
                        </div>
                        <div v-show="nzb.enabled">
                            <div class="field-pair">
                                <label for="nzb_method">
                                    <span class="component-title">Send .nzb files to:</span>
                                    <span class="component-desc">
                                        <select v-model="nzb.method" name="nzb_method" id="nzb_method" class="form-control input-sm">
                                            <option v-for="(client, name) in clients.nzb" :value="name">{{client.title}}</option>
                                        </select>
                                    </span>
                                </label>
                            </div>
                            <div v-show="nzb.method === 'blackhole'" id="blackhole_settings">
                                <div class="field-pair">
                                    <label>
                                        <span class="component-title">Black hole folder location</span>
                                        <span class="component-desc">
                                            <file-browser name="nzb_dir" title="Select .nzb black hole location" :initial-dir="nzb.dir" @update="nzb.dir = $event"></file-browser>
                                            <div class="clear-left">
                                                <p><b>.nzb</b> files are stored at this location for external software to find and use</p>
                                            </div>
                                        </span>
                                    </label>
                                </div>
                            </div>
                            <div v-show="nzb.method === 'sabnzbd'" id="sabnzbd_settings">
                                <div class="field-pair">
                                    <label>
                                        <span class="component-title">SABnzbd server URL</span>
                                        <span class="component-desc">
                                            <input v-model="nzb.sabnzbd.host" type="text" id="sab_host" name="sab_host" class="form-control input-sm input350"/>
                                            <div class="clear-left">
                                                <p v-html="clients.nzb[nzb.method].description"></p>
                                            </div>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label>
                                        <span class="component-title">SABnzbd username</span>
                                        <span class="component-desc">
                                            <input v-model="nzb.sabnzbd.username" type="text" name="sab_username" id="sab_username" class="form-control input-sm input200" autocomplete="no" />
                                            <p>(blank for none)</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label>
                                        <span class="component-title">SABnzbd password</span>
                                        <span class="component-desc">
                                            <input v-model="nzb.sabnzbd.password" type="password" name="sab_password" id="sab_password" class="form-control input-sm input200" autocomplete="no"/>
                                            <p>(blank for none)</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label>
                                        <span class="component-title">SABnzbd API key</span>
                                        <span class="component-desc">
                                            <input v-model="nzb.sabnzbd.apiKey" type="text" name="sab_apikey" id="sab_apikey" class="form-control input-sm input350"/>
                                            <div class="clear-left"><p>locate at... SABnzbd Config -> General -> API Key</p></div>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label>
                                        <span class="component-title">Use SABnzbd category</span>
                                        <span class="component-desc">
                                            <input type="text" name="sab_category" id="sab_category" v-model="nzb.sabnzbd.category" class="form-control input-sm input200"/>
                                            <p>add downloads to this category (e.g. TV)</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label>
                                        <span class="component-title">Use SABnzbd category (backlog episodes)</span>
                                        <span class="component-desc">
                                            <input type="text" name="sab_category_backlog" id="sab_category_backlog" v-model="nzb.sabnzbd.categoryBacklog" class="form-control input-sm input200"/>
                                            <p>add downloads of old episodes to this category (e.g. TV)</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label>
                                        <span class="component-title">Use SABnzbd category for anime</span>
                                        <span class="component-desc">
                                            <input type="text" name="sab_category_anime" id="sab_category_anime" v-model="nzb.sabnzbd.categoryAnime" class="form-control input-sm input200"/>
                                            <p>add anime downloads to this category (e.g. anime)</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label>
                                        <span class="component-title">Use SABnzbd category for anime (backlog episodes)</span>
                                        <span class="component-desc">
                                            <input type="text" name="sab_category_anime_backlog" id="sab_category_anime_backlog" v-model="nzb.sabnzbd.categoryAnimeBacklog" class="form-control input-sm input200"/>
                                            <p>add anime downloads of old episodes to this category (e.g. anime)</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair" v-show="allowHighPriority">
                                    <label for="sab_forced">
                                        <span class="component-title">Use forced priority</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="sab_forced" id="sab_forced" v-model="nzb.sabnzbd.forced"/>
                                            <p>enable to change priority from HIGH to FORCED</p></span>
                                    </label>
                                </div>
                                <div class="testNotification" v-show="nzb.sabnzbd.testStatus" v-html="nzb.sabnzbd.testStatus"></div>
                                <input @click="testSabnzbd" type="button" value="Test SABnzbd" class="btn-medusa test-button"/>
                                <input type="submit" class="btn-medusa config_submitter" value="Save Changes" /><br>
                            </div>
                            <div v-show="nzb.method === 'nzbget'" id="nzbget_settings">
                                <div class="field-pair">
                                    <label for="nzbget_use_https">
                                        <span class="component-title">Connect using HTTPS</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="nzbget_use_https" id="nzbget_use_https" v-model="nzb.nzbget.useHttps"/>
                                            <p><b>note:</b> enable Secure control in NZBGet and set the correct Secure Port here</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label>
                                        <span class="component-title">NZBget host:port</span>
                                        <span class="component-desc">
                                            <input type="text" name="nzbget_host" id="nzbget_host" v-model="nzb.nzbget.host" class="form-control input-sm input350"/>
                                            <div class="clear-left">
                                                <p v-html="clients.nzb[nzb.method].description"></p>
                                            </div>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label>
                                        <span class="component-title">NZBget username</span>
                                        <span class="component-desc">
                                            <input type="text" name="nzbget_username" id="nzbget_username" v-model="nzb.nzbget.username" class="form-control input-sm input200" autocomplete="no" />
                                            <p>locate in nzbget.conf (default:nzbget)</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label>
                                        <span class="component-title">NZBget password</span>
                                        <span class="component-desc">
                                            <input type="password" name="nzbget_password" id="nzbget_password" v-model="nzb.nzbget.password" class="form-control input-sm input200" autocomplete="no"/>
                                            <p>locate in nzbget.conf (default:tegbzn6789)</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label>
                                        <span class="component-title">Use NZBget category</span>
                                        <span class="component-desc">
                                            <input type="text" name="nzbget_category" id="nzbget_category" v-model="nzb.nzbget.category" class="form-control input-sm input200"/>
                                            <p>send downloads marked this category (e.g. TV)</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label>
                                        <span class="component-title">Use NZBget category (backlog episodes)</span>
                                        <span class="component-desc">
                                            <input type="text" name="nzbget_category_backlog" id="nzbget_category_backlog" v-model="nzb.nzbget.categoryBacklog" class="form-control input-sm input200"/>
                                            <p>send downloads of old episodes marked this category (e.g. TV)</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label>
                                        <span class="component-title">Use NZBget category for anime</span>
                                        <span class="component-desc">
                                            <input type="text" name="nzbget_category_anime" id="nzbget_category_anime" v-model="nzb.nzbget.categoryAnime" class="form-control input-sm input200"/>
                                            <p>send anime downloads marked this category (e.g. anime)</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label>
                                        <span class="component-title">Use NZBget category for anime (backlog episodes)</span>
                                        <span class="component-desc">
                                            <input type="text" name="nzbget_category_anime_backlog" id="nzbget_category_anime_backlog" v-model="nzb.nzbget.categoryAnimeBacklog" class="form-control input-sm input200"/>
                                            <p>send anime downloads of old episodes marked this category (e.g. anime)</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label>
                                        <span class="component-title">NZBget priority</span>
                                        <span class="component-desc">
                                            <select name="nzbget_priority" id="nzbget_priority" v-model="nzb.nzbget.priority" class="form-control input-sm">
                                                <option v-for="(value, title) in nzb.nzbget.priorityOptions" :value="value">{{title}}</option>
                                            </select>
                                            <span>priority for daily snatches (no backlog)</span>
                                        </span>
                                    </label>
                                </div>
                                <div class="testNotification" v-show="nzb.nzbget.testStatus" v-html="nzb.nzbget.testStatus"></div>
                                <input @click="testNzbget" type="button" value="Test NZBget" class="btn-medusa test-button"/>
                                <input type="submit" class="btn-medusa config_submitter" value="Save Changes" /><br>
                            </div><!-- /nzb.enabled //-->
                        </div>
                    </fieldset>
                </div><!-- /#nzb-search //-->
                <div id="torrent-search" class="component-group">
                    <div class="component-group-desc-legacy">
                        <h3>Torrent Search</h3>
                        <p>How to handle Torrent search results.</p>
                        <div id="torrent_method_icon" :class="'add-client-icon-' + torrent.method"></div>
                    </div>
                    <fieldset class="component-group-list">
                        <div class="field-pair">
                            <label for="use_torrents">
                                <span class="component-title">Search torrents</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="use_torrents" id="use_torrents" v-model="torrent.enabled"/>
                                    <p>enable torrent search providers</p>
                                </span>
                            </label>
                        </div>
                        <div v-show="torrent.enabled">
                            <div class="field-pair">
                                <label for="torrent_method">
                                    <span class="component-title">Send .torrent files to:</span>
                                    <span class="component-desc">
                                        <select v-model="torrent.method" name="torrent_method" id="torrent_method" class="form-control input-sm">
                                            <option v-for="(client, name) in clients.torrent" :value="name">{{client.title}}</option>
                                        </select>
                                    </span>
                                </label>
                            </div>
                            <div v-show="torrent.method === 'blackhole'">
                                <div class="field-pair">
                                    <label>
                                        <span class="component-title">Black hole folder location</span>
                                        <span class="component-desc">
                                            <file-browser name="torrent_dir" title="Select .torrent black hole location" :initial-dir="torrent.dir" @update="torrent.dir = $event"></file-browser>
                                            <div class="clear-left">
                                                <p><b>.torrent</b> files are stored at this location for external software to find and use</p>
                                            </div>
                                        </span>
                                    </label>
                                </div>
                                <input type="submit" class="btn-medusa config_submitter" value="Save Changes" /><br>
                            </div>
                            <div v-show="torrent.method !== 'blackhole'">
                                <div class="field-pair">
                                    <label>
                                        <span class="component-title" id="host_title">{{clients.torrent[torrent.method].shortTitle || clients.torrent[torrent.method].title}} host:port</span>
                                        <span class="component-desc">
                                            <input type="text" name="torrent_host" id="torrent_host" v-model="torrent.host" class="form-control input-sm input350"/>
                                            <div class="clear-left">
                                                <p v-html="clients.torrent[torrent.method].description"></p>
                                            </div>
                                        </span>
                                    </label>
                                </div>
                                <div v-show="torrent.method === 'transmission'" class="field-pair" id="torrent_rpcurl_option">
                                    <label>
                                        <span class="component-title" id="rpcurl_title">{{clients.torrent[torrent.method].shortTitle || clients.torrent[torrent.method].title}} RPC URL</span>
                                        <span class="component-desc">
                                            <input type="text" name="torrent_rpcurl" id="torrent_rpcurl" v-model="torrent.rpcUrl" class="form-control input-sm input350"/>
                                            <div class="clear-left">
                                                <p id="rpcurl_desc_">The path without leading and trailing slashes (e.g. transmission)</p>
                                            </div>
                                        </span>
                                    </label>
                                </div>
                                <div v-show="torrent.method === 'rtorrent' && !torrent.host.startsWith('scgi://')" class="field-pair" id="torrent_auth_type_option">
                                    <label>
                                        <span class="component-title">Http Authentication</span>
                                        <span class="component-desc">
                                            <select v-model="torrent.authType" name="torrent_auth_type" id="torrent_auth_type" class="form-control input-sm">
                                                <option v-for="(title, name) in httpAuthTypes" :value="name">{{title}}</option>
                                            </select>
                                            <p></p>
                                        </span>
                                    </label>
                                </div>
                                <div v-show="clients.torrent[torrent.method].verifyCertOption" class="field-pair">
                                    <label for="torrent_verify_cert">
                                        <span class="component-title">Verify certificate</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="torrent_verify_cert" id="torrent_verify_cert" v-model="torrent.verifyCert"/>
                                            <p>Verify SSL certificates for HTTPS requests</p>
                                            <p v-show="torrent.method === 'deluge'">disable if you get "Deluge: Authentication Error" in your log</p>
                                        </span>
                                    </label>
                                </div>
                                <div v-show="!['rtorrent', 'deluge'].includes(torrent.method) || (torrent.method === 'rtorrent' && !torrent.host.startsWith('scgi://'))" class="field-pair" id="torrent_username_option">
                                    <label>
                                        <span class="component-title" id="username_title">{{clients.torrent[torrent.method].shortTitle || clients.torrent[torrent.method].title}} username</span>
                                        <span class="component-desc">
                                            <input type="text" name="torrent_username" id="torrent_username" v-model="torrent.username" class="form-control input-sm input200" autocomplete="no" />
                                            <p>(blank for none)</p>
                                        </span>
                                    </label>
                                </div>
                                <div v-show="torrent.method !== 'rtorrent' || (torrent.method === 'rtorrent' && !torrent.host.startsWith('scgi://'))" class="field-pair" id="torrent_password_option">
                                    <label>
                                        <span class="component-title" id="password_title">{{clients.torrent[torrent.method].shortTitle || clients.torrent[torrent.method].title}} password</span>
                                        <span class="component-desc">
                                            <input type="password" name="torrent_password" id="torrent_password" v-model="torrent.password" class="form-control input-sm input200" autocomplete="no"/>
                                            <p>(blank for none)</p>
                                        </span>
                                    </label>
                                </div>
                                <div v-show="clients.torrent[torrent.method].labelOption" class="field-pair" id="torrent_label_option">
                                    <label>
                                        <span class="component-title">Add label to torrent</span>
                                        <span class="component-desc">
                                            <input type="text" name="torrent_label" id="torrent_label" v-model="torrent.label" class="form-control input-sm input200"/>
                                            <span v-show="['deluge', 'deluged'].includes(torrent.method)"><p>(blank spaces are not allowed)</p>
                                                <div class="clear-left"><p>note: label plugin must be enabled in Deluge clients</p></div>
                                            </span>
                                            <span v-show="torrent.method === 'qbittorrent'"><p>(blank spaces are not allowed)</p>
                                                <div class="clear-left"><p>note: for qBitTorrent 3.3.1 and up</p></div>
                                            </span>
                                            <span v-show="torrent.method === 'utorrent'">
                                                <div class="clear-left"><p>Global label for torrents.<br>
                                                <b>%N:</b> use Series-Name as label (can be used with other text)</p></div>
                                            </span>
                                        </span>
                                    </label>
                                </div>
                                <div v-show="clients.torrent[torrent.method].labelAnimeOption" class="field-pair">
                                    <label>
                                        <span class="component-title">Add label to torrent for anime</span>
                                        <span class="component-desc">
                                            <input type="text" name="torrent_label_anime" id="torrent_label_anime" v-model="torrent.labelAnime" class="form-control input-sm input200"/>
                                            <span v-show="['deluge', 'deluged'].includes(torrent.method)"><p>(blank spaces are not allowed)</p>
                                                <div class="clear-left"><p>note: label plugin must be enabled in Deluge clients</p></div>
                                            </span>
                                            <span v-show="torrent.method === 'qbittorrent'"><p>(blank spaces are not allowed)</p>
                                                <div class="clear-left"><p>note: for qBitTorrent 3.3.1 and up</p></div>
                                            </span>
                                            <span v-show="torrent.method === 'utorrent'">
                                                <div class="clear-left"><p>Global label for torrents.<br>
                                                <b>%N:</b> use Series-Name as label (can be used with other text)</p></div>
                                            </span>
                                        </span>
                                    </label>
                                </div>
                                <div v-show="clients.torrent[torrent.method].pathOption" class="field-pair" id="torrent_path_option">
                                    <label>
                                        <span class="component-title" id="directory_title">Downloaded files location</span>
                                        <span class="component-desc">
                                            <file-browser name="torrent_path" title="Select downloaded files location" :initial-dir="torrent.path" @update="torrent.path = $event"></file-browser>
                                            <div class="clear-left"><p>where <span id="torrent_client">{{clients.torrent[torrent.method].shortTitle || clients.torrent[torrent.method].title}}</span> will save downloaded files (blank for client default)
                                                <span v-show="torrent.method === 'download_station'"> <b>note:</b> the destination has to be a shared folder for Synology DS</span></p>
                                            </div>
                                        </span>
                                    </label>
                                </div>
                                <div v-show="clients.torrent[torrent.method].seedLocationOption" class="field-pair">
                                    <label>
                                        <span class="component-title" id="directory_title">Post-Processed seeding torrents location</span>
                                        <span class="component-desc">
                                            <file-browser name="torrent_seed_location" title="Select torrent seed location" :initial-dir="torrent.seedLocation" @update="torrent.seedLocation = $event"></file-browser>
                                            <div class="clear-left">
                                                <p>
                                                    where <span id="torrent_client_seed_path">{{clients.torrent[torrent.method].shortTitle || clients.torrent[torrent.method].title}}</span> will move Torrents after Post-Processing<br/>
                                                    <b>Note:</b> If your Post-Processor method is set to hard/soft link this will move your torrent
                                                    to another location after Post-Processor to prevent reprocessing the same file over and over.
                                                    This feature does a "Set Torrent location" or "Move Torrent" like in client
                                                </p>
                                            </div>
                                        </span>
                                    </label>
                                </div>
                                <div v-show="clients.torrent[torrent.method].seedTimeOption" class="field-pair" id="torrent_seed_time_option">
                                    <label>
                                        <span class="component-title" id="torrent_seed_time_label">{{torrent.method === 'transmission' ? 'Stop seeding when inactive for' : 'Minimum seeding time is'}}</span>
                                        <span class="component-desc">
                                            <input type="number" step="1" name="torrent_seed_time" id="torrent_seed_time" v-model="torrent.seedTime" class="form-control input-sm input100" />
                                            <p>hours. (default: '0' passes blank to client and '-1' passes nothing)</p>
                                        </span>
                                    </label>
                                </div>
                                <div v-show="clients.torrent[torrent.method].pausedOption" class="field-pair" id="torrent_paused_option">
                                    <label>
                                        <span class="component-title">Start torrent paused</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="torrent_paused" id="torrent_paused" v-model="torrent.paused"/>
                                            <p>add .torrent to client but do <b style="font-weight:900;">not</b> start downloading</p>
                                        </span>
                                    </label>
                                </div>
                                <div v-show="torrent.method === 'transmission'" class="field-pair">
                                    <label>
                                        <span class="component-title">Allow high bandwidth</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="torrent_high_bandwidth" id="torrent_high_bandwidth" v-model="torrent.highBandwidth"/>
                                            <p>use high bandwidth allocation if priority is high</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="testNotification" v-show="torrent.testStatus" v-html="torrent.testStatus"></div>
                                <input @click="testTorrentClient" type="button" value="Test Connection" class="btn-medusa test-button"/>
                                <input type="submit" class="btn-medusa config_submitter" value="Save Changes" /><br>
                            </div>
                        </div><!-- /torrent.enabled //-->
                    </fieldset>
                </div><!-- /#torrent-search //-->
                <br>
                <h6 class="pull-right"><b>All non-absolute folder locations are relative to <span class="path">{{dataDir}}</span></b> </h6>
                <input type="submit" class="btn-medusa pull-left config_submitter button" value="Save Changes" />
            </div><!-- /config-components //-->
        </form>
    </div>
</div>
</%block>

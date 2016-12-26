<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import app
    from medusa import clients
%>
<%block name="content">
% if not header is UNDEFINED:
<h1 class="header">${header}</h1>
% else:
<h1 class="title">${title}</h1>
% endif
<div id="config">
    <div id="config-content">
        <form id="configForm" action="config/search/saveSearch" method="post">
            <div id="config-components">
                <ul>
                    ## @TODO: Fix this stupid hack
                    <script>document.write('<li><a href="' + document.location.href + '#episode-search">Episode Search</a></li>');</script>
                    <script>document.write('<li><a href="' + document.location.href + '#nzb-search">NZB Search</a></li>');</script>
                    <script>document.write('<li><a href="' + document.location.href + '#torrent-search">Torrent Search</a></li>');</script>
                </ul>
                <div id="episode-search">
                        <div class="component-group-desc">
                            <h3>General Search Settings</h3>
                            <p>How to manage searching with <a href="config/providers">providers</a>.</p>
                        </div>
                    <div class="component-group">
                        <fieldset class="component-group-list">
                            <div class="field-pair">
                                <label for="randomize_providers">
                                    <span class="component-title">Randomize Providers</span>
                                    <span class="component-desc">
                                        <input type="checkbox" name="randomize_providers" id="randomize_providers" class="enabler" ${'checked="checked"' if app.RANDOMIZE_PROVIDERS else ''}/>
                                        <p>randomize the provider search order instead of going in order of placement</p>
                                    </span>
                                </label>
                            </div><!-- randomize providers -->
                            <div class="field-pair">
                                <label for="download_propers">
                                    <span class="component-title">Download propers</span>
                                    <span class="component-desc">
                                        <input type="checkbox" name="download_propers" id="download_propers" class="enabler" ${'checked="checked"' if app.DOWNLOAD_PROPERS else ''}/>
                                        <p>replace original download with "Proper" or "Repack" if nuked</p>
                                    </span>
                                </label>
                            </div><!-- download propers -->
                            <div id="content_download_propers">
                                <div class="field-pair">
                                    <label for="check_propers_interval">
                                        <span class="component-title">Check propers every:</span>
                                        <span class="component-desc">
                                            <select id="check_propers_interval" name="check_propers_interval" class="form-control input-sm">
    <% check_propers_interval_text = {'daily': "24 hours", '4h': "4 hours", '90m': "90 mins", '45m': "45 mins", '15m': "15 mins"} %>
    % for curInterval in ('daily', '4h', '90m', '45m', '15m'):
                                                <option value="${curInterval}" ${'selected="selected"' if app.CHECK_PROPERS_INTERVAL == curInterval else ''}>${check_propers_interval_text[curInterval]}</option>
    % endfor
                                            </select>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label>
                                        <span class="component-title">Proper search days</span>
                                        <span class="component-desc">
                                            <input type="number" min="2" max="7" step="1" name="propers_search_days" value="${app.PROPERS_SEARCH_DAYS}" class="form-control input-sm input75"/>
                                            <p>how many days to keep searching for propers since episode airdate (default: 2 days)</p>
                                        </span>
                                    </label>
                                </div><!-- check propers -->
                            </div>
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">Backlog search day(s)</span>
                                    <span class="component-desc">
                                        <input type="number" min="1" step="1" name="backlog_days" value="${app.BACKLOG_DAYS}" class="form-control input-sm input75"/>
                                        <p>number of day(s) that the "Forced Backlog Search" will cover (e.g. 7 Days)</p>
                                    </span>
                                </label>
                            </div><!-- backlog days -->
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">Backlog search frequency</span>
                                    <span class="component-desc">
                                        <input type="number" min="720" step="1" name="backlog_frequency" value="${app.BACKLOG_FREQUENCY}" class="form-control input-sm input75"/>
                                        <p>time in minutes between searches (min. ${app.MIN_BACKLOG_FREQUENCY})</p>
                                    </span>
                                </label>
                            </div><!-- backlog frequency -->
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">Daily search frequency</span>
                                    <span class="component-desc">
                                        <input type="number" min="10" step="1" name="dailysearch_frequency" value="${app.DAILYSEARCH_FREQUENCY}" class="form-control input-sm input75"/>
                                        <p>time in minutes between searches (min. ${app.MIN_DAILYSEARCH_FREQUENCY})</p>
                                        </span>
                                </label>
                            </div><!-- daily search frequency -->
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">Usenet retention</span>
                                    <span class="component-desc">
                                        <input type="number" min="1" step="1" name="usenet_retention" value="${app.USENET_RETENTION}" class="form-control input-sm input75"/>
                                        <p>age limit in days for usenet articles to be used (e.g. 500)</p>
                                    </span>
                                </label>
                            </div><!-- usenet retention -->
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">Trackers list</span>
                                    <span class="component-desc">
                                        <input type="text" name="trackers_list" value="${app.TRACKERS_LIST}" class="form-control input-sm input350"/>
                                        <div class="clear-left">Trackers that will be added to magnets without trackers<br>
                                        separate trackers with a comma, e.g. "tracker1,tracker2,tracker3"
                                        </div>
                                    </span>
                                </label>
                            </div><!-- trackers -->
                            <div class="field-pair">
                                <label for="allow_high_priority">
                                    <span class="component-title">Allow high priority</span>
                                    <span class="component-desc">
                                        <input type="checkbox" name="allow_high_priority" id="allow_high_priority" ${'checked="checked"' if app.ALLOW_HIGH_PRIORITY else ''}/>
                                        <p>set downloads of recently aired episodes to high priority</p>
                                    </span>
                                </label>
                            </div><!-- high priority -->
                            <div class="field-pair">
                                <label for="use_failed_downloads">
                                    <span class="component-title">Use Failed Downloads</span>
                                    <span class="component-desc">
                                        <input id="use_failed_downloads" type="checkbox" class="enabler" name="use_failed_downloads" ${'checked="checked"' if app.USE_FAILED_DOWNLOADS else ''} />
                                        Use Failed Download Handling?<br>
                                        Will only work with snatched/downloaded episodes after enabling this
                                    </span>
                                </label>
                            </div><!-- use failed -->
                            <div class="field-pair">
                                <label for="delete_failed">
                                    <span class="component-title">Delete Failed</span>
                                    <span class="component-desc">
                                        <input id="delete_failed" type="checkbox" name="delete_failed" ${'checked="checked"' if app.DELETE_FAILED else ''}/>
                                        Delete files left over from a failed download?<br>
                                        <b>NOTE:</b> This only works if Use Failed Downloads is enabled.
                                    </span>
                                </label>
                            </div><!-- delete failed -->
                            <div class="field-pair">
                                <label for="cache_trimming">
                                    <span class="component-title">Cache Trimming</span>
                                    <span class="component-desc">
                                        <input id="cache_trimming" type="checkbox" name="cache_trimming" ${'checked="checked"' if app.CACHE_TRIMMING else ''}/>
                                        Enable trimming of provider cache<br>
                                    </span>
                                </label>
                            </div><!-- cache trimming -->
                            <div class="field-pair">
                                <label for="max_cache_age">
                                    <span class="component-title">Cache Retention</span>
                                    <span class="component-desc">
                                        <input type="number" min="1" step="1" name="max_cache_age" id="max_cache_age" value="${app.MAX_CACHE_AGE}" class="form-control input-sm input75"/>
                                        days<br>
                                        <br>
                                        Number of days to retain results in cache.  Results older than this will be removed if cache trimming is enabled.
                                    </span>
                                </label>
                            </div><!-- max cache age -->
                            <input type="submit" class="btn config_submitter" value="Save Changes" />
                        </fieldset>
                    </div><!-- general settings -->
                        <div class="component-group-desc">
                            <h3>Search Filters</h3>
                            <p>Options to filter search results</p>
                        </div>
                        <div class="component-group">
                        <fieldset class="component-group-list">
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">Ignore words</span>
                                    <span class="component-desc">
                                        <input type="text" name="ignore_words" value="${app.IGNORE_WORDS}" class="form-control input-sm input350"/>
                                        <div class="clear-left">results with any words from this list will be ignored<br>
                                        separate words with a comma, e.g. "word1,word2,word3"
                                        </div>
                                    </span>
                                </label>
                            </div><!-- ignored words -->
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">Undesired words</span>
                                    <span class="component-desc">
                                        <input type="text" name="undesired_words" value="${app.UNDESIRED_WORDS}" class="form-control input-sm input350"/>
                                        <div class="clear-left">results with words from this list will only be selected as a last resort<br>
                                        separate words with a comma, e.g. "word1,word2,word3"
                                        </div>
                                    </span>
                                </label>
                            </div><!-- undesired words -->
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">Preferred words</span>
                                    <span class="component-desc">
                                        <input type="text" name="preferred_words" value="${app.PREFERRED_WORDS}" class="form-control input-sm input350"/>
                                        <div class="clear-left">results with one or more word from this list will be chosen over others<br>
                                        separate words with a comma, e.g. "word1,word2,word3"
                                        </div>
                                    </span>
                                </label>
                            </div><!-- preferred words -->
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">Require words</span>
                                    <span class="component-desc">
                                        <input type="text" name="require_words" value="${app.REQUIRE_WORDS}" class="form-control input-sm input350"/>
                                        <div class="clear-left">results must include at least one word from this list<br>
                                        separate words with a comma, e.g. "word1,word2,word3"
                                        </div>
                                    </span>
                                </label>
                            </div><!-- required words -->
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">Ignore language names in subbed results</span>
                                    <span class="component-desc">
                                        <input type="text" name="ignored_subs_list" value="${app.IGNORED_SUBS_LIST}" class="form-control input-sm input350"/>
                                        <div class="clear-left">Ignore subbed releases based on language names <br>
                                        Example: "dk" will ignore words: dksub, dksubs, dksubbed, dksubed <br>
                                        separate languages with a comma, e.g. "lang1,lang2,lang3
                                        </div>
                                    </span>
                                </label>
                            </div><!-- subbed results -->
                            <div class="field-pair">
                                <label for="ignore_und_subs">
                                    <span class="component-title">Ignore unknown subbed releases</span>
                                    <span class="component-desc">
                                        <input type="checkbox" name="ignore_und_subs" id="ignore_und_subs" ${'checked="checked"' if app.IGNORE_UND_SUBS else ''}/>
                                        Ignore subbed releases without language names <br>
                                        Filter words: subbed, subpack, subbed, subs, etc.)
                                    </span>
                                </label>
                            </div><!-- ignore unknown subs -->
                            <input type="submit" class="btn config_submitter" value="Save Changes" />
                        </fieldset>
                        </div><!-- search filters -->
                </div><!-- /component-group1 //-->
                <div id="nzb-search" class="component-group">
                    <div class="component-group-desc">
                        <h3>NZB Search</h3>
                        <p>How to handle NZB search results.</p>
                        <div id="nzb_method_icon" class="add-client-icon-${app.NZB_METHOD}"></div>
                    </div>
                    <fieldset class="component-group-list">
                        <div class="field-pair">
                            <label for="use_nzbs">
                                <span class="component-title">Search NZBs</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="use_nzbs" class="enabler" id="use_nzbs" ${'checked="checked"' if app.USE_NZBS else ''}/>
                                    <p>enable NZB search providers</p></span>
                            </label>
                        </div>
                        <div id="content_use_nzbs">
                        <div class="field-pair">
                            <label for="nzb_method">
                                <span class="component-title">Send .nzb files to:</span>
                                <span class="component-desc">
                                    <select name="nzb_method" id="nzb_method" class="form-control input-sm">
<% nzb_method_text = {'blackhole': "Black hole", 'sabnzbd': "SABnzbd", 'nzbget': "NZBget"} %>
% for cur_action in ('sabnzbd', 'blackhole', 'nzbget'):
                                    <option value="${cur_action}" ${'selected="selected"' if app.NZB_METHOD == cur_action else ''}>${nzb_method_text[cur_action]}</option>
% endfor
                                    </select>
                                </span>
                            </label>
                        </div>
                        <div id="blackhole_settings">
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">Black hole folder location</span>
                                    <span class="component-desc">
                                        <input type="text" name="nzb_dir" id="nzb_dir" value="${app.NZB_DIR}" class="form-control input-sm input350"/>
                                        <div class="clear-left"><p><b>.nzb</b> files are stored at this location for external software to find and use</p></div>
                                    </span>
                                </label>
                            </div>
                        </div>
                        <div id="sabnzbd_settings">
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">SABnzbd server URL</span>
                                    <span class="component-desc">
                                        <input type="text" id="sab_host" name="sab_host" value="${app.SAB_HOST}" class="form-control input-sm input350"/>
                                        <div class="clear-left"><p>URL to your SABnzbd server (e.g. http://localhost:8080/)</p></div>
                                    </span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">SABnzbd username</span>
                                    <span class="component-desc">
                                        <input type="text" name="sab_username" id="sab_username" value="${app.SAB_USERNAME}" class="form-control input-sm input200"
                                               autocomplete="no" />
                                        <p>(blank for none)</p>
                                    </span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">SABnzbd password</span>
                                    <span class="component-desc">
                                        <input type="password" name="sab_password" id="sab_password" value="${app.SAB_PASSWORD}" class="form-control input-sm input200" autocomplete="no"/>
                                        <p>(blank for none)</p>
                                    </span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">SABnzbd API key</span>
                                    <span class="component-desc">
                                        <input type="text" name="sab_apikey" id="sab_apikey" value="${app.SAB_APIKEY}" class="form-control input-sm input350"/>
                                        <div class="clear-left"><p>locate at... SABnzbd Config -> General -> API Key</p></div>
                                    </span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">Use SABnzbd category</span>
                                    <span class="component-desc">
                                        <input type="text" name="sab_category" id="sab_category" value="${app.SAB_CATEGORY}" class="form-control input-sm input200"/>
                                        <p>add downloads to this category (e.g. TV)</p>
                                    </span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">Use SABnzbd category (backlog episodes)</span>
                                    <span class="component-desc">
                                        <input type="text" name="sab_category_backlog" id="sab_category_backlog" value="${app.SAB_CATEGORY_BACKLOG}" class="form-control input-sm input200"/>
                                        <p>add downloads of old episodes to this category (e.g. TV)</p>
                                    </span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">Use SABnzbd category for anime</span>
                                    <span class="component-desc">
                                        <input type="text" name="sab_category_anime" id="sab_category_anime" value="${app.SAB_CATEGORY_ANIME}" class="form-control input-sm input200"/>
                                        <p>add anime downloads to this category (e.g. anime)</p>
                                    </span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">Use SABnzbd category for anime (backlog episodes)</span>
                                    <span class="component-desc">
                                        <input type="text" name="sab_category_anime_backlog" id="sab_category_anime_backlog" value="${app.SAB_CATEGORY_ANIME_BACKLOG}" class="form-control input-sm input200"/>
                                        <p>add anime downloads of old episodes to this category (e.g. anime)</p>
                                    </span>
                                </label>
                            </div>
                            % if app.ALLOW_HIGH_PRIORITY is True:
                            <div class="field-pair">
                                <label for="sab_forced">
                                    <span class="component-title">Use forced priority</span>
                                    <span class="component-desc">
                                        <input type="checkbox" name="sab_forced" class="enabler" id="sab_forced" ${'checked="checked"' if app.SAB_FORCED else ''}/>
                                        <p>enable to change priority from HIGH to FORCED</p></span>
                                </label>
                            </div>
                            % endif
                        <div class="testNotification" id="testSABnzbd_result">Click below to test</div>
                            <input class="btn" type="button" value="Test SABnzbd" id="testSABnzbd" class="btn test-button"/>
                            <input type="submit" class="btn config_submitter" value="Save Changes" /><br>
                        </div>
                        <div id="nzbget_settings">
                            <div class="field-pair">
                                <label for="nzbget_use_https">
                                    <span class="component-title">Connect using HTTPS</span>
                                    <span class="component-desc">
                                        <input id="nzbget_use_https" type="checkbox" class="enabler" id="nzbget_use_https" name="nzbget_use_https" ${'checked="checked"' if app.NZBGET_USE_HTTPS else ''}/>
                                        <p><b>note:</b> enable Secure control in NZBGet and set the correct Secure Port here</p>
                                    </span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">NZBget host:port</span>
                                    <span class="component-desc">
                                        <input type="text" name="nzbget_host" id="nzbget_host" value="${app.NZBGET_HOST}" class="form-control input-sm input350"/>
                                        <p>(e.g. localhost:6789)</p>
                                        <div class="clear-left"><p>NZBget RPC host name and port number (not NZBgetweb!)</p></div>
                                    </span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">NZBget username</span>
                                    <span class="component-desc">
                                        <input type="text" name="nzbget_username" id="nzbget_username" value="${app.NZBGET_USERNAME}" class="form-control input-sm input200"
                                               autocomplete="no" />
                                        <p>locate in nzbget.conf (default:nzbget)</p>
                                    </span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">NZBget password</span>
                                    <span class="component-desc">
                                        <input type="password" name="nzbget_password" id="nzbget_password" value="${app.NZBGET_PASSWORD}" class="form-control input-sm input200" autocomplete="no"/>
                                        <p>locate in nzbget.conf (default:tegbzn6789)</p>
                                    </span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">Use NZBget category</span>
                                    <span class="component-desc">
                                        <input type="text" name="nzbget_category" id="nzbget_category" value="${app.NZBGET_CATEGORY}" class="form-control input-sm input200"/>
                                        <p>send downloads marked this category (e.g. TV)</p>
                                    </span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">Use NZBget category (backlog episodes)</span>
                                    <span class="component-desc">
                                        <input type="text" name="nzbget_category_backlog" id="nzbget_category_backlog" value="${app.NZBGET_CATEGORY_BACKLOG}" class="form-control input-sm input200"/>
                                        <p>send downloads of old episodes marked this category (e.g. TV)</p>
                                    </span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">Use NZBget category for anime</span>
                                    <span class="component-desc">
                                        <input type="text" name="nzbget_category_anime" id="nzbget_category_anime" value="${app.NZBGET_CATEGORY_ANIME}" class="form-control input-sm input200"/>
                                        <p>send anime downloads marked this category (e.g. anime)</p>
                                    </span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">Use NZBget category for anime (backlog episodes)</span>
                                    <span class="component-desc">
                                        <input type="text" name="nzbget_category_anime_backlog" id="nzbget_category_anime_backlog" value="${app.NZBGET_CATEGORY_ANIME_BACKLOG}" class="form-control input-sm input200"/>
                                        <p>send anime downloads of old episodes marked this category (e.g. anime)</p>
                                    </span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">NZBget priority</span>
                                    <span class="component-desc">
                                        <select name="nzbget_priority" id="nzbget_priority" class="form-control input-sm">
                                            <option value="-100" ${'selected="selected"' if app.NZBGET_PRIORITY == -100 else ''}>Very low</option>
                                            <option value="-50" ${'selected="selected"' if app.NZBGET_PRIORITY == -50 else ''}>Low</option>
                                            <option value="0" ${'selected="selected"' if app.NZBGET_PRIORITY == 0 else ''}>Normal</option>
                                            <option value="50" ${'selected="selected"' if app.NZBGET_PRIORITY == 50 else ''}>High</option>
                                            <option value="100" ${'selected="selected"' if app.NZBGET_PRIORITY == 100 else ''}>Very high</option>
                                            <option value="900" ${'selected="selected"' if app.NZBGET_PRIORITY == 900 else ''}>Force</option>
                                        </select>
                                        <span>priority for daily snatches (no backlog)</span>
                                    </span>
                                </label>
                            </div>
                            <div class="testNotification" id="testNZBget_result">Click below to test</div>
                                <input class="btn" type="button" value="Test NZBget" id="testNZBget" class="btn test-button"/>
                                <input type="submit" class="btn config_submitter" value="Save Changes" /><br>
                        </div>
                        </div><!-- /content_use_nzbs //-->
                    </fieldset>
                </div><!-- /component-group2 //-->
                <div id="torrent-search" class="component-group">
                    <div class="component-group-desc">
                        <h3>Torrent Search</h3>
                        <p>How to handle Torrent search results.</p>
                        <div id="torrent_method_icon" class="add-client-icon-${app.TORRENT_METHOD}"></div>
                    </div>
                    <fieldset class="component-group-list">
                        <div class="field-pair">
                            <label for="use_torrents">
                                <span class="component-title">Search torrents</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="use_torrents" class="enabler" id="use_torrents" ${'checked="checked"' if app.USE_TORRENTS else ''}/>
                                    <p>enable torrent search providers</p>
                                </span>
                            </label>
                        </div>
                        <div id="content_use_torrents">
                            <div class="field-pair">
                                <label for="torrent_method">
                                    <span class="component-title">Send .torrent files to:</span>
                                    <span class="component-desc">
                                    <select name="torrent_method" id="torrent_method" class="form-control input-sm">
    <% torrent_method_text = {'blackhole': "Black hole", 'utorrent': "uTorrent", 'transmission': "Transmission", 'deluge': "Deluge (via WebUI)", 'deluged': "Deluge (via Daemon)", 'download_station': "Synology DS", 'rtorrent': "rTorrent", 'qbittorrent': "qbittorrent", 'mlnet': "MLDonkey"} %>
    % for cur_action in ('blackhole', 'utorrent', 'transmission', 'deluge', 'deluged', 'download_station', 'rtorrent', 'qbittorrent', 'mlnet'):
                                    <option value="${cur_action}" ${'selected="selected"' if app.TORRENT_METHOD == cur_action else ''}>${torrent_method_text[cur_action]}</option>
    % endfor
                                    </select>
                                    </span>
                                </label>
                                <div id="options_torrent_blackhole">
                                    <div class="field-pair">
                                        <label>
                                            <span class="component-title">Black hole folder location</span>
                                            <span class="component-desc">
                                                <input type="text" name="torrent_dir" id="torrent_dir" value="${app.TORRENT_DIR}" class="form-control input-sm input350"/>
                                                <div class="clear-left"><p><b>.torrent</b> files are stored at this location for external software to find and use</p></div>
                                            </span>
                                        </label>
                                    </div>
                                    <input type="submit" class="btn config_submitter" value="Save Changes" /><br>
                                </div>
                            </div>
                            <div id="options_torrent_clients">
                                <div class="field-pair">
                                    <label>
                                        <span class="component-title" id="host_title">Torrent host:port</span>
                                        <span class="component-desc">
                                            <input type="text" name="torrent_host" id="torrent_host" value="${app.TORRENT_HOST}" class="form-control input-sm input350"/>
                                            <div class="clear-left">
                                                <p id="host_desc_torrent">URL to your torrent client (e.g. http://localhost:8000/)</p>
                                            </div>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair" id="torrent_rpcurl_option">
                                    <label>
                                        <span class="component-title" id="rpcurl_title">Torrent RPC URL</span>
                                        <span class="component-desc">
                                            <input type="text" name="torrent_rpcurl" id="torrent_rpcurl" value="${app.TORRENT_RPCURL}" class="form-control input-sm input350"/>
                                            <div class="clear-left">
                                                <p id="rpcurl_desc_">The path without leading and trailing slashes (e.g. transmission)</p>
                                            </div>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair" id="torrent_auth_type_option">
                                    <label>
                                        <span class="component-title">Http Authentication</span>
                                        <span class="component-desc">
                                            <select name="torrent_auth_type" id="torrent_auth_type" class="form-control input-sm">
                                            <% http_authtype = {'none': "None", 'basic': "Basic", 'digest': "Digest"} %>
                                            % for authvalue, authname in http_authtype.iteritems():
                                                <option id="torrent_auth_type_value" value="${authvalue}" ${'selected="selected"' if app.TORRENT_AUTH_TYPE == authvalue else ''}>${authname}</option>
                                            % endfor
                                            </select>
                                            <p></p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair" id="torrent_verify_cert_option">
                                    <label for="torrent_verify_cert">
                                        <span class="component-title">Verify certificate</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="torrent_verify_cert" class="enabler" id="torrent_verify_cert" ${'checked="checked"' if app.TORRENT_VERIFY_CERT else ''}/>
                                            <p id="torrent_verify_deluge">disable if you get "Deluge: Authentication Error" in your log</p>
                                            <p id="torrent_verify_rtorrent">Verify SSL certificates for HTTPS requests</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair" id="torrent_username_option">
                                    <label>
                                        <span class="component-title" id="username_title">Client username</span>
                                        <span class="component-desc">
                                            <input type="text" name="torrent_username" id="torrent_username" value="${app.TORRENT_USERNAME}" class="form-control input-sm input200"
                                                   autocomplete="no" />
                                            <p>(blank for none)</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair" id="torrent_password_option">
                                    <label>
                                        <span class="component-title" id="password_title">Client password</span>
                                        <span class="component-desc">
                                            <input type="password" name="torrent_password" id="torrent_password" value="${app.TORRENT_PASSWORD}" class="form-control input-sm input200" autocomplete="no"/>
                                            <p>(blank for none)</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair" id="torrent_label_option">
                                    <label>
                                        <span class="component-title">Add label to torrent</span>
                                        <span class="component-desc">
                                            <input type="text" name="torrent_label" id="torrent_label" value="${app.TORRENT_LABEL}" class="form-control input-sm input200"/>
                                            <span id="label_warning_deluge" style="display:none;"><p>(blank spaces are not allowed)</p>
                                                <div class="clear-left"><p>note: label plugin must be enabled in Deluge clients</p></div>
                                            </span>
                                            <span id="label_warning_qbittorrent" style="display:none;"><p>(blank spaces are not allowed)</p>
                                                <div class="clear-left"><p>note: for QBitTorrent 3.3.1 and up</p></div>
                                            </span>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair" id="torrent_label_anime_option">
                                    <label>
                                        <span class="component-title">Add label to torrent for anime</span>
                                        <span class="component-desc">
                                            <input type="text" name="torrent_label_anime" id="torrent_label_anime" value="${app.TORRENT_LABEL_ANIME}" class="form-control input-sm input200"/>
                                            <span id="label_anime_warning_deluge" style="display:none;"><p>(blank spaces are not allowed)</p>
                                                <div class="clear-left"><p>note: label plugin must be enabled in Deluge clients</p></div>
                                            </span>
                                            <span id="label_anime_warning_qbittorrent" style="display:none;"><p>(blank spaces are not allowed)</p>
                                                <div class="clear-left"><p>note: for QBitTorrent 3.3.1 and up </p></div>
                                            </span>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair" id="torrent_path_option">
                                    <label>
                                        <span class="component-title" id="directory_title">Downloaded files location</span>
                                        <span class="component-desc">
                                            <input type="text" name="torrent_path" id="torrent_path" value="${app.TORRENT_PATH}" class="form-control input-sm input350"/>
                                            <div class="clear-left"><p>where <span id="torrent_client">the torrent client</span> will save downloaded files (blank for client default)
                                                <span id="path_synology"> <b>note:</b> the destination has to be a shared folder for Synology DS</span></p>
                                            </div>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair" id="torrent_seed_time_option">
                                    <label>
                                        <span class="component-title" id="torrent_seed_time_label">Minimum seeding time is</span>
                                        <span class="component-desc"><input type="number" step="1" name="torrent_seed_time" id="torrent_seed_time" value="${app.TORRENT_SEED_TIME}" class="form-control input-sm input100" />
                                        <p>hours. (default:'0' passes blank to client and '-1' passes nothing)</p></span>
                                    </label>
                                </div>
                                <div class="field-pair" id="torrent_paused_option">
                                    <label>
                                        <span class="component-title">Start torrent paused</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="torrent_paused" class="enabler" id="torrent_paused" ${'checked="checked"' if app.TORRENT_PAUSED else ''}/>
                                            <p>add .torrent to client but do <b style="font-weight:900;">not</b> start downloading</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair" id="torrent_high_bandwidth_option">
                                    <label>
                                        <span class="component-title">Allow high bandwidth</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="torrent_high_bandwidth" class="enabler" id="torrent_high_bandwidth" ${'checked="checked"' if app.TORRENT_HIGH_BANDWIDTH else ''}/>
                                            <p>use high bandwidth allocation if priority is high</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="testNotification" id="test_torrent_result">Click below to test</div>
                                    <input class="btn" type="button" value="Test Connection" id="test_torrent" class="btn test-button"/>
                                    <input type="submit" class="btn config_submitter" value="Save Changes" /><br>
                                </div>
                        </div><!-- /content_use_torrents //-->
                    </fieldset>
                </div><!-- /component-group3 //-->
                <br>
                <h6 class="pull-right"><b>All non-absolute folder locations are relative to <span class="path">${app.DATA_DIR}</span></b> </h6>
                <input type="submit" class="btn pull-left config_submitter button" value="Save Changes" />
            </div><!-- /config-components //-->
        </form>
    </div>
</div>
</%block>

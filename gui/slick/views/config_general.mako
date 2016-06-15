<%inherit file="/layouts/main.mako"/>
<%!
    import datetime
    import locale
    import sickbeard
    from sickbeard.common import SKIPPED, WANTED, UNAIRED, ARCHIVED, IGNORED, SNATCHED, SNATCHED_PROPER, SNATCHED_BEST, FAILED
    from sickbeard.common import Quality, qualityPresets, statusStrings, qualityPresetStrings, cpu_presets, privacy_levels
    from sickbeard.sbdatetime import sbdatetime, date_presets, time_presets
    from sickbeard import config
    from sickbeard import metadata
    from sickbeard.metadata.generic import GenericMetadata
    from sickbeard.helpers import anon_url
%>
<%block name="content">
% if not header is UNDEFINED:
    <h1 class="header">${header}</h1>
% else:
    <h1 class="title">${title}</h1>
% endif
<% indexer = 0 %>
% if sickbeard.INDEXER_DEFAULT:
    <% indexer = sickbeard.INDEXER_DEFAULT %>
% endif
<div id="config">
    <div id="config-content">
        <form id="configForm" action="saveGeneral" method="post">
            <div id="config-components">
                <ul>
                    <li><a href="#misc">Misc</a></li>
                    <li><a href="#interface">Interface</a></li>
                    <li><a href="#advanced-settings">Advanced Settings</a></li>
                </ul>
                <div id="misc">
                    <div class="component-group">
                        <div class="component-group-desc">
                            <h3>Misc</h3>
                            <p>Startup options. Indexer options. Log and show file locations.</p>
                            <p><b>Some options may require a manual restart to take effect.</b></p>
                        </div>
                        <fieldset class="component-group-list">
                            <div class="field-pair">
                                <label for="indexerDefaultLang">
                                    <span class="component-title">Default Indexer Language</span>
                                    <span class="component-desc">
                                        <select name="indexerDefaultLang" id="indexerDefaultLang" class="form-control form-control-inline input-sm bfh-languages" data-language=${sickbeard.INDEXER_DEFAULT_LANGUAGE} data-available="${','.join(sickbeard.indexerApi().config['valid_languages'])}"></select>
                                        <span>for adding shows and metadata providers</span>
                                    </span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label for="launch_browser">
                                    <span class="component-title">Launch browser</span>
                                    <span class="component-desc">
                                        <input type="checkbox" name="launch_browser" id="launch_browser" ${'checked="checked"' if sickbeard.LAUNCH_BROWSER else ''}/>
                                        <p>open the Medusa home page on startup</p>
                                    </span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label for="default_page">
                                    <span class="component-title">Initial page</span>
                                    <span class="component-desc">
                                        <select id="default_page" name="default_page" class="form-control input-sm">
                                            <option value="home" ${'selected="selected"' if sickbeard.DEFAULT_PAGE == 'home' else ''}>Shows</option>
                                            <option value="schedule" ${'selected="selected"' if sickbeard.DEFAULT_PAGE == 'schedule' else ''}>Schedule</option>
                                            <option value="history" ${'selected="selected"' if sickbeard.DEFAULT_PAGE == 'history' else ''}>History</option>
                                            <option value="news" ${'selected="selected"' if sickbeard.DEFAULT_PAGE == 'news' else ''}>News</option>
                                            <option value="IRC" ${'selected="selected"' if sickbeard.DEFAULT_PAGE == 'IRC' else ''}>IRC</option>
                                        </select>
                                        <span>when launching Medusa interface</span>
                                    </span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label for="showupdate_hour">
                                    <span class="component-title">Choose hour to update shows</span>
                                    <span class="component-desc">
                                        <input type="number" min="0" max="23" step="1" name="showupdate_hour" id="showupdate_hour" value="${sickbeard.SHOWUPDATE_HOUR}" class="form-control input-sm input75" autocapitalize="off" />
                                        <p>with information such as next air dates, show ended, etc. Use 15 for 3pm, 4 for 4am etc.</p>
                                        <p>Note: minutes are randomized each time Medusa is started</p>
                                    </span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <span class="component-title">Send to trash for actions</span>
                                <span class="component-desc">
                                    <label for="trash_remove_show" class="nextline-block">
                                        <input type="checkbox" name="trash_remove_show" id="trash_remove_show" ${'checked="checked"' if sickbeard.TRASH_REMOVE_SHOW else ''}/>
                                        <p>when using show "Remove" and delete files</p>
                                    </label>
                                    <label for="trash_rotate_logs" class="nextline-block">
                                        <input type="checkbox" name="trash_rotate_logs" id="trash_rotate_logs" ${'checked="checked"' if sickbeard.TRASH_ROTATE_LOGS else ''}/>
                                        <p>on scheduled deletes of the oldest log files</p>
                                    </label>
                                    <div class="clear-left"><p>selected actions use trash (recycle bin) instead of the default permanent delete</p></div>
                                </span>
                            </div>
                            <div class="field-pair">
                                <label for="log_dir">
                                    <span class="component-title">Log file folder location</span>
                                    <span class="component-desc">
                                        <input type="text" name="log_dir" id="log_dir" value="${sickbeard.ACTUAL_LOG_DIR}" class="form-control input-sm input350" autocapitalize="off" />
                                    </span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label for="log_nr">
                                    <span class="component-title">Number of Log files saved</span>
                                    <span class="component-desc">
                                        <input type="number" min="1" step="1" name="log_nr" id="log_nr" value="${sickbeard.LOG_NR}" class="form-control input-sm input75" autocapitalize="off" />
                                        <p>number of log files saved when rotating logs (default: 5) (REQUIRES RESTART)</p>
                                    </span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label for="log_size">
                                    <span class="component-title">Size of Log files saved</span>
                                    <span class="component-desc">
                                        <input type="number" min="0.5" step="0.1" name="log_size" id="log_size" value="${sickbeard.LOG_SIZE}" class="form-control input-sm input75" autocapitalize="off" />
                                        <p>maximum size in MB of the log file (default: 1MB) (REQUIRES RESTART)</p>
                                    </span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label for="indexer_default">
                                    <span class="component-title">Use initial indexer set to</span>
                                    <span class="component-desc">
                                        <select id="indexer_default" name="indexer_default" class="form-control input-sm">
                                            <option value="0" ${'selected="selected"' if indexer == 0 else ''}>All Indexers</option>
                                            % for indexer in sickbeard.indexerApi().indexers:
                                            <option value="${indexer}" ${'selected="selected"' if sickbeard.INDEXER_DEFAULT == indexer else ''}>${sickbeard.indexerApi().indexers[indexer]}</option>
                                            % endfor
                                        </select>
                                        <span>as the default selection when adding new shows</span>
                                    </span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label for="indexer_timeout">
                                    <span class="component-title">Timeout show indexer at</span>
                                    <span class="component-desc">
                                        <input type="number" min="10" step="1" name="indexer_timeout" id="indexer_timeout" value="${sickbeard.INDEXER_TIMEOUT}" class="form-control input-sm input75" autocapitalize="off" />
                                        <p>seconds of inactivity when finding new shows (default:20)</p>
                                    </span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">Show root directories</span>
                                    <span class="component-desc">
                                        <p>where the files of shows are located</p>
                                        <%include file="/inc_rootDirs.mako"/>
                                    </span>
                                </label>
                            </div>
                            <input type="submit" class="btn config_submitter" value="Save Changes" />
                        </fieldset>
                    </div>
                    <div class="component-group">
                        <div class="component-group-desc">
                            <h3>Updates</h3>
                            <p>Options for software updates.</p>
                        </div>
                        <fieldset class="component-group-list">
                            <div class="field-pair">
                                <label for="version_notify">
                                    <span class="component-title">Check software updates</span>
                                    <span class="component-desc">
                                        <input type="checkbox" name="version_notify" id="version_notify" ${'checked="checked"' if sickbeard.VERSION_NOTIFY else ''}/>
                                        <p>and display notifications when updates are available.
                                        Checks are run on startup and at the frequency set below*</p>
                                    </span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label for="auto_update">
                                    <span class="component-title">Automatically update</span>
                                    <span class="component-desc">
                                        <input type="checkbox" name="auto_update" id="auto_update" ${'checked="checked"' if sickbeard.AUTO_UPDATE else ''}/>
                                        <p>fetch and install software updates.
                                        Updates are run on startup and in the background at the frequency set below*</p>
                                    </span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">Check the server every*</span>
                                    <span class="component-desc">
                                        <input type="number" min="1" step="1" name="update_frequency" id="update_frequency" value="${sickbeard.UPDATE_FREQUENCY}" class="form-control input-sm input75" autocapitalize="off" />
                                        <p>hours for software updates (default:1)</p>
                                    </span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label for="notify_on_update">
                                    <span class="component-title">Notify on software update</span>
                                    <span class="component-desc">
                                        <input type="checkbox" name="notify_on_update" id="notify_on_update" ${'checked="checked"' if sickbeard.NOTIFY_ON_UPDATE else ''}/>
                                        <p>send a message to all enabled notifiers when Medusa has been updated</p>
                                    </span>
                                </label>
                            </div>
                            <input type="submit" class="btn config_submitter" value="Save Changes" />
                        </fieldset>
                    </div>
                </div><!-- /component-group1 //-->
                <div id="interface">
                <div class="component-group">
                    <div class="component-group-desc">
                        <h3>User Interface</h3>
                        <p>Options for visual appearance.</p>
                    </div>
                    <fieldset class="component-group-list">
                        <div class="field-pair">
                            <label for="theme_name">
                                <span class="component-title">Display theme:</span>
                                <span class="component-desc">
                                    <select id="theme_name" name="theme_name" class="form-control input-sm">
                                        <option value="dark" ${'selected="selected"' if sickbeard.THEME_NAME == 'dark' else ''}>Dark</option>
                                        <option value="light" ${'selected="selected"' if sickbeard.THEME_NAME == 'light' else ''}>Light</option>
                                    </select>
                                    <span class="red-text">for appearance to take effect, save then refresh your browser</span>
                                </span>
                            </label>
                        </div>
              
                        <div class="field-pair">
                            <label for="fanart_background">
                                <span class="component-title">Show fanart in the background</span>
                                <span class="component-desc">
                                    <input type="checkbox" class="enabler" name="fanart_background" id="fanart_background" ${('', 'checked="checked"')[bool(sickbeard.FANART_BACKGROUND)]}>
                                    <p>on the show summary page</p>
                                </span>
                            </label>
                        </div>
                        <div id="content_fanart_background">
                            <div class="field-pair">
                                <label for="fanart_background_opacity">
                                    <span class="component-title">Fanart transparency</span>
                                    <span class="component-desc">
                                    <input type="number" step="0.1" min="0.1" max="1.0" name="fanart_background_opacity" id="fanart_background_opacity" value="${sickbeard.FANART_BACKGROUND_OPACITY}" class="form-control input-sm input75" />
                                    <p>Transparency of the fanart in the background</p>
                                    </span>
                                </label>
                            </div>
                        </div>

                        <div class="field-pair">
                            <label for="display_all_seasons">
                                <span class="component-title">Show all seasons</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="display_all_seasons" id="display_all_seasons" ${'checked="checked"' if sickbeard.DISPLAY_ALL_SEASONS else ''}>
                                    <p>on the show summary page</p>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="sort_article">
                                <span class="component-title">Sort with "The", "A", "An"</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="sort_article" id="sort_article" ${'checked="checked"' if sickbeard.SORT_ARTICLE else ''}/>
                                    <p>include articles ("The", "A", "An") when sorting show lists</p>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="coming_eps_missed_range">
                                <span class="component-title">Missed episodes range</span>
                                <span class="component-desc">
                                    <input type="number" step="1" min="7" name="coming_eps_missed_range" id="coming_eps_missed_range" value="${sickbeard.COMING_EPS_MISSED_RANGE}" class="form-control input-sm input75" />
                                    <p>Set the range in days of the missed episodes in the Schedule page</p>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="fuzzy_dating">
                                <span class="component-title">Display fuzzy dates</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="fuzzy_dating" id="fuzzy_dating" class="viewIf datePresets" ${'checked="checked"' if sickbeard.FUZZY_DATING else ''}/>
                                    <p>move absolute dates into tooltips and display e.g. "Last Thu", "On Tue"</p>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair show_if_fuzzy_dating ${'' if not sickbeard.FUZZY_DATING else ' metadataDiv'}">
                            <label for="trim_zero">
                                <span class="component-title">Trim zero padding</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="trim_zero" id="trim_zero" ${'checked="checked"' if sickbeard.TRIM_ZERO else ''}/>
                                    <p>remove the leading number "0" shown on hour of day, and date of month</p>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="date_presets">
                                <span class="component-title">Date style:</span>
                                <span class="component-desc">
                                    <select class="form-control input-sm ${' metadataDiv' if sickbeard.FUZZY_DATING else ''}" id="date_presets${'' if sickbeard.FUZZY_DATING else '_na'}" name="date_preset${'' if sickbeard.FUZZY_DATING else '_na'}">
                                        % for cur_preset in date_presets:
                                            <option value="${cur_preset}" ${'selected="selected"' if sickbeard.DATE_PRESET == cur_preset or "%x" == sickbeard.DATE_PRESET and cur_preset == '%a, %b %d, %Y' else ''}>${datetime.datetime(datetime.datetime.now().year, 12, 31, 14, 30, 47).strftime(cur_preset)}</option>
                                        % endfor
                                    </select>
                                    <select class="form-control input-sm ${'' if not sickbeard.FUZZY_DATING else ' metadataDiv'}" id="date_presets${'' if not sickbeard.FUZZY_DATING else ' metadataDiv'}" name="date_preset${'' if not sickbeard.FUZZY_DATING else '_na'}">
                                        <option value="%x" ${'selected="selected"' if sickbeard.DATE_PRESET == '%x' else ''}>Use System Default</option>
                                        % for cur_preset in date_presets:
                                            <option value="${cur_preset}" ${'selected="selected"' if sickbeard.DATE_PRESET == cur_preset else ''}>${datetime.datetime(datetime.datetime.now().year, 12, 31, 14, 30, 47).strftime(cur_preset)}</option>
                                        % endfor
                                    </select>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="time_presets">
                                <span class="component-title">Time style:</span>
                                <span class="component-desc">
                                    <select id="time_presets" name="time_preset" class="form-control input-sm">
                                         % for cur_preset in time_presets:
                                            <option value="${cur_preset}" ${'selected="selected"' if sickbeard.TIME_PRESET_W_SECONDS == cur_preset else ''}>${sbdatetime.now().sbftime(show_seconds=True, t_preset=cur_preset)}</option>
                                         % endfor
                                    </select>
                                    <span><b>note:</b> seconds are only shown on the History page</span>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <span class="component-title">Timezone:</span>
                            <span class="component-desc">
                                <label for="local" class="space-right">
                                    <input type="radio" name="timezone_display" id="local" value="local" ${'checked="checked"' if sickbeard.TIMEZONE_DISPLAY == "local" else ''} />Local
                                </label>
                                <label for="network">
                                    <input type="radio" name="timezone_display" id="network" value="network" ${'checked="checked"' if sickbeard.TIMEZONE_DISPLAY == "network" else ''} />Network
                                </label>
                                <div class="clear-left">
                                <p>display dates and times in either your timezone or the shows network timezone</p>
                                </div>
                                <div class="clear-left">
                                <p> <b>Note:</b> Use local timezone to start searching for episodes minutes after show ends (depends on your dailysearch frequency)</p>
                                </div>
                            </span>
                        </div>
                        <div class="field-pair">
                            <label for="download_url">
                                <span class="component-title">Download url</span>
                                <input type="text" name="download_url" id="download_url" value="${sickbeard.DOWNLOAD_URL}" size="35" autocapitalize="off" />
                            </label>
                            <label>
                                <span class="component-title">&nbsp;</span>
                            <span class="component-desc">URL where the shows can be downloaded.</span>
                            </label>
                        </div>
                        <input type="submit" class="btn config_submitter" value="Save Changes" />
                    </fieldset>
                </div><!-- /User interface component-group -->
                <div class="component-group">
                    <div class="component-group-desc">
                        <h3>Web Interface</h3>
                        <p>It is recommended that you enable a username and password to secure Medusa from being tampered with remotely.</p>
                        <p><b>These options require a manual restart to take effect.</b></p>
                    </div>
                    <fieldset class="component-group-list">
                        <div class="field-pair">
                            <label for="api_key">
                                <span class="component-title">API key</span>
                                <span class="component-desc">
                                    <input type="text" name="api_key" id="api_key" value="${sickbeard.API_KEY}" class="form-control input-sm input300" readonly="readonly" autocapitalize="off" />
                                    <input class="btn btn-inline" type="button" id="generate_new_apikey" value="Generate">
                                    <div class="clear-left">
                                        <p>used to give 3rd party programs limited access to Medusa</p>
                                        <p>you can try all the features of the API <a href="/apibuilder/">here</a></p>
                                    </div>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="web_log">
                                <span class="component-title">HTTP logs</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="web_log" id="web_log" ${'checked="checked"' if sickbeard.WEB_LOG else ''}/>
                                    <p>enable logs from the internal Tornado web server</p>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="web_username">
                                <span class="component-title">HTTP username</span>
                                <span class="component-desc">
                                    <input type="text" name="web_username" id="web_username" value="${sickbeard.WEB_USERNAME}" class="form-control input-sm input300" autocapitalize="off" autocomplete="no" />
                                    <p>set blank for no login</p>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="web_password">
                                <span class="component-title">HTTP password</span>
                                <span class="component-desc">
                                    <input type="password" name="web_password" id="web_password" value="${sickbeard.WEB_PASSWORD}" class="form-control input-sm input300" autocomplete="no" autocapitalize="off" />
                                    <p>blank = no authentication</span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="web_port">
                                <span class="component-title">HTTP port</span>
                                <span class="component-desc">
                                    <input type="number" min="1" step="1" name="web_port" id="web_port" value="${sickbeard.WEB_PORT}" class="form-control input-sm input100" autocapitalize="off" />
                                    <p>web port to browse and access Medusa (default:8081)</p>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="notify_on_login">
                                <span class="component-title">Notify on login</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="notify_on_login" class="enabler" id="notify_on_login" ${'checked="checked"' if sickbeard.NOTIFY_ON_LOGIN else ''}/>
                                    <p>enable to be notified when a new login happens in webserver</p>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="web_ipv6">
                                <span class="component-title">Listen on IPv6</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="web_ipv6" id="web_ipv6" ${'checked="checked"' if sickbeard.WEB_IPV6 else ''}/>
                                    <p>attempt binding to any available IPv6 address</p>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="enable_https">
                                <span class="component-title">Enable HTTPS</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="enable_https" class="enabler" id="enable_https" ${'checked="checked"' if sickbeard.ENABLE_HTTPS else ''}/>
                                    <p>enable access to the web interface using a HTTPS address</p>
                                </span>
                            </label>
                        </div>
                        <div id="content_enable_https">
                            <div class="field-pair">
                                <label for="https_cert">
                                    <span class="component-title">HTTPS certificate</span>
                                    <span class="component-desc">
                                        <input type="text" name="https_cert" id="https_cert" value="${sickbeard.HTTPS_CERT}" class="form-control input-sm input300" autocapitalize="off" />
                                        <div class="clear-left"><p>file name or path to HTTPS certificate</p></div>
                                    </span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label for="https_key">
                                    <span class="component-title">HTTPS key</span>
                                    <span class="component-desc">
                                        <input type="text" name="https_key" id="https_key" value="${sickbeard.HTTPS_KEY}" class="form-control input-sm input300" autocapitalize="off" />
                                        <div class="clear-left"><p>file name or path to HTTPS key</p></div>
                                    </span>
                                </label>
                            </div>
                        </div>
                        <div class="field-pair">
                            <label for="handle_reverse_proxy">
                                <span class="component-title">Reverse proxy headers</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="handle_reverse_proxy" id="handle_reverse_proxy" ${'checked="checked"' if sickbeard.HANDLE_REVERSE_PROXY else ''}/>
                                    <p>accept the following reverse proxy headers (advanced)...<br />(X-Forwarded-For, X-Forwarded-Host, and X-Forwarded-Proto)</p>
                                </span>
                            </label>
                        </div>
                        <input type="submit" class="btn config_submitter" value="Save Changes" />
                    </fieldset>
                </div><!-- /component-group2 //-->
                </div>
                <div id="advanced-settings" class="component-group">
                <div class="component-group">
                    <div class="component-group-desc">
                        <h3>Advanced Settings</h3>
                    </div>
                    <fieldset class="component-group-list">
                        <div class="field-pair">
                            <label>
                                <span class="component-title">CPU throttling:</span>
                                <span class="component-desc">
                                    <select id="cpu_presets" name="cpu_preset" class="form-control input-sm">
                                    % for cur_preset in cpu_presets:
                                        <option value="${cur_preset}" ${'selected="selected"' if sickbeard.CPU_PRESET == cur_preset else ''}>${cur_preset.capitalize()}</option>
                                    % endfor
                                    </select>
                                    <span>Normal (default). High is lower and Low is higher CPU use</span>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label>
                                <span class="component-title">Anonymous redirect</span>
                                <span class="component-desc">
                                    <input type="text" name="anon_redirect" value="${sickbeard.ANON_REDIRECT}" class="form-control input-sm input300" autocapitalize="off" />
                                    <div class="clear-left"><p>backlink protection via anonymizer service, must end in "?"</p></div>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="ssl_verify">
                                <span class="component-title">Verify SSL Certs</span>
                                    <span class="component-desc">
                                        <input type="checkbox" name="ssl_verify" id="ssl_verify" ${'checked="checked"' if sickbeard.SSL_VERIFY else ''}/>
                                        <p>Verify SSL Certificates (Disable this for broken SSL installs (Like QNAP))<p>
                                    </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="no_restart">
                                <span class="component-title">No Restart</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="no_restart" id="no_restart" ${'checked="checked"' if sickbeard.NO_RESTART else ''}/>
                                    <p>Only shutdown when restarting SR.
                                    Only select this when you have external software restarting SR automatically when it stops (like FireDaemon)</p>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="encryption_version">
                                <span class="component-title">Encrypt passwords</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="encryption_version" id="encryption_version" ${'checked="checked"' if sickbeard.ENCRYPTION_VERSION else ''}/>
                                    <p>in the <code>config.ini</code> file.
                                    <b>Warning:</b> Passwords must only contain <a target="_blank" href="${anon_url('http://en.wikipedia.org/wiki/ASCII#ASCII_printable_characters')}">ASCII characters</a></p>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="calendar_unprotected">
                                <span class="component-title">Unprotected calendar</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="calendar_unprotected" id="calendar_unprotected" ${'checked="checked"' if sickbeard.CALENDAR_UNPROTECTED else ''}/>
                                    <p>allow subscribing to the calendar without user and password.
                                    Some services like Google Calendar only work this way</p>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="calendar_icons">
                                <span class="component-title">Google Calendar Icons</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="calendar_icons" id="calendar_icons" ${'checked="checked"' if sickbeard.CALENDAR_ICONS else ''}/>
                                    <p>show an icon next to exported calendar events in Google Calendar.</p>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label>
                                <span class="component-title">Proxy host</span>
                                <span class="component-desc">
                                    <input type="text" name="proxy_setting" value="${sickbeard.PROXY_SETTING}" class="form-control input-sm input300" autocapitalize="off" />
                                    <div class="clear-left"><p>blank to disable or proxy to use when connecting to providers</p></div>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="proxy_indexers">
                                <span class="component-title">Use proxy for indexers</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="proxy_indexers" id="proxy_indexers" ${'checked="checked"' if sickbeard.PROXY_INDEXERS else ''}/>
                                    <p>use proxy host for connecting to indexers (thetvdb)</p>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="skip_removed_files">
                                <span class="component-title">Skip Remove Detection</span>
                                <span class="component-desc">
                                <input type="checkbox" name="skip_removed_files" id="skip_removed_files" ${'checked="checked"' if sickbeard.SKIP_REMOVED_FILES else ''}/>
                                <p>Skip detection of removed files. If disabled the episode will be set to the default deleted status</p>
                                 </span>
                                <div class="clear-left">
                                <span class="component-desc"><b>NOTE:</b> This may mean Medusa misses renames as well</span>
                                </div>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="ep_default_deleted_status">
                                <span class="component-title">Default deleted episode status:</span>
                                    <span class="component-desc">
% if not sickbeard.SKIP_REMOVED_FILES:
                                        <select name="ep_default_deleted_status" id="ep_default_deleted_status" class="form-control input-sm">
                                        % for defStatus in [SKIPPED, IGNORED, ARCHIVED]:
                                            <option value="${defStatus}" ${'selected="selected"' if int(sickbeard.EP_DEFAULT_DELETED_STATUS) == defStatus else ''}>${statusStrings[defStatus]}</option>
                                        % endfor
                                        </select>
% else:
                                        <select name="ep_default_deleted_status" id="ep_default_deleted_status" class="form-control input-sm" disabled="disabled">
                                        % for defStatus in [SKIPPED, IGNORED]:
                                            <option value="${defStatus}" ${'selected="selected"' if sickbeard.EP_DEFAULT_DELETED_STATUS == defStatus else ''}>${statusStrings[defStatus]}</option>
                                        % endfor
                                        </select>
                                        <input type="hidden" name="ep_default_deleted_status" value="${sickbeard.EP_DEFAULT_DELETED_STATUS}" />
% endif
                                    <span>Define the status to be set for media file that has been deleted.</span>
                                    <div class="clear-left">
                                    <p> <b>NOTE:</b> Archived option will keep previous downloaded quality</p>
                                    <p>Example: Downloaded (1080p WEB-DL) ==> Archived (1080p WEB-DL)</p>
                                    </div>
                                </span>
                            </label>
                        </div>

                        <div class="field-pair">
                            <label for="use_legacy_name_parser">
                                <span class="component-title">Use legacy name parser</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="use_legacy_name_parser" id="use_legacy_name_parser" ${('', 'checked="checked"')[bool(sickbeard.USE_LEGACY_NAME_PARSER)]}/>
                                    <p>Use the legacy name parser. If disabled <a href=${anon_url("https://github.com/guessit-io/guessit")}>Guessit</a> is used for release and filename parsing.</p>
                                </span>
                            </label>
                        </div>
                        <input type="submit" class="btn config_submitter" value="Save Changes" />
                    </fieldset>
                </div>
                <div class="component-group">
                    <div class="component-group-desc">
                        <h3>Logging</h3>
                    </div>
                    <fieldset class="component-group-list">
                        <div class="field-pair">
                            <label for="debug">
                                <span class="component-title">Enable debug</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="debug" id="debug" ${'checked="checked"' if sickbeard.DEBUG else ''}/>
                                    <p>Enable debug logs<p>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="subliminal_log">
                                <span class="component-title">Subliminal logs</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="subliminal_log" id="subliminal_log" ${'checked="checked"' if sickbeard.SUBLIMINAL_LOG else ''}/>
                                    <p>enable logs from subliminal library (subtitles)</p>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label>
                                <span class="component-title">Privacy:</span>
                                <span class="component-desc">
                                    <select id="privacy_level" name="privacy_level" class="form-control input-sm">
                                    % for privacy_level in ['high', 'normal', 'low', ]:
                                        <option value="${privacy_level}" ${'selected="selected"' if sickbeard.PRIVACY_LEVEL == privacy_level else ''}>${privacy_level.capitalize()}</option>
                                    % endfor
                                    </select>
                                    <span>
                                        Set the level of log-filtering.
                                        Normal (default).
                                        <br />NOTE: A restart may be required to take effect.
                                        <br />WARNING: Setting to "DISABLED" will show sensitive information such as passwords in the logs!
                                    </span>
                                </span>
                            </label>
                        </div>
                        <input type="submit" class="btn config_submitter" value="Save Changes" />
                    </fieldset>
                </div>
                <div class="component-group">
                    <div class="component-group-desc">
                        <h3>GitHub</h3>
                        <p>Options for github related features.</p>
                    </div>
                    <fieldset class="component-group-list">
                        <div class="field-pair">
                            <label>
                                <span class="component-title">Branch version:</span>
                                <span class="component-desc">
                                    <select id="branchVersion" class="form-control form-control-inline input-sm pull-left">
                                    <% gh_branch = sickbeard.versionCheckScheduler.action.list_remote_branches() %>
                                    % if gh_branch:
                                        % for cur_branch in gh_branch:
                                            % if sickbeard.GIT_USERNAME and sickbeard.GIT_PASSWORD and sickbeard.DEVELOPER == 1:
                                                <option value="${cur_branch}" ${'selected="selected"' if sickbeard.BRANCH == cur_branch else ''}>${cur_branch}</option>
                                            % elif sickbeard.GIT_USERNAME and sickbeard.GIT_PASSWORD and cur_branch in ['master', 'develop']:
                                                <option value="${cur_branch}" ${'selected="selected"' if sickbeard.BRANCH == cur_branch else ''}>${cur_branch}</option>
                                            % elif cur_branch == 'master':
                                                <option value="${cur_branch}" ${'selected="selected"' if sickbeard.BRANCH == cur_branch else ''}>${cur_branch}</option>
                                            % endif
                                        % endfor
                                    % endif
                                    </select>
                                    % if not gh_branch:
                                       <input class="btn btn-inline" style="margin-left: 6px;" type="button" id="branchCheckout" value="Checkout Branch" disabled>
                                    % else:
                                       <input class="btn btn-inline" style="margin-left: 6px;" type="button" id="branchCheckout" value="Checkout Branch">
                                    % endif
                                    % if not gh_branch:
                                       <div class="clear-left" style="color:rgb(255, 0, 0);"><p>Error: No branches found.</p></div>
                                    % else:
                                       <div class="clear-left"><p>select branch to use (restart required)</p></div>
                                    % endif
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="git_username">
                                <span class="component-title">GitHub username</span>
                                <span class="component-desc">
                                    <input type="text" name="git_username" id="git_username" value="${sickbeard.GIT_USERNAME}" class="form-control input-sm input300" autocapitalize="off" autocomplete="no" />
                                    <div class="clear-left"><p>*** (REQUIRED FOR SUBMITTING ISSUES) ***</p></div>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="git_password">
                                <span class="component-title">GitHub password</span>
                                <span class="component-desc">
                                    <input type="password" name="git_password" id="git_password" value="${sickbeard.GIT_PASSWORD}" class="form-control input-sm input300" autocomplete="no" autocapitalize="off" />
                                    <div class="clear-left"><p>*** (REQUIRED FOR SUBMITTING ISSUES) ***</p></div>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="git_remote">
                                <span class="component-title">GitHub remote for branch</span>
                                <span class="component-desc">
                                    <input type="text" name="git_remote" id="git_remote" value="${sickbeard.GIT_REMOTE}" class="form-control input-sm input300" autocapitalize="off" />
                                    <div class="clear-left"><p>default:origin. Access repo configured remotes (save then refresh browser)</p></div>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label>
                                <span class="component-title">Git executable path</span>
                                <span class="component-desc">
                                    <input type="text" name="git_path" value="${sickbeard.GIT_PATH}" class="form-control input-sm input300" autocapitalize="off" />
                                    <div class="clear-left"><p>only needed if OS is unable to locate git from env</p></div>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair" hidden>
                            <label for="git_reset">
                                <span class="component-title">Git reset</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="git_reset" id="git_reset" ${'checked="checked"' if sickbeard.GIT_RESET else ''}/>
                                    <p>removes untracked files and performs a hard reset on git branch automatically to help resolve update issues</p>
                                </span>
                            </label>
                        </div>
                        <input type="submit" class="btn config_submitter" value="Save Changes" />
                    </fieldset>
                </div>
                </div><!-- /component-group3 //-->
                <br />
                <h6 class="pull-right"><b>All non-absolute folder locations are relative to <span class="path">${sickbeard.DATA_DIR}</span></b> </h6>
                <input type="submit" class="btn pull-left config_submitter button" value="Save Changes" />
            </div><!-- /config-components -->
        </form>
    </div>
</div>
</%block>

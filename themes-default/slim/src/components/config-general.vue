<template>
    <div id="config-genaral">
        <div id="config-content">
            <form id="configForm" method="post" @submit.prevent="save()">
                <div id="config-components">
                    <ul>
                        <li><app-link href="#misc">Misc</app-link></li>
                        <li><app-link href="#interface">Interface</app-link></li>
                        <li><app-link href="#advanced-settings">Advanced Settings</app-link></li>
                    </ul>
                    <div id="misc">
                        <div class="row component-group">
                            <div class="component-group-desc col-xs-12 col-md-2">
                                <h3>Misc</h3>
                                <p>Startup options. Indexer options. Log and show file locations.</p>
                                <p><b>Some options may require a manual restart to take effect.</b></p>
                            </div>
                            <div class="col-xs-12 col-md-10">
                                <fieldset class="component-group-list">

                                    <config-toggle-slider v-model="config.launchBrowser" label="Launch browser" id="launch_browser">
                                        <span>open the Medusa home page on startup</span>
                                    </config-toggle-slider>

                                    <config-template label-for="default_page" label="Initial page">
                                        <select id="default_page" name="default_page" v-model="config.defaultPage" class="form-control input-sm">
                                            <option :value="option.value" v-for="option in defaultPageOptions" :key="option.value">{{ option.text }}</option>
                                        </select>
                                        <span>when launching Medusa interface</span>
                                    </config-template>

                                    <config-template label-for="trash_remove_show" label="Send to trash for actions">
                                        <label for="trash_remove_show" class="nextline-block">
                                            <toggle-button :width="45" :height="22" id="trash_remove_show" name="trash_remove_show" v-model="config.trashRemoveShow" sync />
                                            <p>when using show "Remove" and delete files</p>
                                        </label>
                                        <label for="trash_rotate_logs" class="nextline-block">
                                            <toggle-button :width="45" :height="22" id="trash_rotate_logs" name="trash_rotate_logs" v-model="config.trashRotateLogs" sync />
                                            <p>on scheduled deletes of the oldest log files</p>
                                        </label>
                                        <p>selected actions use trash (recycle bin) instead of the default permanent delete</p>
                                    </config-template>

                                    <config-textbox v-model="config.logs.actualLogDir" label="Location for Log files" id="log_id" @change="save()" />

                                    <config-textbox-number v-model="config.logs.nr" label="Number of Log files saved" id="log_nr" :min="1" :step="1">
                                        <p>number of log files saved when rotating logs (default: 5) <b>(REQUIRES RESTART)</b></p>
                                    </config-textbox-number>

                                    <config-textbox-number v-model="config.logs.size" label="Size of Log files saved" id="log_size" :min="0.5" :step="0.1">
                                        <p>maximum size in MB of the log file (default: 1MB) <b>(REQUIRES RESTART)</b></p>
                                    </config-textbox-number>

                                    <config-template label-for="show_root_dir" label="Show root directories">
                                        <p>where the files of shows are located</p>
                                        <p>These changes are automatically saved!</p>
                                        <root-dirs />
                                    </config-template>

                                    <input type="submit" class="btn-medusa config_submitter" value="Save Changes">
                                </fieldset>
                            </div>
                        </div>

                        <div class="row component-group">
                            <div class="component-group-desc col-xs-12 col-md-2">
                                <h3>Indexer</h3>
                                <p>Options for controlling the show indexers.</p>
                            </div>
                            <div class="col-xs-12 col-md-10">
                                <fieldset class="component-group-list">

                                    <config-template label-for="show_root_dir" label="Default Indexer Language">
                                        <language-select @update-language="config.indexerDefaultLanguage = $event" ref="indexerLanguage"
                                                         :language="config.indexerDefaultLanguage" :available="indexers.main.validLanguages.join(',')"
                                                         class="form-control form-control-inline input-sm" />
                                        <span>for adding shows and metadata providers</span>
                                    </config-template>

                                    <config-textbox-number v-model="config.showUpdateHour" label="Choose hour to update shows" id="showupdate_hour" :min="0" :max="23" :step="1">
                                        <p>with information such as next air dates, show ended, etc. Use 15 for 3pm, 4 for 4am etc.</p>
                                        <p><b>Note:</b> minutes are randomized each time Medusa is started</p>
                                    </config-textbox-number>

                                    <config-textbox-number v-model="config.indexerTimeout" label="Timeout show indexer at" id="indexer_timeout" :min="10" :step="1">
                                        <p>seconds of inactivity when finding new shows (default:20)</p>
                                    </config-textbox-number>

                                    <config-template label-for="indexer_default" label="Use initial indexer set to">
                                        <select id="indexer_default" name="indexer_default" v-model="indexerDefault" class="form-control input-sm">
                                            <option v-for="option in indexerListOptions" :value="option.value" :key="option.value">
                                                {{ option.text }}
                                            </option>
                                        </select>
                                    </config-template>

                                    <config-toggle-slider v-model="config.plexFallBack.enable" label="Enable fallback to plex" id="fallback_plex_enable">
                                        <p>Plex provides a tvdb mirror, that can be utilized when Tvdb's api is unavailable.</p>
                                    </config-toggle-slider>

                                    <config-toggle-slider v-model="config.plexFallBack.notifications" label="Enable fallback notifications" id="fallback_plex_notifications">
                                        <p>When this settings has been enabled, you may receive frequent notifications when falling back to the plex mirror.</p>
                                    </config-toggle-slider>

                                    <config-textbox-number v-model="config.plexFallBack.timeout" label="Timeout show indexer at" id="Fallback duration" :min="1" :step="1">
                                        <p>Amount of hours after we try to revert back to the thetvdb.com api url (default:3).</p>
                                    </config-textbox-number>
                                </fieldset>
                            </div>
                        </div>

                        <div class="row component-group">
                            <div class="component-group-desc col-xs-12 col-md-2">
                                <h3>Updates</h3>
                                <p>Options for software updates.</p>
                            </div>
                            <div class="col-xs-12 col-md-10">
                                <fieldset class="component-group-list">

                                    <config-toggle-slider v-model="config.versionNotify" label="Check software updates" id="version_notify">
                                        <p>and display notifications when updates are available.
                                            Checks are run on startup and at the frequency set below*</p>
                                    </config-toggle-slider>

                                    <config-toggle-slider v-model="config.autoUpdate" label="Automatically update" id="auto_update">
                                        <p>fetch and install software updates.
                                            Updates are run on startup and in the background at the frequency set below*</p>
                                    </config-toggle-slider>

                                    <config-textbox-number v-model="config.updateFrequency" label="Check the server every*" id="update_frequency duration" :min="1" :step="1">
                                        <p>hours for software updates (default:1)</p>
                                    </config-textbox-number>

                                    <config-toggle-slider v-model="config.notifyOnUpdate" label="Notify on software update" id="notify_on_update">
                                        <p>send a message to all enabled notifiers when Medusa has been updated</p>
                                    </config-toggle-slider>

                                    <input type="submit" class="btn-medusa config_submitter" value="Save Changes">
                                </fieldset>
                            </div>
                        </div>

                    </div><!-- /component-group1 //-->

                    <div id="interface">
                        <div class="row component-group">
                            <div class="component-group-desc col-xs-12 col-md-2">
                                <h3>User Interface</h3>
                                <p>Options for visual appearance.</p>
                            </div>
                            <div class="col-xs-12 col-md-10">
                                <fieldset class="component-group-list">

                                    <config-template label-for="theme_name" label="Display theme">
                                        <select id="theme_name" name="theme_name" class="form-control input-sm" v-model="layout.themeName" @change="changeTheme(layout.themeName)">
                                            <option :value="option.value" v-for="option in availableThemesOptions"
                                                    :key="option.value">{{ option.text }}
                                            </option>
                                        </select>
                                    </config-template>

                                    <config-toggle-slider v-model="layout.wide" label="Use wider layout" id="layout_wide">
                                        <p>uses all available space in the page</p>
                                    </config-toggle-slider>

                                    <config-toggle-slider v-model="layout.fanartBackground" label="Show fanart in the background" id="fanart_background">
                                        <p>on the show summary page</p>
                                    </config-toggle-slider>

                                    <config-textbox-number v-if="layout.fanartBackground" v-model="layout.fanartBackgroundOpacity" label="Fanart transparency" id="fanart_background_opacity duration" :step="0.1" :min="0.1" :max="1.0">
                                        <p>Transparency of the fanart in the background</p>
                                    </config-textbox-number>

                                    <config-toggle-slider v-model="layout.sortArticle" label="Sort with 'The' 'A', 'An'" id="sort_article">
                                        <p>include articles ("The", "A", "An") when sorting show lists</p>
                                    </config-toggle-slider>

                                    <config-textbox-number v-model="layout.comingEps.missedRange" label="Missed episodes range" id="coming_eps_missed_range duration" :step="1" :min="7">
                                        <p>Set the range in days of the missed episodes in the Schedule page</p>
                                    </config-textbox-number>

                                    <config-toggle-slider v-model="layout.fuzzyDating" label="Display fuzzy dates" id="fuzzy_dating">
                                        <p>move absolute dates into tooltips and display e.g. "Last Thu", "On Tue"</p>
                                    </config-toggle-slider>

                                    <config-toggle-slider v-model="layout.trimZero" label="Trim zero padding" id="trim_zero">
                                        <p>remove the leading number "0" shown on hour of day, and date of month</p>
                                    </config-toggle-slider>

                                    <config-template label-for="date_preset" label="Date style">
                                        <select id="date_preset" name="date_preset" v-model="layout.dateStyle" class="form-control input-sm">
                                            <option :value="option.value" v-for="option in datePresetOptions" :key="option.value">{{ option.text }}</option>
                                        </select>
                                    </config-template>

                                    <config-template label-for="time_preset" label="Time style">
                                        <select id="time_preset" name="time_preset" v-model="layout.timeStyle" class="form-control input-sm">
                                            <option :value="option.value" v-for="option in timePresetOptions" :key="option.value">{{ option.text }}</option>
                                        </select>
                                        <span><b>Note:</b> seconds are only shown on the History page</span>
                                    </config-template>

                                    <config-template label-for="timezone_display" label="Timezone">
                                        <div class="radio-item">
                                            <input type="radio" name="timezone_display_local" id="timezone_display_local" value="local" v-model="layout.timezoneDisplay">
                                            <label for="one">local</label>
                                        </div>
                                        <div class="radio-item">
                                            <input type="radio" name="timezone_display_network" id="timezone_display_network" value="network" v-model="layout.timezoneDisplay">
                                            <label for="one">network</label>
                                        </div>
                                        <p>display dates and times in either your timezone or the shows network timezone</p>
                                        <p><b>Note:</b> Use local timezone to start searching for episodes minutes after show ends (depends on your dailysearch frequency)</p>
                                    </config-template>

                                    <config-textbox v-model="config.downloadUrl" label="Download url" id="download_url">
                                        <span class="component-desc">URL where the shows can be downloaded.</span>
                                    </config-textbox>

                                    <config-toggle-slider v-model="layout.show.pagination.enable" label="Use table pagination" id="show_pagination" />

                                    <input type="submit" class="btn-medusa config_submitter" value="Save Changes">
                                </fieldset>
                            </div>
                        </div> <!-- /User interface row/component-group -->

                        <div class="row component-group">
                            <div class="component-group-desc col-xs-12 col-md-2">
                                <h3>Web Interface</h3>
                                <p>It is recommended that you enable a username and password to secure Medusa from being tampered with remotely.</p>
                                <p><b>These options require a manual restart to take effect.</b></p>
                            </div>
                            <div class="col-xs-12 col-md-10">

                                <fieldset class="component-group-list">

                                    <!-- FIXME: config-textbox Should get a property that makes it read-only  -->
                                    <config-textbox v-model="config.webInterface.apiKey" label="API key" id="api_key" readonly="readonly">
                                        <input class="btn-medusa btn-inline" type="button" id="generate_new_apikey" value="Generate" @click="generateApiKey">
                                        <p>used to give 3rd party programs limited access to Medusa</p>
                                        <p>you can try all the features of the legacy API (v1) <app-link href="apibuilder/">here</app-link></p>
                                    </config-textbox>

                                    <config-toggle-slider v-model="config.webInterface.log" label="HTTP logs" id="web_log">
                                        <p>enable logs from the internal Tornado web server</p>
                                    </config-toggle-slider>

                                    <config-textbox v-model="config.webInterface.username" label="HTTP username" id="web_username" autocomplete="no">
                                        <p>set blank for no login</p>
                                    </config-textbox>

                                    <config-textbox v-model="config.webInterface.password" label="HTTP password" id="web_password" type="password" autocomplete="no">
                                        <p>blank = no authentication</p>
                                    </config-textbox>

                                    <config-textbox-number v-model="config.webInterface.port" label="HTTP port" id="web_port" :min="1" :step="1">
                                        <p>web port to browse and access Medusa (default:8081)</p>
                                    </config-textbox-number>

                                    <config-toggle-slider v-model="config.webInterface.notifyOnLogin" label="Notify on login" id="notify_on_login">
                                        <p>enable to be notified when a new login happens in webserver</p>
                                    </config-toggle-slider>

                                    <config-toggle-slider v-model="config.webInterface.ipv6" label="Listen on IPv6" id="web_ipv6">
                                        <p>enable to be notified when a new login happens in webserver</p>
                                    </config-toggle-slider>

                                    <config-toggle-slider v-model="config.webInterface.httpsEnable" label="Enable HTTPS" id="enable_https">
                                        <p>enable access to the web interface using a HTTPS address</p>
                                    </config-toggle-slider>

                                    <div v-if="config.webInterface.httpsEnable">
                                        <config-textbox v-model="config.webInterface.httpsCert" label="HTTPS certificate" id="https_cert">
                                            <p>file name or path to HTTPS certificate</p>
                                        </config-textbox>

                                        <config-textbox v-model="config.webInterface.httpsKey" label="HTTPS key" id="https_key">
                                            <p>file name or path to HTTPS key</p>
                                        </config-textbox>
                                    </div>

                                    <config-toggle-slider v-model="config.webInterface.handleReverseProxy" label="Reverse proxy headers" id="handle_reverse_proxy">
                                        <p>accept the following reverse proxy headers (advanced)...<br>(X-Forwarded-For, X-Forwarded-Host, and X-Forwarded-Proto)</p>
                                    </config-toggle-slider>

                                    <config-textbox v-model="config.webRoot" label="HTTP web root" id="web_root" autocomplete="no">
                                        <p>Set a base URL, for use in reverse proxies.</p>
                                        <p>blank = disabled</p>
                                        <p><b>Note:</b> Must restart to have effect. Keep in mind that any previously configured base URLs won't work, after this change.</p>
                                    </config-textbox>

                                    <input type="submit" class="btn-medusa config_submitter" value="Save Changes">
                                </fieldset>
                            </div>
                        </div><!-- /web-interface row/component-group //-->
                    </div><!-- /component-group2 //-->

                    <div id="advanced-settings">
                        <div class="row component-group">
                            <div class="component-group-desc col-xs-12 col-md-2">
                                <h3>Advanced Settings</h3>
                            </div>
                            <div class="col-xs-12 col-md-10">
                                <fieldset class="component-group-list">

                                    <config-template label-for="cpu_presets" label="CPU throttling">
                                        <select id="cpu_presets" name="cpu_presets" v-model="config.cpuPreset" class="form-control input-sm">
                                            <option :value="option.value" v-for="option in cpuPresetOptions" :key="option.value">{{ option.text }}</option>
                                        </select>
                                        <span>Normal (default). High is lower and Low is higher CPU use</span>
                                    </config-template>

                                    <config-textbox v-model="config.anonRedirect" label="Anonymous redirect" id="anon_redirect">
                                        <p>backlink protection via anonymizer service, must end in "?"</p>
                                    </config-textbox>

                                    <config-toggle-slider v-model="config.sslVerify" label="Verify SSL Certs" id="ssl_verify">
                                        <p>Verify SSL Certificates (Disable this for broken SSL installs (Like QNAP))</p>
                                    </config-toggle-slider>

                                    <config-textbox v-model="config.sslCaBundle" label="SSL CA Bundle" id="ssl_ca_bundle">
                                        <p>Path to an SSL CA Bundle. Will replace default bundle(certifi) with the one specified.</p>
                                        <b>Note:</b> This only apply to call made using Medusa's Requests implementation.
                                    </config-textbox>

                                    <config-toggle-slider v-model="config.noRestart" label="No Restart" id="no_restart">
                                        <p>Only shutdown when restarting Medusa.
                                            Only select this when you have external software restarting Medusa automatically when it stops (like FireDaemon)</p>
                                    </config-toggle-slider>

                                    <config-toggle-slider v-model="config.encryptionVersion" label="Encrypt passwords" id="encryption_version">
                                        <p>in the <code>config.ini</code> file.
                                            <b>Warning:</b> Passwords must only contain <app-link href="https://en.wikipedia.org/wiki/ASCII#ASCII_printable_characters">ASCII characters</app-link></p>
                                    </config-toggle-slider>

                                    <config-toggle-slider v-model="config.calendarUnprotected" label="Unprotected calendar" id="calendar_unprotected">
                                        <p>allow subscribing to the calendar without user and password.
                                            Some services like Google Calendar only work this way</p>
                                    </config-toggle-slider>

                                    <config-toggle-slider v-model="config.calendarIcons" label="Google Calendar Icons" id="calendar_icons">
                                        <p>show an icon next to exported calendar events in Google Calendar.</p>
                                    </config-toggle-slider>

                                    <config-textbox v-model="config.proxySetting" label="Proxy host" id="proxy_setting">
                                        <p>blank to disable or proxy to use when connecting to providers</p>
                                    </config-textbox>

                                    <config-toggle-slider v-if="config.proxySetting !== ''" v-model="config.proxyIndexers" label="Use proxy for indexers" id="proxy_indexers">
                                        <p>use proxy host for connecting to indexers (thetvdb)</p>
                                    </config-toggle-slider>

                                    <config-toggle-slider v-model="config.skipRemovedFiles" label="Skip Remove Detection" id="skip_removed_files">
                                        <span>
                                            <p>Skip detection of removed files. If disabled the episode will be set to the default deleted status</p>
                                            <b>Note:</b> This may mean Medusa misses renames as well
                                        </span>
                                    </config-toggle-slider>

                                    <config-template label-for="ep_default_deleted_status" label="Default deleted episode status">
                                        <select id="ep_default_deleted_status" name="ep_default_deleted_status" v-model="config.epDefaultDeletedStatus" class="form-control input-sm margin-bottom-5">
                                            <option disabled value="">Please select a default status</option>
                                            <option :value="option.value" v-for="option in defaultDeletedEpOptions" :key="option.value">{{ option.text }}</option>
                                        </select>
                                        <span>Define the status to be set for media file that has been deleted.</span>
                                        <p><b>Note:</b> Archived option will keep previous downloaded quality</p>
                                        <p>Example: Downloaded (1080p WEB-DL) ==> Archived (1080p WEB-DL)</p>
                                    </config-template>

                                    <input type="submit" class="btn-medusa config_submitter" value="Save Changes">
                                </fieldset>
                            </div>
                        </div> <!-- /row -->

                        <div class="row component-group">
                            <div class="component-group-desc col-xs-12 col-md-2">
                                <h3>Logging</h3>
                            </div>
                            <div class="col-xs-12 col-md-10">
                                <fieldset class="component-group-list">

                                    <config-toggle-slider v-model="config.logs.debug" label="Enable debug" id="debug">
                                        <p>Enable debug logs</p>
                                    </config-toggle-slider>

                                    <config-toggle-slider v-if="config.developer" v-model="config.logs.dbDebug" label="Enable DB debug" id="dbdebug">
                                        <p>Enable DB debug logs</p>
                                    </config-toggle-slider>

                                    <config-toggle-slider v-model="config.logs.subliminalLog" label="Subliminal logs" id="subliminal_log">
                                        <p>enable logs from subliminal library (subtitles)</p>
                                    </config-toggle-slider>

                                    <config-template label-for="privacy_level" label="Privacy">
                                        <select id="privacy_level" name="privacy_level" v-model="config.logs.privacyLevel" class="form-control input-sm">
                                            <option :value="option.value" v-for="option in privacyLevelOptions" :key="option.value">{{ option.text }}</option>
                                        </select>
                                        <span>
                                            Set the level of log-filtering.
                                            Normal (default).
                                        </span>
                                    </config-template>

                                    <input type="submit" class="btn-medusa config_submitter" value="Save Changes">
                                </fieldset>
                            </div>
                        </div>

                        <div class="row component-group">
                            <div class="component-group-desc col-xs-12 col-md-2">
                                <h3>GitHub</h3>
                                <p>Options for github related features.</p>
                            </div>
                            <div class="col-xs-12 col-md-10">
                                <fieldset class="component-group-list">

                                    <config-template label-for="github_remote_branches" label="Branch version">
                                        <select id="github_remote_branches" name="github_remote_branches" v-model="system.branch" class="form-control input-sm margin-bottom-5">
                                            <option disabled value="">Please select a branch</option>
                                            <option :value="option.value" v-for="option in githubRemoteBranchesOptions" :key="option.value">{{ option.text }}</option>
                                        </select>
                                        <input :disabled="!githubBranches.length > 0" class="btn-medusa btn-inline" style="margin-left: 6px;" type="button" id="branchCheckout" value="Checkout Branch">
                                        <span v-if="!githubBranches.length > 0" style="color:rgb(255, 0, 0);"><p>Error: No branches found.</p></span>
                                        <p v-else>select branch to use (restart required)</p>
                                    </config-template>

                                    <config-template label-for="date_presets" label="GitHub authentication type">
                                        <div class="radio-item">
                                            <input type="radio" name="git_auth_type_basic" id="git_auth_type_basic" :value="0" v-model="config.git.authType">
                                            <label for="one">Username and password</label>
                                        </div>
                                        <div class="radio-item">
                                            <input type="radio" name="git_auth_type_token" id="git_auth_type_token" :value="1" v-model="config.git.authType">
                                            <label for="one">Personal access token</label>
                                        </div>
                                        <p>You must use a personal access token if you're using "two-factor authentication" on GitHub.</p>
                                    </config-template>

                                    <div v-show="config.git.authType === 0">
                                        <!-- username + password authentication -->
                                        <config-textbox v-model="config.git.username" label="GitHub username" id="git_username">
                                            <p>*** (REQUIRED FOR SUBMITTING ISSUES) ***</p>
                                        </config-textbox>
                                        <config-textbox v-model="config.git.password" label="GitHub password" id="git_password" type="password">
                                            <p>*** (REQUIRED FOR SUBMITTING ISSUES) ***</p>
                                        </config-textbox>
                                    </div>
                                    <div v-show="config.git.authType !== 0">
                                        <!-- Token authentication -->
                                        <config-textbox v-model="config.git.token" @focus.native="$event.target.select()" label="GitHub personal access token" id="git_token" input-class="display-inline margin-bottom-5">
                                            <template v-if="config.git.token === ''">
                                                <v-popover
                                                    trigger="click"
                                                    offset="16"
                                                    placement="right"
                                                    popoverBaseClass="tooltip-base"
                                                    :popoverClass="`tooltip-themed${layout.themeName === 'dark' ? '-dark' : '-light'}`"
                                                >
                                                    <input class="btn-medusa btn-inline" type="button" id="create_access_token" value="Generate Token">
                                                    <template slot="popover">
                                                        <div class="tooltip-title">Github Token</div>
                                                        <div class="tooltip-content">
                                                            <p>Copy the generated token and paste it in the token input box.</p>
                                                            <p>
                                                                <a :href="`${(config.anonRedirect || '')}https://github.com/settings/tokens/new?description=Medusa&scopes=gist,public_repo`" target="_blank">
                                                                    <input class="btn-medusa" type="button" value="Continue to Github...">
                                                                </a>
                                                            </p><br>
                                                        </div>
                                                    </template>
                                                </v-popover>
                                            </template>
                                            <template v-else>
                                                <a :href="`${(config.anonRedirect || '')}https://github.com/settings/tokens`" target="_blank">
                                                    <input class="btn-medusa btn-inline" type="button" id="manage_tokens" value="Manage Tokens">
                                                </a>
                                            </template>

                                            <p>*** (REQUIRED FOR SUBMITTING ISSUES) ***</p>
                                        </config-textbox>
                                    </div>

                                    <config-textbox v-model="config.git.remote" label="GitHub remote for branch" id="git_remote">
                                        <p>default:origin. Access repo configured remotes (save then refresh browser)</p>
                                    </config-textbox>

                                    <config-textbox v-model="config.git.path" label="Git executable path" id="git_path">
                                        <p>only needed if OS is unable to locate git from env</p>
                                    </config-textbox>

                                    <config-toggle-slider v-if="config.developer" v-model="config.git.reset" label="Git reset" id="git_reset">
                                        <p>removes untracked files and performs a hard reset on git branch automatically to help resolve update issues</p>
                                    </config-toggle-slider>

                                    <config-template v-if="config.developer" label-for="git_reset_branches" label="Branches to reset">
                                        <multiselect
                                            v-model="config.git.resetBranches"
                                            :multiple="true"
                                            :options="githubBranches"
                                        />
                                        <input class="btn-medusa btn-inline" style="margin-left: 6px;" type="button" id="branch_force_update" value="Update Branches" @click="githubBranchForceUpdate">
                                        <span class="component-desc"><b>Note:</b> Empty selection means that any branch could be reset.</span>
                                    </config-template>
                                    <input type="submit" class="btn-medusa config_submitter" value="Save Changes">
                                </fieldset>
                            </div><!-- /col -->
                        </div>
                    </div><!-- /component-group3 //-->
                    <br>
                    <h6 class="pull-right"><b>All non-absolute folder locations are relative to <span class="path">{{system.dataDir}}</span></b> </h6>
                    <input type="submit" class="btn-medusa pull-left config_submitter button" value="Save Changes">
                </div><!-- /config-components -->
            </form>
        </div>
    </div>
</template>

<script>
import { apiRoute } from '../api.js';
import { mapActions, mapGetters, mapState } from 'vuex';
import RootDirs from './root-dirs.vue';
import {
    AppLink,
    ConfigTemplate,
    ConfigTextbox,
    ConfigTextboxNumber,
    ConfigToggleSlider,
    LanguageSelect
} from './helpers';
import { convertDateFormat } from '../utils/core.js';
import formatDate from 'date-fns/format';
import { ToggleButton } from 'vue-js-toggle-button';
import Multiselect from 'vue-multiselect';
import 'vue-multiselect/dist/vue-multiselect.min.css';

import { VTooltip, VPopover } from 'v-tooltip';

export default {
    name: 'config-general',
    components: {
        AppLink,
        ConfigTemplate,
        ConfigTextbox,
        ConfigTextboxNumber,
        ConfigToggleSlider,
        LanguageSelect,
        Multiselect,
        VPopover,
        ToggleButton,
        RootDirs
    },
    directives: {
        tooltip: VTooltip
    },
    data() {
        const defaultPageOptions = [
            { value: 'home', text: 'Shows' },
            { value: 'schedule', text: 'Schedule' },
            { value: 'history', text: 'History' },
            { value: 'news', text: 'News' },
            { value: 'IRC', text: 'IRC' }
        ];

        const privacyLevelOptions = [
            { value: 'high', text: 'HIGH' },
            { value: 'normal', text: 'NORMAL' },
            { value: 'low', text: 'LOW' }
        ];

        return {
            defaultPageOptions,
            privacyLevelOptions,
            githubBranchesForced: [],
            resetBranchSelected: null
        };
    },
    beforeMount() {
        // Wait for the next tick, so the component is rendered
        this.$nextTick(() => {
            $('#config-components').tabs();
        });
    },
    computed: {
        ...mapState({
            config: state => state.config.general,
            configLoaded: state => state.config.consts.statuses.length > 0,
            layout: state => state.config.layout,
            statuses: state => state.config.consts.statuses,
            indexers: state => state.config.indexers,
            system: state => state.config.system
        }),
        ...mapGetters([
            'getStatus'
        ]),
        indexerDefault: {
            get() {
                const { config } = this;
                const { indexerDefault } = config;
                return indexerDefault || 0;
            },
            set(indexer) {
                this.config.indexerDefault = indexer;
            }
        },
        indexerListOptions() {
            const { indexers } = this;
            const allIndexers = [{ text: 'All Indexers', value: 0 }];

            const indexerOptions = Object.values(indexers.indexers).map(indexer => ({ value: indexer.id, text: indexer.name }));
            return [...allIndexers, ...indexerOptions];
        },
        datePresetOptions() {
            const { config } = this;
            const { datePresets } = config;
            const systemDefault = [{ value: '%x', text: 'Use System Default' }];
            const formattedDatePresets = datePresets.map(preset => ({ value: preset, text: formatDate(new Date(), convertDateFormat(preset)) }));
            return [...systemDefault, ...formattedDatePresets];
        },
        timePresetOptions() {
            const { config } = this;
            const { timePresets } = config;
            const systemDefault = [{ value: '%x', text: 'Use System Default' }];
            const formattedTimePresets = timePresets.map(preset => ({ value: preset, text: formatDate(new Date(), convertDateFormat(preset)) }));
            return [...systemDefault, ...formattedTimePresets];
        },
        availableThemesOptions() {
            const { config } = this;
            const { availableThemes } = config;
            if (!availableThemes) {
                return [];
            }
            return availableThemes.map(theme => ({ value: theme.name, text: `${theme.name} (${theme.version})` }));
        },
        cpuPresetOptions() {
            const { system } = this;
            const { cpuPresets } = system;
            if (!cpuPresets) {
                return [];
            }
            return Object.keys(cpuPresets).map(key => ({ value: key, text: key }));
        },
        defaultDeletedEpOptions() {
            const { config, getStatus } = this;
            let status = [];

            if (config.skipRemovedFiles) {
                status = ['skipped', 'ignored'].map(key => getStatus({
                    key
                }));
            } else {
                // Get status objects, when skip removed files is enabled
                status = ['skipped', 'ignored', 'archived'].map(key => getStatus({ key }));
            }

            if (status.every(x => x !== undefined)) {
                return status.map(status => ({ text: status.name, value: status.value }));
            }

            return [];
        },
        githubRemoteBranchesOptions() {
            const { config, githubBranches, githubBranchForceUpdate } = this;
            const { system } = this;
            const { username, password, token } = config.git;

            if (!system.gitRemoteBranches) {
                return [];
            }

            if (!system.gitRemoteBranches.length > 0) {
                githubBranchForceUpdate();
            }

            let filteredBranches = [];

            if (((username && password) || token) && config.developer) {
                filteredBranches = githubBranches;
            } else if ((username && password) || token) {
                filteredBranches = githubBranches.filter(branch => ['master', 'develop'].includes(branch));
            } else {
                filteredBranches = githubBranches.filter(branch => ['master'].includes(branch));
            }

            return filteredBranches.map(branch => ({ text: branch, value: branch }));
        },
        githubBranches() {
            const { system, githubBranchesForced } = this;
            return system.gitRemoteBranches || githubBranchesForced;
        },
        githubTokenPopover() {
            const { config } = this;
            return '<p>Copy the generated token and paste it in the token input box.</p>' +
                `<p><a href="${(config.anonRedirect || '')}https://github.com/settings/tokens/new?description=Medusa&scopes=gist,public_repo" target="_blank">` +
                '<input class="btn-medusa" type="button" value="Continue to Github..."></a></p><br/>';
        }
    },
    methods: {
        ...mapActions([
            'setConfig',
            'setTheme',
            'getApiKey'
        ]),
        async githubBranchForceUpdate() {
            const response = await apiRoute('home/branchForceUpdate');
            if (response.data._size > 0) {
                this.githubBranchesForced = response.data.resetBranches;
            }
        },
        async generateApiKey() {
            const { getApiKey, save } = this;
            try {
                await getApiKey();
                this.$snotify.success(
                    'Saving and reloading the page, to utilize the new api key',
                    'Warning',
                    { timeout: 5000 }
                );
                setTimeout(() => {
                    // Save the new apiKey. No choice to reload because of /src/api.js
                    save();
                }, 500);
                setTimeout(() => {
                    // For now we reload the page since the layouts use python still
                    location.reload();
                }, 500);
            } catch (error) {
                this.$snotify.error(
                    'Error while trying to get a new api key',
                    `Error: ${error}`
                );
            }
        },
        async changeTheme(themeName) {
            const { setTheme } = this;
            try {
                await setTheme({ themeName });
                this.$snotify.success(
                    'Saving and reloading the page',
                    'Saving',
                    { timeout: 5000 }
                );
                setTimeout(() => {
                    // For now we reload the page since the layouts use python still
                    location.reload();
                }, 1000);
            } catch (error) {
                this.$snotify.error(
                    'Error while trying to change the theme',
                    `Error: ${error}`
                );
            }
        },
        async save() {
            const { config, layout, setConfig } = this;

            // Disable the save button until we're done.
            this.saving = true;

            const {
                availableThemes,
                backlogOverview,
                datePresets,
                loggingLevels,
                logs,
                timePresets,
                randomShowSlug,
                recentShows,
                themeName,
                ...filteredConfig } = config;

            const { local, ...filteredLayout } = layout;

            const configMain = {
                section: 'main',
                config: {
                    ...filteredConfig,
                    ...{ layout: filteredLayout },
                    ...{ logs: {
                        debug: config.logs.debug,
                        dbDebug: config.logs.dbDebug,
                        actualLogDir: config.logs.actualLogDir,
                        nr: config.logs.nr,
                        size: config.logs.size,
                        subliminalLog: config.logs.subliminalLog,
                        privacyLevel: config.logs.privacyLevel
                    } }
                }
            };

            try {
                await setConfig(configMain);
                this.$snotify.success(
                    'Saved general config',
                    'Saved',
                    { timeout: 5000 }
                );
            } catch (error) {
                this.$snotify.error(
                    'Error while trying to save general config',
                    `Error: ${error}`
                );
            } finally {
                this.saving = false;
            }
        }
    }
};
</script>
<style>
.display-inline {
    display: inline;
}

.radio-item {
    display: block;
}

.multiselect {
    margin-bottom: 10px;
}

.margin-bottom-5 {
    margin-bottom: 5px;
}

.plotInfo {
    cursor: help;
    float: right;
    position: relative;
    top: 2px;
}

.plotInfoNone {
    cursor: help;
    float: right;
    position: relative;
    top: 2px;
    opacity: 0.4;
}

.v-popover {
    display: inline;
}

.tooltip-base {
    position: relative;
    display: inline-block !important;
    z-index: 999;
    max-width: 276px;
    padding: 1px;
    font-family: Helvetica Neue, Helvetica, Arial, sans-serif;
    font-style: normal;
    font-weight: 400;
    font-size: 14px;
    line-height: 1.42857143;
    line-break: auto;
    text-align: start;
    text-decoration: none;
    text-shadow: none;
    text-transform: none;
    letter-spacing: normal;
    word-break: normal;
    word-spacing: normal;
    word-wrap: normal;
    white-space: normal;
    background-color: #fff;
    background-clip: padding-box;
    border: 1px solid rgba(0, 0, 0, 0.2);
    border-radius: 6px;
    box-shadow: 0 5px 10px rgba(0, 0, 0, 0.2);
}

.tooltip-base.tooltip-themed-dark {
    background-color: rgb(51, 51, 51);
    border-color: #111;
}

.tooltip-base .tooltip-inner {
    background-color: inherit;
    color: inherit;
    text-align: inherit;
    max-width: inherit;
    padding: 0;
    border-radius: 6px;
}

.tooltip-title {
    padding: 8px 14px;
    margin: 0;
    border-radius: 5px 5px 0 0;
}

.tooltip-content {
    padding: 9px 14px;
    margin: 0;
}

.tooltip-themed-dark .tooltip-title {
    background-color: rgb(35, 35, 35);
    border-bottom-color: #111;
}

.tooltip-themed-light .tooltip-title {
    padding: 8px 14px;
    margin: 0;
    font-size: 14px;
    background-color: #f7f7f7;
    border-bottom: 1px solid #ebebeb;
    border-radius: 5px 5px 0 0;
}

.tooltip-base[x-placement^="left"]::after,
.tooltip-base[x-placement^="left"]::before {
    left: 100%;
    top: 50%;
    border: solid transparent;
    content: " ";
    height: 0;
    width: 0;
    position: absolute;
    pointer-events: none;
}

.tooltip-base[x-placement^="left"]::after {
    border-color: rgba(255, 255, 255, 0);
    border-left-color: #fff;
    border-width: 11px;
    margin-top: -11px;
    content: " ";
}

.tooltip-base[x-placement^="left"]::before {
    border-color: rgba(0, 0, 0, 0);
    border-left-color: rgba(0, 0, 0, 0.2);
    border-width: 12px;
    margin-top: -12px;
    content: " ";
}

.tooltip-base[x-placement^="right"]::after,
.tooltip-base[x-placement^="right"]::before {
    right: 100%;
    top: 50%;
    border: solid transparent;
    content: " ";
    height: 0;
    width: 0;
    position: absolute;
    pointer-events: none;
}

.tooltip-base[x-placement^="right"]::after {
    border-color: rgba(255, 255, 255, 0);
    border-right-color: #fff;
    border-width: 11px;
    margin-top: -11px;
    content: " ";
}

.tooltip-base[x-placement^="right"]::before {
    border-color: rgba(0, 0, 0, 0);
    border-right-color: rgba(0, 0, 0, 0.2);
    border-width: 12px;
    margin-top: -12px;
    content: " ";
}

/* The background of the arrow, the outline */
.tooltip-themed-dark[x-placement^="left"]::before {
    border-left-color: #000 !important;
}

/* The background of the arrow, the outline */
.tooltip-themed-dark[x-placement^="right"]::before {
    border-right-color: #000 !important;
}

/* The foreground of the arrow, the filling  */
.tooltip-themed-dark[x-placement^="left"]::after {
    border-left-color: rgb(51, 51, 51) !important;
}

/* The foreground of the arrow, the filling  */
.tooltip-themed-dark[x-placement^="right"]::after {
    border-right-color: rgb(51, 51, 51) !important;
}

.tooltip-arrow {
    display: none;
}

</style>

<%inherit file="/layouts/main.mako"/>
<%!
    import re
    from medusa import app
    from medusa.common import SKIPPED, WANTED, UNAIRED, ARCHIVED, IGNORED, SNATCHED, SNATCHED_PROPER, SNATCHED_BEST, FAILED
    from medusa.common import Quality, qualityPresets, statusStrings, qualityPresetStrings, cpu_presets, MULTI_EP_STRINGS
    from medusa.indexers.indexer_api import indexerApi
    from medusa.indexers.utils import get_trakt_indexer
%>
<%block name="scripts">
<script>
window.app = {};
window.app = new Vue({
    store,
    router,
    el: '#vue-wrap',

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
                    <li><app-link href="#home-theater-nas">Home Theater / NAS</app-link></li>
                    <li><app-link href="#devices">Devices</app-link></li>
                    <li><app-link href="#social">Social</app-link></li>
                </ul>

                <div id="home-theater-nas">
                    <div class="row component-group">
                        <div class="component-group-desc col-xs-12 col-md-2">
                            <span class="icon-notifiers-kodi" title="KODI"></span>
                            <h3><app-link href="http://kodi.tv">KODI</app-link></h3>
                            <p>A free and open source cross-platform media center and home entertainment system software with a 10-foot user interface designed for the living-room TV.</p>
                        </div>
                        <div class="col-xs-12 col-md-10">
                            <fieldset class="component-group-list">
                                <!-- All form components here for KODI -->

                                <config-toggle-slider v-model="notifiers.kodi.enabled" label="Enable" id="use_kodi" :explanations="['Send KODI commands?']" @change="save()" ></config-toggle-slider>

                                <div v-show="notifiers.kodi.enabled" id="content-use-kodi"> <!-- show based on notifiers.kodi.enabled -->

                                    <config-toggle-slider v-model="notifiers.kodi.alwaysOn" label="Always on" id="kodi_always_on" :explanations="['log errors when unreachable?']" @change="save()" ></config-toggle-slider>

                                    <config-toggle-slider v-model="notifiers.kodi.notifyOnSnatch" label="Notify on snatch" id="kodi_notify_onsnatch" :explanations="['send a notification when a download starts?']" @change="save()" ></config-toggle-slider>

                                    <config-toggle-slider v-model="notifiers.kodi.notifyOnDownload" label="Notify on download" id="kodi_notify_ondownload" :explanations="['send a notification when a download finishes?']" @change="save()" ></config-toggle-slider>

                                    <config-toggle-slider v-model="notifiers.kodi.notifyOnSubtitleDownload" label="Notify on subtitle download" id="kodi_notify_onsubtitledownload" :explanations="['send a notification when subtitles are downloaded?']" @change="save()" ></config-toggle-slider>

                                    <config-toggle-slider v-model="notifiers.kodi.update.library" label="Update library" id="kodi_update_library" :explanations="['update KODI library when a download finishes?']" @change="save()" ></config-toggle-slider>
                                    <config-toggle-slider v-model="notifiers.kodi.update.full" label="Full library update" id="kodi_update_full" :explanations="['perform a full library update if update per-show fails?']" @change="save()" ></config-toggle-slider>

                                    <config-toggle-slider v-model="notifiers.kodi.cleanLibrary" label="Clean library" id="kodi_clean_library" :explanations="['clean KODI library when replaces a already downloaded episode?']" @change="save()" ></config-toggle-slider>
                                    <config-toggle-slider v-model="notifiers.kodi.update.onlyFirst" label="Only update first host" id="kodi_update_onlyfirst" :explanations="['only send library updates/clean to the first active host?']" @change="save()" ></config-toggle-slider>


                                    <div class="form-group">
                                        <div class="row">
                                            <label for="kodi_host" class="col-sm-2 control-label">
                                                <span>KODI IP:Port</span>
                                            </label>
                                            <div class="col-sm-10 content">
                                                <select-list name="kodi_host" id="kodi_host" :list-items="notifiers.kodi.host" @change="notifiers.kodi.host = $event.map(x => x.value)"></select-list>
                                                <p>host running KODI (eg. 192.168.1.100:8080)</p>
                                            </div>
                                        </div>
                                    </div>

                                    <config-textbox v-model="notifiers.kodi.username" label="Username" id="kodi_username" :explanations="['username for your KODI server (blank for none)']" @change="save()"></config-textbox>
                                    <config-textbox v-model="notifiers.kodi.password" type="password" label="Password" id="kodi_password" :explanations="['password for your KODI server (blank for none)']" @change="save()"></config-textbox>

                                    <div class="testNotification" id="testKODI-result">Click below to test.</div>
                                    <input  class="btn-medusa" type="button" value="Test KODI" id="testKODI" @click="testKODI"/>
                                    <input type="submit" class="config_submitter btn-medusa" value="Save Changes"/>

                                </div>

                            </fieldset>
                        </div>

                    </div>

                    <div class="row component-group">
                        <div class="component-group-desc col-xs-12 col-md-2">
                            <span class="icon-notifiers-plex" title="Plex Media Server"></span>
                            <h3><app-link href="https://plex.tv">Plex Media Server</app-link></h3>
                            <p>Experience your media on a visually stunning, easy to use interface on your Mac connected to your TV. Your media library has never looked this good!</p>
                            <p v-if="notifiers.plex.server.enabled" class="plexinfo">For sending notifications to Plex Home Theater (PHT) clients, use the KODI notifier with port <b>3005</b>.</p>
                        </div>
                        <div class="col-xs-12 col-md-10">
                            <fieldset class="component-group-list">
                                <!-- All form components here for plex media server -->

                                <config-toggle-slider v-model="notifiers.plex.server.enabled" label="Enable" id="use_plex_server" :explanations="['Send KODI commands?']" @change="save()" ></config-toggle-slider>

                                <div v-show="notifiers.plex.server.enabled" id="content-use-plex-server"> <!-- show based on notifiers.plex.server.enabled -->
                                    <config-textbox v-model="notifiers.plex.server.token" label="Plex Media Server Auth Token" id="plex_server_token" @change="save()" >
                                        <p>Auth Token used by plex</p>
                                        <p><span>See: <app-link href="https://support.plex.tv/hc/en-us/articles/204059436-Finding-your-account-token-X-Plex-Token" class="wiki"><strong>Finding your account token</strong></app-link></span></p>
                                    </config-textbox>

                                    <config-textbox v-model="notifiers.plex.server.username" label="Username" id="plex_server_username" :explanations="['blank = no authentication']" @change="save()"></config-textbox>
                                    <config-textbox v-model="notifiers.plex.server.password" type="password" label="Password" id="plex_server_password" :explanations="['blank = no authentication']" @change="save()"></config-textbox>

                                    <config-toggle-slider v-model="notifiers.plex.server.updateLibrary" label="Update Library" id="plex_update_library" :explanations="['log errors when unreachable?']" @change="save()"></config-toggle-slider>

                                    <config-template label-for="plex_server_host" label="Plex Media Server IP:Port">
                                        <select-list name="plex_server_host" id="plex_server_host" :list-items="notifiers.plex.server.host" @change="notifiers.plex.server.host = $event.map(x => x.value)"></select-list>
                                        <p>one or more hosts running Plex Media Server<br>(eg. 192.168.1.1:32400, 192.168.1.2:32400)</p>
                                    </config-template>

                                    <config-toggle-slider v-model="notifiers.plex.server.https" label="HTTPS" id="plex_server_https" :explanations="['use https for plex media server requests?']" @change="save()"></config-toggle-slider>

                                    <div class="field-pair">
                                        <div class="testNotification" id="testPMS-result">Click below to test Plex Media Server(s)</div>
                                        <input class="btn-medusa" type="button" value="Test Plex Media Server" id="testPMS" @click="testPMS"/>
                                        <input type="submit" class="config_submitter btn-medusa" value="Save Changes"/>
                                        <div class="clear-left">&nbsp;</div>
                                    </div>

                                </div>
                            </fieldset>
                        </div>
                    </div>

                    <div class="row component-group">
                        <div class="component-group-desc col-xs-12 col-md-2">
                            <span class="icon-notifiers-plexth" title="Plex Media Client"></span>
                            <h3><app-link href="https://plex.tv">Plex Home Theater</app-link></h3>
                        </div>
                        <div class="col-xs-12 col-md-10">
                            <fieldset class="component-group-list">
                                <!-- All form components here for plex media client -->
                                <config-toggle-slider v-model="notifiers.plex.client.enabled" label="Enable" id="use_plex_client" :explanations="['Send Plex Home Theater notifications?']" @change="save()" ></config-toggle-slider>

                                <div v-show="notifiers.plex.client.enabled" id="content-use-plex-client"> <!-- show based on notifiers.plex.server.enabled -->
                                    <config-toggle-slider v-model="notifiers.plex.client.notifyOnSnatch" label="Notify on snatch" id="plex_notify_onsnatch" :explanations="['send a notification when a download starts?']" @change="save()" ></config-toggle-slider>
                                    <config-toggle-slider v-model="notifiers.plex.client.notifyOnDownload" label="Notify on download" id="plex_notify_ondownload" :explanations="['send a notification when a download finishes?']" @change="save()" ></config-toggle-slider>
                                    <config-toggle-slider v-model="notifiers.plex.client.notifyOnSubtitleDownload" label="Notify on subtitle download" id="plex_notify_onsubtitledownload" :explanations="['send a notification when subtitles are downloaded?']" @change="save()" ></config-toggle-slider>

                                    <config-template label-for="plex_client_host" label="Plex Home Theater IP:Port">
                                        <select-list name="plex_client_host" id="plex_client_host" :list-items="notifiers.plex.client.host" @change="notifiers.plex.client.host = $event.map(x => x.value)"></select-list>
                                        <p>one or more hosts running Plex Home Theater<br>(eg. 192.168.1.100:3000, 192.168.1.101:3000)</p>
                                    </config-template>

                                    <config-textbox v-model="notifiers.plex.client.username" label="Username" id="plex_client_username" :explanations="['blank = no authentication']" @change="save()" ></config-textbox>
                                    <config-textbox v-model="notifiers.plex.client.password" type="password" label="Password" id="plex_client_password" :explanations="['blank = no authentication']" @change="save()" ></config-textbox>

                                    <div class="field-pair">
                                        <div class="testNotification" id="testPHT-result">Click below to test Plex Home Theater(s)</div>
                                        <input class="btn-medusa" type="button" value="Test Plex Home Theater" id="testPHT" @click="testPHT"/>
                                        <input type="submit" class="config_submitter btn-medusa" value="Save Changes"/>
                                        <div class=clear-left><p>Note: some Plex Home Theaters <b class="boldest">do not</b> support notifications e.g. Plexapp for Samsung TVs</p></div>
                                    </div>

                                </div>
                            </fieldset>
                        </div>
                    </div>

                    <div class="row component-group">
                        <div class="component-group-desc col-xs-12 col-md-2">
                            <span class="icon-notifiers-emby" title="Emby"></span>
                            <h3><app-link href="http://emby.media">Emby</app-link></h3>
                            <p>A home media server built using other popular open source technologies.</p>
                        </div>
                        <div class="col-xs-12 col-md-10">
                            <fieldset class="component-group-list">
                                <!-- All form components here for emby -->
                                <config-toggle-slider v-model="notifiers.emby.enabled" label="Enable" id="use_emby" :explanations="['Send update commands to Emby?']" @change="save()" ></config-toggle-slider>

                                <div v-show="notifiers.emby.enabled" id="content_use_emby">
                                    <config-textbox v-model="notifiers.emby.host" label="Emby IP:Port" id="emby_host" :explanations="['host running Emby (eg. 192.168.1.100:8096)']" @change="save()" ></config-textbox>
                                    <config-textbox v-model="notifiers.emby.apiKey" label="Api Key" id="emby_apikey" @change="save()" ></config-textbox>

                                    <div class="testNotification" id="testEMBY-result">Click below to test.</div>
                                    <input class="btn-medusa" type="button" value="Test Emby" id="testEMBY" @click="testEMBY"/>
                                </div>
                            </fieldset>
                        </div>
                    </div>

                    <div class="row component-group">
                        <div class="component-group-desc col-xs-12 col-md-2">
                            <span class="icon-notifiers-nmj" title="Networked Media Jukebox"></span>
                            <h3><app-link href="http://www.popcornhour.com/">NMJ</app-link></h3>
                            <p>The Networked Media Jukebox, or NMJ, is the official media jukebox interface made available for the Popcorn Hour 200-series.</p>
                        </div>
                        <div class="col-xs-12 col-md-10">
                            <fieldset class="component-group-list">
                                <!-- All form components here for nmj -->
                                <config-toggle-slider v-model="notifiers.nmj.enabled" label="Enable" id="use_nmj" :explanations="['Send update commands to NMJ?']" @change="save()" ></config-toggle-slider>
                                <div v-show="notifiers.nmj.enabled" id="content-use-nmj">
                                    <config-textbox v-model="notifiers.nmj.host" label="Popcorn IP address" id="nmj_host" :explanations="['IP address of Popcorn 200-series (eg. 192.168.1.100)']" @change="save()" ></config-textbox>

                                    <config-template label-for="settingsNMJ" label="Get settings">
                                        <input class="btn-medusa btn-inline" type="button" value="Get Settings" id="settingsNMJ" @click="settingsNMJ"/>
                                        <span>the Popcorn Hour device must be powered on and NMJ running.</span>
                                    </config-template>

                                    <config-textbox v-model="notifiers.nmj.database" label="NMJ database" id="nmj_database" :explanations="['automatically filled via the \'Get Settings\' button.']" @change="save()" ></config-textbox>

                                    <config-textbox v-model="notifiers.nmj.mount" label="NMJ mount" id="nmj_mount" :explanations="['automatically filled via the \'Get Settings\' button.']" @change="save()" ></config-textbox>

                                    <div class="testNotification" id="testNMJ-result">Click below to test.</div>
                                    <input class="btn-medusa" type="button" value="Test NMJ" id="testNMJ" @click="testNMJ"/>
                                    <input type="submit" class="config_submitter btn-medusa" value="Save Changes"/>

                                </div>
                            </fieldset>
                        </div>
                    </div>

                    <div class="row component-group">
                        <div class="component-group-desc col-xs-12 col-md-2">
                            <span class="icon-notifiers-nmj" title="Networked Media Jukebox v2"></span>
                            <h3><app-link href="http://www.popcornhour.com/">NMJv2</app-link></h3>
                            <p>The Networked Media Jukebox, or NMJv2, is the official media jukebox interface made available for the Popcorn Hour 300 & 400-series.</p>
                        </div>
                        <div class="col-xs-12 col-md-10">
                            <fieldset class="component-group-list">
                                <!-- All form components here for njm (popcorn) client -->
                                <config-toggle-slider v-model="notifiers.nmjv2.enabled" label="Enable" id="use_nmjv2" :explanations="['Send popcorn hour (nmjv2) notifications?']" @change="save()" ></config-toggle-slider>
                                <div v-show="notifiers.nmjv2.enabled" id="content-use-nmjv2">

                                    <config-textbox v-model="notifiers.nmjv2.host" label="Popcorn IP address" id="nmjv2_host" :explanations="['IP address of Popcorn 300/400-series (eg. 192.168.1.100)']" @change="save()" ></config-textbox>

                                    <config-template label-for="nmjv2_database_location" label="Database location">
                                        <label for="NMJV2_DBLOC_A" class="space-right">
                                            <input type="radio" NAME="nmjv2_dbloc" VALUE="local" id="NMJV2_DBLOC_A" v-model="notifiers.nmjv2.dbloc" value="local"/>
                                            PCH Local Media
                                        </label>
                                        <label for="NMJV2_DBLOC_B">
                                            <input type="radio" NAME="nmjv2_dbloc" VALUE="network" id="NMJV2_DBLOC_B" v-model="notifiers.nmjv2.dbloc" value="network"/>
                                            PCH Network Media
                                        </label>
                                    </config-template>

                                    <config-template label-for="nmjv2_database_instance" label="Database instance">
                                        <select id="NMJv2db_instance" class="form-control input-sm">
                                            <option value="0">#1 </option>
                                            <option value="1">#2 </option>
                                            <option value="2">#3 </option>
                                            <option value="3">#4 </option>
                                            <option value="4">#5 </option>
                                            <option value="5">#6 </option>
                                            <option value="6">#7 </option>
                                        </select>
                                        <span>adjust this value if the wrong database is selected.</span>
                                    </config-template>

                                    <config-template label-for="get_nmjv2_find_database" label="Find database">
                                        <input type="button" class="btn-medusa btn-inline" value="Find Database" id="settingsNMJv2" @click="settingsNMJv2"/>
                                        <span>the Popcorn Hour device must be powered on.</span>
                                    </config-template>

                                    <config-textbox v-model="notifiers.nmjv2.database" label="NMJv2 database" id="nmjv2_database" :explanations="['automatically filled via the \'Find Database\' buttons.']" @change="save()" ></config-textbox>
                                    <div class="testNotification" id="testNMJv2-result">Click below to test.</div>
                                    <input class="btn-medusa" type="button" value="Test NMJv2" id="testNMJv2" @click="testNMJv2"/>
                                    <input type="submit" class="config_submitter btn-medusa" value="Save Changes"/>
                                </div>
                            </fieldset>
                        </div>
                    </div>

                    <div class="row component-group">
                        <div class="component-group-desc col-xs-12 col-md-2">
                            <span class="icon-notifiers-syno1" title="Synology"></span>
                            <h3><app-link href="http://synology.com/">Synology</app-link></h3>
                            <p>The Synology DiskStation NAS.</p>
                            <p>Synology Indexer is the daemon running on the Synology NAS to build its media database.</p>
                        </div>
                        <div class="col-xs-12 col-md-10">
                            <fieldset class="component-group-list">
                                <!-- All form components here for synology indexer -->
                                <config-toggle-slider v-model="notifiers.synologyIndex.enabled" label="HTTPS" id="use_synoindex" :explanations="['Note: requires Medusa to be running on your Synology NAS.']" @change="save()" ></config-toggle-slider>
                                <div v-show="notifiers.synologyIndex.enabled" id="content_use_synoindex">
                                        <input type="submit" class="config_submitter btn-medusa" value="Save Changes"/>
                                </div>
                            </fieldset>
                        </div>
                    </div>

                    <div class="row component-group">
                        <div class="component-group-desc col-xs-12 col-md-2">
                            <span class="icon-notifiers-syno2" title="Synology Indexer"></span>
                            <h3><app-link href="http://synology.com/">Synology Notifier</app-link></h3>
                            <p>Synology Notifier is the notification system of Synology DSM</p>
                        </div>
                        <div class="col-xs-12 col-md-10">
                            <fieldset class="component-group-list">
                                <!-- All form components here for synology notifier -->
                                <config-toggle-slider v-model="notifiers.synology.enabled" label="Enable" id="use_synologynotifier"
                                    :explanations="['Send notifications to the Synology Notifier?', 'Note: requires Medusa to be running on your Synology DSM.']"
                                    @change="save()" >
                                </config-toggle-slider>
                                <div v-show="notifiers.synology.enabled" id="content-use-synology-notifier">
                                    <config-toggle-slider v-model="notifiers.synology.notifyOnSnatch" label="Notify on snatch" id="_notify_onsnatch" :explanations="['send a notification when a download starts?']" @change="save()" ></config-toggle-slider>
                                    <config-toggle-slider v-model="notifiers.synology.notifyOnDownload" label="Notify on download" id="synology_notify_ondownload" :explanations="['send a notification when a download finishes?']" @change="save()" ></config-toggle-slider>
                                    <config-toggle-slider v-model="notifiers.synology.notifyOnSubtitleDownload" label="Notify on subtitle download" id="synology_notify_onsubtitledownload" :explanations="['send a notification when subtitles are downloaded?']" @change="save()" ></config-toggle-slider>
                                    <input type="submit" class="config_submitter btn-medusa" value="Save Changes"/>
                                </div>
                            </fieldset>
                        </div>
                    </div>

                    <div class="row component-group">
                        <div class="component-group-desc col-xs-12 col-md-2">
                            <span class="icon-notifiers-pytivo" title="pyTivo"></span>
                            <h3><app-link href="http://pytivo.sourceforge.net/wiki/index.php/PyTivo">pyTivo</app-link></h3>
                            <p>pyTivo is both an HMO and GoBack server. This notifier will load the completed downloads to your Tivo.</p>
                        </div>
                        <div class="col-xs-12 col-md-10">
                            <fieldset class="component-group-list">
                                <!-- All form components here for pyTivo client -->
                                <config-toggle-slider v-model="notifiers.pyTivo.enabled" label="Enable" id="use_pytivo" :explanations="['Send Plex Home Theater notifications?']" @change="save()" ></config-toggle-slider>
                                <div v-show="notifiers.pyTivo.enabled" id="content-use-pytivo"> <!-- show based on notifiers.pyTivo.enabled -->
                                    <config-textbox v-model="notifiers.pyTivo.host" label="pyTivo IP:Port" id="pytivo_host" :explanations="['host running pyTivo (eg. 192.168.1.1:9032)']" @change="save()" ></config-textbox>
                                    <config-textbox v-model="notifiers.pyTivo.shareName" label="pyTivo share name" id="pytivo_name" :explanations="['(Messages \& Settings > Account \& System Information > System Information > DVR name)']" @change="save()" ></config-textbox>
                                    <config-textbox v-model="notifiers.pyTivo.name" label="Tivo name" id="pytivo_tivo_name" :explanations="['value used in pyTivo Web Configuration to name the share.']" @change="save()" ></config-textbox>
                                    <input type="submit" class="config_submitter btn-medusa" value="Save Changes"/>
                                </div>
                            </fieldset>
                        </div>
                    </div>
                </div><!-- #home-theater-nas //-->

                <div id="devices">
                    <div class="row component-group">
                        <div class="component-group-desc col-xs-12 col-md-2">
                            <span class="icon-notifiers-growl" title="Growl"></span>
                            <h3><app-link href="http://growl.info/">Growl</app-link></h3>
                            <p>A cross-platform unobtrusive global notification system.</p>
                        </div>
                        <div class="col-xs-12 col-md-10">
                            <fieldset class="component-group-list">
                                <!-- All form components here for growl client -->
                                <config-toggle-slider v-model="notifiers.growl.enabled" label="Enable" id="use_growl_client" :explanations="['Send growl Home Theater notifications?']" @change="save()" ></config-toggle-slider>
                                <div v-show="notifiers.growl.enabled" id="content-use-growl-client"> <!-- show based on notifiers.growl.enabled -->

                                    <config-toggle-slider v-model="notifiers.growl.notifyOnSnatch" label="Notify on snatch" id="growl_notify_onsnatch" :explanations="['send a notification when a download starts?']" @change="save()" ></config-toggle-slider>
                                    <config-toggle-slider v-model="notifiers.growl.notifyOnDownload" label="Notify on download" id="growl_notify_ondownload" :explanations="['send a notification when a download finishes?']" @change="save()" ></config-toggle-slider>
                                    <config-toggle-slider v-model="notifiers.growl.notifyOnSubtitleDownload" label="Notify on subtitle download" id="growl_notify_onsubtitledownload" :explanations="['send a notification when subtitles are downloaded?']" @change="save()" ></config-toggle-slider>
                                    <config-textbox v-model="notifiers.growl.host" label="Growl IP:Port" id="growl_host" :explanations="['host running Growl (eg. 192.168.1.100:23053)']" @change="save()" ></config-textbox>
                                    <config-textbox v-model="notifiers.growl.password" label="Password" id="growl_password" :explanations="['may leave blank if Medusa is on the same host.', 'otherwise Growl requires a password to be used.']" @change="save()" ></config-textbox>

                                    <div class="testNotification" id="testGrowl-result">Click below to register and test Growl, this is required for Growl notifications to work.</div>
                                    <input  class="btn-medusa" type="button" value="Register Growl" id="testGrowl" @click="testGrowl"/>
                                    <input type="submit" class="config_submitter btn-medusa" value="Save Changes"/>
                                </div>
                            </fieldset>
                        </div>
                    </div>

                    <div class="row component-group">
                        <div class="component-group-desc col-xs-12 col-md-2">
                            <span class="icon-notifiers-prowl" title="Prowl"></span>
                            <h3><app-link href="http://www.prowlapp.com/">Prowl</app-link></h3>
                            <p>A Growl client for iOS.</p>
                        </div>
                        <div class="col-xs-12 col-md-10">
                            <fieldset class="component-group-list">
                                <!-- All form components here for prowl client -->
                                <config-toggle-slider v-model="notifiers.prowl.enabled" label="Enable" id="use_prowl" :explanations="['Send Prowl notifications?']" @change="save()" ></config-toggle-slider>
                                <div v-show="notifiers.prowl.enabled" id="content-use-prowl"> <!-- show based on notifiers.plex.server.enabled -->
                                    <config-toggle-slider v-model="notifiers.prowl.notifyOnSnatch" label="Notify on snatch" id="prowl_notify_onsnatch" :explanations="['send a notification when a download starts?']" @change="save()" ></config-toggle-slider>
                                    <config-toggle-slider v-model="notifiers.prowl.notifyOnDownload" label="Notify on download" id="prowl_notify_ondownload" :explanations="['send a notification when a download finishes?']" @change="save()" ></config-toggle-slider>
                                    <config-toggle-slider v-model="notifiers.prowl.notifyOnSubtitleDownload" label="Notify on subtitle download" id="prowl_notify_onsubtitledownload" :explanations="['send a notification when subtitles are downloaded?']" @change="save()" ></config-toggle-slider>
                                    <config-textbox v-model="notifiers.prowl.messageTitle" label="Prowl Message Title" id="prowl_message_title" @change="save()" ></config-textbox>

                                    <config-template label-for="prowl_api" label="Api">
                                        <select-list name="prowl_api" id="prowl_api" csv-enabled :list-items="notifiers.prowl.api" @change="onChangeProwlApi"></select-list>
                                        <span>Prowl API(s) listed here, will receive notifications for <b>all</b> shows.
                                            Your Prowl API key is available at:
                                            <app-link href="https://www.prowlapp.com/api_settings.php">
                                            https://www.prowlapp.com/api_settings.php</app-link><br>
                                            (This field may be blank except when testing.)
                                        </span>
                                    </config-template>

                                    <config-template label-for="prowl_show_notification_list" label="Show notification list">
                                        <show-selector select-class="form-control input-sm max-input350" placeholder="-- Select a Show --" @change="prowlUpdateApiKeys($event)"></show-selector>
                                    </config-template>

                                    <div class="form-group">
                                        <div class="row">
                                            <!-- bs3 and 4 -->
                                            <div class="offset-sm-2 col-sm-offset-2 col-sm-10 content">
                                                <select-list name="prowl-show-list" id="prowl-show-list" :list-items="prowlSelectedShowApiKeys" @change="savePerShowNotifyList('prowl')"></select-list>
                                                Configure per-show notifications here by entering Prowl API key(s), after selecting a show in the drop-down box.
                                                Be sure to activate the \'Save for this show\' button below after each entry.
                                            </div>
                                        </div>
                                    </div>

                                    <config-template label-for="prowl-show-save-button" label="">
                                        <input id="prowl-show-save-button" class="btn-medusa" type="button" value="Save for this show" @click="savePerShowNotifyList('prowl')"/>
                                    </config-template>

                                    <config-template label-for="prowl_priority" label="Prowl priority">
                                        <select id="prowl_priority" name="prowl_priority" v-model="notifiers.prowl.priority" class="form-control input-sm">
                                            <option v-for="option in prowlPriorityOptions" v-bind:value="option.value">
                                                {{ option.text }}
                                            </option>
                                        </select>
                                        <span>priority of Prowl messages from Medusa.</span>
                                    </config-template>

                                    <div class="testNotification" id="testProwl-result">Click below to test.</div>
                                    <input class="btn-medusa" type="button" value="Test Prowl" id="testProwl" @click="testProwl"/>
                                    <input type="submit" class="config_submitter btn-medusa" value="Save Changes"/>
                                </div>
                            </fieldset>
                        </div>
                    </div>

                    <div class="row component-group">
                        <div class="component-group-desc col-xs-12 col-md-2">
                            <span class="icon-notifiers-libnotify" title="Libnotify"></span>
                            <h3><app-link href="http://library.gnome.org/devel/libnotify/">Libnotify</app-link></h3>
                            <p>The standard desktop notification API for Linux/*nix systems.  This notifier will only function if the pynotify module is installed (Ubuntu/Debian package <app-link href="apt:python-notify">python-notify</app-link>).</p>
                        </div>
                        <div class="col-xs-12 col-md-10">
                            <fieldset class="component-group-list">
                                <!-- All form components here for plex media client -->
                                <config-toggle-slider v-model="notifiers.libnotify.enabled" label="Enable" id="use_libnotify_client" :explanations="['Send Libnotify notifications?']" @change="save()" ></config-toggle-slider>
                                <div v-show="notifiers.libnotify.enabled" id="content-use-libnotify">

                                    <config-toggle-slider v-model="notifiers.libnotify.notifyOnSnatch" label="Notify on snatch" id="libnotify_notify_onsnatch" :explanations="['send a notification when a download starts?']" @change="save()" ></config-toggle-slider>
                                    <config-toggle-slider v-model="notifiers.libnotify.notifyOnDownload" label="Notify on download" id="libnotify_notify_ondownload" :explanations="['send a notification when a download finishes?']" @change="save()" ></config-toggle-slider>
                                    <config-toggle-slider v-model="notifiers.libnotify.notifyOnSubtitleDownload" label="Notify on subtitle download" id="libnotify_notify_onsubtitledownload" :explanations="['send a notification when subtitles are downloaded?']" @change="save()" ></config-toggle-slider>

                                    <div class="testNotification" id="testLibnotify-result">Click below to test.</div>
                                    <input  class="btn-medusa" type="button" value="Test Libnotify" id="testLibnotify" @click="testLibnotify"/>
                                    <input type="submit" class="config_submitter btn-medusa" value="Save Changes"/>
                                </div>
                            </fieldset>
                        </div>
                    </div>

                    <div class="row component-group">
                        <div class="component-group-desc col-xs-12 col-md-2">
                            <span class="icon-notifiers-pushover" title="Pushover"></span>
                            <h3><app-link href="https://pushover.net/">Pushover</app-link></h3>
                            <p>Pushover makes it easy to send real-time notifications to your Android and iOS devices.</p>
                        </div>
                        <div class="col-xs-12 col-md-10">
                            <fieldset class="component-group-list">
                                <!-- All form components here for pushover -->
                                <config-toggle-slider v-model="notifiers.pushover.enabled" label="Enable" id="use_pushover_client" :explanations="['Send Pushover notifications?']" @change="save()" ></config-toggle-slider>
                                <div v-show="notifiers.pushover.enabled" id="content-use-pushover">
                                    <config-toggle-slider v-model="notifiers.pushover.notifyOnSnatch" label="Notify on snatch" id="pushover_notify_onsnatch" :explanations="['send a notification when a download starts?']" @change="save()" ></config-toggle-slider>
                                    <config-toggle-slider v-model="notifiers.pushover.notifyOnDownload" label="Notify on download" id="pushover_notify_ondownload" :explanations="['send a notification when a download finishes?']" @change="save()" ></config-toggle-slider>
                                    <config-toggle-slider v-model="notifiers.pushover.notifyOnSubtitleDownload" label="Notify on subtitle download" id="pushover_notify_onsubtitledownload" :explanations="['send a notification when subtitles are downloaded?']" @change="save()" ></config-toggle-slider>

                                    <config-textbox v-model="notifiers.pushover.userKey" label="Pushover Key" id="pushover_userkey" :explanations="['user key of your Pushover account']" @change="save()" ></config-textbox>

                                    <config-textbox v-model="notifiers.pushover.apiKey" label="Pushover API key" id="pushover_apikey" @change="save()" >
                                        <span><app-link href="https://pushover.net/apps/build/"><b>Click here</b></app-link> to create a Pushover API key</span>
                                    </config-textbox>

                                    <config-template label-for="pushover_device" label="Pushover Devices">
                                        <select-list name="pushover_device" id="pushover_device" :list-items="notifiers.pushover.device" @change="notifiers.pushover.device = $event.map(x => x.value)"></select-list>
                                        <p>List of pushover devices you want to send notifications to</p>
                                    </config-template>

                                    <config-template label-for="pushover_spound" label="Pushover notification sound">
                                        <select id="pushover_sound" name="pushover_sound" v-model="notifiers.pushover.sound" class="form-control">
                                            <option v-for="option in pushoverSoundOptions" v-bind:value="option.value">
                                                {{ option.text }}
                                            </option>
                                        </select>
                                        <span>Choose notification sound to use</span>
                                    </config-template>

                                    <div class="testNotification" id="testPushover-result">Click below to test.</div>
                                    <input  class="btn-medusa" type="button" value="Test Pushover" id="testPushover" @click="testPushover"/>
                                    <input type="submit" class="config_submitter btn-medusa" value="Save Changes"/>
                                </div>
                            </fieldset>
                        </div>
                    </div>

                    <div class="row component-group">
                        <div class="component-group-desc col-xs-12 col-md-2">
                            <span class="icon-notifiers-boxcar2" title="Boxcar 2"></span>
                            <h3><app-link href="https://new.boxcar.io/">Boxcar 2</app-link></h3>
                            <p>Read your messages where and when you want them!</p>
                        </div>
                        <div class="col-xs-12 col-md-10">
                            <fieldset class="component-group-list">
                                <!-- All form components here for boxcar2 client -->
                                <config-toggle-slider v-model="notifiers.boxcar2.enabled" label="Enable" id="use_boxcar2" :explanations="['Send boxcar2 notifications?']" @change="save()" ></config-toggle-slider>
                                <div v-show="notifiers.boxcar2.enabled" id="content-use-boxcar2-client"> <!-- show based on notifiers.boxcar2.enabled -->

                                    <config-toggle-slider v-model="notifiers.boxcar2.notifyOnSnatch" label="Notify on snatch" id="boxcar2_notify_onsnatch" :explanations="['send a notification when a download starts?']" @change="save()" ></config-toggle-slider>
                                    <config-toggle-slider v-model="notifiers.boxcar2.notifyOnDownload" label="Notify on download" id="boxcar2_notify_ondownload" :explanations="['send a notification when a download finishes?']" @change="save()" ></config-toggle-slider>
                                    <config-toggle-slider v-model="notifiers.boxcar2.notifyOnSubtitleDownload" label="Notify on subtitle download" id="boxcar2_notify_onsubtitledownload" :explanations="['send a notification when subtitles are downloaded?']" @change="save()" ></config-toggle-slider>
                                    <config-textbox v-model="notifiers.boxcar2.accessToken" label="Boxcar2 Access token" id="boxcar2_accesstoken" :explanations="['access token for your Boxcar account.']" @change="save()" ></config-textbox>

                                    <div class="testNotification" id="testBoxcar2-result">Click below to test.</div>
                                    <input  class="btn-medusa" type="button" value="Test Boxcar" id="testBoxcar2" @click="testBoxcar2"/>
                                    <input type="submit" class="config_submitter btn-medusa" value="Save Changes"/>
                                </div>
                            </fieldset>
                        </div>
                    </div>

                    <div class="row component-group">
                        <div class="component-group-desc col-xs-12 col-md-2">
                            <span class="icon-notifiers-pushalot" title="Pushalot"></span>
                            <h3><app-link href="https://pushalot.com">Pushalot</app-link></h3>
                            <p>Pushalot is a platform for receiving custom push notifications to connected devices running Windows Phone or Windows 8.</p>
                        </div>
                        <div class="col-xs-12 col-md-10">
                            <fieldset class="component-group-list">
                                <!-- All form components here for pushalot client -->
                                <config-toggle-slider v-model="notifiers.pushalot.enabled" label="Enable" id="use_pushalot" :explanations="['Send Pushalot notifications?']" @change="save()" ></config-toggle-slider>
                                <div v-show="notifiers.pushalot.enabled" id="content-use-pushalot-client"> <!-- show based on notifiers.pushalot.enabled -->

                                    <config-toggle-slider v-model="notifiers.pushalot.notifyOnSnatch" label="Notify on snatch" id="pushalot_notify_onsnatch" :explanations="['send a notification when a download starts?']" @change="save()" ></config-toggle-slider>
                                    <config-toggle-slider v-model="notifiers.pushalot.notifyOnDownload" label="Notify on download" id="pushalot_notify_ondownload" :explanations="['send a notification when a download finishes?']" @change="save()" ></config-toggle-slider>
                                    <config-toggle-slider v-model="notifiers.pushalot.notifyOnSubtitleDownload" label="Notify on subtitle download" id="pushalot_notify_onsubtitledownload" :explanations="['send a notification when subtitles are downloaded?']" @change="save()" ></config-toggle-slider>
                                    <config-textbox v-model="notifiers.pushalot.authToken" label="Pushalot authorization token" id="pushalot_authorizationtoken" :explanations="['authorization token of your Pushalot account.']" @change="save()" ></config-textbox>

                                    <div class="testNotification" id="testPushalot-result">Click below to test.</div>
                                    <input type="button" class="btn-medusa" value="Test Pushalot" id="testPushalot" @click="testPushalot"/>
                                    <input type="submit" class="btn-medusa config_submitter" value="Save Changes"/>
                                </div>
                            </fieldset>
                        </div>
                    </div>

                    <div class="row component-group">
                        <div class="component-group-desc col-xs-12 col-md-2">
                            <span class="icon-notifiers-pushbullet" title="Pushbullet"></span>
                            <h3><app-link href="https://www.pushbullet.com">Pushbullet</app-link></h3>
                            <p>Pushbullet is a platform for receiving custom push notifications to connected devices running Android and desktop Chrome browsers.</p>
                        </div>
                        <div class="col-xs-12 col-md-10">
                            <fieldset class="component-group-list">
                                <!-- All form components here for pushbullet client -->
                                <config-toggle-slider v-model="notifiers.pushbullet.enabled" label="Enable" id="use_pushbullet" :explanations="['Send pushbullet notifications?']" @change="save()" ></config-toggle-slider>
                                <div v-show="notifiers.pushbullet.enabled" id="content-use-pushbullet-client"> <!-- show based on notifiers.pushbullet.enabled -->

                                    <config-toggle-slider v-model="notifiers.pushbullet.notifyOnSnatch" label="Notify on snatch" id="pushbullet_notify_onsnatch" :explanations="['send a notification when a download starts?']" @change="save()" ></config-toggle-slider>
                                    <config-toggle-slider v-model="notifiers.pushbullet.notifyOnDownload" label="Notify on download" id="pushbullet_notify_ondownload" :explanations="['send a notification when a download finishes?']" @change="save()" ></config-toggle-slider>
                                    <config-toggle-slider v-model="notifiers.pushbullet.notifyOnSubtitleDownload" label="Notify on subtitle download" id="pushbullet_notify_onsubtitledownload" :explanations="['send a notification when subtitles are downloaded?']" @change="save()" ></config-toggle-slider>
                                    <config-textbox v-model="notifiers.pushbullet.api" label="Pushbullet API key" id="pushbullet_api" :explanations="['API key of your Pushbullet account.']" @change="save()" ></config-textbox>

                                    <config-template label-for="pushbullet_device_list" label="Pushbullet devices">
                                        <input type="button" class="btn-medusa btn-inline" value="Update device list" id="get-pushbullet-devices" @click="getPushbulletDeviceOptions" />
                                        <select id="pushbullet_device_list" name="pushbullet_device_list" v-model="notifiers.pushbullet.device" class="form-control">
                                            <option v-for="option in pushbulletDeviceOptions" v-bind:value="option.value" @change="pushbulletTestInfo = 'Don\'t forget to save your new pushbullet settings.'">
                                                {{ option.text }}
                                            </option>
                                        </select>
                                        <span>select device you wish to push to.</span>
                                    </config-template>

                                    <div class="testNotification" id="testPushbullet-resultsfsf">{{pushbulletTestInfo}}</div>
                                    <input type="button" class="btn-medusa" value="Test Pushbullet" id="testPushbullet" @click="testPushbulletApi" />
                                    <input type="submit" class="btn-medusa config_submitter" value="Save Changes"/>
                                </div>
                            </fieldset>
                        </div>
                    </div>

                    <div class="row component-group">
                        <div class="component-group-desc col-xs-12 col-md-2">
                                <span class="icon-notifiers-freemobile" title="Free Mobile"></span>
                                <h3><app-link href="http://mobile.free.fr/">Free Mobile</app-link></h3>
                                <p>Free Mobile is a famous French cellular network provider.<br> It provides to their customer a free SMS API.</p>
                        </div>
                        <div class="col-xs-12 col-md-10">
                            <fieldset class="component-group-list">
                                <!-- All form components here for freemobile client -->
                                <config-toggle-slider v-model="notifiers.freemobile.enabled" label="Enable" id="use_freemobile" :explanations="['Send SMS notifications?']" @change="save()" ></config-toggle-slider>
                                <div v-show="notifiers.freemobile.enabled" id="content-use-freemobile-client"> <!-- show based on notifiers.freemobile.enabled -->

                                    <config-toggle-slider v-model="notifiers.freemobile.notifyOnSnatch" label="Notify on snatch" id="freemobile_notify_onsnatch" :explanations="['send an SMS when a download starts?']" @change="save()" ></config-toggle-slider>
                                    <config-toggle-slider v-model="notifiers.freemobile.notifyOnDownload" label="Notify on download" id="freemobile_notify_ondownload" :explanations="['send an SMS when a download finishes?']" @change="save()" ></config-toggle-slider>
                                    <config-toggle-slider v-model="notifiers.freemobile.notifyOnSubtitleDownload" label="Notify on subtitle download" id="freemobile_notify_onsubtitledownload" :explanations="['send an SMS when subtitles are downloaded?']" @change="save()" ></config-toggle-slider>
                                    <config-textbox v-model="notifiers.freemobile.id" label="Free Mobile customer ID" id="freemobile_id" :explanations="['It\'s your Free Mobile customer ID (8 digits)']" @change="save()" ></config-textbox>
                                    <config-textbox v-model="notifiers.freemobile.api" label="Free Mobile API Key" id="freemobile_apikey" :explanations="['Find your API Key in your customer portal.']" @change="save()" ></config-textbox>

                                    <div class="testNotification" id="testFreeMobile-result">Click below to test your settings.</div>
                                    <input  class="btn-medusa" type="button" value="Test SMS" id="testFreeMobile" @click="testFreeMobile"/>
                                    <input type="submit" class="config_submitter btn-medusa" value="Save Changes"/>
                                </div>
                            </fieldset>
                        </div>
                    </div>

                    <div class="row component-group">
                        <div class="component-group-desc col-xs-12 col-md-2">
                            <span class="icon-notifiers-telegram" title="Telegram"></span>
                            <h3><app-link href="https://telegram.org/">Telegram</app-link></h3>
                            <p>Telegram is a cloud-based instant messaging service.</p>
                        </div>
                        <div class="col-xs-12 col-md-10">
                            <fieldset class="component-group-list">
                                <!-- All form components here for telegram client -->
                                <config-toggle-slider v-model="notifiers.telegram.enabled" label="Enable" id="use_telegram" :explanations="['Send Telegram notifications?']" @change="save()" ></config-toggle-slider>
                                <div v-show="notifiers.telegram.enabled" id="content-use-telegram-client"> <!-- show based on notifiers.telegram.enabled -->

                                    <config-toggle-slider v-model="notifiers.telegram.notifyOnSnatch" label="Notify on snatch" id="telegram_notify_onsnatch" :explanations="['Send a message when a download starts??']" @change="save()" ></config-toggle-slider>
                                    <config-toggle-slider v-model="notifiers.telegram.notifyOnDownload" label="Notify on download" id="telegram_notify_ondownload" :explanations="['send a message when a download finishes?']" @change="save()" ></config-toggle-slider>
                                    <config-toggle-slider v-model="notifiers.telegram.notifyOnSubtitleDownload" label="Notify on subtitle download" id="telegram_notify_onsubtitledownload" :explanations="['send a message when subtitles are downloaded?']" @change="save()" ></config-toggle-slider>
                                    <config-textbox v-model="notifiers.telegram.id" label="User/group ID" id="telegram_id" :explanations="['Contact @myidbot on Telegram to get an ID']" @change="save()" ></config-textbox>
                                    <config-textbox v-model="notifiers.telegram.api" label="Bot API token" id="telegram_apikey" :explanations="['Contact @BotFather on Telegram to set up one']" @change="save()" ></config-textbox>

                                    <div class="testNotification" id="testTelegram-result">Click below to test your settings.</div>
                                    <input  class="btn-medusa" type="button" value="Test Telegram" id="testTelegram" @click="testTelegram"/>
                                    <input type="submit" class="config_submitter btn-medusa" value="Save Changes"/>
                                </div>
                            </fieldset>
                        </div>
                    </div>

                </div><!-- #devices //-->

                <div id="social">
                    <div class="row component-group">
                        <div class="component-group-desc col-xs-12 col-md-2">
                            <span class="icon-notifiers-twitter" title="Twitter"></span>
                            <h3><app-link href="https://www.twitter.com">Twitter</app-link></h3>
                            <p>A social networking and microblogging service, enabling its users to send and read other users' messages called tweets.</p>
                        </div>
                        <div class="col-xs-12 col-md-10">
                            <fieldset class="component-group-list">
                                <!-- All form components here for twitter client -->
                                <config-toggle-slider v-model="notifiers.twitter.enabled" label="Enable" id="use_twitter" :explanations="['Should Medusa post tweets on Twitter?', 'Note: you may want to use a secondary account.']" @change="save()" ></config-toggle-slider>
                                <div v-show="notifiers.twitter.enabled" id="content-use-twitter"> <!-- show based on notifiers.twitter.enabled -->

                                    <config-toggle-slider v-model="notifiers.twitter.notifyOnSnatch" label="Notify on snatch" id="twitter_notify_onsnatch" :explanations="['send an SMS when a download starts?']" @change="save()" ></config-toggle-slider>
                                    <config-toggle-slider v-model="notifiers.twitter.notifyOnDownload" label="Notify on download" id="twitter_notify_ondownload" :explanations="['send an SMS when a download finishes?']" @change="save()" ></config-toggle-slider>
                                    <config-toggle-slider v-model="notifiers.twitter.notifyOnSubtitleDownload" label="Notify on subtitle download" id="twitter_notify_onsubtitledownload" :explanations="['send an SMS when subtitles are downloaded?']" @change="save()" ></config-toggle-slider>
                                    <config-toggle-slider v-model="notifiers.twitter.directMessage" label="Send direct message" id="twitter_usedm" :explanations="['send a notification via Direct Message, not via status update']" @change="save()" ></config-toggle-slider>


                                    <config-textbox v-model="notifiers.twitter.dmto" label="Send DM to" id="twitter_dmto" :explanations="['Twitter account to send Direct Messages to (must follow you)']" @change="save()" ></config-textbox>

                                    <config-template label-for="twitterStep1" label="Step 1">
                                        <span style="font-size: 11px;">Click the "Request Authorization" button. </br>This will open a new page containing an auth key. </br>Note: if nothing happens check your popup blocker.</span>
                                        <p><input class="btn-medusa" type="button" value="Request Authorization" id="twitter-step-1" @click="twitterStep1($event)"/></p>
                                    </config-template>

                                    <config-template label-for="twitterStep2" label="Step 2">
                                        <input type="text" id="twitter_key" v-model="twitterKey" class="form-control input-sm max-input350" style="display: inline" placeholder="Enter the key Twitter gave you, and click 'Verify Key'"/>
                                        <input class="btn-medusa btn-inline" type="button" value="Verify Key" id="twitter-step-2" @click="twitterStep2($event)"/>
                                    </config-template>

                                    <div class="testNotification" id="testTwitter-result" v-html="twitterTestInfo"></div>
                                    <input  class="btn-medusa" type="button" value="Test Twitter" id="testTwitter" @click="twitterTest" />
                                    <input type="submit" class="config_submitter btn-medusa" value="Save Changes"/>
                                </div>
                            </fieldset>
                        </div>
                    </div>

                    <div class="row component-group">
                        <div class="component-group-desc col-xs-12 col-md-2">
                            <span class="icon-notifiers-trakt" title="Trakt"></span>
                            <h3><app-link href="https://trakt.tv/">Trakt</app-link></h3>
                            <p>trakt helps keep a record of what TV shows and movies you are watching. Based on your favorites, trakt recommends additional shows and movies you'll enjoy!</p>
                        </div>
                        <div class="col-xs-12 col-md-10">
                            <fieldset class="component-group-list">
                                <!-- All form components here for trakt -->
                                <config-toggle-slider v-model="notifiers.trakt.enabled" label="Enable" id="use_trakt" :explanations="['Send Trakt.tv notifications?']" @change="save()" ></config-toggle-slider>
                                <div v-show="notifiers.trakt.enabled" id="content-use-trakt-client"> <!-- show based on notifiers.trakt.enabled -->

                                    <config-textbox v-model="notifiers.trakt.username" label="Username" id="trakt_username" :explanations="['username of your Trakt account.']" @change="save()" ></config-textbox>

                                    <config-template label-for="twitterStep2" label="Trakt PIN">
                                        <input type="text" name="trakt_pin" id="trakt_pin" value="" style="display: inline" class="form-control input-sm max-input250" :disabled="notifiers.trakt.accessToken"/>
                                        <input type="button" class="btn-medusa" :value="traktNewTokenMessage" id="TraktGetPin" @click="TraktGetPin"/>
                                        <input type="button" class="btn-medusa hide" value="Authorize Medusa" id="authTrakt" @click="authTrakt"/>
                                        <p>PIN code to authorize Medusa to access Trakt on your behalf.</p>
                                    </config-template>

                                    <config-textbox-number v-model="notifiers.trakt.timeout" label="API Timeout" id="trakt_timeout" :explanations="['Seconds to wait for Trakt API to respond. (Use 0 to wait forever)']"></config-textbox-number>

                                    <config-template label-for="twitterStep2" label="Trakt PIN">
                                        <select id="trakt_default_indexer" name="trakt_default_indexer" v-model="notifiers.trakt.defaultIndexer" class="form-control">
                                            <option v-for="option in traktIndexersOptions" v-bind:value="option.value">
                                                {{ option.text }}
                                            </option>
                                        </select>
                                    </config-template id="trakt_default_indexer" label="Default Indexer">

                                    <config-toggle-slider v-model="notifiers.trakt.sync" label="Sync libraries" id="trakt_sync" :explanations="
                                    ['Sync your Medusa show library with your Trakt collection.',
                                    'Note: Don\'t enable this setting if you use the Trakt addon for Kodi or any other script that syncs your library.',
                                    'Kodi detects that the episode was deleted and removes from collection which causes Medusa to re-add it. This causes a loop between Medusa and Kodi adding and deleting the episode.']"
                                        @change="save()" ></config-toggle-slider>
                                    <div v-show="notifiers.trakt.sync" id="content-use-trakt-client">
                                            <config-toggle-slider v-model="notifiers.trakt.removeWatchlist" label="Remove Episodes From Collection" id="trakt_remove_watchlist" :explanations="['Remove an Episode from your Trakt Collection if it is not in your Medusa Library.',
                                                'Note:Don\'t enable this setting if you use the Trakt addon for Kodi or any other script that syncs your library.']" @change="save()" ></config-toggle-slider>
                                    </div>

                                    <config-toggle-slider v-model="notifiers.trakt.syncWatchlist" label="Sync watchlist" id="trakt_sync_watchlist" :explanations="
                                    ['Sync your Medusa library with your Trakt Watchlist (either Show and Episode).',
                                    'Episode will be added on watch list when wanted or snatched and will be removed when downloaded',
                                    'Note: By design, Trakt automatically removes episodes and/or shows from watchlist as soon you have watched them.']"
                                        @change="save()" ></config-toggle-slider>
                                    <div v-show="notifiers.trakt.syncWatchlist" id="content-use-trakt-client">
                                        <config-template label-for="trakt_default_indexer" label="Watchlist add method">
                                            <select id="trakt_method_add" name="trakt_method_add" v-model="notifiers.trakt.methodAdd" class="form-control">
                                                <option v-for="option in traktMethodOptions" v-bind:value="option.value">
                                                    {{ option.text }}
                                                </option>
                                            </select>
                                            <p>method in which to download episodes for new shows.</p>
                                        </config-template>

                                        <config-toggle-slider v-model="notifiers.trakt.removeWatchlist" label="Remove episode" id="trakt_remove_watchlist" :explanations="['remove an episode from your watchlist after it\'s downloaded.']" @change="save()" ></config-toggle-slider>
                                        <config-toggle-slider v-model="notifiers.trakt.removeSerieslist" label="Remove series" id="trakt_remove_serieslist" :explanations="['remove the whole series from your watchlist after any download.']" @change="save()" ></config-toggle-slider>
                                        <config-toggle-slider v-model="notifiers.trakt.removeShowFromApplication" label="Remove watched show" id="trakt_remove_show_from_application" :explanations="['remove the show from Medusa if it\'s ended and completely watched']" @change="save()" ></config-toggle-slider>
                                        <config-toggle-slider v-model="notifiers.trakt.startPaused" label="Start paused" id="trakt_start_paused" :explanations="['shows grabbed from your trakt watchlist start paused.']" @change="save()" ></config-toggle-slider>

                                    </div>
                                    <config-textbox v-model="notifiers.trakt.blacklistName" label="Trakt blackList name" id="trakt_blacklist_name" :explanations="['Name(slug) of List on Trakt for blacklisting show on \'Add Trending Show\' & \'Add Recommended Shows\' pages']" @change="save()" ></config-textbox>

                                    <div class="testNotification" id="testTrakt-result">Click below to test.</div>
                                    <input type="button" class="btn-medusa" value="Test Trakt" id="testTrakt" @click="testTrakt"/>
                                    <input type="button" class="btn-medusa" value="Force Sync" id="forceSync" @click="traktForceSync"/>
                                    <input type="hidden" id="trakt_pin_url" :value="notifiers.trakt.pinUrl">
                                    <input type="submit" class="btn-medusa config_submitter" value="Save Changes"/>
                                </div>
                            </fieldset>
                        </div>
                    </div>

                    <div class="row component-group">
                        <div class="component-group-desc col-xs-12 col-md-2">
                            <span class="icon-notifiers-email" title="Email"></span>
                            <h3><app-link href="https://en.wikipedia.org/wiki/Comparison_of_webmail_providers">Email</app-link></h3>
                            <p>Allows configuration of email notifications on a per show basis.</p>
                        </div>
                        <div class="col-xs-12 col-md-10">
                            <fieldset class="component-group-list">
                                <!-- All form components here for the email client -->
                                <config-toggle-slider v-model="notifiers.email.enabled" label="Enable" id="use_telegram" :explanations="['Send email notifications?']" @change="save()" ></config-toggle-slider>
                                <div v-show="notifiers.email.enabled" id="content-use-email">

                                    <config-toggle-slider v-model="notifiers.email.notifyOnSnatch" label="Notify on snatch" id="telegram_notify_onsnatch" :explanations="['Send a message when a download starts??']" @change="save()" ></config-toggle-slider>
                                    <config-toggle-slider v-model="notifiers.email.notifyOnDownload" label="Notify on download" id="telegram_notify_ondownload" :explanations="['send a message when a download finishes?']" @change="save()" ></config-toggle-slider>
                                    <config-toggle-slider v-model="notifiers.email.notifyOnSubtitleDownload" label="Notify on subtitle download" id="telegram_notify_onsubtitledownload" :explanations="['send a message when subtitles are downloaded?']" @change="save()" ></config-toggle-slider>
                                    <config-textbox v-model="notifiers.email.host" label="SMTP host" id="email_host" :explanations="['hostname of your SMTP email server.']" @change="save()" ></config-textbox>
                                    <config-textbox-number :min="1" :step="1" v-model="notifiers.email.port" label="SMTP port" id="email_port" :explanations="['port number used to connect to your SMTP host.']" @change="save()" ></config-textbox-number>
                                    <config-textbox v-model="notifiers.email.from" label="SMTP from" id="email_from" :explanations="['sender email address, some hosts require a real address.']" @change="save()" ></config-textbox>
                                    <config-toggle-slider v-model="notifiers.email.tls" label="Use TLS" id="email_tls" :explanations="['check to use TLS encryption.']" @change="save()" ></config-toggle-slider>
                                    <config-textbox v-model="notifiers.email.username" label="SMTP username" id="email_username" :explanations="['(optional) your SMTP server username.']" @change="save()" ></config-textbox>
                                    <config-textbox v-model="notifiers.email.password" label="SMTP password" id="email_password" :explanations="['(optional) your SMTP server password.']" @change="save()" ></config-textbox>

                                    <config-template label-for="email_list" label="Global email list">
                                        <select-list name="email_list" id="email_list" :list-items="notifiers.email.addressList" @change="emailUpdateAddressList"></select-list>
                                        Email addresses listed here, will receive notifications for <b>all</b> shows.<br>
                                        (This field may be blank except when testing.)
                                    </config-template>

                                    <config-textbox v-model="notifiers.email.subject" label="Email Subject" id="email_subject" :explanations="
                                    ['Use a custom subject for some privacy protection?<br>',
                                        '(Leave blank for the default Medusa subject)']" @change="save()" >
                                    </config-textbox>

                                    <config-template label-for="email_show" label="Show notification list">
                                        <show-selector select-class="form-control input-sm max-input350" placeholder="-- Select a Show --" @change="emailUpdateShowEmail($event)"></show-selector>
                                    </config-template>

                                    <div class="form-group">
                                        <div class="row">
                                            <!-- bs3 and 4 -->
                                            <div class="offset-sm-2 col-sm-offset-2 col-sm-10 content">
                                                <select-list name="email_list" id="email_list" :list-items="emailSelectedShowAdresses" @change="savePerShowNotifyList('email')" @update="emailSelectedShowAdresses = $event"></select-list>
                                                Email addresses listed here, will receive notifications for <b>all</b> shows.<br>
                                                (This field may be blank except when testing.)
                                            </div>
                                        </div>
                                    </div>

                                    <div class="testNotification" id="testEmail-result">Click below to test.</div><!-- #testEmail-result //-->
                                    <input class="btn-medusa" type="button" value="Test Email" id="testEmail" @click="testEmail"/>
                                    <input class="btn-medusa" type="submit" class="config_submitter" value="Save Changes"/>
                                </div>
                            </fieldset>
                        </div>
                    </div>

                    <div class="row component-group">
                        <div class="component-group-desc col-xs-12 col-md-2">
                            <span class="icon-notifiers-slack" title="Slack"></span>
                            <h3><app-link href="https://slack.com">Slack</app-link></h3>
                            <p>Slack is a messaging app for teams.</p>
                        </div>
                        <div class="col-xs-12 col-md-10">
                            <fieldset class="component-group-list">
                                <!-- All form components here for slack client -->
                                <config-toggle-slider v-model="notifiers.slack.enabled" label="Enable" id="use_slack_client" :explanations="['Send slack Home Theater notifications?']" @change="save()" ></config-toggle-slider>
                                <div v-show="notifiers.slack.enabled" id="content-use-slack-client"> <!-- show based on notifiers.slack.enabled -->

                                    <config-toggle-slider v-model="notifiers.slack.notifyOnSnatch" label="Notify on snatch" id="slack_notify_onsnatch" :explanations="['send a notification when a download starts?']" @change="save()" ></config-toggle-slider>
                                    <config-toggle-slider v-model="notifiers.slack.notifyOnDownload" label="Notify on download" id="slack_notify_ondownload" :explanations="['send a notification when a download finishes?']" @change="save()" ></config-toggle-slider>
                                    <config-toggle-slider v-model="notifiers.slack.notifyOnSubtitleDownload" label="Notify on subtitle download" id="slack_notify_onsubtitledownload" :explanations="['send a notification when subtitles are downloaded?']" @change="save()" ></config-toggle-slider>
                                    <config-textbox v-model="notifiers.slack.webhook" label="Slack Incoming Webhook" id="slack_webhook" :explanations="['Create an incoming webhook, to communicate with your slack channel.']" @change="save()" >
                                        <app-link href="https://my.slack.com/services/new/incoming-webhook">https://my.slack.com/services/new/incoming-webhook/</app-link></span>
                                    </config-textbox>

                                    <div class="testNotification" id="testSlack-result">Click below to test your settings.</div>
                                    <input  class="btn-medusa" type="button" value="Test Slack" id="testSlack" @click="testSlack"/>
                                    <input type="submit" class="config_submitter btn-medusa" value="Save Changes"/>
                                </div>
                            </fieldset>
                        </div>
                    </div>

                </div><!-- #social //-->
                <br><input type="submit" class="config_submitter btn-medusa" value="Save Changes"/><br>
            </div><!-- #config-components //-->
        </form><!-- #configForm //-->
    </div><!-- #config-content //-->
</div><!-- #config //-->
<div class="clearfix"></div>
</%block>

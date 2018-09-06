<%inherit file="/layouts/main.mako"/>
<%!
    import json

    from medusa import app
    from medusa import subtitles
%>
<%block name="scripts">
<script>
window.app = {};
window.app = new Vue({
    store,
    router,
    el: '#vue-wrap',
    data() {
        <%
            subtitle_code_filter = [{'id': code, 'name': subtitles.name_from_code(code)}
                                    for code in subtitles.subtitle_code_filter()]
            wanted_languages = [{'id': code, 'name': subtitles.name_from_code(code)}
                                for code in subtitles.wanted_languages()]
        %>
        return {
            services: ${json.dumps(subtitles.sorted_service_list())},
            subtitleCodeFilter: ${json.dumps(subtitle_code_filter)},
            wantedLanguages: ${json.dumps(wanted_languages)},
        };
    },
    computed: {
        enabledServices() {
            const { services } = this;
            return services.map(service => service.name + ':' + (service.enabled ? '1' : '0')).join(' ');
        }
    },
    methods: {
        serviceOrderUpdated(event, ui) {
            event.preventDefault(); // Stop sortable from changing the DOM, let Vue do it.
            const newOrder = $('#service_order_list').sortable('toArray');
            this.services = this.services.slice().sort((a, b) => {
                return newOrder.indexOf(a.name) - newOrder.indexOf(b.name);
            });
        }
    },
    beforeMount() {
        $('#config-components').tabs();
    },
    mounted() {
        const { subtitleCodeFilter, wantedLanguages, serviceOrderUpdated } = this;
        $("#subtitles_languages").tokenInput(subtitleCodeFilter, {
            method: 'POST',
            hintText: 'Write to search a language and select it',
            preventDuplicates: true,
            prePopulate: wantedLanguages,
            resultsFormatter: item => "<li><img src='images/subtitles/flags/" + item.id + ".png' onError='this.onerror=null;this.src=\"images/flags/unknown.png\";' style='vertical-align: middle !important;' /> " + item.name + "</li>",
            tokenFormatter: item => "<li><img src='images/subtitles/flags/" + item.id + ".png' onError='this.onerror=null;this.src=\"images/flags/unknown.png\";' style='vertical-align: middle !important;' /> " + item.name + "</li>"
        });
        $('#subtitles_dir').fileBrowser({ title: 'Select Subtitles Download Directory' });
        $('#service_order_list').sortable({ update: serviceOrderUpdated }).disableSelection();
    },
    filters: {
        capitalize: str => str.replace(/\b\w/g, str => str.toUpperCase())
    }
});
</script>
</%block>
<%block name="content">
<h1 class="header">{{ $route.meta.header }}</h1>
<div id="config">
    <div id="config-content">
        <form id="configForm" action="config/subtitles/saveSubtitles" method="post">
            <div id="config-components">
                <ul>
                    <li><app-link href="#subtitles-search">Subtitles Search</app-link></li>
                    <li><app-link href="#subtitles-plugin">Subtitles Plugin</app-link></li>
                    <li><app-link href="#plugin-settings">Plugin Settings</app-link></li>
                </ul>
                <div id="subtitles-search" class="component-group">
                    <div class="component-group-desc-legacy">
                        <h3>Subtitles Search</h3>
                        <p>Settings that dictate how Medusa handles subtitles search results.</p>
                    </div>
                    <fieldset class="component-group-list">
                        <div class="field-pair">
                            <label for="use_subtitles" class="clearfix">
                                <span class="component-title">Search Subtitles</span>
                                <span class="component-desc">
                                    <input type="checkbox" class="enabler" ${' checked="checked"' if app.USE_SUBTITLES else ''} id="use_subtitles" name="use_subtitles">
                                    <p>Search subtitles for episodes with DOWNLOADED status</p>
                                </span>
                            </label>
                        </div>
                        <div id="content_use_subtitles">
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">Subtitle Languages</span>
                                    <span class="component-desc"><input type="text" id="subtitles_languages" name="subtitles_languages"/></span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label class="clearfix" for="subtitles_stop_at_first">
                                    <span class="component-title">Download only one language (any)</span>
                                    <span class="component-desc">
                                        <input type="checkbox" name="subtitles_stop_at_first" id="subtitles_stop_at_first" ${('', 'checked="checked"')[bool(app.SUBTITLES_STOP_AT_FIRST)]}/>
                                        <p>Stop download subtitles after first download</p>
                                    </span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label class="clearfix" for="subtitles_erase_cache">
                                    <span class="component-title">Erase subtitles cache on next boot</span>
                                    <span class="component-desc">
                                        <input type="checkbox" name="subtitles_erase_cache" id="subtitles_erase_cache" ${('', 'checked="checked"')[bool(app.SUBTITLES_ERASE_CACHE)]}/>
                                        <p>Erases all subtitles cache files. May help fix some subtitles not being found</p>
                                    </span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">Subtitle Directory</span>
                                    <input type="text" value="${app.SUBTITLES_DIR}" id="subtitles_dir" name="subtitles_dir" class="form-control input-sm input350">
                                </label>
                                <label>
                                    <span class="component-title">&nbsp;</span>
                                    <span class="component-desc">The directory where Medusa should store your <i>Subtitles</i> files.</span>
                                </label>
                                <label>
                                    <span class="component-title">&nbsp;</span>
                                    <span class="component-desc"><b>NOTE:</b> Leave empty if you want store subtitle in episode path.</span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">Subtitle Find Frequency</span>
                                    <input type="number" name="subtitles_finder_frequency" value="${app.SUBTITLES_FINDER_FREQUENCY}" hours="1" min="1" step="1" class="form-control input-sm input75" />
                                    <span class="component-desc">time in hours between scans (default: 1)</span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label for="subtitles_perfect_match" class="clearfix">
                                    <span class="component-title">Perfect matches</span>
                                    <span class="component-desc">
                                        <input type="checkbox" class="enabler" ${' checked="checked"' if app.SUBTITLES_PERFECT_MATCH else ''} id="subtitles_perfect_match" name="subtitles_perfect_match">
                                        <p>Only download subtitles that match: release group, video codec, audio codec and resolution</p>
                                        <p>If disabled you may get out of sync subtitles</p>
                                    </span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label class="clearfix" for="subtitles_history">
                                    <span class="component-title">Subtitles History</span>
                                    <span class="component-desc">
                                        <input type="checkbox" name="subtitles_history" id="subtitles_history" ${'checked="checked"' if app.SUBTITLES_HISTORY else ''}/>
                                        <p>Log downloaded Subtitle on History page?</p>
                                    </span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label class="clearfix" for="subtitles_multi">
                                    <span class="component-title">Subtitles Multi-Language</span>
                                    <span class="component-desc">
                                        <input type="checkbox" name="subtitles_multi" id="subtitles_multi" ${'checked="checked"' if app.SUBTITLES_MULTI else ''}/>
                                        <p>Append language codes to subtitle filenames?</p>
                                    </span>
                                </label>
                                <label>
                                    <span class="component-title">&nbsp;</span>
                                    <span class="component-desc"><b>NOTE:</b> This option is required if you use multiple subtitle languages.</span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label class="clearfix" for="subtitles_keep_only_wanted">
                                    <span class="component-title">Delete unwanted subtitles</span>
                                    <span class="component-desc">
                                        <input type="checkbox" name="subtitles_keep_only_wanted" id="subtitles_keep_only_wanted" ${'checked="checked"' if app.SUBTITLES_KEEP_ONLY_WANTED else ''}/>
                                        <p>Enable to delete unwanted subtitle languages bundled with release</p>
                                        <p>Avoid post-process releases with unwanted language subtitles when feature 'postpone if no subs' is enabled</p>
                                    </span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label class="clearfix" for="embedded_subtitles_all">
                                    <span class="component-title">Embedded Subtitles</span>
                                    <span class="component-desc">
                                        <input type="checkbox" name="embedded_subtitles_all" id="embedded_subtitles_all" ${'checked="checked"' if app.IGNORE_EMBEDDED_SUBS else ''}/>
                                        <p>Ignore subtitles embedded inside video file?</p>
                                        <p><b>Warning: </b>this will ignore <em>all</em> embedded subtitles for every video file!</p>
                                    </span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label class="clearfix" for="embedded_subtitles_unknown_lang">
                                    <span class="component-title">Unknown language</span>
                                    <span class="component-desc">
                                        <input type="checkbox" name="embedded_subtitles_unknown_lang" id="embedded_subtitles_unknown_lang" ${('', 'checked="checked"')[bool(app.ACCEPT_UNKNOWN_EMBEDDED_SUBS)]}/>
                                        <p>Consider unknown embedded subtitles as wanted language to avoid postpone post-process</p>
                                        <p>Only works with setting 'Postpone post processing' enabled</p>
                                    </span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label class="clearfix" for="subtitles_hearing_impaired">
                                    <span class="component-title">Hearing Impaired Subtitles</span>
                                    <span class="component-desc">
                                        <input type="checkbox" name="subtitles_hearing_impaired" id="subtitles_hearing_impaired" ${'checked="checked"' if app.SUBTITLES_HEARING_IMPAIRED else ''}/>
                                        <p>Download hearing impaired style subtitles?</p>
                                    </span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">Pre-Scripts</span>
                                    <input type="text" name="subtitles_pre_scripts" value="${'|'.join(app.SUBTITLES_PRE_SCRIPTS)}" class="form-control input-sm input350"/>
                                </label>
                                <label>
                                    <span class="component-desc">
                                        <p>Show's media filename is passed as argument for the pre-scripts. Pre-scripts are executed before trying to find subtitles from usual sources.</p>
                                    </span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label>
                                <span class="component-title">Extra Scripts</span>
                                   <input type="text" name="subtitles_extra_scripts" value="${'|'.join(app.SUBTITLES_EXTRA_SCRIPTS)}" class="form-control input-sm input350"/>
                                </label>
                                <label>
                                <span class="component-desc">
                                    <li>See the <app-link href="${app.SUBTITLES_URL}" class="wiki"><strong>Wiki</strong></app-link> for a script arguments description.</li>
                                    <li>Additional scripts separated by <b>|</b>.</li>
                                    <li>Scripts are called after each episode has searched and downloaded subtitles.</li>
                                    <li>For any scripted languages, include the interpreter executable before the script. See the following example:</li>
                                    <ul>
                                        <li>For Windows: <pre>C:\Python27\pythonw.exe C:\Script\test.py</pre></li>
                                        <li>For Linux: <pre>python /Script/test.py</pre></li>
                                    </ul>
                                </span>
                                </label>
                            </div>
                        </div>
                        <br><input type="submit" class="btn-medusa config_submitter" value="Save Changes" /><br>
                    </fieldset>
                </div><!-- /component-group1 //-->
                <div id="subtitles-plugin" class="component-group">
                    <div class="component-group-desc-legacy">
                        <h3>Subtitle Providers</h3>
                        <p>Check off and drag the plugins into the order you want them to be used.</p>
                        <p class="note">At least one plugin is required.</p>
                    </div>
                    <fieldset class="component-group-list" style="margin-left: 50px; margin-top:36px;">
                        <ul id="service_order_list">
                            <li v-for="service in services" class="ui-state-default" :id="service.name">
                                <input v-model="service.enabled" type="checkbox" :id="'enable_' + service.name" :checked="service.enabled"/>
                                <app-link :href="service.url" class="imgLink">
                                    <img :src="'images/subtitles/' + service.image" :alt="service.url" :title="service.url" width="16" height="16" style="vertical-align: middle;"/>
                                </app-link>
                                <span style="vertical-align: middle;">{{service.name | capitalize}}</span>
                                <span class="ui-icon ui-icon-arrowthick-2-n-s pull-right" style="vertical-align:middle;"></span>
                            </li>
                        </ul>
                        <input v-model="enabledServices" type="hidden" name="service_order" id="service_order"/>
                        <br><input type="submit" class="btn-medusa config_submitter" value="Save Changes" /><br>
                    </fieldset>
                </div><!-- /component-group2 //-->
                <div id="plugin-settings" class="component-group">
                    <div class="component-group-desc-legacy">
                        <h3>Provider Settings</h3>
                        <p>Set user and password for each provider.</p>
                    </div><!-- /component-group-desc-legacy //-->
                    <fieldset class="component-group-list" style="margin-left: 50px; margin-top:36px;">
                        <%
                            providerLoginDict = {
                                'addic7ed': {'user': app.ADDIC7ED_USER, 'pass': app.ADDIC7ED_PASS},
                                'itasa': {'user': app.ITASA_USER, 'pass': app.ITASA_PASS},
                                'legendastv': {'user': app.LEGENDASTV_USER, 'pass': app.LEGENDASTV_PASS},
                                'opensubtitles': {'user': app.OPENSUBTITLES_USER, 'pass': app.OPENSUBTITLES_PASS}}
                        %>
                        % for curService in subtitles.sorted_service_list():
                            <% provider_name = curService['name'] %>
                            % if provider_name not in providerLoginDict.keys():
                                <% continue %>
                            % endif
                            ##<div class="field-pair${(' hidden', '')[curService['enabled']]}"> ## Need js to show/hide on save
                            <div class="field-pair">
                                <label class="nocheck" for="${provider_name}_user">
                                    <span class="component-title">${provider_name.capitalize()} User Name</span>
                                    <span class="component-desc">
                                        <input type="text" name="${provider_name}_user" id="${provider_name}_user" value="${providerLoginDict[provider_name]['user']}" class="form-control input-sm input300" autocomplete="no" />
                                    </span>
                                </label>
                                <label class="nocheck" for="${provider_name}_pass">
                                    <span class="component-title">${provider_name.capitalize()} Password</span>
                                    <span class="component-desc">
                                        <input type="password" name="${provider_name}_pass" id="${provider_name}_pass" value="${providerLoginDict[provider_name]['pass']}" class="form-control input-sm input300" autocomplete="no"/>
                                    </span>
                                </label>
                            </div>
                        % endfor
                        <br><input type="submit" class="btn-medusa config_submitter" value="Save Changes" /><br>
                    </fieldset>
                </div><!-- /component-group3 //-->
                <br><input type="submit" class="btn-medusa config_submitter" value="Save Changes" /><br>
            </div><!-- /config-components //-->
        </form>
    </div>
</div>
<div class="clearfix"></div>
</%block>

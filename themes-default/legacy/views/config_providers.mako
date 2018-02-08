<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import app
    from medusa.helpers import anon_url
    from medusa.providers import sorted_provider_list
    from medusa.providers.generic_provider import GenericProvider
%>
<%block name="scripts">
<script type="text/javascript" src="js/config-providers.js"></script>
<script type="text/javascript">
$(document).ready(function(){
    // @TODO: This needs to be moved to an API function
    % if app.USE_NZBS:
        var show_nzb_providers = ${("false", "true")[bool(app.USE_NZBS)]};
        % for cur_newznab_provider in app.newznabProviderList:
        $(this).addProvider('${cur_newznab_provider.get_id()}', '${cur_newznab_provider.name}', '${cur_newznab_provider.url}', '${cur_newznab_provider.api_key}', '${",".join(cur_newznab_provider.cat_ids)}', ${int(cur_newznab_provider.default)}, show_nzb_providers);
        % endfor
    % endif
    % if app.USE_TORRENTS:
        % for cur_torrent_rss_provider in app.torrentRssProviderList:
        $(this).addTorrentRssProvider('${cur_torrent_rss_provider.get_id()}', '${cur_torrent_rss_provider.name}', '${cur_torrent_rss_provider.url}', '${cur_torrent_rss_provider.cookies}', '${cur_torrent_rss_provider.title_tag}');
        % endfor
    % endif
});
$('#config-components').tabs();
</script>
</%block>
<%block name="content">
% if not header is UNDEFINED:
    <h1 class="header">${header}</h1>
% else:
    <h1 class="title">${title}</h1>
% endif
<div id="config">
    <div id="config-content">
        <form id="configForm" action="config/providers/saveProviders" method="post">
            <div id="config-components">
                <ul>
                    ## @TODO: Fix this stupid hack
                    <script>document.write('<li><a href="' + document.location.href + '#provider-priorities">Provider Priorities</a></li>');</script>
                    <script>document.write('<li><a href="' + document.location.href + '#provider-options">Provider Options</a></li>');</script>
                  % if app.USE_NZBS:
                    <script>document.write('<li><a href="' + document.location.href + '#custom-newznab">Configure Custom Newznab Providers</a></li>');</script>
                  % endif
                  % if app.USE_TORRENTS:
                    <li><a href="${base_url}config/providers/#custom-torrent">Configure Custom Torrent Providers</a></li>
                  % endif
                </ul>
                <div id="provider-priorities" class="component-group" style='min-height: 550px;'>
                    <div class="component-group-desc">
                        <h3>Provider Priorities</h3>
                        <p>Check off and drag the providers into the order you want them to be used.</p>
                        <p>At least one provider is required but two are recommended.</p>
                        % if not app.USE_NZBS or not app.USE_TORRENTS:
                        <blockquote style="margin: 20px 0;">NZB/Torrent providers can be toggled in <b><a href="config/search">Search Settings</a></b></blockquote>
                        % else:
                        <br>
                        % endif
                        <div>
                            <p class="note"><span class="red-text">*</span> Provider does not support backlog searches at this time.</p>
                            <p class="note"><span class="red-text">!</span> Provider is <b>NOT WORKING</b>.</p>
                        </div>
                    </div>
                    <fieldset class="component-group-list">
                        <ul id="provider_order_list">
                        % for cur_provider in sorted_provider_list():
                            <%
                                ## These will show the '!' not saying they are broken
                                if cur_provider.provider_type == GenericProvider.NZB and not app.USE_NZBS:
                                    continue
                                elif cur_provider.provider_type == GenericProvider.TORRENT and not app.USE_TORRENTS:
                                    continue
                                curName = cur_provider.get_id()
                                if hasattr(cur_provider, 'custom_url'):
                                    curURL = cur_provider.custom_url or cur_provider.url
                                else:
                                    curURL = cur_provider.url
                            %>
                            <li class="ui-state-default ${('nzb-provider', 'torrent-provider')[bool(cur_provider.provider_type == GenericProvider.TORRENT)]}" id="${curName}">
                                <input type="checkbox" id="enable_${curName}" class="provider_enabler" ${'checked="checked"' if cur_provider.is_enabled() is True and cur_provider.get_id() not in app.BROKEN_PROVIDERS else ''}/>
                                <a href="${anon_url(curURL)}" class="imgLink" rel="noreferrer" onclick="window.open(this.href, '_blank'); return false;"><img src="images/providers/${cur_provider.image_name()}" alt="${cur_provider.name}" title="${cur_provider.name}" width="16" height="16" style="vertical-align:middle;"/></a>
                                <span style="vertical-align:middle;">${cur_provider.name}</span>
                                ${('<span class="red-text">*</span>', '')[bool(cur_provider.supports_backlog)]}
                                ${('<span class="red-text">!</span>', '')[bool(cur_provider.get_id() not in app.BROKEN_PROVIDERS)]}
                                <span class="ui-icon ui-icon-arrowthick-2-n-s pull-right" style="vertical-align:middle;" title="Re-order provider"></span>
                                <span class="ui-icon ${('ui-icon-locked','ui-icon-unlocked')[bool(cur_provider.public)]} pull-right" style="vertical-align:middle;" title="Public or Private"></span>
                                <span class="${('','ui-icon enable-manual-search-icon pull-right')[bool(cur_provider.enable_manualsearch)]}" style="vertical-align:middle;" title="Enabled for 'Manual Search' feature"></span>
                                <span class="${('','ui-icon enable-backlog-search-icon pull-right')[bool(cur_provider.enable_backlog)]}" style="vertical-align:middle;" title="Enabled for Backlog Searches"></span>
                                <span class="${('','ui-icon enable-daily-search-icon pull-right')[bool(cur_provider.enable_daily)]}" style="vertical-align:middle;" title="Enabled for Daily Searches"></span>
                            </li>
                        % endfor
                        </ul>
                        <input type="hidden" name="provider_order" id="provider_order" value="${" ".join([x.get_id()+':'+str(int(x.is_enabled())) for x in sorted_provider_list()])}"/>
                        <br><input type="submit" class="btn config_submitter" value="Save Changes" /><br>
                    </fieldset>
                </div><!-- /component-group1 //-->
                <div id="provider-options" class="component-group">
                    <div class="component-group-desc">
                        <h3>Provider Options</h3>
                        <p>Configure individual provider settings here.</p>
                        <p>Check with provider's website on how to obtain an API key if needed.</p>
                    </div>
                    <fieldset class="component-group-list">
                        <div class="field-pair">
                            <label for="editAProvider" id="provider-list">
                                <span class="component-title">Configure provider:</span>
                                <span class="component-desc">
                                    <%
                                        provider_config_list = []
                                        for cur_provider in sorted_provider_list():
                                            if cur_provider.provider_type == GenericProvider.NZB and (not app.USE_NZBS or not cur_provider.is_enabled()):
                                                continue
                                            elif cur_provider.provider_type == GenericProvider.TORRENT and ( not app.USE_TORRENTS or not cur_provider.is_enabled()):
                                                continue
                                            provider_config_list.append(cur_provider)
                                    %>
                                    % if provider_config_list:
                                        <select id="editAProvider" class="form-control input-sm">
                                            % for cur_provider in provider_config_list:
                                                <option value="${cur_provider.get_id()}">${cur_provider.name}</option>
                                            % endfor
                                        </select>
                                    % else:
                                        No providers available to configure.
                                    % endif
                                </span>
                            </label>
                        </div>
                    <!-- start div for editing providers //-->
                    % for cur_newznab_provider in [cur_provider for cur_provider in app.newznabProviderList]:
                    <div class="providerDiv" id="${cur_newznab_provider.get_id()}Div">
                        % if cur_newznab_provider.default and cur_newznab_provider.needs_auth:
                        <div class="field-pair">
                            <label for="${cur_newznab_provider.get_id()}_url">
                                <span class="component-title">URL:</span>
                                <span class="component-desc">
                                    <input type="text" id="${cur_newznab_provider.get_id()}_url" value="${cur_newznab_provider.url}" class="form-control input-sm input350" disabled/>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="${cur_newznab_provider.get_id()}_hash">
                                <span class="component-title">API key:</span>
                                <span class="component-desc">
                                    <input type="password" id="${cur_newznab_provider.get_id()}_hash" value="${cur_newznab_provider.api_key}" newznab_name="${cur_newznab_provider.get_id()}_hash" class="newznab_api_key form-control input-sm input350"/>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_newznab_provider, 'enable_daily'):
                        <div class="field-pair">
                            <label for="${cur_newznab_provider.get_id()}_enable_daily">
                                <span class="component-title">Enable daily searches</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_newznab_provider.get_id()}_enable_daily" id="${cur_newznab_provider.get_id()}_enable_daily" ${'checked="checked"' if cur_newznab_provider.enable_daily else ''}/>
                                    <p>enable provider to perform daily searches.</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_newznab_provider, 'enable_manualsearch'):
                        <div class="field-pair${(' hidden', '')[cur_newznab_provider.supports_backlog]}">
                            <label for="${cur_newznab_provider.get_id()}_enable_manualsearch">
                                <span class="component-title">Enable for 'Manual search' feature</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_newznab_provider.get_id()}_enable_manualsearch" id="${cur_newznab_provider.get_id()}_enable_manualsearch" ${'checked="checked"' if cur_newznab_provider.enable_manualsearch  and cur_newznab_provider.supports_backlog else ''}/>
                                    <p>enable provider to be used in 'Manual Search' feature.</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_newznab_provider, 'enable_backlog'):
                        <div class="field-pair${(' hidden', '')[cur_newznab_provider.supports_backlog]}">
                            <label for="${cur_newznab_provider.get_id()}_enable_backlog">
                                <span class="component-title">Enable backlog searches</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_newznab_provider.get_id()}_enable_backlog" id="${cur_newznab_provider.get_id()}_enable_backlog" ${'checked="checked"' if cur_newznab_provider.enable_backlog and cur_newznab_provider.supports_backlog else ''}/>
                                    <p>enable provider to perform backlog searches.</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_newznab_provider, 'search_mode'):
                        <div class="field-pair">
                            <label>
                                <span class="component-title">Season search mode</span>
                                <span class="component-desc">
                                    <p>when searching for complete seasons you can choose to have it look for season packs only, or choose to have it build a complete season from just single episodes.</p>
                                </span>
                            </label>
                            <label>
                                <span class="component-title"></span>
                                <span class="component-desc">
                                    <input type="radio" name="${cur_newznab_provider.get_id()}_search_mode" id="${cur_newznab_provider.get_id()}_search_mode_sponly" value="sponly" ${'checked="checked"' if cur_newznab_provider.search_mode=="sponly" else ''}/>season packs only.
                                </span>
                            </label>
                            <label>
                                <span class="component-title"></span>
                                <span class="component-desc">
                                    <input type="radio" name="${cur_newznab_provider.get_id()}_search_mode" id="${cur_newznab_provider.get_id()}_search_mode_eponly" value="eponly" ${'checked="checked"' if cur_newznab_provider.search_mode=="eponly" else ''}/>episodes only.
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_newznab_provider, 'search_fallback'):
                        <div class="field-pair">
                            <label for="${cur_newznab_provider.get_id()}_search_fallback">
                                <span class="component-title">Enable fallback</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_newznab_provider.get_id()}_search_fallback" id="${cur_newznab_provider.get_id()}_search_fallback" ${'checked="checked"' if cur_newznab_provider.search_fallback else ''}/>
                                    <p>when searching for a complete season depending on search mode you may return no results, this helps by restarting the search using the opposite search mode.</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_newznab_provider, 'enable_search_delay'):
                        <div class="field-pair">
                            <label for="${cur_newznab_provider.get_id()}_enable_search_delay">
                                <span class="component-title">Enable search delay</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_newznab_provider.get_id()}_enable_search_delay" id="${cur_newznab_provider.get_id()}_enable_search_delay" ${'checked="checked"' if cur_newznab_provider.enable_search_delay else ''}/>
                                    <p>Enable to delay downloads for this provider for an x amount of hours. The provider will start snatching results for a specific episode after a delay has expired, compared to when it first got a result for the specific episode.</p>
                                    <p>Searches for PROPER releases are exempted from the delay.</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_newznab_provider, 'search_delay'):
                        <div class="field-pair">
                            <label for="${cur_newznab_provider.get_id()}_ratio">
                                <span class="component-title" id="${cur_newznab_provider.get_id()}_search_delay">Search delay (hours):</span>
                                <span class="component-desc">
                                    <input type="number" min="0.5" step="0.5" name="${cur_newznab_provider.get_id()}_search_delay" id="${cur_newznab_provider.get_id()}_search_delay" value="${8 if cur_newznab_provider.search_delay is None else round(cur_newznab_provider.search_delay / 60, 1)}" class="form-control input-sm input75" />
                                </span>
                            </label>
                            <label>
                                <span class="component-title">&nbsp;</span>
                                <span class="component-desc">
                                    <p>Amount of hours to wait for downloading a result compared to the first result for a specific episode.</p>
                                </span>
                            </label>
                        </div>
                        % endif
                    </div>
                    % endfor
                    % for cur_nzb_provider in [cur_provider for cur_provider in sorted_provider_list() if cur_provider.provider_type == GenericProvider.NZB and cur_provider not in app.newznabProviderList]:
                    <div class="providerDiv" id="${cur_nzb_provider.get_id()}Div">
                        % if hasattr(cur_nzb_provider, 'username'):
                        <div class="field-pair">
                            <label for="${cur_nzb_provider.get_id()}_username">
                                <span class="component-title">Username:</span>
                                <span class="component-desc">
                                    <input type="text" name="${cur_nzb_provider.get_id()}_username" value="${cur_nzb_provider.username}" class="form-control input-sm input350"
                                           autocomplete="no" />
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_nzb_provider, 'api_key'):
                        <div class="field-pair">
                            <label for="${cur_nzb_provider.get_id()}_api_key">
                                <span class="component-title">API key:</span>
                                <span class="component-desc">
                                    <input type="text" name="${cur_nzb_provider.get_id()}_api_key" value="${cur_nzb_provider.api_key}" class="form-control input-sm input350"/>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_nzb_provider, 'enable_daily'):
                        <div class="field-pair">
                            <label for="${cur_nzb_provider.get_id()}_enable_daily">
                                <span class="component-title">Enable daily searches</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_nzb_provider.get_id()}_enable_daily" id="${cur_nzb_provider.get_id()}_enable_daily" ${'checked="checked"' if cur_nzb_provider.enable_daily else ''}/>
                                    <p>enable provider to perform daily searches.</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_nzb_provider, 'enable_manualsearch'):
                        <div class="field-pair${(' hidden', '')[cur_nzb_provider.supports_backlog]}">
                            <label for="${cur_nzb_provider.get_id()}_enable_manualsearch">
                                <span class="component-title">Enable 'Manual Search' feature</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_nzb_provider.get_id()}_enable_manualsearch" id="${cur_nzb_provider.get_id()}_enable_manualsearch" ${'checked="checked"' if cur_nzb_provider.enable_manualsearch and cur_nzb_provider.supports_backlog else ''}/>
                                     <p>enable provider to be used in 'Manual Search' feature.</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_nzb_provider, 'enable_backlog'):
                        <div class="field-pair${(' hidden', '')[cur_nzb_provider.supports_backlog]}">
                            <label for="${cur_nzb_provider.get_id()}_enable_backlog">
                                <span class="component-title">Enable backlog searches</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_nzb_provider.get_id()}_enable_backlog" id="${cur_nzb_provider.get_id()}_enable_backlog" ${'checked="checked"' if cur_nzb_provider.enable_backlog and cur_nzb_provider.supports_backlog else ''}/>
                                    <p>enable provider to perform backlog searches.</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_nzb_provider, 'search_mode'):
                        <div class="field-pair">
                            <label>
                                <span class="component-title">Season search mode</span>
                                <span class="component-desc">
                                    <p>when searching for complete seasons you can choose to have it look for season packs only, or choose to have it build a complete season from just single episodes.</p>
                                </span>
                            </label>
                            <label>
                                <span class="component-title"></span>
                                <span class="component-desc">
                                    <input type="radio" name="${cur_nzb_provider.get_id()}_search_mode" id="${cur_nzb_provider.get_id()}_search_mode_sponly" value="sponly" ${'checked="checked"' if cur_nzb_provider.search_mode=="sponly" else ''}/>season packs only.
                                </span>
                            </label>
                            <label>
                                <span class="component-title"></span>
                                <span class="component-desc">
                                    <input type="radio" name="${cur_nzb_provider.get_id()}_search_mode" id="${cur_nzb_provider.get_id()}_search_mode_eponly" value="eponly" ${'checked="checked"' if cur_nzb_provider.search_mode=="eponly" else ''}/>episodes only.
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_nzb_provider, 'search_fallback'):
                        <div class="field-pair">
                            <label for="${cur_nzb_provider.get_id()}_search_fallback">
                                <span class="component-title">Enable fallback</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_nzb_provider.get_id()}_search_fallback" id="${cur_nzb_provider.get_id()}_search_fallback" ${'checked="checked"' if cur_nzb_provider.search_fallback else ''}/>
                                    <p>when searching for a complete season depending on search mode you may return no results, this helps by restarting the search using the opposite search mode.</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_nzb_provider, 'enable_search_delay'):
                        <div class="field-pair">
                            <label for="${cur_nzb_provider.get_id()}_enable_search_delay">
                                <span class="component-title">Enable search delay</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_nzb_provider.get_id()}_enable_search_delay" id="${cur_nzb_provider.get_id()}_enable_search_delay" ${'checked="checked"' if cur_nzb_provider.enable_search_delay else ''}/>
                                    <p>Enable to delay downloads for this provider for an x amount of hours. The provider will start snatching results for a specific episode after a delay has expired, compared to when it first got a result for the specific episode.</p>
                                    <p>Searches for PROPER releases are exempted from the delay.</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_nzb_provider, 'search_delay'):
                        <div class="field-pair">
                            <label for="${cur_nzb_provider.get_id()}_ratio">
                                <span class="component-title" id="${cur_nzb_provider.get_id()}_search_delay">Search delay (hours):</span>
                                <span class="component-desc">
                                    <input type="number" min="0.5" step="0.5" name="${cur_nzb_provider.get_id()}_search_delay" id="${cur_nzb_provider.get_id()}_search_delay" value="${8 if cur_nzb_provider.search_delay is None else round(cur_nzb_provider.search_delay / 60, 1)}" class="form-control input-sm input75" />
                                </span>
                            </label>
                            <label>
                                <span class="component-title">&nbsp;</span>
                                <span class="component-desc">
                                    <p>Amount of hours to wait for downloading a result compared to the first result for a specific episode.</p>
                                </span>
                            </label>
                        </div>
                        % endif
                    </div>
                    % endfor
                    % for cur_torrent_provider in [cur_provider for cur_provider in sorted_provider_list() if cur_provider.provider_type == GenericProvider.TORRENT]:
                    <div class="providerDiv" id="${cur_torrent_provider.get_id()}Div">
                        % if hasattr(cur_torrent_provider, 'custom_url'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_custom_url">
                                <span class="component-title">Custom URL:</span>
                                <span class="component-desc">
                                    <input type="text" name="${cur_torrent_provider.get_id()}_custom_url" id="${cur_torrent_provider.get_id()}_custom_url" value="${cur_torrent_provider.custom_url}" class="form-control input-sm input350"/>
                                </span>
                            </label>
                            <label>
                                <span class="component-title">&nbsp;</span>
                                <span class="component-desc">
                                    <p>The URL should include the protocol (and port if applicable).  Examples:  http://192.168.1.4/ or http://localhost:3000/</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'api_key'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_api_key">
                                <span class="component-title">Api key:</span>
                                <span class="component-desc">
                                    <input type="text" name="${cur_torrent_provider.get_id()}_api_key" id="${cur_torrent_provider.get_id()}_api_key" value="${cur_torrent_provider.api_key}" class="form-control input-sm input350"/>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'digest'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_digest">
                                <span class="component-title">Digest:</span>
                                <span class="component-desc">
                                    <input type="text" name="${cur_torrent_provider.get_id()}_digest" id="${cur_torrent_provider.get_id()}_digest" value="${cur_torrent_provider.digest}" class="form-control input-sm input350"/>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'hash'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_hash">
                                <span class="component-title">Hash:</span>
                                <span class="component-desc">
                                    <input type="text" name="${cur_torrent_provider.get_id()}_hash" id="${cur_torrent_provider.get_id()}_hash" value="${cur_torrent_provider.hash}" class="form-control input-sm input350"/>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'username'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_username">
                                <span class="component-title">Username:</span>
                                <span class="component-desc">
                                    <input type="text" name="${cur_torrent_provider.get_id()}_username" id="${cur_torrent_provider.get_id()}_username" value="${cur_torrent_provider.username}" class="form-control input-sm input350"
                                           autocomplete="no" />
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'password'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_password">
                                <span class="component-title">Password:</span>
                                <span class="component-desc">
                                    <input type="password" name="${cur_torrent_provider.get_id()}_password" id="${cur_torrent_provider.get_id()}_password" value="${cur_torrent_provider.password | h}" class="form-control input-sm input350" autocomplete="no"/>
                                </span>
                            </label>
                        </div>
                        % endif

                        % if cur_torrent_provider.enable_cookies or cur_torrent_provider in app.torrentRssProviderList:
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_cookies">
                                <span class="component-title">Cookies:</span>
                                <span class="component-desc">
                                    <input type="text" name="${cur_torrent_provider.get_id()}_cookies" id="${cur_torrent_provider.get_id()}_cookies" value="${cur_torrent_provider.cookies}" class="form-control input-sm input350" autocapitalize="off" autocomplete="no" />
                                </span>
                            </label>
                            <label>
                                <span class="component-title">&nbsp;</span>
                                <span class="component-desc">
                                    % if hasattr(cur_torrent_provider, 'required_cookies'):
                                        <p>eg. ${'=xx;'.join(cur_torrent_provider.required_cookies) + '=xx'}</p>
                                        <p>This provider requires the following cookies: ${', '.join(cur_torrent_provider.required_cookies)}. <br/>For a step by step guide please follow the link to our <a target="_blank" href="${anon_url('https://github.com/pymedusa/Medusa/wiki/Configure-Providers-with-captcha-protection')}">WIKI</a></p>
                                    % endif
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'passkey'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_passkey">
                                <span class="component-title">Passkey:</span>
                                <span class="component-desc">
                                    <input type="text" name="${cur_torrent_provider.get_id()}_passkey" id="${cur_torrent_provider.get_id()}_passkey" value="${cur_torrent_provider.passkey}" class="form-control input-sm input350"/>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'pin'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_pin">
                                <span class="component-title">Pin:</span>
                                <span class="component-desc">
                                    <input type="password" name="${cur_torrent_provider.get_id()}_pin" id="${cur_torrent_provider.get_id()}_pin" value="${cur_torrent_provider.pin}" class="form-control input-sm input100" autocomplete="no"/>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'ratio'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_ratio">
                                <span class="component-title" id="${cur_torrent_provider.get_id()}_ratio_desc">Seed ratio:</span>
                                <span class="component-desc">
                                    <input type="number" min="-1" step="0.1" name="${cur_torrent_provider.get_id()}_ratio" id="${cur_torrent_provider.get_id()}_ratio" value="${'' if cur_torrent_provider.ratio is None else cur_torrent_provider.ratio}" class="form-control input-sm input75" />
                                </span>
                            </label>
                            <label>
                                <span class="component-title">&nbsp;</span>
                                <span class="component-desc">
                                    <p>stop transfer when ratio is reached<br>(-1 Medusa default to seed forever, or leave blank for downloader default)</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'minseed'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_minseed">
                                <span class="component-title" id="${cur_torrent_provider.get_id()}_minseed_desc">Minimum seeders:</span>
                                <span class="component-desc">
                                    <input type="number" min="0" step="1" name="${cur_torrent_provider.get_id()}_minseed" id="${cur_torrent_provider.get_id()}_minseed" value="${cur_torrent_provider.minseed}" class="form-control input-sm input75" />
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'minleech'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_minleech">
                                <span class="component-title" id="${cur_torrent_provider.get_id()}_minleech_desc">Minimum leechers:</span>
                                <span class="component-desc">
                                    <input type="number" min="0" step="1" name="${cur_torrent_provider.get_id()}_minleech" id="${cur_torrent_provider.get_id()}_minleech" value="${cur_torrent_provider.minleech}" class="form-control input-sm input75" />
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'confirmed'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_confirmed">
                                <span class="component-title">Confirmed download</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_torrent_provider.get_id()}_confirmed" id="${cur_torrent_provider.get_id()}_confirmed" ${'checked="checked"' if cur_torrent_provider.confirmed else ''}/>
                                    <p>only download torrents from trusted or verified uploaders ?</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'ranked'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_ranked">
                                <span class="component-title">Ranked torrents</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_torrent_provider.get_id()}_ranked" id="${cur_torrent_provider.get_id()}_ranked" ${'checked="checked"' if cur_torrent_provider.ranked else ''} />
                                    <p>only download ranked torrents (trusted releases)</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'engrelease'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_engrelease">
                                <span class="component-title">English torrents</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_torrent_provider.get_id()}_engrelease" id="${cur_torrent_provider.get_id()}_engrelease" ${'checked="checked"' if cur_torrent_provider.engrelease else ''} />
                                    <p>only download english torrents, or torrents containing english subtitles</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'onlyspasearch'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_onlyspasearch">
                                <span class="component-title">For Spanish torrents</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_torrent_provider.get_id()}_onlyspasearch" id="${cur_torrent_provider.get_id()}_onlyspasearch" ${'checked="checked"' if cur_torrent_provider.onlyspasearch else ''} />
                                    <p>ONLY search on this provider if show info is defined as "Spanish" (avoid provider's use for VOS shows)</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'sorting'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_sorting">
                                <span class="component-title">Sorting results by</span>
                                <span class="component-desc">
                                    <select name="${cur_torrent_provider.get_id()}_sorting" id="${cur_torrent_provider.get_id()}_sorting" class="form-control input-sm">
                                    % for cur_action in ('last', 'seeders', 'leechers'):
                                    <option value="${cur_action}" ${'selected="selected"' if cur_action == cur_torrent_provider.sorting else ''}>${cur_action}</option>
                                    % endfor
                                    </select>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'freeleech'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_freeleech">
                                <span class="component-title">Freeleech</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_torrent_provider.get_id()}_freeleech" id="${cur_torrent_provider.get_id()}_freeleech" ${'checked="checked"' if cur_torrent_provider.freeleech else ''}/>
                                    <p>only download <b>"FreeLeech"</b> torrents.</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'enable_daily'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_enable_daily">
                                <span class="component-title">Enable daily searches</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_torrent_provider.get_id()}_enable_daily" id="${cur_torrent_provider.get_id()}_enable_daily" ${'checked="checked"' if cur_torrent_provider.enable_daily else ''}/>
                                    <p>enable provider to perform daily searches.</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'enable_manualsearch'):
                        <div class="field-pair${(' hidden', '')[cur_torrent_provider.supports_backlog]}">
                            <label for="${cur_torrent_provider.get_id()}_enable_manualsearch">
                                <span class="component-title">Enable 'Manual Search' feature</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_torrent_provider.get_id()}_enable_manualsearch" id="${cur_torrent_provider.get_id()}_enable_manualsearch" ${'checked="checked"' if cur_torrent_provider.enable_manualsearch and cur_torrent_provider.supports_backlog else ''}/>
                                    <p>enable provider to be used in 'Manual Search' feature.</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'enable_backlog'):
                        <div class="field-pair${(' hidden', '')[cur_torrent_provider.supports_backlog]}">
                            <label for="${cur_torrent_provider.get_id()}_enable_backlog">
                                <span class="component-title">Enable backlog searches</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_torrent_provider.get_id()}_enable_backlog" id="${cur_torrent_provider.get_id()}_enable_backlog" ${'checked="checked"' if cur_torrent_provider.enable_backlog and cur_torrent_provider.supports_backlog else ''}/>
                                    <p>enable provider to perform backlog searches.</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'search_mode'):
                        <div class="field-pair">
                            <label>
                                <span class="component-title">Season search mode</span>
                                <span class="component-desc">
                                    <p>when searching for complete seasons you can choose to have it look for season packs only, or choose to have it build a complete season from just single episodes.</p>
                                </span>
                            </label>
                            <label>
                                <span class="component-title"></span>
                                <span class="component-desc">
                                    <input type="radio" name="${cur_torrent_provider.get_id()}_search_mode" id="${cur_torrent_provider.get_id()}_search_mode_sponly" value="sponly" ${'checked="checked"' if cur_torrent_provider.search_mode=="sponly" else ''}/>season packs only.
                                </span>
                            </label>
                            <label>
                                <span class="component-title"></span>
                                <span class="component-desc">
                                    <input type="radio" name="${cur_torrent_provider.get_id()}_search_mode" id="${cur_torrent_provider.get_id()}_search_mode_eponly" value="eponly" ${'checked="checked"' if cur_torrent_provider.search_mode=="eponly" else ''}/>episodes only.
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'search_fallback'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_search_fallback">
                                <span class="component-title">Enable fallback</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_torrent_provider.get_id()}_search_fallback" id="${cur_torrent_provider.get_id()}_search_fallback" ${'checked="checked"' if cur_torrent_provider.search_fallback else ''}/>
                                    <p>when searching for a complete season depending on search mode you may return no results, this helps by restarting the search using the opposite search mode.</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'cat') and cur_torrent_provider.get_id() == 'tntvillage':
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_cat">
                                <span class="component-title">Category:</span>
                                <span class="component-desc">
                                    <select name="${cur_torrent_provider.get_id()}_cat" id="${cur_torrent_provider.get_id()}_cat" class="form-control input-sm">
                                        % for i in cur_torrent_provider.category_dict.keys():
                                        <option value="${cur_torrent_provider.category_dict[i]}" ${('', 'selected="selected"')[cur_torrent_provider.category_dict[i] == cur_torrent_provider.cat]}>${i}</option>
                                        % endfor
                                    </select>
                                </span>
                           </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'subtitle') and cur_torrent_provider.get_id() == 'tntvillage':
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_subtitle">
                                <span class="component-title">Subtitled</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_torrent_provider.get_id()}_subtitle" id="${cur_torrent_provider.get_id()}_subtitle" ${'checked="checked"' if cur_torrent_provider.subtitle else ''}/>
                                    <p>select torrent with Italian subtitle</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'enable_search_delay'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_enable_search_delay">
                                <span class="component-title">Enable search delay</span>
                                <span class="component-desc">
                                    <input type="checkbox" name="${cur_torrent_provider.get_id()}_enable_search_delay" id="${cur_torrent_provider.get_id()}_enable_search_delay" ${'checked="checked"' if cur_torrent_provider.enable_search_delay else ''}/>
                                    <p>Enable to delay downloads for this provider for an x amount of hours. The provider will start snatching results for a specific episode after a delay has expired, compared to when it first got a result for the specific episode.</p>
                                    <p>Searches for PROPER releases are exempted from the delay.</p>
                                </span>
                            </label>
                        </div>
                        % endif
                        % if hasattr(cur_torrent_provider, 'search_delay'):
                        <div class="field-pair">
                            <label for="${cur_torrent_provider.get_id()}_ratio">
                                <span class="component-title" id="${cur_torrent_provider.get_id()}_search_delay">Search delay (hours):</span>
                                <span class="component-desc">
                                    <input type="number" min="0.5" step="0.5" name="${cur_torrent_provider.get_id()}_search_delay" id="${cur_torrent_provider.get_id()}_search_delay" value="${8 if cur_torrent_provider.search_delay is None else round(cur_torrent_provider.search_delay / 60, 1)}" class="form-control input-sm input75" />
                                </span>
                            </label>
                            <label>
                                <span class="component-title">&nbsp;</span>
                                <span class="component-desc">
                                    <p>Amount of hours to wait for downloading a result compared to the first result for a specific episode.</p>
                                </span>
                            </label>
                        </div>
                        % endif
                    </div>
                    % endfor
                    <!-- end div for editing providers -->
                    <input type="submit" class="btn config_submitter" value="Save Changes" /><br>
                    </fieldset>
                </div><!-- /component-group2 //-->
                % if app.USE_NZBS:
                <div id="custom-newznab" class="component-group">
                    <div class="component-group-desc">
                        <h3>Configure Custom<br>Newznab Providers</h3>
                        <p>Add and setup or remove custom Newznab providers.</p>
                    </div>
                    <fieldset class="component-group-list">
                        <div class="field-pair">
                            <label for="newznab_string">
                                <span class="component-title">Select provider:</span>
                                <span class="component-desc">
                                    <input type="hidden" name="newznab_string" id="newznab_string" />
                                    <select id="editANewznabProvider" class="form-control input-sm">
                                        <option value="addNewznab">-- add new provider --</option>
                                    </select>
                                </span>
                            </label>
                        </div>
                    <div class="newznabProviderDiv" id="addNewznab">
                        <div class="field-pair">
                            <label for="newznab_name">
                                <span class="component-title">Provider name:</span>
                                <input type="text" id="newznab_name" class="form-control input-sm input200"/>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="newznab_url">
                                <span class="component-title">Site URL:</span>
                                <input type="text" id="newznab_url" class="form-control input-sm input350"/>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="newznab_key">
                                <span class="component-title">API key:</span>
                                <input type="password" id="newznab_api_key" class="form-control input-sm input350"/>
                            </label>
                            <label>
                                <span class="component-title">&nbsp;</span>
                                <span class="component-desc">(if not required, type 0)</span>
                            </label>
                        </div>
                        <div class="field-pair" id="newznabcapdiv">
                            <label>
                                <span class="component-title">Newznab search categories:</span>
                                <select id="newznab_cap" multiple="multiple" style="min-width:10em;" ></select>
                                <select id="newznab_cat" multiple="multiple" style="min-width:10em;" ></select>
                            </label>
                            <label>
                                <span class="component-title">&nbsp;</span>
                                <span class="component-desc">(select your Newznab categories on the left, and click the "update categories" button to use them for searching.) <b>don't forget to to save the form!</b></span>
                            </label>
                            <label>
                                <span class="component-title">&nbsp;</span>
                                <span class="component-desc"><input class="btn" type="button" class="newznab_cat_update" id="newznab_cat_update" value="Update Categories" />
                                    <span class="updating_categories"></span>
                                </span>
                            </label>
                        </div>
                        <div id="newznab_add_div">
                            <input class="btn" type="button" class="newznab_save" id="newznab_add" value="Add" />
                        </div>
                        <div id="newznab_update_div" style="display: none;">
                            <input class="btn btn-danger newznab_delete" type="button" class="newznab_delete" id="newznab_delete" value="Delete" />
                        </div>
                    </div>
                    </fieldset>
                </div><!-- /component-group3 //-->
                % endif
                % if app.USE_TORRENTS:
                <div id="custom-torrent" class="component-group">
                <div class="component-group-desc">
                    <h3>Configure Custom Torrent Providers</h3>
                    <p>Add and setup or remove custom RSS providers.</p>
                </div>
                <fieldset class="component-group-list">
                    <div class="field-pair">
                        <label for="torrentrss_string">
                            <span class="component-title">Select provider:</span>
                            <span class="component-desc">
                            <input type="hidden" name="torrentrss_string" id="torrentrss_string" />
                                <select id="editATorrentRssProvider" class="form-control input-sm">
                                    <option value="addTorrentRss">-- add new provider --</option>
                                </select>
                            </span>
                        </label>
                        <label>
                            <span class="component-desc">Note: Jackett must be configured as custom Newznab providers: <a target="_blank" href="${anon_url('https://github.com/pymedusa/Medusa/wiki/Using-Jackett-with-Medusa')}"><font color="blue">Wiki</font></a></span>
                        </label>
                    </div>
                    <div class="torrentRssProviderDiv" id="addTorrentRss">
                        <div class="field-pair">
                            <label for="torrentrss_name">
                                <span class="component-title">Provider name:</span>
                                <input type="text" id="torrentrss_name" class="form-control input-sm input200"/>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="torrentrss_url">
                                <span class="component-title">RSS URL:</span>
                                <input type="text" id="torrentrss_url" class="form-control input-sm input350"/>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="torrentrss_cookies">
                                <span class="component-title">Cookies (optional):</span>
                                <input type="text" id="torrentrss_cookies" class="form-control input-sm input350" />
                            </label>
                            <label>
                                <span class="component-title">&nbsp;</span>
                                <span class="component-desc">eg. uid=xx;pass=yy, please use "Provider options" to reconfigure!</span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="torrentrss_title_tag">
                                <span class="component-title">Search element:</span>
                                <input type="text" id="torrentrss_title_tag" class="form-control input-sm input200" value="title"/>
                            </label>
                            <label>
                                <span class="component-title">&nbsp;</span>
                                <span class="component-desc">eg: title</span>
                            </label>
                        </div>
                        <div id="torrentrss_add_div">
                            <input type="button" class="btn torrentrss_save" id="torrentrss_add" value="Add" />
                        </div>
                        <div id="torrentrss_update_div" style="display: none;">
                            <input type="button" class="btn btn-danger torrentrss_delete" id="torrentrss_delete" value="Delete" />
                        </div>
                    </div>
                </fieldset>
            </div><!-- /component-group4 //-->
            % endif
            <br><input type="submit" class="btn config_submitter_refresh" value="Save Changes" /><br>
            </div><!-- /config-components //-->
        </form>
    </div>
</div>
</%block>

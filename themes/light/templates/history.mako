<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import app
    import os.path
    from datetime import datetime
    import re
    import time
    from random import choice
    from medusa import providers
    from medusa.sbdatetime import sbdatetime
    from medusa.common import SKIPPED, WANTED, UNAIRED, ARCHIVED, IGNORED, SNATCHED, SNATCHED_PROPER, SNATCHED_BEST, FAILED, DOWNLOADED, SUBTITLED
    from medusa.common import statusStrings
    from medusa.show.history import History
    from medusa.providers.generic_provider import GenericProvider
%>
<%block name="scripts">
<script type="text/x-template" id="history-template">
<div>
% if historyResults:
<backstretch :slug="config.randomShowSlug"></backstretch>
% endif

    <div class="row">
        <div class="col-md-6">
            <h1 class="header">{{ $route.meta.header }}</h1>
        </div> <!-- layout title -->
        <div class="col-md-6 pull-right"> <!-- Controls -->
            <div class="layout-controls pull-right">
                <div class="show-option">
                    <span>Limit:</span>
                    <select v-model="stateLayout.historyLimit" name="history_limit" id="history_limit" class="form-control form-control-inline input-sm">
                        <option value="10">10</option>
                        <option value="25">25</option>
                        <option value="50">50</option>
                        <option value="100">100</option>
                        <option value="250">250</option>
                        <option value="500">500</option>
                        <option value="750">750</option>
                        <option value="1000">1000</option>
                        <option value="0">All</option>
                    </select>
                </div>
                <div class="show-option">
                    <span> Layout:
                        <select v-model="historyLayout" name="layout" class="form-control form-control-inline input-sm">
                            <option :value="option.value" v-for="option in layoutOptions" :key="option.value">{{ option.text }}</option>
                        </select>
                    </span>
                </div>
            </div> <!-- layout controls -->
        </div>
    </div> <!-- row -->

    <!-- Title -->
    <div class="row">
        <div class="col-md-12">
            <div class="horizontal-scroll">
                <table v-if="historyLayout === 'detailed'" id="historyTable" class="${'fanartOpacity' if app.FANART_BACKGROUND else ''} defaultTable tablesorter" cellspacing="1" border="0" cellpadding="0">
                    <thead>
                        <tr>
                            <th class="nowrap" width="15%">Time</th>
                            <th width="35%">Episode</th>
                            <th>Action</th>
                            <th>Provider</th>
                            <th width="14%">Quality</th>
                        </tr>
                    </thead>
                    <tfoot>
                        <tr>
                            <th class="nowrap" colspan="5">&nbsp;</th>
                        </tr>
                    </tfoot>
                    <tbody>
                    % for hItem in historyResults:
                        <tr>
                            <td align="center" class="triggerhighlight">
                                <% airDate = sbdatetime.sbfdatetime(datetime.strptime(str(hItem.date), History.date_format), show_seconds=True) %>
                                <% isoDate = datetime.strptime(str(hItem.date), History.date_format).isoformat('T') %>
                                <time datetime="${isoDate}" class="date">${airDate}</time>
                            </td>
                            <td class="tvShow triggerhighlight"><app-link indexer-id="${hItem.indexer_id}" href="home/displayShow?indexername=indexer-to-name&seriesid=${hItem.show_id}#season-${hItem.season}">${hItem.show_name} - ${"S%02i" % int(hItem.season)}${"E%02i" % int(hItem.episode)} ${"""<quality-pill :quality="0" :override="{ class: 'quality proper', text: 'Proper' }"></quality-pill>""" if hItem.proper_tags else ''} </app-link></td>
                            <td align="center" ${'class="triggerhighlight subtitles_column"' if hItem.action == SUBTITLED else 'triggerhighlight'}>
                            % if hItem.action == SUBTITLED:
                                <img width="16" height="11" style="vertical-align:middle;" src="images/subtitles/flags/${hItem.resource}.png" onError="this.onerror=null;this.src='images/flags/unknown.png';">
                            % endif
                                <span style="cursor: help; vertical-align:middle;" title="${os.path.basename(hItem.resource)}">${statusStrings[hItem.action]}</span>
                                % if hItem.manually_searched:
                                    <img src="images/manualsearch.png" width="16" height="16" style="vertical-align:middle;" title="Manual searched episode" />
                                % endif
                                % if hItem.proper_tags:
                                    <img src="images/info32.png" width="16" height="16" style="vertical-align:middle;" title="${hItem.proper_tags.replace('|', ', ')}"/>
                                % endif
                            </td>
                            <!-- Provider column -->
                            <td align="center" class="triggerhighlight">
                            % if hItem.action in [DOWNLOADED, ARCHIVED]:
                                % if hItem.provider != "-1":
                                    <span style="vertical-align:middle;"><i>${hItem.provider}</i></span>
                                % else:
                                    <span style="vertical-align:middle;"><i>Unknown</i></span>
                                % endif
                            % else:
                                % if hItem.provider:
                                    % if hItem.action in [SNATCHED, FAILED]:
                                        <% provider = providers.get_provider_class(GenericProvider.make_id(hItem.provider)) %>
                                        % if provider is not None:
                                            <img src="images/providers/${provider.image_name()}" width="16" height="16" style="vertical-align:middle;" /> <span style="vertical-align:middle;">${provider.name}</span>
                                        % else:
                                            <img src="images/providers/missing.png" width="16" height="16" style="vertical-align:middle;" title="missing provider"/> <span style="vertical-align:middle;">Missing Provider</span>
                                        % endif
                                    % else:
                                            <img src="images/subtitles/${hItem.provider}.png" width="16" height="16" style="vertical-align:middle;" /> <span style="vertical-align:middle;">${hItem.provider.capitalize()}</span>
                                    % endif
                                % endif
                            % endif
                            </td>
                            <td align="center" class="triggerhighlight" quality="${hItem.quality}">
                                <quality-pill :quality="${hItem.quality}"></quality-pill>
                            </td>
                        </tr>
                    % endfor
                    </tbody>
                </table>
                <table v-else id="historyTable" class="${'fanartOpacity' if app.FANART_BACKGROUND else ''} defaultTable tablesorter" cellspacing="1" border="0" cellpadding="0">
                    <thead>
                        <tr>
                            <th class="nowrap" width="18%">Time</th>
                            <th width="25%">Episode</th>
                            <th>Snatched</th>
                            <th>Downloaded</th>
                            <th v-if="config.subtitles.enabled">Subtitled</th>
                            <th width="14%">Quality</th>
                        </tr>
                    </thead>
                    <tfoot>
                        <tr>
                            <th class="nowrap shadow" colspan="6">&nbsp;</th>
                        </tr>
                    </tfoot>
                    <tbody>
                    % for hItem in compactResults:
                        <tr>
                            <td align="center" class="triggerhighlight">
                                <% airDate = sbdatetime.sbfdatetime(datetime.strptime(str(hItem.actions[0].date), History.date_format), show_seconds=True) %>
                                <% isoDate = datetime.strptime(str(hItem.actions[0].date), History.date_format).isoformat('T') %>
                                <time datetime="${isoDate}" class="date">${airDate}</time>
                            </td>
                            <td class="tvShow triggerhighlight">
                                <% proper_tags = [action.proper_tags for action in hItem.actions if action.proper_tags] %>
                                <span><app-link indexer-id="${hItem.index.indexer_id}" href="home/displayShow?indexername=indexer-to-name&seriesid=${hItem.index.show_id}#season-${hItem.index.season}">${hItem.show_name} - ${"S%02i" % int(hItem.index.season)}${"E%02i" % int(hItem.index.episode)} ${"""<quality-pill :quality="0" :override="{ class: 'quality proper', text: 'Proper' }"></quality-pill>""" if proper_tags else ''}</app-link></span>
                            </td>
                            <td class="triggerhighlight" align="center" provider="${str(sorted(hItem.actions)[0].provider)}">
                                % for cur_action in sorted(hItem.actions, key=lambda x: x.date):
                                    % if cur_action.action == SNATCHED:
                                        <% provider = providers.get_provider_class(GenericProvider.make_id(cur_action.provider)) %>
                                        % if provider is not None:
                                            <img src="images/providers/${provider.image_name()}" width="16" height="16" style="vertical-align:middle; cursor: help" alt="${provider.name}" title="${provider.name}: ${cur_action.resource}"/>
                                            % if cur_action.manually_searched:
                                                <img src="images/manualsearch.png" width="16" height="16" style="vertical-align:middle;" title="Manual searched episode" />
                                            % endif
                                            % if cur_action.proper_tags:
                                                <img src="images/info32.png" width="16" height="16" style="vertical-align:middle;" title="${cur_action.proper_tags.replace('|', ', ')}"/>
                                            % endif
                                        % else:
                                            <img src="images/providers/missing.png" width="16" height="16" style="vertical-align:middle;" alt="missing provider" title="Missing provider: ${cur_action.provider}"/>
                                        % endif
                                    % endif
                                    % if cur_action.action == FAILED:
                                            <img src="images/no16.png" width="16" height="16" style="vertical-align:middle;" title="${provider.name if provider else cur_action.provider} download failed: ${cur_action.resource}"/>
                                    % endif
                                % endfor
                            </td>
                            <td align="center" class="triggerhighlight">
                                % for cur_action in sorted(hItem.actions):
                                    % if cur_action.action in [DOWNLOADED, ARCHIVED]:
                                        % if cur_action.provider != "-1":
                                            <span style="cursor: help;" title="${os.path.basename(cur_action.resource)}"><i>${cur_action.provider}</i></span>
                                        % else:
                                            <span style="cursor: help;" title="${os.path.basename(cur_action.resource)}"><i>Unknown</i></span>
                                        % endif
                                    % endif
                                % endfor
                            </td>
                            <td v-if="config.subtitles.enabled" align="center" class="triggerhighlight">
                                % for cur_action in sorted(hItem.actions):
                                    % if cur_action.action == SUBTITLED:
                                        <img src="images/subtitles/${cur_action.provider}.png" width="16" height="16" style="vertical-align:middle;" alt="${cur_action.provider}" title="${cur_action.provider.capitalize()}: ${os.path.basename(cur_action.resource)}"/>
                                        <span style="vertical-align:middle;"> / </span>
                                        <img width="16" height="11" src="images/subtitles/flags/${cur_action.resource}.png" onError="this.onerror=null;this.src='images/flags/unknown.png';" style="vertical-align: middle !important;">
                                        &nbsp;
                                    % endif
                                % endfor
                            </td>
                            <td align="center" class="triggerhighlight" quality="${hItem.index.quality}">
                                <span><quality-pill :quality="${hItem.index.quality}"></quality-pill></span>
                            </td>
                        </tr>
                    % endfor
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>
</script>
<script>
    window.app = new Vue({
        el: '#vue-wrap',
        store,
        router,
        data() {
            return {
                // This loads history.vue
                pageComponent: 'history'
            }
        }
    });
</script>
</%block>

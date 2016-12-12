<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import app
    import os.path
    from datetime import datetime
    import re
    import time
    from medusa import providers
    from medusa.sbdatetime import sbdatetime
    from medusa.common import SKIPPED, WANTED, UNAIRED, ARCHIVED, IGNORED, SNATCHED, SNATCHED_PROPER, SNATCHED_BEST, FAILED, DOWNLOADED, SUBTITLED
    from medusa.common import Quality, statusStrings, Overview
    from medusa.show.history import History
    from medusa.providers.generic_provider import GenericProvider
%>
<%block name="content">
<%namespace file="/inc_defs.mako" import="renderQualityPill"/>
<!-- Title -->
<div class="row">
    <div class="col-md-12">
        % if not header is UNDEFINED:
            <h1 class="header">${header}</h1>
        % else:
            <h1 class="title">${title}</h1>
        % endif
    </div>
</div>
<!-- Controls -->
<div class="row">
    <div class="col-md-12">
        <div class="layout-controls pull-right">
            <div class="show-option">
                <span>Limit:</span>
                    <select name="history_limit" id="history_limit" class="form-control form-control-inline input-sm">
                        <option value="10" ${'selected="selected"' if limit == 10 else ''}>10</option>
                        <option value="25" ${'selected="selected"' if limit == 25 else ''}>25</option>
                        <option value="50" ${'selected="selected"' if limit == 50 else ''}>50</option>
                        <option value="100" ${'selected="selected"' if limit == 100 else ''}>100</option>
                        <option value="250" ${'selected="selected"' if limit == 250 else ''}>250</option>
                        <option value="500" ${'selected="selected"' if limit == 500 else ''}>500</option>
                        <option value="750" ${'selected="selected"' if limit == 750 else ''}>750</option>
                        <option value="1000" ${'selected="selected"' if limit == 1000 else ''}>1000</option>
                        <option value="0"   ${'selected="selected"' if limit == 0   else ''}>All</option>
                    </select>
            </div>
            <div class="show-option">
                <span> Layout:
                    <select name="HistoryLayout" class="form-control form-control-inline input-sm" onchange="location = this.options[this.selectedIndex].value;">
                        <option value="setHistoryLayout/?layout=compact"  ${'selected="selected"' if app.HISTORY_LAYOUT == 'compact' else ''}>Compact</option>
                        <option value="setHistoryLayout/?layout=detailed" ${'selected="selected"' if app.HISTORY_LAYOUT == 'detailed' else ''}>Detailed</option>
                    </select>
                </span>
            </div>
        </div> <!-- layout controls -->
    </div>
</div> <!-- row -->

<!-- Title -->
<div class="row">
    <div class="col-md-12">
        % if app.HISTORY_LAYOUT == "detailed":
            <table id="historyTable" class="defaultTable tablesorter" cellspacing="1" border="0" cellpadding="0">
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
                    <% composite = Quality.split_composite_status(int(hItem.action)) %>
                    <tr>
                        <td align="center">
                            <% airDate = sbdatetime.sbfdatetime(datetime.strptime(str(hItem.date), History.date_format), show_seconds=True) %>
                            <% isoDate = datetime.strptime(str(hItem.date), History.date_format).isoformat('T') %>
                            <time datetime="${isoDate}" class="date">${airDate}</time>
                        </td>
                        <td class="tvShow"><a href="home/displayShow?show=${hItem.show_id}#season-${hItem.season}">${hItem.show_name} - ${"S%02i" % int(hItem.season)}${"E%02i" % int(hItem.episode)} ${'<span class="quality Proper">Proper</span>' if hItem.proper_tags else ''} </a></td>
                        <td align="center" ${'class="subtitles_column"' if composite.status == SUBTITLED else ''}>
                        % if composite.status == SUBTITLED:
                            <img width="16" height="11" style="vertical-align:middle;" src="images/subtitles/flags/${hItem.resource}.png" onError="this.onerror=null;this.src='images/flags/unknown.png';">
                        % endif
                            <span style="cursor: help; vertical-align:middle;" title="${os.path.basename(hItem.resource)}">${statusStrings[composite.status]}</span>
                            % if hItem.manually_searched:
                                <img src="images/manualsearch.png" width="16" height="16" style="vertical-align:middle;" title="Manual searched episode" />
                            % endif
                            % if hItem.proper_tags:
                                <img src="images/info32.png" width="16" height="16" style="vertical-align:middle;" title="${hItem.proper_tags.replace('|', ', ')}"/>
                            % endif
                        </td>
                        <td align="center">
                        % if composite.status in [DOWNLOADED, ARCHIVED]:
                            % if hItem.provider != "-1":
                                <span style="vertical-align:middle;"><i>${hItem.provider}</i></span>
                            % else:
                                <span style="vertical-align:middle;"><i>Unknown</i></span>
                            % endif
                        % else:
                            % if hItem.provider > 0:
                                % if composite.status in [SNATCHED, FAILED]:
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
                        <span style="display: none;">${composite.quality}</span>
                        <td align="center">${renderQualityPill(composite.quality)}</td>
                    </tr>
                % endfor
                </tbody>
            </table>
        % else:
            <table id="historyTable" class="defaultTable tablesorter" cellspacing="1" border="0" cellpadding="0">
                <thead>
                    <tr>
                        <th class="nowrap" width="18%">Time</th>
                        <th width="25%">Episode</th>
                        <th>Snatched</th>
                        <th>Downloaded</th>
                        % if app.USE_SUBTITLES:
                        <th>Subtitled</th>
                        % endif
                        <th width="14%">Quality</th>
                    </tr>
                </thead>
                <tfoot>
                    <tr>
                        <th class="nowrap" colspan="6">&nbsp;</th>
                    </tr>
                </tfoot>
                <tbody>
                % for hItem in compactResults:
                    <tr>
                        <td align="center">
                            <% airDate = sbdatetime.sbfdatetime(datetime.strptime(str(hItem.actions[0].date), History.date_format), show_seconds=True) %>
                            <% isoDate = datetime.strptime(str(hItem.actions[0].date), History.date_format).isoformat('T') %>
                            <time datetime="${isoDate}" class="date">${airDate}</time>
                        </td>
                        <td class="tvShow">
                            <% proper_tags = [action.proper_tags for action in hItem.actions if action.proper_tags] %>
                            <span><a href="home/displayShow?show=${hItem.index.show_id}#season-${hItem.index.season}">${hItem.show_name} - ${"S%02i" % int(hItem.index.season)}${"E%02i" % int(hItem.index.episode)} ${'<span class="quality Proper">Proper</span>' if proper_tags else ''}</a></span>
                        </td>
                        <td align="center" provider="${str(sorted(hItem.actions)[0].provider)}">
                            % for cur_action in sorted(hItem.actions, key=lambda x: x.date):
                                <% composite = Quality.split_composite_status(int(cur_action.action)) %>
                                % if composite.status == SNATCHED:
                                    <% provider = providers.get_provider_class(GenericProvider.make_id(cur_action.provider)) %>
                                    % if provider is not None:
                                        <img src="images/providers/${provider.image_name()}" width="16" height="16" style="vertical-align:middle;" alt="${provider.name}" style="cursor: help;" title="${provider.name}: ${cur_action.resource}"/>
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
                                % if composite.status == FAILED:
                                        <img src="images/no16.png" width="16" height="16" style="vertical-align:middle;" title="${provider.name if provider else cur_action.provider} download failed: ${cur_action.resource}"/>
                                % endif
                            % endfor
                        </td>
                        <td align="center">
                            % for cur_action in sorted(hItem.actions):
                                <% composite = Quality.split_composite_status(int(cur_action.action)) %>
                                % if composite.status in [DOWNLOADED, ARCHIVED]:
                                    % if cur_action.provider != "-1":
                                        <span style="cursor: help;" title="${os.path.basename(cur_action.resource)}"><i>${cur_action.provider}</i></span>
                                    % else:
                                        <span style="cursor: help;" title="${os.path.basename(cur_action.resource)}"><i>Unknown</i></span>
                                    % endif
                                % endif
                            % endfor
                        </td>
                        % if app.USE_SUBTITLES:
                        <td align="center">
                            % for cur_action in sorted(hItem.actions):
                                <% composite = Quality.split_composite_status(int(cur_action.action)) %>
                                % if composite.status == SUBTITLED:
                                    <img src="images/subtitles/${cur_action.provider}.png" width="16" height="16" style="vertical-align:middle;" alt="${cur_action.provider}" title="${cur_action.provider.capitalize()}: ${os.path.basename(cur_action.resource)}"/>
                                    <span style="vertical-align:middle;"> / </span>
                                    <img width="16" height="11" style="vertical-align:middle;" src="images/subtitles/flags/${cur_action.resource}.png" onError="this.onerror=null;this.src='images/flags/unknown.png';" style="vertical-align: middle !important;">
                                    &nbsp;
                                % endif
                            % endfor
                        </td>
                        % endif
                        <td align="center" quality="${composite.quality}">${renderQualityPill(composite.quality)}</td>
                    </tr>
                % endfor
                </tbody>
            </table>
            % endif
        </div>
    </div>
</%block>

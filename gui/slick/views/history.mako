<%inherit file="/layouts/main.mako"/>
<%!
    import sickbeard
    import os.path
    from datetime import datetime
    import re
    import time

    from guessit import guessit

    from sickbeard import providers
    from sickbeard.sbdatetime import sbdatetime

    from sickbeard.common import SKIPPED, WANTED, UNAIRED, ARCHIVED, IGNORED, SNATCHED, SNATCHED_PROPER, SNATCHED_BEST, FAILED, DOWNLOADED, SUBTITLED
    from sickbeard.common import Quality, statusStrings, Overview

    from sickrage.show.History import History
    from sickrage.helper.encoding import ek
    from sickrage.providers.GenericProvider import GenericProvider
%>
<%block name="content">
<%namespace file="/inc_defs.mako" import="renderQualityPill"/>
% if not header is UNDEFINED:
    <h1 class="header">${header}</h1>
% else:
    <h1 class="title">${title}</h1>
% endif
<div class="h2footer pull-right"><b>Limit:</b>
    <select name="history_limit" id="history_limit" class="form-control form-control-inline input-sm">
        <option value="10" ${('', 'selected="selected"')[limit == 10]}>10</option>
        <option value="25" ${('', 'selected="selected"')[limit == 25]}>25</option>
        <option value="50" ${('', 'selected="selected"')[limit == 50]}>50</option>
        <option value="100" ${('', 'selected="selected"')[limit == 100]}>100</option>
        <option value="250" ${('', 'selected="selected"')[limit == 250]}>250</option>
        <option value="500" ${('', 'selected="selected"')[limit == 500]}>500</option>
        <option value="750" ${('', 'selected="selected"')[limit == 750]}>750</option>
        <option value="1000" ${('', 'selected="selected"')[limit == 1000]}>1000</option>
        <option value="0"   ${('', 'selected="selected"')[limit == 0  ]}>All</option>
    </select>

    <span> Layout:
        <select name="HistoryLayout" class="form-control form-control-inline input-sm" onchange="location = this.options[this.selectedIndex].value;">
            <option value="${srRoot}/setHistoryLayout/?layout=compact"  ${('', 'selected="selected"')[sickbeard.HISTORY_LAYOUT == 'compact']}>Compact</option>
            <option value="${srRoot}/setHistoryLayout/?layout=detailed" ${('', 'selected="selected"')[sickbeard.HISTORY_LAYOUT == 'detailed']}>Detailed</option>
        </select>
    </span>
</div>
<br>

% if sickbeard.HISTORY_LAYOUT == "detailed":
    <table id="historyTable" class="sickbeardTable tablesorter" cellspacing="1" border="0" cellpadding="0">
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
            <% composite = Quality.splitCompositeStatus(int(hItem.action)) %>
            <tr>
                <td align="center">
                    <% airDate = sbdatetime.sbfdatetime(datetime.strptime(str(hItem.date), History.date_format), show_seconds=True) %>
                    <% isoDate = datetime.strptime(str(hItem.date), History.date_format).isoformat('T') %>
                    <time datetime="${isoDate}" class="date">${airDate}</time>
                </td>
                <td class="tvShow"><a href="${srRoot}/home/displayShow?show=${hItem.show_id}#S${hItem.season}E${hItem.episode}">${hItem.show_name} - ${"S%02i" % int(hItem.season)}${"E%02i" % int(hItem.episode)} ${'<span class="quality Proper">Proper</span>' if guessit(hItem.resource).get('proper_count') else ''}</a></td>
                <td align="center" ${('', 'class="subtitles_column"')[composite.status == SUBTITLED]}>
                % if composite.status == SUBTITLED:
                    <img width="16" height="11" style="vertical-align:middle;" src="${srRoot}/images/subtitles/flags/${hItem.resource}.png" onError="this.onerror=null;this.src='${srRoot}/images/flags/unknown.png';">
                % endif
                    <span style="cursor: help; vertical-align:middle;" title="${ek(os.path.basename, hItem.resource)}">${statusStrings[composite.status]}</span>
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
                            <% provider = providers.getProviderClass(GenericProvider.make_id(hItem.provider)) %>
                            % if provider is not None:
                                <img src="${srRoot}/images/providers/${provider.image_name()}" width="16" height="16" style="vertical-align:middle;" /> <span style="vertical-align:middle;">${provider.name}</span>
                            % else:
                                <img src="${srRoot}/images/providers/missing.png" width="16" height="16" style="vertical-align:middle;" title="missing provider"/> <span style="vertical-align:middle;">Missing Provider</span>
                            % endif
                        % else:
                                <img src="${srRoot}/images/subtitles/${hItem.provider}.png" width="16" height="16" style="vertical-align:middle;" /> <span style="vertical-align:middle;">${hItem.provider.capitalize()}</span>
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

    <table id="historyTable" class="sickbeardTable tablesorter" cellspacing="1" border="0" cellpadding="0">
        <thead>
            <tr>
                <th class="nowrap" width="18%">Time</th>
                <th width="25%">Episode</th>
                <th>Snatched</th>
                <th>Downloaded</th>
                % if sickbeard.USE_SUBTITLES:
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
                    <span><a href="${srRoot}/home/displayShow?show=${hItem.index.show_id}#season-${hItem.index.season}">${hItem.show_name} - ${"S%02i" % int(hItem.index.season)}${"E%02i" % int(hItem.index.episode)}${' <span class="quality Proper">Proper</span>' if guessit(hItem.actions[0].resource).get('proper_count') else ''}</a></span>
                </td>
                <td align="center" provider="${str(sorted(hItem.actions)[0].provider)}">
                    % for cur_action in sorted(hItem.actions):
                        <% composite = Quality.splitCompositeStatus(int(cur_action.action)) %>
                        % if composite.status in [SNATCHED, FAILED]:
                            <% provider = providers.getProviderClass(GenericProvider.make_id(cur_action.provider)) %>
                            % if provider is not None:
                                <img src="${srRoot}/images/providers/${provider.image_name()}" width="16" height="16" style="vertical-align:middle;" alt="${provider.name}" style="cursor: help;" title="${provider.name}: ${ek(os.path.basename, cur_action.resource)}"/>
                            % else:
                                <img src="${srRoot}/images/providers/missing.png" width="16" height="16" style="vertical-align:middle;" alt="missing provider" title="missing provider"/>
                            % endif
                        % endif
                    % endfor
                </td>
                <td align="center">
                    % for cur_action in sorted(hItem.actions):
                        <% composite = Quality.splitCompositeStatus(int(cur_action.action)) %>
                        % if composite.status in [DOWNLOADED, ARCHIVED]:
                            % if cur_action.provider != "-1":
                                <span style="cursor: help;" title="${ek(os.path.basename, cur_action.resource)}"><i>${cur_action.provider}</i></span>
                            % else:
                                <span style="cursor: help;" title="${ek(os.path.basename, cur_action.resource)}"><i>Unknown</i></span>
                            % endif
                        % endif
                    % endfor
                </td>
                % if sickbeard.USE_SUBTITLES:
                <td align="center">
                    % for cur_action in sorted(hItem.actions):
                        <% composite = Quality.splitCompositeStatus(int(cur_action.action)) %>
                        % if composite.status == SUBTITLED:
                            <img src="${srRoot}/images/subtitles/${cur_action.provider}.png" width="16" height="16" style="vertical-align:middle;" alt="${cur_action.provider}" title="${cur_action.provider.capitalize()}: ${ek(os.path.basename, cur_action.resource)}"/>
                            <span style="vertical-align:middle;"> / </span>
                            <img width="16" height="11" style="vertical-align:middle;" src="${srRoot}/images/subtitles/flags/${cur_action.resource}.png" onError="this.onerror=null;this.src='${srRoot}/images/flags/unknown.png';" style="vertical-align: middle !important;">
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
</%block>

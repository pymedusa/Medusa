<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import app
    import calendar
    from medusa.common import SKIPPED, WANTED, UNAIRED, ARCHIVED, IGNORED, SNATCHED, SNATCHED_PROPER, SNATCHED_BEST, FAILED
    from medusa.common import Quality, qualityPresets, qualityPresetStrings
    from medusa import db, sbdatetime, network_timezones
    from random import choice
    import datetime
    import re
%>
<%block name="scripts">
<script type="text/javascript" src="js/test-rename.js"></script>
</%block>
<%block name="content">
    % if app.PROCESS_METHOD == 'symlink':
<div class="text-center">
<div class="alert alert-danger upgrade-notification hidden-print" role="alert">
    <span>WARNING: Your current process method is SYMLINK. Renaming these files will break all symlinks in your Post-Processor${('', '/Seeding')[bool(app.TORRENT_SEED_LOCATION)]} directory for this show</span>
</div>
</div>
    % endif
<input type="hidden" id="series-id" value="${show.indexerid}" />
<input type="hidden" id="series-slug" value="${show.slug}" />
% if not header is UNDEFINED:
    <h1 class="header">${header}</h1>
% else:
    <h1 class="title">${title}</h1>
% endif
<h3>Preview of the proposed name changes</h3>
<blockquote>
% if int(show.air_by_date) == 1 and app.NAMING_CUSTOM_ABD:
    ${app.NAMING_ABD_PATTERN}
% elif int(show.sports) == 1 and app.NAMING_CUSTOM_SPORTS:
    ${app.NAMING_SPORTS_PATTERN}
% else:
    ${app.NAMING_PATTERN}
% endif
</blockquote>
<% cur_season = -1 %>
<% odd = False%>
<h2>All Seasons</h2>
<div class="row">
    <div class="col-md-2">
    <table id="SelectAllTable" class="defaultTable" cellspacing="1" border="0" cellpadding="0">
        <thead>
            <tr class="seasoncols" id="selectall">
                <th class="col-checkbox"><input type="checkbox" class="seriesCheck" id="SelectAll" /></th>
                <th align="left" valign="top" class="nowrap">Select All</th>
            </tr>
        </thead>
    </table>
    </div>
    <div class="col-md-10">
        <input type="submit" value="Rename Selected" class="btn btn-success"> <a href="home/displayShow?show=${show.indexerid}" class="btn btn-danger">Cancel Rename</a>
    </div>
</div>
<table id="testRenameTable" class="defaultTable ${"summaryFanArt" if app.FANART_BACKGROUND else ""}" cellspacing="1" border="0" cellpadding="0">
% for cur_ep_obj in ep_obj_list:
<%
    curLoc = cur_ep_obj.location[len(cur_ep_obj.show.location)+1:]
    curExt = curLoc.split('.')[-1]
    newLoc = cur_ep_obj.proper_path() + '.' + curExt
%>
% if int(cur_ep_obj.season) != cur_season:
    <thead>
        <tr class="seasonheader" id="season-${cur_ep_obj.season}">
            <td colspan="4">
                 <br>
                <h2>${'Specials' if int(cur_ep_obj.season) == 0 else 'Season '+str(cur_ep_obj.season)}</h2>
            </td>
        </tr>
        <tr class="seasoncols" id="season-${cur_ep_obj.season}-cols">
            <th class="col-checkbox"><input type="checkbox" class="seasonCheck" id="${cur_ep_obj.season}" /></th>
            <th class="nowrap">Episode</th>
            <th class="col-name">Old Location</th>
            <th class="col-name">New Location</th>
        </tr>
    </thead>
<% cur_season = int(cur_ep_obj.season) %>
% endif
    <tbody>
<%
odd = not odd
epStr = str(cur_ep_obj.season) + "x" + str(cur_ep_obj.episode)
epList = sorted([cur_ep_obj.episode] + [x.episode for x in cur_ep_obj.related_episodes])
if len(epList) > 1:
    epList = [min(epList), max(epList)]
%>
        <tr class="season-${cur_season} ${'good' if curLoc == newLoc else 'wanted'} seasonstyle">
            <td class="col-checkbox">
            % if curLoc != newLoc:
                <input type="checkbox" class="epCheck" id="${str(cur_ep_obj.season) + 'x' + str(cur_ep_obj.episode)}" name="${str(cur_ep_obj.season) + "x" + str(cur_ep_obj.episode)}" />
            % endif
            </td>
            <td align="center" valign="top" class="nowrap">${"-".join(map(str, epList))}</td>
            <td width="50%" class="col-name">${curLoc}</td>
            <td width="50%" class="col-name">${newLoc}</td>
        </tr>
    </tbody>
% endfor
</table><br>
<input type="submit" value="Rename Selected" class="btn btn-success"> <a href="home/displayShow?show=${show.indexerid}" class="btn btn-danger">Cancel Rename</a>
</%block>

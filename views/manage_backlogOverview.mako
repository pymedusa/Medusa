<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import app
    import datetime
    from medusa.common import Overview, Quality
    from medusa.helper.common import episode_num
    from medusa import sbdatetime, network_timezones
%>
<%block name="scripts">
<script type="text/javascript">
</script>
</%block>
<%block name="content">
<div id="content960">
% if not header is UNDEFINED:
    <h1 class="header">${header}</h1>
% else:
    <h1 class="title">${title}</h1>
% endif
<%
    totalWanted = totalQual = 0
    backLogShows = sorted([x for x in app.showList if showCounts[x.indexerid][Overview.QUAL] + showCounts[x.indexerid][Overview.WANTED]], key=lambda x: x.name)
    for cur_show in backLogShows:
        totalWanted += showCounts[cur_show.indexerid][Overview.WANTED]
        totalQual += showCounts[cur_show.indexerid][Overview.QUAL]
%>
<div class="h2footer pull-right">
    % if totalWanted > 0:
    <span class="listing-key wanted">Wanted: <b>${totalWanted}</b></span>
    % endif
    % if totalQual > 0:
    <span class="listing-key qual">Quality: <b>${totalQual}</b></span>
    % endif
</div><br>
<div class="float-left">
Jump to Show:
    <select id="pickShow" class="form-control form-control-inline input-sm">
    % for cur_show in backLogShows:
        <option value="${cur_show.indexerid}">${cur_show.name}</option>
    % endfor
    </select>
</div>
<table class="defaultTable" cellspacing="0" border="0" cellpadding="0">
% for cur_show in backLogShows:
    % if not showCounts[cur_show.indexerid][Overview.WANTED] + showCounts[cur_show.indexerid][Overview.QUAL]:
        <% continue %>
    % endif
    <tr class="seasonheader" id="show-${cur_show.indexerid}">
        <td colspan="3" class="align-left" style="position: relative;">
            <h2 style="display: inline-block;"><a href="home/displayShow?show=${cur_show.indexerid}">${cur_show.name}</a></h2>
            <div style="position: absolute; bottom: 10px; right: 0;">
                % if showCounts[cur_show.indexerid][Overview.WANTED] > 0:
                <span class="listing-key wanted">Wanted: <b>${showCounts[cur_show.indexerid][Overview.WANTED]}</b></span>
                % endif
                % if showCounts[cur_show.indexerid][Overview.QUAL] > 0:
                <span class="listing-key qual">Quality: <b>${showCounts[cur_show.indexerid][Overview.QUAL]}</b></span>
                % endif
                <a class="btn btn-inline forceBacklog" href="manage/backlogShow?indexer_id=${cur_show.indexerid}"><i class="icon-play-circle icon-white"></i> Force Backlog</a>
            </div>
        </td>
    </tr>
    <tr class="seasoncols"><th>Episode</th><th>Name</th><th class="nowrap">Airdate</th></tr>
    % for cur_result in showSQLResults[cur_show.indexerid]:
        <%
            whichStr = episode_num(cur_result['season'], cur_result['episode']) or episode_num(cur_result['season'], cur_result['episode'], numbering='absolute')
            if whichStr not in showCats[cur_show.indexerid] or showCats[cur_show.indexerid][whichStr] not in (Overview.QUAL, Overview.WANTED):
                continue
        %>
        <tr class="seasonstyle ${Overview.overviewStrings[showCats[cur_show.indexerid][whichStr]]}">
            <td class="tableleft" align="center">${whichStr}</td>
            <td class="tableright" align="center" class="nowrap">
                ${cur_result["name"]}
            </td>
            <td>
                <% epResult = cur_result %>
                <% show = cur_show %>
                % if int(epResult['airdate']) != 1:
                    ## Lets do this exactly like ComingEpisodes and History
                    ## Avoid issues with dateutil's _isdst on Windows but still provide air dates
                    <% airDate = datetime.datetime.fromordinal(epResult['airdate']) %>
                    % if airDate.year >= 1970 or show.network:
                        <% airDate = sbdatetime.sbdatetime.convert_to_setting(network_timezones.parse_date_time(epResult['airdate'], show.airs, show.network)) %>
                    % endif
                    <time datetime="${airDate.isoformat('T')}" class="date">${sbdatetime.sbdatetime.sbfdatetime(airDate)}</time>
                % else:
                    Never
                % endif
            </td>
        </tr>
    % endfor
% endfor
</table>
</div>
</%block>

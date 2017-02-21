<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import app
    import datetime
    from medusa.common import ARCHIVED, DOWNLOADED,Overview, Quality, qualityPresets, statusStrings
    from medusa.helper.common import episode_num
    from medusa import sbdatetime, network_timezones
%>
<%block name="scripts">
<script type="text/javascript">
</script>
</%block>
<%block name="content">
<%namespace file="/inc_defs.mako" import="renderQualityPill"/>
<div class="clearfix"></div><!-- div.clearfix //-->
</div>
<div class="clearfix"></div>
<div id="content-col" class="col-lg-10 col-lg-offset-1 col-md-10 col-md-offset-1 col-sm-12 col-xs-12">
    <div class="row col-md-12">
    % if not header is UNDEFINED:
        <h1 class="header">${header}</h1>
    % else:
        <h1 class="title">${title}</h1>
    % endif
    </div>
<%
    totalWanted = totalQual = 0
    backLogShows = sorted([x for x in app.showList if showCounts[x.indexerid][Overview.QUAL] + showCounts[x.indexerid][Overview.WANTED]], key=lambda x: x.name)
    for cur_show in backLogShows:
        totalWanted += showCounts[cur_show.indexerid][Overview.WANTED]
        totalQual += showCounts[cur_show.indexerid][Overview.QUAL]
%>
    <div class="clearfix"></div>
    <div class="row col-md-12">
        <div class="col-md-6">
            <div class="col-md-12">Jump to Show: <select id="pickShow" class="form-control-inline input-sm-custom">
                % for cur_show in backLogShows:
                    <option value="${cur_show.indexerid}">${cur_show.name}</option>
                % endfor
                </select>
            </div>
        </div>
        <div class="col-md-6 pull-right">
            <div class="h2footer pull-right">
                % if totalWanted > 0:
                <span class="listing-key wanted">Wanted: <b>${totalWanted}</b></span>
                % endif
                % if totalQual > 0:
                <span class="listing-key qual">Quality: <b>${totalQual}</b></span>
                % endif
            </div>
        </div>
    </div>
    <div class="clearfix"></div>
    <div class="row col-md-12">
        <table class="defaultTable" cellspacing="0" border="0" cellpadding="0">
        % for cur_show in backLogShows:
            % if not showCounts[cur_show.indexerid][Overview.WANTED] + showCounts[cur_show.indexerid][Overview.QUAL]:
                <% continue %>
            % endif
            <tr class="seasonheader"><td colspan="5">&nbsp;</td></tr>
            <tr class="seasonheader" id="show-${cur_show.indexerid}">
                <td class="row-seasonheader" colspan="5" style="vertical-align: bottom; width: auto;">
                    <div class="col-md-12">
                        <div class="col-md-8 left-30">
                            <h3 style="display: inline;"><a href="home/displayShow?show=${cur_show.indexerid}">${cur_show.name}</a></h3>
                             % if cur_show.quality in qualityPresets:
                                &nbsp;&nbsp;&nbsp;&nbsp;<i>Quality:</i>&nbsp;&nbsp;${renderQualityPill(cur_show.quality)}
                             % endif
                        </div>
                        <div class="col-md-4 pull-right right-30">
                            <div class="top-5 bottom-5 pull-right">
                                % if showCounts[cur_show.indexerid][Overview.WANTED] > 0:
                                <span class="listing-key wanted">Wanted: <b>${showCounts[cur_show.indexerid][Overview.WANTED]}</b></span>
                                % endif
                                % if showCounts[cur_show.indexerid][Overview.QUAL] > 0:
                                <span class="listing-key qual">Quality: <b>${showCounts[cur_show.indexerid][Overview.QUAL]}</b></span>
                                % endif
                                <a class="btn btn-inline forceBacklog" href="manage/backlogShow?indexer_id=${cur_show.indexerid}"><i class="icon-play-circle icon-white"></i> Force Backlog</a>
                                <a class="btn btn-inline editShow" href="manage/editShow?show=${cur_show.indexerid}"><i class="icon-play-circle icon-white"></i> Edit Show</a>
                            </div>
                        </div>
                    </div>
                </td>
            </tr>
            % if not cur_show.quality in qualityPresets:
            <% allowed_qualities, preferred_qualities = Quality.split_quality(int(cur_show.quality)) %>
            <tr>
                <td colspan="5" class="backlog-quality">
                    <div class="col-md-12 left-30">
                    % if allowed_qualities:
                        <div class="col-md-12 align-left">
                           <i>Allowed:</i>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ${' '.join([capture(renderQualityPill, x) for x in sorted(allowed_qualities)])}${'<br>' if preferred_qualities else ''}
                        </div>
                    % endif
                    % if preferred_qualities:
                        <div class="col-md-12 align-left">
                           <i>Preferred:</i>&nbsp;&nbsp; ${' '.join([capture(renderQualityPill, x) for x in sorted(preferred_qualities)])}
                       </div>
                    % endif
                    </div>
                </td>
            </tr>
            % endif
            <tr class="seasoncols">
                <th>Episode</th>
                <th>Status / Quality</th>
                <th>Episode Title</th>
                <th class="nowrap">Airdate</th>
                <th>Actions</th>
            </tr>
            % for cur_result in showSQLResults[cur_show.indexerid]:
                <%
                    whichStr = episode_num(cur_result['season'], cur_result['episode']) or episode_num(cur_result['season'], cur_result['episode'], numbering='absolute')
                    if whichStr not in showCats[cur_show.indexerid] or showCats[cur_show.indexerid][whichStr] not in (Overview.QUAL, Overview.WANTED):
                        continue
                    old_status, old_quality = Quality.split_composite_status(cur_result['status'])
                    archived_status = Quality.composite_status(ARCHIVED, old_quality)
                %>
                <tr class="seasonstyle ${Overview.overviewStrings[showCats[cur_show.indexerid][whichStr]]}">
                    <td class="tableleft" align="center">${whichStr}</td>
                    <td class="col-status">
                        % if old_quality != Quality.NONE:
                            ${statusStrings[old_status]} ${renderQualityPill(old_quality)}
                        % else:
                            ${statusStrings[old_status]}
                        % endif
                    </td>
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
                    <td class="col-search">
                        <a class="epSearch" id="${str(cur_show.indexerid)}x${str(cur_result['season'])}x${str(cur_result['episode'])}" name="${str(cur_show.indexerid)}x${str(cur_result['season'])}x${str(cur_result['episode'])}" href="home/searchEpisode?show=${cur_show.indexerid}&amp;season=${cur_result['season']}&amp;episode=${cur_result['episode']}"><img data-ep-search src="images/search16.png" width="16" height="16" alt="search" title="Forced Search" /></a>
                        <a class="epManualSearch" id="${str(cur_show.indexerid)}x${str(cur_result['season'])}x${str(cur_result['episode'])}" name="${str(cur_show.indexerid)}x${str(cur_result['season'])}x${str(cur_result['episode'])}" href="home/snatchSelection?show=${cur_show.indexerid}&amp;season=${cur_result['season']}&amp;episode=${cur_result['episode']}"><img data-ep-manual-search src="images/manualsearch.png" width="16" height="16" alt="search" title="Manual Search" /></a>
                        % if old_status == DOWNLOADED:
                            <a class="epArchive" id="${str(cur_show.indexerid)}x${str(cur_result['season'])}x${str(cur_result['episode'])}" name="${str(cur_show.indexerid)}x${str(cur_result['season'])}x${str(cur_result['episode'])}" href="home/setStatus?show=${cur_show.indexerid}&eps=${cur_result['season']}x${cur_result['episode']}&status=${archived_status}&direct=1"><img data-ep-archive src="images/archive.png" width="16" height="16" alt="search" title="Archive episode" /></a>
                        % endif
                    </td>
                </tr>
            % endfor
        % endfor
        </table>
    </div>
</div>
</%block>

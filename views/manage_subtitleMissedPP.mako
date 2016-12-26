<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import app
    import os
    from medusa.helper.common import episode_num
%>
<%block name="scripts">
<script type="text/javascript" src="js/lib/jquery.bookmarkscroll.js?${sbPID}"></script>
<script type="text/javascript" src="js/ajax-episode-subtitles.js?${sbPID}"></script>
</%block>
<%block name="content">
    <div>
    % if not header is UNDEFINED:
        <h1 class="header">${header}</h1>
    % else:
        <h1 class="title">${title}</h1>
    % endif
    </div>
<div id="container">
    <table id="releasesPP" class="defaultTable" cellspacing="1" border="0" cellpadding="0">
        <thead aria-live="polite" aria-relevant="all">
            <tr>
                <th>Show</th>
                <th>Episode</th>
                <th>Release</th>
                <th>Age</th>
                <th class="col-search">Search</th>
            </tr>
        </thead>
        <tbody aria-live="polite" aria-relevant="all">
        % for index, epResult in enumerate(releases_in_pp):
            <tr class="snatched" role="row" release_id=${index}>
                <td class="tvShow" align="left"><a href="home/displayShow?show=${epResult['show']}#season-${epResult['season']}">
                        ${epResult['show_name']}
                </td>
                <td class="tvShow" align="center">
                        ${episode_num(epResult['season'], epResult['episode'])}
                </td>
                <td class="tvShow" align="left">
                    <span class="break-word" title=${os.path.relpath(epResult['release'], app.TV_DOWNLOAD_DIR)}>
                        ${os.path.basename(epResult['release'])}
                    </span>
                </td>
                <td class="tvShow" align="center">
                        ${epResult['age']}${epResult['age_unit']}
                </td>
                <td class="col-search" align="center">
                    <a class="epSubtitlesSearchPP" release_id=${index} href="home/manual_search_subtitles?release_id=${index}"><img src="images/closed_captioning.png" height="16" alt="search subtitles" title="Search Subtitles" /></a>
                </td>
            </tr>
        % endfor
        </tbody>
    </table>
<%include file="subtitle_modal.mako"/>
<br>
<form name="processForm" method="post" action="home/postprocess/processEpisode" style="float: right;">
<table>
    <input type="hidden" id="proc_type" name="type" value="manual">
    <input type="hidden" id="process_method" name="process_method" value=${app.PROCESS_METHOD}>
    <input type="hidden" id="episodeDir" type="text" name="proc_dir" value=${app.TV_DOWNLOAD_DIR}>
    <input type="hidden" id="force" name="force" value="0">
    <input type="hidden" id="is_priority" name="is_priority" value="0">
    <input type="hidden" id="delete_on" name="delete_on" value=${not app.NO_DELETE}>
    <input type="hidden" id="failed" name="failed" value="0">
    <input type="hidden" id="ignore_subs" name="ignore_subs" value="0">
</table>
    <input id="submit" class="btn" type="submit" value="Run Manual Post-Process" />
</form>
</div>
</%block>

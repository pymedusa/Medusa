<%inherit file="/layouts/main.mako"/>
<%!
    import medusa as app
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
    <table id="showListTable" class="defaultTable" cellspacing="1" border="0" cellpadding="0">
        <thead aria-live="polite" aria-relevant="all">
            <tr>
                <th>Show</th>
                <th>Episode</th>
                <th>Release</th>
                <th class="col-search">Search</th>
            </tr>
        </thead>
        <tbody aria-live="polite" aria-relevant="all">
        % for index, epResult in enumerate(releases_in_pp):
            <tr class="snatched" role="row">
                <td class="tvShow" align="left">
                        ${epResult['show_name']}
                </td>
                <td class="tvShow" align="center">
                        ${episode_num(epResult['season'], epResult['episode'])}
                </td>
                <td class="tvShow" align="left">
                    <span class="break-word">
                        ${os.path.relpath(epResult['release'], app.TV_DOWNLOAD_DIR)}
                    </span>
                </td>
                <td class="col-search">
                    <a class="epSubtitlesSearchPP" release_id=${index} href="home/manual_search_subtitles?release_id=${index}"><img src="images/closed_captioning.png" height="16" alt="search subtitles" title="Search Subtitles" /></a>
                </td>
            </tr>
        % endfor
        </tbody>
    </table>
<%include file="subtitle_modal.mako"/>
</div>
</%block>

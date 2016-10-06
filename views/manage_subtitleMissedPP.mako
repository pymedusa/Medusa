<%inherit file="/layouts/main.mako"/>
<%!
    import medusa as app
    import os
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
                <th>Release</th>
                <th class="col-search">Search</th>
            </tr>
        </thead>
        <tbody aria-live="polite" aria-relevant="all">
        % for epResult in releases_in_pp:
            <tr class="snatched" role="row">
                <td class="tvShow" align="left">
                    <span class="break-word">
                        ${os.path.relpath(epResult['release'], app.TV_DOWNLOAD_DIR)}
                    </span>
                </td>
                <td class="col-search">
                    <a class="epSubtitlesSearchPP" href="home/manual_search_subtitles?show=${epResult["indexer_id"]}&amp;season=${epResult["season"]}&amp;episode=${epResult["episode"]}&amp;filepath=${epResult["release"]}"><img src="images/closed_captioning.png" height="16" alt="search subtitles" title="Search Subtitles" /></a>
                </td>
            </tr>
        % endfor
        </tbody>
    </table>
<div id="manualSubtitleSearchModal" class="modal fade modal-wide" >
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
                <h4 class="modal-title"></h4>
            </div>
            <div class="modal-body">
                <table id=subtitle_results style="width:100%">
                <tbody>
                <tr>
                    <th>Provider/Lang</th>
                    <th>Score</th>
                    <th>Subtitle</th>
                    <th>Missing/wrong</th>
                    <th></th>
                </tr>
                </tbody>
                </table> 
            </div>
        </div>
    </div>
</div>
</div>
</%block>

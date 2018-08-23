<%inherit file="/layouts/main.mako"/>
<%!
    import os

    from medusa import app
    from medusa.helper.common import episode_num
%>
<%block name="scripts">
<script type="text/javascript" src="js/ajax-episode-subtitles.js?${sbPID}"></script>
<script>
window.app = {};
window.app = new Vue({
    store,
    router,
    el: '#vue-wrap',
    mounted() {
        this.$once('loaded', () => {
            startAjaxEpisodeSubtitles(); // eslint-disable-line no-undef
            $.ajaxEpSubtitlesSearch();
        });

        $('#releasesPP:has(tbody tr)').tablesorter({
            sortList: [[3, 1], [0, 0]],
            textExtraction: {
                0(node) { return $(node).find('a').text().toLowerCase(); }, // eslint-disable-line brace-style
                1(node) { return $(node).text().toLowerCase(); }, // eslint-disable-line brace-style
                2(node) { return $(node).find('span').text().toLowerCase(); }, // eslint-disable-line brace-style
                3(node) { return $(node).find('span').attr('datetime'); } // eslint-disable-line brace-style
            },
            widgets: ['saveSort', 'filter'],
            headers: {
                0: { sorter: 'show' },
                1: { sorter: 'episode' },
                2: { sorter: 'release' },
                3: { sorter: 'realISODate' },
                4: { sorter: false, filter: false }
            },
            widgetOptions: {
                filter_columnFilters: true, // eslint-disable-line camelcase
                filter_hideFilters: true, // eslint-disable-line camelcase
                filter_saveFilters: true, // eslint-disable-line camelcase
                columnSelector_mediaquery: false // eslint-disable-line camelcase
            }
        });
    }
});
</script>
</%block>
<%block name="content">
<div class="row">
<div class="col-md-12">
<h1 class="header">{{ $route.meta.header }}</h1>
</div>
</div>
<div class="row">
<div class="col-md-12">
<div class="horizontal-scroll">
    <table id="releasesPP" class="defaultTable" cellspacing="1" border="0" cellpadding="0">
        <thead aria-live="polite" aria-relevant="all">
            <tr>
                <th>Show</th>
                <th class="col-search">Episode</th>
                <th>Release</th>
                <th class="col-search">Age</th>
                <th class="col-search">Search</th>
            </tr>
        </thead>
        <tbody aria-live="polite" aria-relevant="all">
        % for index, epResult in enumerate(releases_in_pp):
           % if epResult['status'] != 'snatched':
               <% continue %>
           % endif
            <tr class="snatched" role="row" release_id=${index}>
                <td class="tvShow" align="left">
                    <app-link href="home/displayShow?indexername=${epResult['indexername']}&seriesid=${epResult['seriesid']}#season-${epResult['season']}">${epResult['show_name']}</app-link>
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
                <span class="tvShow" datetime="${epResult['date'].isoformat('T')}">
                        ${epResult['age']}${epResult['age_unit']}
                </span>
                </td>
                <td class="col-search" align="center">
                    <app-link class="epSubtitlesSearchPP" release_id=${index} href="home/manual_search_subtitles?release_id=${index}"><img src="images/closed_captioning.png" height="16" alt="search subtitles" title="Search Subtitles" /></app-link>
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
    <input id="submit" class="btn-medusa" type="submit" value="Run Manual Post-Process" />
</form>
</div><!-- Releases missed subtitles -->
</div><!-- col -->
</div><!-- row -->
<br>
<div class="row ${' hidden' if app.TORRENT_SEED_LOCATION else ''}">
<div class="col-md-12">
<h3 style="display: inline;">Releases waiting minimum ratio</h3>
<div class="horizontal-scroll">
    <table id="releasesPP-downloaded" class="defaultTable" cellspacing="1" border="0" cellpadding="0">
        <thead aria-live="polite" aria-relevant="all">
            <tr>
                <th>Show</th>
                <th>Episode</th>
                <th>Release</th>
            </tr>
        </thead>
        <tbody aria-live="polite" aria-relevant="all">
        % for index, epResult in enumerate(releases_in_pp):
           % if epResult['status'] != 'downloaded':
               <% continue %>
           % endif
            <tr class="downloaded" role="row" release_id=${index}>
                <td class="tvShow" align="left">
                    <app-link href="home/displayShow?indexername=${epResult['indexername']}&seriesid=${epResult['seriesid']}#season-${epResult['season']}">${epResult['show_name']}</app-link>
                </td>
                <td class="tvShow" align="center">
                        ${episode_num(epResult['season'], epResult['episode'])}
                </td>
                <td class="tvShow" align="left">
                    <span class="break-word" title=${os.path.relpath(epResult['release'], app.TV_DOWNLOAD_DIR)}>
                        ${os.path.basename(epResult['release'])}
                    </span>
                </td>
            </tr>
        % endfor
        </tbody>
    </table>
</div><!-- Releases waiting minimum ratio -->
</div><!-- col -->
</div><!-- row -->
</%block>

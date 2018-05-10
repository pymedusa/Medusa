<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import app
    import datetime
    from medusa.common import SKIPPED, WANTED, UNAIRED, ARCHIVED, IGNORED, SNATCHED, SNATCHED_PROPER, SNATCHED_BEST, FAILED
    from medusa.common import Quality, qualityPresets, statusStrings, qualityPresetStrings, cpu_presets
%>
<%block name="scripts">
<script>
window.app = {};
const startVue = () => {
    window.app = new Vue({
        el: '#vue-wrap',
        metaInfo: {
            title: 'Manage Searches'
        },
        data() {
            return {
                header: 'Manage Searches'
            };
        }
    });
};
</script>
</%block>
<%block name="content">
<div id="content800">
<h1 class="header">{{header}}</h1>
<div id="summary2" class="align-left">

<h3>Backlog Search:</h3>
<h5>Note: Limited by backlog days setting: last ${app.BACKLOG_DAYS} days</h5>
<app-link class="btn-medusa" href="manage/manageSearches/forceBacklog"><i class="icon-exclamation-sign"></i> Force</app-link>
<app-link class="btn-medusa" href="manage/manageSearches/pauseBacklog?paused=${('1', '0')[bool(backlogPaused)]}"><i class="icon-${('paused', 'play')[bool(backlogPaused)]}"></i> ${('pause', 'Unpause')[bool(backlogPaused)]}</app-link>
% if not backlogRunning:
    Not in progress<br>
% else:
    ${'Paused:' if backlogPaused else ''}
    Currently running<br>
% endif

<h3>Daily Search:</h3>
<app-link class="btn-medusa" href="manage/manageSearches/forceSearch"><i class="icon-exclamation-sign"></i> Force</app-link>
${('Not in progress', 'In Progress')[dailySearchStatus]}<br>

<h3>Propers Search:</h3>
<app-link class="btn-medusa ${('disabled', '')[bool(app.DOWNLOAD_PROPERS)]}" href="manage/manageSearches/forceFindPropers"><i class="icon-exclamation-sign"></i> Force</app-link>
% if not app.DOWNLOAD_PROPERS:
    Propers search disabled <br>
% elif not findPropersStatus:
    Not in progress<br>
% else:
    In Progress<br>
% endif

<h3>Subtitle Search:</h3>
<app-link class="btn-medusa ${('disabled', '')[bool(app.USE_SUBTITLES)]}" href="manage/manageSearches/forceSubtitlesFinder"><i class="icon-exclamation-sign"></i> Force</app-link>
% if not app.USE_SUBTITLES:
    Subtitle search disabled <br>
% elif not subtitlesFinderStatus:
    Not in progress<br>
% else:
    In Progress<br>
% endif

<h3>Scene Exceptions:</h3>
<app-link class="btn-medusa disabled forceSceneExceptionRefresh"><i class="icon-exclamation-sign"></i> Force</app-link>
<span id="sceneExceptionStatus"></span>

<h3>Search Queue:</h3>
<ul class='simpleList'>
    <li>Backlog: <i>${searchQueueLength['backlog']} pending items</i>
    <li>Daily: <i>${searchQueueLength['daily']} pending items</i>
    <li>Forced: <i>${forcedSearchQueueLength['forced_search']} pending items</i>
    <li>Manual: <i>${forcedSearchQueueLength['manual_search']} pending items</i>
    <li>Failed: <i>${forcedSearchQueueLength['failed']} pending items</i>
</ul>
</div>
</div>
</%block>

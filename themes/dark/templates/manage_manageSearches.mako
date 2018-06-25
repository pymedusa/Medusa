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
        store,
        el: '#vue-wrap',
        metaInfo: {
            title: 'Manage Searches'
        },
        data() {
            return {
                header: 'Manage Searches'
            };
        },
        mounted() {
            /**
             * Get total number current scene exceptions per source. Will request medusa, xem and anidb name exceptions.
             * @param exceptions - A list of exception types with their last_updates.
             */
            const updateExceptionTable = function(exceptions) {
                const status = $('#sceneExceptionStatus');

                const medusaException = exceptions.data.filter(obj => {
                    return obj.id === 'local';
                });
                const cusExceptionDate = new Date(medusaException[0].lastRefresh * 1000).toLocaleDateString();

                const xemException = exceptions.data.filter(obj => {
                    return obj.id === 'xem';
                });
                const xemExceptionDate = new Date(xemException[0].lastRefresh * 1000).toLocaleDateString();

                const anidbException = exceptions.data.filter(obj => {
                    return obj.id === 'anidb';
                });
                const anidbExceptionDate = new Date(anidbException[0].lastRefresh * 1000).toLocaleDateString();

                const table = $('<ul class="simpleList"></ul>')
                    .append(
                        '<li>' +
                        '<a href="' + MEDUSA.config.anonRedirect +
                        'https://github.com/pymedusa/Medusa/wiki/Scene-exceptions-and-numbering">' +
                        'Last updated medusa\'s exceptions</a> ' +
                            cusExceptionDate
                    )
                    .append(
                        '<li>' +
                        '<a href="' + MEDUSA.config.anonRedirect +
                        'http://thexem.de">' +
                        'Last updated xem exceptions</a> ' +
                            xemExceptionDate
                    )
                    .append(
                        '<li>Last updated anidb exceptions ' +
                            anidbExceptionDate
                    );

                status.append(table);
                $('.forceSceneExceptionRefresh').removeClass('disabled');
            };

            /**
             * Update an element with a spinner gif and a descriptive message.
             * @param spinnerContainer - An element we can use to add the spinner and message to.
             * @param message - A string with the message to display behind the spinner.
             * @param showSpinner - A boolean to show or not show the spinner (gif).
             */
            const updateSpinner = function(spinnerContainer, message, showSpinner) {
                if (showSpinner) {
                    message = '<img id="searchingAnim" src="images/loading32' +
                        MEDUSA.config.themeSpinner + '.gif" height="16" width="16" />&nbsp;' + message;
                }
                $(spinnerContainer).empty().append(message);
            };

            /**
             * Trigger the force refresh of all the exception types.
             */
            $('.forceSceneExceptionRefresh').on('click', () => {
                const status = $('#sceneExceptionStatus');
                // Start a spinner.
                updateSpinner(status, 'Retrieving scene exceptions...', true);

                api.post('alias-source/all/operation', { type: 'REFRESH' }, {
                    timeout: 60000
                }).then(response => {
                    status[0].innerHTML = '';
                    status.append(
                        $('<span></span>').text(response.data.result)
                    );

                    api.get('alias-source').then(response => {
                        updateExceptionTable(response);
                        $('.forceSceneExceptionRefresh').addClass('disabled');
                    }).catch(err => {
                        log.error('Trying to get scene exceptions failed with error: ' + err);
                        updateSpinner(status, 'Trying to get scene exceptions failed with error: ' + err, false);
                    });
                    updateSpinner(status, 'Finished updating scene exceptions.', false);
                }).catch(err => {
                    log.error('Trying to update scene exceptions failed with error: ' + err);
                    updateSpinner(status, 'Trying to update scene exceptions failed with error: ' + err, false);
                });
            });

            // Initially load the exception types last updates on page load.
            api.get('alias-source').then(response => {
                updateExceptionTable(response);
            }).catch(err => {
                log.error('Trying to get scene exceptions failed with error: ' + err);
            });
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

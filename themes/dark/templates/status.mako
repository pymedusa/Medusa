<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import app
    from medusa import helpers
    from medusa.show_queue import ShowQueueActions
    from medusa.helper.common import dateTimeFormat
    from six import iteritems
%>
<%block name="scripts">
<script type="text/x-template" id="status-template">
<%
    schedulerList = {
        'Daily Search': 'daily_search_scheduler',
        'Backlog': 'backlog_search_scheduler',
        'Show Update': 'show_update_scheduler',
        'Version Check': 'version_check_scheduler',
        'Show Queue': 'show_queue_scheduler',
        'Search Queue': 'search_queue_scheduler',
        'Proper Finder': 'proper_finder_scheduler',
        'Post-Processor': 'post_processor_scheduler',
        'Subtitles Finder': 'subtitles_finder_scheduler',
        'Trakt Checker': 'trakt_checker_scheduler',
        'Torrent Checker': 'torrent_checker_scheduler',
    }
%>
<div>
    <backstretch :slug="config.randomShowSlug"></backstretch>

    <div id="config-content">
        <h2 class="header">Scheduler</h2>
        <table id="schedulerStatusTable" class="tablesorter ${'fanartOpacity' if app.FANART_BACKGROUND else ''}" width="100%">
            <thead>
                <tr>
                    <th>Scheduler</th>
                    <th>Alive</th>
                    <th>Enabled</th>
                    <th>Active</th>
                    <th>Start Time</th>
                    <th>Cycle Time</th>
                    <th>Next Run</th>
                    <th>Last Run</th>
                    <th>Silent</th>
                </tr>
            </thead>
            <tbody>
                % for schedulerName, scheduler in iteritems(schedulerList):
                <% service = getattr(app, scheduler) %>
            <tr>
                <td>${schedulerName}</td>
                % if service.is_alive():
                <td style="background-color:rgb(0, 128, 0);">${service.is_alive()}</td>
                % else:
                <td style="background-color:rgb(255, 0, 0);">${service.is_alive()}</td>
                % endif
                % if scheduler == 'backlog_search_scheduler':
                    <% searchQueue = getattr(app, 'search_queue_scheduler') %>
                    <% BLSpaused = searchQueue.action.is_backlog_paused() %>
                    <% del searchQueue %>
                    % if BLSpaused:
                <td>Paused</td>
                    % else:
                <td>${service.enable}</td>
                    % endif
                % else:
                <td>${service.enable}</td>
                % endif
                % if scheduler == 'backlog_search_scheduler':
                    <% searchQueue = getattr(app, 'search_queue_scheduler') %>
                    <% BLSinProgress = searchQueue.action.is_backlog_in_progress() %>
                    <% del searchQueue %>
                    % if BLSinProgress:
                <td>True</td>
                    % else:
                        % try:
                        <% amActive = service.action.amActive %>
                <td>${amActive}</td>
                        % except Exception:
                <td>N/A</td>
                        % endtry
                    % endif
                % else:
                    % try:
                    <% amActive = service.action.amActive %>
                <td>${amActive}</td>
                    % except Exception:
                <td>N/A</td>
                    % endtry
                % endif
                % if service.start_time:
                <td align="right">${service.start_time}</td>
                % else:
                <td align="right"></td>
                % endif
                <% cycleTime = service.cycleTime.seconds %>
                <td align="right" data-seconds="${cycleTime}">${helpers.pretty_time_delta(cycleTime)}</td>
                % if service.enable:
                    <% timeLeft = service.timeLeft().seconds %>
                <td align="right" data-seconds="${timeLeft}">${helpers.pretty_time_delta(timeLeft)}</td>
                % else:
                <td></td>
                % endif
                <td>${service.lastRun.strftime(dateTimeFormat)}</td>
                <td>${service.silent}</td>
            </tr>
            <% del service %>
            % endfor
        </tbody>
        </table>
        <h2 class="header">Show Queue</h2>
        <table id="queueStatusTable" class="tablesorter ${'fanartOpacity' if app.FANART_BACKGROUND else ''}" width="100%">
            <thead>
                <tr>
                    <th>Show id</th>
                    <th>Show name</th>
                    <th>In Progress</th>
                    <th>Priority</th>
                    <th>Added</th>
                    <th>Queue type</th>
                </tr>
            </thead>
            <tbody>
                % if app.show_queue_scheduler.action.currentItem is not None:
                    <tr>
                        % try:
                            <% showindexerid = app.show_queue_scheduler.action.currentItem.show.indexerid %>
                            <td>${showindexerid}</td>
                        % except Exception:
                            <td></td>
                        % endtry
                        % try:
                            <% showname = app.show_queue_scheduler.action.currentItem.show.name %>
                            <td>${showname}</td>
                        % except Exception:
                            % if app.show_queue_scheduler.action.currentItem.action_id == ShowQueueActions.ADD:
                                <td>${app.show_queue_scheduler.action.currentItem.show_dir}</td>
                            % else:
                                <td></td>
                            % endif
                        % endtry
                        <td>${app.show_queue_scheduler.action.currentItem.inProgress}</td>
                        % if app.show_queue_scheduler.action.currentItem.priority == 10:
                            <td>LOW</td>
                        % elif app.show_queue_scheduler.action.currentItem.priority == 20:
                            <td>NORMAL</td>
                        % elif app.show_queue_scheduler.action.currentItem.priority == 30:
                            <td>HIGH</td>
                        % else:
                            <td>app.show_queue_scheduler.action.currentItem.priority</td>
                        % endif
                        <td>${app.show_queue_scheduler.action.currentItem.added.strftime(dateTimeFormat)}</td>
                        <td>${ShowQueueActions.names[app.show_queue_scheduler.action.currentItem.action_id]}</td>
                    </tr>
                % endif
                % for item in app.show_queue_scheduler.action.queue:
                    <tr>
                        % try:
                            <% showindexerid = item.show.indexerid %>
                            <td>${showindexerid}</td>
                        % except Exception:
                            <td></td>
                        % endtry
                        % try:
                            <% showname = item.show.name %>
                            <td>${showname}</td>
                        % except Exception:
                            % if item.action_id == ShowQueueActions.ADD:
                                <td>${item.show_dir}</td>
                            % else:
                                <td></td>
                            % endif
                        % endtry
                        <td>${item.inProgress}</td>
                        % if item.priority == 10:
                            <td>LOW</td>
                        % elif item.priority == 20:
                            <td>NORMAL</td>
                        % elif item.priority == 30:
                            <td>HIGH</td>
                        % else:
                            <td>${item.priority}</td>
                        % endif
                        <td>${item.added.strftime(dateTimeFormat)}</td>
                        <td>${ShowQueueActions.names[item.action_id]}</td>
                    </tr>
                % endfor
            </tbody>
        </table>
        <h2 class="header">Disk Space</h2>
        <table id="DFStatusTable" class="tablesorter ${'fanartOpacity' if app.FANART_BACKGROUND else ''}" width="50%">
            <thead>
                <tr>
                    <th>Type</th>
                    <th>Location</th>
                    <th>Free space</th>
                </tr>
            </thead>
            <tbody>
                % if app.TV_DOWNLOAD_DIR:
                <tr>
                    <td>TV Download Directory</td>
                    <td>${app.TV_DOWNLOAD_DIR}</td>
                    % if tvdirFree is not False:
                    <td align="middle">${tvdirFree}</td>
                    % else:
                    <td align="middle"><i>Missing</i></td>
                    % endif
                </tr>
                % endif
                % for cur_index, cur_dir in enumerate(rootDir):
                <tr>
                    % if cur_index == 0:
                    <td rowspan="${len(rootDir)}">Media Root Directories</td>
                    % endif
                    <td>${cur_dir}</td>
                    % if rootDir[cur_dir] is not False:
                        <td align="middle">${rootDir[cur_dir]}</td>
                    % else:
                        <td align="middle"><i>Missing</i></td>
                    % endif
                </tr>
                % endfor
            </tbody>
        </table>
    </div>
</div>
</script>
<script>
window.app = new Vue({
    el: '#vue-wrap',
    store,
    router,
    data() {
        return {
            // This loads status.vue
            pageComponent: 'status'
        }
    }
});
</script>
</%block>

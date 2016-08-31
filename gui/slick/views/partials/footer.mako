<%!
    from datetime import datetime
    from time import time
    from contextlib2 import suppress
    import os
    import re
    from sickbeard import (
        dailySearchScheduler as daily_search_scheduler,
        backlogSearchScheduler as backlog_search_scheduler,
        BRANCH, DATE_PRESET, TIME_PRESET
    )
    from sickrage.helper.common import pretty_file_size
    from sickrage.show.Show import Show

    mem_usage = None
    with suppress(ImportError):
        from psutil import Process
        from os import getpid
        mem_usage = 'psutil'

    with suppress(ImportError):
        if not mem_usage:
            import resource # resource module is unix only
            mem_usage = 'resource'

    stats = Show.overall_stats()
    ep_downloaded = stats['episodes']['downloaded']
    ep_snatched = stats['episodes']['snatched']
    ep_total = stats['episodes']['total']
    ep_percentage = '' if ep_total == 0 else '(<span class="footerhighlight">%s%%</span>)' % re.sub(r'(\d+)(\.\d)\d+', r'\1\2', str((float(ep_downloaded)/float(ep_total))*100))
%>
<!-- BEGIN FOOTER -->
% if loggedIn:
    <footer>
        <div class="footer clearfix">
            <span class="footerhighlight">${stats['shows']['total']}</span> Shows (<span class="footerhighlight">${stats['shows']['active']}</span> Active)
            | <span class="footerhighlight">${ep_downloaded}</span>
            % if ep_snatched:
            <span class="footerhighlight"><a href="manage/episodeStatuses?whichStatus=2" title="View overview of snatched episodes">+${ep_snatched}</a></span> Snatched
            % endif
            &nbsp;/&nbsp;<span class="footerhighlight">${ep_total}</span> Episodes Downloaded ${ep_percentage}
            | Daily Search: <span class="footerhighlight">${str(daily_search_scheduler.timeLeft()).split('.')[0]}</span>
            | Backlog Search: <span class="footerhighlight">${str(backlog_search_scheduler.timeLeft()).split('.')[0]}</span>
            <div>
            % if mem_usage:
                Memory used: <span class="footerhighlight">
                % if mem_usage == 'resource':
                    ${pretty_file_size(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)}
                % else:
                    ${pretty_file_size(Process(getpid()).memory_info().rss)}
                % endif
                </span> |
            % endif
                Load time: <span class="footerhighlight">${"%.4f" % (time() - sbStartTime)}s</span> / Mako: <span class="footerhighlight">${"%.4f" % (time() - makoStartTime)}s</span> |
                Branch: <span class="footerhighlight">${BRANCH}</span> |
                Now: <span class="footerhighlight">${datetime.now().strftime(DATE_PRESET+" "+TIME_PRESET)}</span>
            </div>
        </div>
    </footer>
    <script type="text/javascript" src="js/vender.min.js?${sbPID}"></script>
    <script type="text/javascript" src="js/lib/jquery.cookiejar.js?${sbPID}"></script>
    <script type="text/javascript" src="js/lib/jquery.form.min.js?${sbPID}"></script>
    <script type="text/javascript" src="js/lib/jquery.json-2.2.min.js?${sbPID}"></script>
    <script type="text/javascript" src="js/lib/jquery.selectboxes.min.js?${sbPID}"></script>
    <script type="text/javascript" src="js/lib/formwizard.js?${sbPID}"></script>
    <script type="text/javascript" src="js/parsers.js?${sbPID}"></script>
    <script type="text/javascript" src="js/root-dirs.js?${sbPID}"></script>
    <script type="text/javascript" src="js/core.js?${sbPID}"></script>

    <script type="text/javascript" src="js/config/backup-restore.js?${sbPID}"></script>
    <script type="text/javascript" src="js/config/index.js?${sbPID}"></script>
    <script type="text/javascript" src="js/config/init.js?${sbPID}"></script>
    <script type="text/javascript" src="js/config/notifications.js?${sbPID}"></script>
    <script type="text/javascript" src="js/config/post-processing.js?${sbPID}"></script>
    <script type="text/javascript" src="js/config/search.js?${sbPID}"></script>
    <script type="text/javascript" src="js/config/subtitles.js?${sbPID}"></script>

    <script type="text/javascript" src="js/add-shows/add-existing-show.js?${sbPID}"></script>
    <script type="text/javascript" src="js/add-shows/init.js?${sbPID}"></script>
    <script type="text/javascript" src="js/add-shows/new-show.js?${sbPID}"></script>
    <script type="text/javascript" src="js/add-shows/popular-shows.js?${sbPID}"></script>
    <script type="text/javascript" src="js/add-shows/recommended-shows.js?${sbPID}"></script>
    <script type="text/javascript" src="js/add-shows/trending-shows.js?${sbPID}"></script>

    <script type="text/javascript" src="js/schedule/index.js?${sbPID}"></script>

    <script type="text/javascript" src="js/common/init.js?${sbPID}"></script>

    <script type="text/javascript" src="js/home/display-show.js?${sbPID}"></script>
    <script type="text/javascript" src="js/home/edit-show.js?${sbPID}"></script>
    <script type="text/javascript" src="js/home/index.js?${sbPID}"></script>
    <script type="text/javascript" src="js/home/post-process.js?${sbPID}"></script>
    <script type="text/javascript" src="js/home/restart.js?${sbPID}"></script>
    <script type="text/javascript" src="js/home/snatch-selection.js?${sbPID}"></script>
    <script type="text/javascript" src="js/home/status.js?${sbPID}"></script>

    <script type="text/javascript" src="js/manage/backlog-overview.js?${sbPID}"></script>
    <script type="text/javascript" src="js/manage/episode-statuses.js?${sbPID}"></script>
    <script type="text/javascript" src="js/manage/failed-downloads.js?${sbPID}"></script>
    <script type="text/javascript" src="js/manage/index.js?${sbPID}"></script>
    <script type="text/javascript" src="js/manage/init.js?${sbPID}"></script>
    <script type="text/javascript" src="js/manage/mass-edit.js?${sbPID}"></script>
    <script type="text/javascript" src="js/manage/subtitle-missed.js?${sbPID}"></script>

    <script type="text/javascript" src="js/lib/jquery.scrolltopcontrol-1.1.js?${sbPID}"></script>
    <script type="text/javascript" src="js/browser.js?${sbPID}"></script>
    <script type="text/javascript" src="js/ajax-notifications.js?${sbPID}"></script>
% endif
<!-- END FOOTER -->

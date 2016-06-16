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
        mem_usage = Process(getpid()).memory_info().rss

    with suppress(ImportError):
        if not mem_usage:
            import resource # resource module is unix only
            mem_usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

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
            <span class="footerhighlight"><a href="/manage/episodeStatuses?whichStatus=2" title="View overview of snatched episodes">+${ep_snatched}</a></span> Snatched
            % endif
            &nbsp;/&nbsp;<span class="footerhighlight">${ep_total}</span> Episodes Downloaded ${ep_percentage}
            | Daily Search: <span class="footerhighlight">${str(daily_search_scheduler.timeLeft()).split('.')[0]}</span>
            | Backlog Search: <span class="footerhighlight">${str(backlog_search_scheduler.timeLeft()).split('.')[0]}</span>
            <div>
                % if mem_usage:
                Memory used: <span class="footerhighlight">${pretty_file_size(mem_usage)}</span> |
                % endif
                Load time: <span class="footerhighlight">${"%.4f" % (time() - sbStartTime)}s</span> / Mako: <span class="footerhighlight">${"%.4f" % (time() - makoStartTime)}s</span> |
                Branch: <span class="footerhighlight">${BRANCH}</span> |
                Now: <span class="footerhighlight">${datetime.now().strftime(DATE_PRESET+" "+TIME_PRESET)}</span>
            </div>
        </div>
    </footer>
    <script type="text/javascript" src="/js/vender.min.js?${sbPID}"></script>
    <script type="text/javascript" src="/js/lib/jquery.cookiejar.js?${sbPID}"></script>
    <script type="text/javascript" src="/js/lib/jquery.form.min.js?${sbPID}"></script>
    <script type="text/javascript" src="/js/lib/jquery.json-2.2.min.js?${sbPID}"></script>
    <script type="text/javascript" src="/js/lib/jquery.selectboxes.min.js?${sbPID}"></script>
    <script type="text/javascript" src="/js/lib/formwizard.js?${sbPID}"></script>
    <script type="text/javascript" src="/js/parsers.js?${sbPID}"></script>
    <script type="text/javascript" src="/js/rootDirs.js?${sbPID}"></script>
    <script type="text/javascript" src="/js/core.js?${sbPID}"></script>
    <script type="text/javascript" src="/js/lib/jquery.scrolltopcontrol-1.1.js?${sbPID}"></script>
    <script type="text/javascript" src="/js/browser.js?${sbPID}"></script>
    <script type="text/javascript" src="/js/ajaxNotifications.js?${sbPID}"></script>
% endif
<!-- END FOOTER -->

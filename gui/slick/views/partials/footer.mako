<%!
    import datetime
    import re
    import sickbeard
    from sickrage.helper.common import pretty_file_size
    from sickrage.show.Show import Show
    from time import time

    # resource module is unix only
    has_resource_module = True
    try:
        import resource
    except ImportError:
        has_resource_module = False
%>
<%
    srRoot = sickbeard.WEB_ROOT
%>
% if loggedIn:
    <footer>
        <div class="footer clearfix">
        <%
            stats = Show.overall_stats()
            ep_downloaded = stats['episodes']['downloaded']
            ep_snatched = stats['episodes']['snatched']
            ep_total = stats['episodes']['total']
            ep_percentage = '' if ep_total == 0 else '(<span class="footerhighlight">%s%%</span>)' % re.sub(r'(\d+)(\.\d)\d+', r'\1\2', str((float(ep_downloaded)/float(ep_total))*100))
        %>
            <span class="footerhighlight">${stats['shows']['total']}</span> Shows (<span class="footerhighlight">${stats['shows']['active']}</span> Active)
            | <span class="footerhighlight">${ep_downloaded}</span>

            % if ep_snatched:
            <span class="footerhighlight"><a href="/manage/episodeStatuses?whichStatus=2" title="View overview of snatched episodes">+${ep_snatched}</a></span> Snatched
            % endif

            &nbsp;/&nbsp;<span class="footerhighlight">${ep_total}</span> Episodes Downloaded ${ep_percentage}
            | Daily Search: <span class="footerhighlight">${str(sickbeard.dailySearchScheduler.timeLeft()).split('.')[0]}</span>
            | Backlog Search: <span class="footerhighlight">${str(sickbeard.backlogSearchScheduler.timeLeft()).split('.')[0]}</span>

            <div>
                % if has_resource_module:
                Memory used: <span class="footerhighlight">${pretty_file_size(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)}</span> |
                % endif
                Load time: <span class="footerhighlight">${"%.4f" % (time() - sbStartTime)}s</span> / Mako: <span class="footerhighlight">${"%.4f" % (time() - makoStartTime)}s</span> |
                Branch: <span class="footerhighlight">${sickbeard.BRANCH}</span> |
                Now: <span class="footerhighlight">${datetime.datetime.now().strftime(sickbeard.DATE_PRESET+" "+sickbeard.TIME_PRESET)}</span>
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

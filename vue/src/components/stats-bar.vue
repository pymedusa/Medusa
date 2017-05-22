<template>
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
                Branch: <span class="footerhighlight">{{config.branch}}</span> |
                Now: <span class="footerhighlight">${datetime.now().strftime(DATE_PRESET+" "+TIME_PRESET)}</span>
            </div>
        </div>
    </footer>
</template>

<script>
import {mapGetters} from 'vuex';

export default {
    name: 'stats-bar',
    computed: {
        ...mapGetters([
            // 'stats',
            'config'
        ])
    }
};
</script>

<%inherit file="/layouts/main.mako"/>
<%!
    import json
    from medusa import app
    from medusa.logger import LOGGING_LEVELS
    from random import choice
%>
<%block name="scripts">
<script>
const sortObject = list => {
    const sortable = [];
    for (let key in list) {
        sortable.push([key, list[key]]);
    }

    sortable.sort((a, b) => a[1] > b[1] ? -1 : (a[1] < b[1] ? 1 : 0));

    const orderedList = {};
    for (let i = 0; i < sortable.length; i++) {
        orderedList[sortable[i][0]] = sortable[i][1];
    }

    return orderedList;
};
window.app = {};
const startVue = () => {
    window.app = new Vue({
        el: '#vue-wrap',
        metaInfo: {
            title: 'Logs'
        },
        data() {
            const filters = sortObject(JSON.parse('${json.dumps(log_name_filters)}'));
            const noFilter = filters['null'];
            filters['None'] = noFilter;
            delete filters['null'];

            return {
                header: 'Log File',
                fanartOpacity: '${app.FANART_BACKGROUND}' === 'True',
                // pick a random series to show as background
                <% random_show = choice(app.showList) if app.showList else None %>
                randomShow: {indexerId: '${getattr(random_show, "indexerid", "")}', slug: '${getattr(random_show, "slug", "")}'},
                log: {
                    minLevel: Number('${min_level}'),
                    filter: '${log_filter}',
                    period: '${log_period}',
                    search: '${log_search}' === 'None' ? '' : '${log_search}'
                },
                logs: ${json.dumps(log_lines)},
                disabled: false,
                filters,
                periods: {
                    all: 'All',
                    one_day: 'Last 24h',
                    three_days: 'Last 3 days',
                    one_week: 'Last 7 days'
                },
                <%
                    levels = LOGGING_LEVELS.keys()
                    levels.sort(key=lambda x: LOGGING_LEVELS[x])
                    if not app.DEBUG:
                        levels.remove('DEBUG')
                    if not app.DBDEBUG:
                        levels.remove('DB')
                %>
                LoggingLevelLabels: JSON.parse('${json.dumps(LOGGING_LEVELS)}'),
                loggingLevels: JSON.parse('${json.dumps(levels)}')
            };
        },
        computed: {
            params() {
                const { log } = this;
                const { minLevel, filter, period, search } = log;

                return $.param({
                    min_level: minLevel,
                    log_filter: filter,
                    log_period: period,
                    log_search: search
                });
            }
        },
        methods: {
            viewLogAsText() {
                const { params } = this;

                const win = window.open('errorlogs/viewlog/?' + params + '&text_view=1', '_blank');
                win.focus();
            },
            async getLogs() {
                const { params } = this;

                this.disabled = true;

                const data = await $.get('errorlogs/viewlog/?' + params);
                history.pushState('data', '', 'errorlogs/viewlog/?' + params);

                this.logs = $(data).find('pre').html();
                this.disabled = false;
            }
        },
        watch: {
            disabled(disabled) {
                document.body.style.cursor = disabled ? 'wait' : 'default';
            },
            log: {
                async handler() {
                    await this.getLogs();
                },
                deep: true
            }
        }
    });
};
</script>
</%block>
<%block name="css">
<style>
pre {
  overflow: auto;
  word-wrap: normal;
  white-space: pre;
}
.notepad {
    top: 10px;
}
.notepad:hover {
    cursor: pointer;
}
</style>
</%block>
<%block name="content">
<input type="hidden" id="series-id" :value="randomShow.indexerId" />
<input type="hidden" id="series-slug" :value="randomShow.slug" />

<div class="row">
    <div class="col-md-12">
        <h1 class="header">{{header}}</h1>
    </div>
    <div class="col-md-12 pull-right ">
        <div class="logging-filter-controll pull-right">
            <!-- Select Loglevel -->
            <div class="show-option">
                <span>Logging level:
                    <select v-model.number="log.minLevel" name="min_level" id="min_level" class="form-control form-control-inline input-sm">
                        <option v-for="level in loggingLevels" :value="LoggingLevelLabels[level]" selected="log.minLevel === LoggingLevelLabels[level]">{{level.toLowerCase().replace(/^[a-z]/g, txt => txt.toUpperCase())}}</option>
                    </select>
                </span>
            </div>
            <div class="show-option">
                <!-- Filter log -->
                <span>Filter log by:
                    <select v-model="log.filter" name="log_filter" id="log_filter" class="form-control form-control-inline input-sm">
                        <option v-for="filter in Object.keys(filters).slice().reverse()" :value="filter" v-html="filters[filter]" selected="log.filter === filter"></option>
                    </select>
                </span>
            </div>
            <div class="show-option">
                <!-- Select period -->
                <span>Period:
                    <select v-model="log.period" name="log_period" id="log_period" class="form-control form-control-inline input-sm">
                        <option v-for="(title, period) in periods" :value="period" selected="log.period == period">{{title}}</option>
                    </select>
                </span>
            </div>
            <div class="show-option">
                <!-- Search Log -->
                <span>Search log by:
                    <input v-model="log.search" type="text" name="log_search" placeholder="clear to reset" id="log_search" class="form-control form-control-inline input-sm"/>
                </span>
            </div>
        </div>
    </div> <!-- End form group -->
</div> <!-- row -->
<div class="row">
    <div :class="{fanartOpacity: fanartOpacity}" class="col-md-12">
        <div class="notepad"><span @click="viewLogAsText"><img src="images/notepad.png"/></span></div>
        <pre v-html="logs"></pre>
    </div>
</div>
</%block>

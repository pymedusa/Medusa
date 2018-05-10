<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import app
    from medusa import classes
    from medusa.logger import LOGGING_LEVELS
    from random import choice
%>
<%block name="scripts">
<script>
window.app = {};
const startVue = () => {
    window.app = new Vue({
        el: '#vue-wrap',
        metaInfo: {
            title: 'Logs'
        },
        data() {
            return {
                header: 'Log File'
            };
        },
        mounted() {
            function getParams() {
                return $.param({
                    min_level: $('select[name=min_level]').val(), // eslint-disable-line camelcase
                    log_filter: $('select[name=log_filter]').val(), // eslint-disable-line camelcase
                    log_period: $('select[name=log_period]').val(), // eslint-disable-line camelcase
                    log_search: $('#log_search').val() // eslint-disable-line camelcase
                });
            }

            $('#min_level,#log_filter,#log_search,#log_period').on('keyup change', _.debounce(() => {
                const params = getParams();
                $('#min_level').prop('disabled', true);
                $('#log_filter').prop('disabled', true);
                $('#log_period').prop('disabled', true);
                document.body.style.cursor = 'wait';

                $.get('errorlogs/viewlog/?' + params, data => {
                    history.pushState('data', '', 'errorlogs/viewlog/?' + params);
                    $('pre').html($(data).find('pre').html());
                    $('#min_level').prop('disabled', false);
                    $('#log_filter').prop('disabled', false);
                    $('#log_period').prop('disabled', false);
                    document.body.style.cursor = 'default';
                });
            }, 500));

            $(document.body).on('click', '#viewlog-text-view', e => {
                e.preventDefault();
                const params = getParams();
                const win = window.open('errorlogs/viewlog/?' + params + '&text_view=1', '_blank');
                win.focus();
            });
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
</style>
</%block>
<%block name="content">

<%
    # pick a random series to show as background
    random_show = choice(app.showList) if app.showList else None
%>
<input type="hidden" id="series-id" value="${getattr(random_show, 'indexerid', '')}" />
<input type="hidden" id="series-slug" value="${getattr(random_show, 'slug', '')}" />

<div class="row">
        <div class="col-md-12">
            <h1 class="header">{{header}}</h1>
        </div>
        <div class="col-md-12 pull-right ">
            <div class="logging-filter-controll pull-right">
                <!-- Select Loglevel -->
                <div class="show-option">
                    <span>Logging level:
                        <select name="min_level" id="min_level" class="form-control form-control-inline input-sm">
                            <%
                                levels = LOGGING_LEVELS.keys()
                                levels.sort(key=lambda x: LOGGING_LEVELS[x])
                                if not app.DEBUG:
                                    levels.remove('DEBUG')
                                if not app.DBDEBUG:
                                    levels.remove('DB')
                            %>
                        % for level in levels:
                            <option value="${LOGGING_LEVELS[level]}" ${('', 'selected="selected"')[min_level == LOGGING_LEVELS[level]]}>${level.title()}</option>
                        % endfor
                        </select>
                    </span>
                </div>
                <div class="show-option">
                    <!-- Filter log -->
                    <span>Filter log by:
                        <select name="log_filter" id="log_filter" class="form-control form-control-inline input-sm">
                        % for log_name_filter in sorted(log_name_filters):
                            <option value="${log_name_filter}" ${'selected="selected"' if log_filter == log_name_filter else ''}>${log_name_filters[log_name_filter]}</option>
                        % endfor
                        </select>
                    </span>
                </div>
                <div class="show-option">
                    <!-- Select period -->
                    <span>Period:
                        <select name="log_period" id="log_period" class="form-control form-control-inline input-sm">
                            <option value="all" ${'selected="selected"' if log_period == 'all' else ''}>All</option>
                            <option value="one_day" ${'selected="selected"' if log_period == 'one_day' else ''}>Last 24h</option>
                            <option value="three_days" ${'selected="selected"' if log_period == 'three_days' else ''}>Last 3 days</option>
                            <option value="one_week" ${'selected="selected"' if log_period == 'one_week' else ''}>Last 7 days</option>
                        </select>
                    </span>
                </div>
                <div class="show-option">
                    <!-- Search Log -->
                    <span>Search log by:
                        <input type="text" name="log_search" placeholder="clear to reset" id="log_search" value="${('', log_search)[bool(log_search)]}" class="form-control form-control-inline input-sm"/>
                    </span>
                </div>
            </div>
        </div> <!-- End form group -->
</div> <!-- row -->
<div class="row">
    <div class="col-md-12 ${'fanartOpacity' if app.FANART_BACKGROUND else ''}">
        <pre><div class="notepad"><app-link id="viewlog-text-view" href="errorlogs/viewlog/?text_view=1"><img src="images/notepad.png"/></app-link></div>${log_lines}</pre>
    </div>
</div>
</%block>

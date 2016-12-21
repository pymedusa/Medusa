<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import app
    from medusa import classes
    from medusa.logger import LOGGING_LEVELS
%>
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
<div class="row wide">
    <div class="col-md-12">
        % if not header is UNDEFINED:
            <h1 class="header">${header}</h1>
        % else:
            <h1 class="title">${title}</h1>
        % endif
    </div>
</div>
<div class="row wide">
    <div class="col-md-12">
        <div class="logging-filter-controll pull-right">
            <!-- Select Loglevel -->
            <div class="show-option pull-right">
                <span>Logging level:
                    <select name="min_level" id="min_level" class="form-control form-control-inline input-sm">
                        <%
                            levels = LOGGING_LEVELS.keys()
                            levels.sort(lambda x, y: cmp(LOGGING_LEVELS[x], LOGGING_LEVELS[y]))
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
            <div class="show-option pull-right">
                <!-- Filter log -->
                <span>Filter log by:
                    <select name="log_filter" id="log_filter" class="form-control form-control-inline input-sm">
                    % for log_name_filter in sorted(log_name_filters):
                        <option value="${log_name_filter}" ${'selected="selected"' if log_filter == log_name_filter else ''}>${log_name_filters[log_name_filter]}</option>
                    % endfor
                    </select>
                </span>
            </div>
            <div class="show-option pull-right">
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
            <div class="show-option pull-right">
                <!-- Search Log -->
                <span>Search log by:
                    <input type="text" name="log_search" placeholder="clear to reset" id="log_search" value="${('', log_search)[bool(log_search)]}" class="form-control form-control-inline input-sm"/>
                </span>
            </div>
        </div>
    </div> <!-- End form group -->
</div> <!-- row -->
<div class="row wide">
    <div class="col-md-12">
        <pre>${log_lines}</pre>
    </div>
</div>
</%block>

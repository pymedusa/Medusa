<%inherit file="/layouts/main.mako"/>
<%!
    import sickbeard
    from sickbeard import classes
    from sickbeard.logger import LOGGING_LEVELS
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
% if not header is UNDEFINED:
    <h1 class="header">${header}</h1>
% else:
    <h1 class="title">${title}</h1>
% endif
<div class="h2footer pull-right">
    <!-- Select Loglevel -->
    <span style="margin-left: 130px;">Logging level:
        <select name="minLevel" id="minLevel" class="form-control form-control-inline input-sm">
            <%
                levels = LOGGING_LEVELS.keys()
                levels.sort(lambda x, y: cmp(LOGGING_LEVELS[x], LOGGING_LEVELS[y]))
                if not sickbeard.DEBUG:
                    levels.remove('DEBUG')
                if not sickbeard.DBDEBUG:
                    levels.remove('DB')
            %>
        % for level in levels:
            <option value="${LOGGING_LEVELS[level]}" ${('', 'selected="selected"')[minLevel == LOGGING_LEVELS[level]]}>${level.title()}</option>
        % endfor
        </select>
    </span>
    <!-- Filter log -->
    <span>Filter log by:
        <select name="logFilter" id="logFilter" class="form-control form-control-inline input-sm">
        % for logNameFilter in sorted(logNameFilters):
            <option value="${logNameFilter}" ${'selected="selected"' if logFilter == logNameFilter else ''}>${logNameFilters[logNameFilter]}</option>
        % endfor
        </select>
    </span>
    <!-- Search Log -->
    <span>Search log by:
        <input type="text" name="logSearch" placeholder="clear to reset" id="logSearch" value="${('', logSearch)[bool(logSearch)]}" class="form-control form-control-inline input-sm"/>
    </span>
</div> <!-- End form group -->
<br />
<div class="align-left">
<pre>
${logLines}
</pre>
</div>
<br />
</%block>

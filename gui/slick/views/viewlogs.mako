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
	    <table style="width: 100%;" class="home-header">
	    <tr>
            <td nowrap>
                % if not header is UNDEFINED:
                    <h1 class="header" style="margin: 0;">${header}</h1>
                % else:
                    <h1 class="title" style="margin: 0;">${title}</h1>
                % endif
            </td>
            <td align="right">
                <div>
                    Minimum level:
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
                    Filter log by: 
                    <select name="logFilter" id="logFilter" class="form-control form-control-inline input-sm">
                    % for logNameFilter in sorted(logNameFilters):
                        <option value="${logNameFilter}" ${('', 'selected="selected"')[logFilter == logNameFilter]}>${logNameFilters[logNameFilter]}</option>
                    % endfor
                    </select>
                    Search log by:
                    <input type="text" name="logSearch" placeholder="clear to reset" id="logSearch" value="${('', logSearch)[bool(logSearch)]}" class="form-control form-control-inline input-sm" autocapitalize="off" />
                </div>
			</td>
        </tr>
        </table>
<br>
<div class="align-left">
<pre>
${logLines}
</pre>
</div>
<br>
</%block>

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
<div class="row">
	<div class="col-xs-3 col-sm-3">
	% if not header is UNDEFINED:
	    <h1 class="header">${header}</h1>
	% else:
	    <h1 class="title">${title}</h1>
	% endif
	</div>
	<div class="col-xs-12 col-sm-9 pull-right pull-xs-left log-filter">
	    <div class="form-group form-horizontal">
		    <!-- Select Loglevel -->
		    <label for="minLevel" class="col-xs-2 col-sm-2 control-label text-right hidden-xs">Logging level: </label>
		    <div class="col-xs-4 col-sm-2">
			    <select name="minLevel" id="minLevel" class="form-control">
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
		    </div>
		    <!-- Filter log -->
		    <label for="logFilter" class="col-sm-2 control-label text-right hidden-xs">Filter log by: </label>
		    <div class="col-xs-4 col-sm-2">
			    <select name="logFilter" id="logFilter" class="form-control">
			    % for logNameFilter in sorted(logNameFilters):
			        <option value="${logNameFilter}" ${'selected="selected"' if logFilter == logNameFilter else ''}>${logNameFilters[logNameFilter]}</option>
			    % endfor
			    </select>
		    </div>
		    <!-- Search Log -->
		    <label for="logFilter" class="col-xs-2 col-sm-2 control-label text-right hidden-xs">Search log by: </label>
		    <div class="col-xs-4 col-sm-2">
		       <input type="text" name="logSearch" placeholder="clear to reset" id="logSearch" value="${('', logSearch)[bool(logSearch)]}" class="form-control" autocapitalize="off" />
		    </div>
	    </div> <!-- End form group -->
	</div>
</div>
<br />
<div class="row">
<pre>
${logLines}
</pre>
</div>
<br />
</%block>

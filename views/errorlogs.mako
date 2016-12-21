<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import logger
    from medusa import classes
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
<%
    if logLevel == logger.WARNING:
        errors = classes.WarningViewer.errors
        title = 'WARNING logs'
    else:
        errors = classes.ErrorViewer.errors
        title = 'ERROR logs'
%>

<div class="row wide">
    <div class="col-md-12 wide">
        % if not header is UNDEFINED:
            <h1 class="header">${header}</h1>
        % else:
            <h1 class="title">${title}</h1>
        % endif
    </div>
</div>

<div class="row wide">
    <div class="col-md-12">
<pre>
% if errors:
% for logline in errors[:500]:
<span>${logline}</span>
% endfor
% else:
<span>There are no events to display.</span>
% endif
</pre>
</div>
</div>
</%block>

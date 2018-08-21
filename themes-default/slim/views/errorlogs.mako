<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import logger
    from medusa import classes
%>
<%block name="scripts">
<script>
window.app = {};
window.app = new Vue({
    store,
    router,
    el: '#vue-wrap'
});
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
    from mako.filters import html_escape
    if logLevel == logger.WARNING:
        errors = classes.WarningViewer.errors
        page_header = 'Warning Logs'
    else:
        errors = classes.ErrorViewer.errors
        page_header = 'Error Logs'
%>

<div class="row">
    <div class="col-md-12 wide">
        <h1 class="header">${page_header}</h1>
    </div>
</div>

<div class="row">
<div class="col-md-12">
<pre>
% if errors:
${'\n'.join([html_escape(logline) for logline in errors[:500]])}
% else:
There are no events to display.
% endif
</pre>
</div>
</div>
</%block>

<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import logger
    from medusa import classes
%>
<%block name="scripts">
<script>
window.app = {};
const startVue = () => {
    window.app = new Vue({
        el: '#vue-wrap',
        metaInfo: {
            title: 'Logs & Errors'
        },
        data() {
            return {
                header: 'Logs & Errors'
            };
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
    from mako.filters import html_escape
    if logLevel == logger.WARNING:
        errors = classes.WarningViewer.errors
        title = 'WARNING logs'
    else:
        errors = classes.ErrorViewer.errors
        title = 'ERROR logs'
%>

<div class="row">
    <div class="col-md-12 wide">
        <h1 class="header">{{header}}</h1>
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
